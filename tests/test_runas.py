"""
tests/test_runas.py

Tests de integración para el sistema de Runas (v0.42.0): CmdRunas
(estado, grabar, borrar) y _get_runas().

Antes de este archivo no existía NINGÚN test de integración para este
sistema (solo tests/test_runas_system.py, puro, sobre el catálogo) — el
mismo hueco de cobertura que dejó pasar los bugs de mascotas/percepción
en esta misma sesión. Aquí escondía el más grave de los tres: _get_runas()
comprobaba `isinstance(runas, dict)`, pero un dict guardado y releído vía
char.db.* vuelve como _SaverDict (que NO es subclase de dict — ver nota
en CLAUDE.md), así que la comprobación fallaba SIEMPRE tras el primer
guardado y el diccionario de runas grabadas se reseteaba a vacío en cada
llamada posterior a _get_runas(), incluida la que hace el propio
`runas estado` justo después de grabar. Los tests de regresión de este
archivo reproducen el bug releyendo el atributo real desde una segunda
invocación de comando (no reutilizando el dict en memoria de la primera
llamada), que es exactamente el escenario que lo disparaba.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_runas
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from features.runes.commands import CmdRunas, _get_runas


def _make_cmd(CmdClass, caller, args=""):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = []
    cmd.lhs = args
    cmd.rhs = ""
    return cmd


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        cap = self

        def _capture(m=None, **kw):
            text = m
            if text is None:
                text = kw.get("text", "")
            if isinstance(text, tuple):
                text = text[0]
            cap.msgs.append(str(text or ""))

        char.msg = _capture

    def all(self):
        return "\n".join(self.msgs)


def _preparar_para_grabar(char, slot="arma", cantidad_material=3):
    """Deja al personaje listo para grabar RUNA_VIGOR (slot None → cualquiera,
    nivel_req 1, materiales {'hierba medicinal': 3}, coste 30)."""
    arma = create_object("typeclasses.objects.Equipo", key="espada de runas", location=char)
    char.db.equipamiento = {"arma": None, "armadura": None, "accesorio": None}
    char.db.equipamiento[slot] = arma
    char.db.nivel = 1
    char.db.monedas = 100
    for _ in range(cantidad_material):
        create_object("typeclasses.objects.Object", key="hierba medicinal", location=char)
    return arma


class TestGetRunas(EvenniaTest):

    def test_primera_llamada_crea_slots_vacios(self):
        runas = _get_runas(self.char1)
        self.assertEqual(runas, {"arma": None, "armadura": None, "accesorio": None})

    def test_persiste_tras_segunda_llamada_real(self):
        primera = _get_runas(self.char1)
        primera["arma"] = "RUNA_VIGOR"
        self.char1.db.runas_equipadas = primera

        # Regresión: la llamada anterior a esta línea guarda el dict, que
        # Evennia envuelve en _SaverDict al releerlo — _get_runas() debe
        # reconocerlo como diccionario válido y NO resetearlo.
        segunda = _get_runas(self.char1)
        self.assertEqual(segunda["arma"], "RUNA_VIGOR")


class TestCmdRunasGrabarYPersistencia(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _runas(self, args):
        cmd = _make_cmd(CmdRunas, self.char1, args)
        cmd.func()

    def test_grabar_runa_confirma(self):
        _preparar_para_grabar(self.char1)
        self._runas("grabar RUNA_VIGOR en arma")
        self.assertIn("Runa grabada", self.cap.all())

    def test_grabar_runa_consume_monedas(self):
        _preparar_para_grabar(self.char1)
        self._runas("grabar RUNA_VIGOR en arma")
        self.assertEqual(self.char1.db.monedas, 70)

    def test_grabar_runa_consume_materiales(self):
        _preparar_para_grabar(self.char1, cantidad_material=3)
        self._runas("grabar RUNA_VIGOR en arma")
        restantes = [o for o in self.char1.contents if o.key == "hierba medicinal"]
        self.assertEqual(len(restantes), 0)

    def test_runa_grabada_sigue_presente_en_llamada_posterior(self):
        """Regresión directa del bug: grabar, luego pedir 'estado' en un
        comando NUEVO (segunda invocación real) — antes del fix, el
        segundo _get_runas() reseteaba el slot a None."""
        _preparar_para_grabar(self.char1)
        self._runas("grabar RUNA_VIGOR en arma")
        self.cap.msgs.clear()

        self._runas("estado")

        texto = self.cap.all()
        self.assertIn("Runa de Vigor", texto)
        linea_arma = next(l for l in texto.splitlines() if "Arma:" in l)
        self.assertNotIn("vacío", linea_arma)

    def test_runa_grabada_persiste_en_el_atributo_real(self):
        _preparar_para_grabar(self.char1)
        self._runas("grabar RUNA_VIGOR en arma")
        # Releer el atributo desde cero, como haría cualquier comando futuro.
        runas = _get_runas(self.char1)
        self.assertEqual(runas["arma"], "RUNA_VIGOR")

    def test_grabar_dos_runas_en_slots_distintos_conserva_ambas(self):
        _preparar_para_grabar(self.char1, slot="arma", cantidad_material=3)
        self._runas("grabar RUNA_VIGOR en arma")

        armadura = create_object("typeclasses.objects.Equipo", key="peto de runas", location=self.char1)
        self.char1.db.equipamiento["armadura"] = armadura
        self.char1.db.monedas = 100
        for _ in range(3):
            create_object("typeclasses.objects.Object", key="mineral de hierro", location=self.char1)
        self.char1.db.nivel = 3

        self._runas("grabar RUNA_ESCUDO en armadura")

        runas = _get_runas(self.char1)
        self.assertEqual(runas["arma"], "RUNA_VIGOR")
        self.assertEqual(runas["armadura"], "RUNA_ESCUDO")


class TestCmdRunasBorrar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _runas(self, args):
        cmd = _make_cmd(CmdRunas, self.char1, args)
        cmd.func()

    def test_borrar_slot_vacio_informa(self):
        _preparar_para_grabar(self.char1)
        self._runas("borrar arma")
        self.assertIn("no tienes", self.cap.all().lower())

    def test_borrar_runa_grabada_la_elimina(self):
        _preparar_para_grabar(self.char1)
        self._runas("grabar RUNA_VIGOR en arma")
        self._runas("borrar arma")
        runas = _get_runas(self.char1)
        self.assertIsNone(runas["arma"])


if __name__ == "__main__":
    import unittest
    unittest.main()
