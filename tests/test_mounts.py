"""
tests/test_mounts.py

Tests de integración para el sistema de Monturas: CmdMontura (estado,
lista, comprar, invocar, desmontar) y el bonus pasivo en combate.

No existía ningún test de integración para este sistema (solo
tests/test_mounts_system.py, puro sobre el catálogo) — el mismo hueco de
cobertura visto en mascotas/percepción/runas esta sesión.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_mounts
"""
from evennia.utils.test_resources import EvenniaTest

from features.mounts.commands import CmdMontura


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


def _preparar_char(char, monedas=500, nivel=5):
    char.db.monturas = []
    char.db.montura_activa = None
    char.db.monedas = monedas
    char.db.nivel = nivel
    char.db.reputacion = {}
    char.db.jefes_mundo_derrotados = {}


class TestCmdMonturaEstado(EvenniaTest):

    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _montura(self, args=""):
        cmd = _make_cmd(CmdMontura, self.char1, args)
        cmd.func()

    def test_sin_monturas_informa(self):
        self._montura("")
        self.assertIn("No posees ninguna montura", self.cap.all())

    def test_no_montado_informa(self):
        self._montura("")
        self.assertIn("No estás montado", self.cap.all())


class TestCmdMonturaComprar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _montura(self, args=""):
        cmd = _make_cmd(CmdMontura, self.char1, args)
        cmd.func()

    def test_comprar_monedas_suficientes(self):
        self._montura("comprar Poni Viejo")
        self.assertIn("poni_viejo", list(self.char1.db.monturas or []))

    def test_comprar_descuenta_monedas(self):
        self._montura("comprar Poni Viejo")
        self.assertEqual(self.char1.db.monedas, 500 - 200)

    def test_comprar_sin_monedas_falla(self):
        self.char1.db.monedas = 0
        self._montura("comprar Poni Viejo")
        self.assertNotIn("poni_viejo", list(self.char1.db.monturas or []))
        self.assertIn("No puedes comprar", self.cap.all())

    def test_comprar_nivel_insuficiente_falla(self):
        self.char1.db.nivel = 1
        self._montura("comprar Corcel Oscuro")  # nivel_min 8
        self.assertNotIn("corcel_oscuro", list(self.char1.db.monturas or []))

    def test_comprar_ya_poseida_falla(self):
        self._montura("comprar Poni Viejo")
        monedas_tras_primera = self.char1.db.monedas
        self._montura("comprar Poni Viejo")
        self.assertEqual(self.char1.db.monedas, monedas_tras_primera)

    def test_comprar_nombre_ambiguo_avisa(self):
        # "corcel" coincide con "Corcel de Guerra" y "Corcel Oscuro"
        self._montura("comprar corcel")
        self.assertIn("específico", self.cap.all().lower())

    def test_comprar_dragon_gratis_requiere_jefe(self):
        self._montura("comprar Dragón de Ceniza")
        self.assertNotIn("dragon_ceniza", list(self.char1.db.monturas or []))
        self.char1.db.jefes_mundo_derrotados = {"DRAGON_CENIZA": 1}
        self._montura("comprar Dragón de Ceniza")
        self.assertIn("dragon_ceniza", list(self.char1.db.monturas or []))


class TestCmdMonturaInvocarYDesmontar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.char1.db.monturas = ["poni_viejo"]
        self.cap = _MsgCapture(self.char1)

    def _montura(self, args=""):
        cmd = _make_cmd(CmdMontura, self.char1, args)
        cmd.func()

    def test_invocar_montura_poseida(self):
        self._montura("invocar Poni Viejo")
        self.assertEqual(self.char1.db.montura_activa, "poni_viejo")

    def test_invocar_montura_no_poseida_falla(self):
        self._montura("invocar Corcel de Guerra")
        self.assertIsNone(self.char1.db.montura_activa)

    def test_invocar_dos_veces_informa(self):
        self._montura("invocar Poni Viejo")
        self.cap.msgs.clear()
        self._montura("invocar Poni Viejo")
        self.assertIn("Ya estás montado", self.cap.all())

    def test_desmontar_limpia_montura_activa(self):
        self._montura("invocar Poni Viejo")
        self._montura("desmontar")
        self.assertIsNone(self.char1.db.montura_activa)

    def test_desmontar_sin_montar_informa(self):
        self._montura("desmontar")
        self.assertIn("No estás montado", self.cap.all())

    def test_nombre_de_montura_sin_subcomando_invoca(self):
        """"montura <nombre>" sin escribir "invocar" también monta (fallback)."""
        self._montura("Poni Viejo")
        self.assertEqual(self.char1.db.montura_activa, "poni_viejo")


class TestBonusMonturaEnCombate(EvenniaTest):
    """El bonus pasivo de la montura activa debe reflejarse en _get_stats()."""

    def setUp(self):
        super().setUp()
        self.char1.db.destreza = 10
        self.char1.db.montura_activa = None

    def test_sin_montura_no_hay_bonus(self):
        from features.combat.handler import _get_stats
        stats = _get_stats(self.char1)
        self.assertEqual(stats["destreza"], 10)

    def test_con_lobo_cazador_suma_destreza(self):
        from features.combat.handler import _get_stats
        self.char1.db.montura_activa = "lobo_cazador"
        stats = _get_stats(self.char1)
        self.assertEqual(stats["destreza"], 13)  # +3 DES


if __name__ == "__main__":
    import unittest
    unittest.main()
