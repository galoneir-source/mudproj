"""
tests/test_coleccionables.py

Tests de integración para el sistema de Coleccionables: CmdBuscar (cooldown,
gating por nivel/zona/requiere_kill vía bestiario real) y CmdColeccion.

No existía ningún test de integración para este sistema (solo
tests/test_collectibles_system.py, puro sobre el catálogo) — el mismo hueco
de cobertura visto en mascotas/monturas/profesiones/bestiario esta sesión.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_coleccionables
"""
from evennia.utils.test_resources import EvenniaTest

from features.collectibles.commands import CmdBuscar, CmdColeccion


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


def _preparar_char(char, nivel=5):
    char.db.tesoros_encontrados = []
    char.db.bestiary = {}
    char.db.nivel = nivel
    char.db.monedas = 0
    char.ndb.buscar_ultimo = None


class TestCmdBuscarSinRequisitos(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)
        self.char1.location = self.room1

    def _buscar(self, args=""):
        cmd = _make_cmd(CmdBuscar, self.char1, args)
        cmd.func()

    def test_zona_sin_tesoro_informa(self):
        self.room1.db.zona = "boca_mina"
        self._buscar()
        self.assertIn("no encuentras nada especial", self.cap.all())

    def test_zona_con_tesoro_lo_encuentra(self):
        self.room1.db.zona = "plaza_ciudad"
        self._buscar()
        self.assertIn("moneda_antigua", self.char1.db.tesoros_encontrados)
        self.assertIn("Tesoro hallado", self.cap.all())

    def test_encontrarlo_da_monedas(self):
        self.room1.db.zona = "plaza_ciudad"
        self._buscar()
        self.assertEqual(self.char1.db.monedas, 60)

    def test_buscar_dos_veces_la_segunda_ya_encontrado(self):
        self.room1.db.zona = "plaza_ciudad"
        self._buscar()
        self.char1.ndb.buscar_ultimo = None  # saltar cooldown para el test
        self.cap.msgs.clear()
        self._buscar()
        self.assertIn("Ya encontraste", self.cap.all())
        self.assertEqual(self.char1.db.monedas, 60)  # no se duplica la recompensa

    def test_cooldown_bloquea_busqueda_inmediata(self):
        self.room1.db.zona = "plaza_ciudad"
        self._buscar()
        self.cap.msgs.clear()
        self.room1.db.zona = "taberna"
        self._buscar()
        self.assertIn("esperar", self.cap.all())
        self.assertNotIn("pergamino_taberna", self.char1.db.tesoros_encontrados)

    def test_nivel_insuficiente_bloquea(self):
        self.char1.db.nivel = 1
        self.room1.db.zona = "sala_tumbas"  # nivel_min 4
        self._buscar()
        self.assertIn("Necesitas nivel", self.cap.all())
        self.assertEqual(self.char1.db.tesoros_encontrados, [])


class TestCmdBuscarPistas(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)
        self.char1.location = self.room1

    def _buscar(self, args=""):
        cmd = _make_cmd(CmdBuscar, self.char1, args)
        cmd.func()

    def test_pistas_no_consume_cooldown(self):
        self._buscar("pistas")
        self.assertIsNone(self.char1.ndb.buscar_ultimo)

    def test_pistas_lista_tesoros_pendientes(self):
        self._buscar("pistas")
        self.assertIn("Pistas", self.cap.all())


class TestCmdBuscarRequiereKill(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1, nivel=10)
        self.cap = _MsgCapture(self.char1)
        self.char1.location = self.room1
        self.room1.db.zona = "guarida_troll"  # corona_lodo, requiere_kill=TROLL

    def _buscar(self, args=""):
        cmd = _make_cmd(CmdBuscar, self.char1, args)
        cmd.func()

    def test_sin_haber_matado_al_guardian_bloquea(self):
        self._buscar()
        self.assertIn("Debes haber derrotado", self.cap.all())
        self.assertEqual(self.char1.db.tesoros_encontrados, [])

    def test_con_bestiary_registrado_permite_reclamar(self):
        self.char1.db.bestiary = {"TROLL": {"kills": 1, "primera_vez": 100}}
        self._buscar()
        self.assertIn("corona_lodo", self.char1.db.tesoros_encontrados)

    def test_bestiary_con_cero_kills_sigue_bloqueando(self):
        self.char1.db.bestiary = {"TROLL": {"kills": 0, "primera_vez": 100}}
        self._buscar()
        self.assertEqual(self.char1.db.tesoros_encontrados, [])


class TestCmdColeccion(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _coleccion(self, args=""):
        cmd = _make_cmd(CmdColeccion, self.char1, args)
        cmd.func()

    def test_sin_tesoros_muestra_cero(self):
        self._coleccion()
        self.assertIn("0/", self.cap.all())

    def test_con_tesoro_lo_refleja(self):
        self.char1.db.tesoros_encontrados = ["moneda_antigua"]
        self._coleccion()
        self.assertIn("1/", self.cap.all())
        self.assertIn("Moneda Antigua", self.cap.all())

    def test_pistas_via_coleccion(self):
        self._coleccion("pistas")
        self.assertIn("Pistas", self.cap.all())


class TestDespachoRealCmdSet(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.char1.location = self.room1
        self.room1.db.zona = "plaza_ciudad"
        self.cap = _MsgCapture(self.char1)

    def test_comando_buscar_real_encuentra_tesoro(self):
        self.char1.execute_cmd("buscar")
        self.assertIn("moneda_antigua", self.char1.db.tesoros_encontrados)

    def test_comando_coleccion_real_muestra_progreso(self):
        self.char1.execute_cmd("coleccion")
        self.assertIn("Colección", self.cap.all())


if __name__ == "__main__":
    import unittest
    unittest.main()
