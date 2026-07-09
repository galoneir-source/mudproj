"""
tests/test_subclases_system.py

Tests de integración del sistema de subclases con Evennia.
Requieren Django configurado: usar `evennia test tests.test_subclases_system`
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import Command

from systems.subclasses.subclasses import SUBCLASES, NIVEL_MIN_SUBCLASE
from features.subclasses.commands import CmdSubclase


# ─── Helpers ─────────────────────────────────────────────────────────────────

class _MsgCapture:
    def __init__(self, obj):
        self._msgs = []
        obj.msg = lambda text, **kw: self._msgs.append(str(text))

    def all(self):
        return "\n".join(self._msgs)

    def clear(self):
        self._msgs.clear()


def _init_char(char, clase=None, subclase=None, nivel=5):
    from systems.combat.engine import STAT_DEFAULTS
    from systems.skills.trees import HABILIDADES_INICIALES
    for key, val in STAT_DEFAULTS.items():
        if getattr(char.db, key, None) is None:
            setattr(char.db, key, val)
    char.db.nivel = nivel
    char.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES)
    char.db.clase = clase
    char.db.subclase = subclase
    char.db.logros = []
    char.db.titulo_activo = None
    char.db.kills_totales = 0
    char.db.jefes_derrotados = []
    char.db.objetos_crafteados = 0
    char.db.encantamiento_max = 0
    char.db.banco_usado = False


def _make_cmd(cmd_class, caller, args=""):
    cmd = cmd_class()
    cmd.caller = caller
    cmd.args = " " + args if args else ""
    cmd.cmdstring = cmd_class.key
    cmd.raw_string = cmd_class.key + (" " + args if args else "")
    return cmd


# ─── CmdSubclase: visualización ──────────────────────────────────────────────

class TestCmdSubclaseVista(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, clase="guerrero", nivel=5)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_muestra_subclases_disponibles(self):
        cmd = _make_cmd(CmdSubclase, self.char1)
        cmd.func()
        output = self.cap.all().upper()
        self.assertIn("PALADÍN", output)
        self.assertIn("BERSERKER", output)

    def test_sin_clase_muestra_mensaje(self):
        self.char1.db.clase = None
        cmd = _make_cmd(CmdSubclase, self.char1)
        cmd.func()
        self.assertIn("clase", self.cap.all().lower())

    def test_nivel_bajo_muestra_aviso(self):
        self.char1.db.nivel = 4
        cmd = _make_cmd(CmdSubclase, self.char1)
        cmd.func()
        self.assertIn(str(NIVEL_MIN_SUBCLASE), self.cap.all())

    def test_subclase_activa_mostrada(self):
        self.char1.db.subclase = "paladin"
        cmd = _make_cmd(CmdSubclase, self.char1)
        cmd.func()
        self.assertIn("ACTUAL", self.cap.all())

    def test_muestra_bonuses(self):
        cmd = _make_cmd(CmdSubclase, self.char1)
        cmd.func()
        output = self.cap.all().upper()
        self.assertIn("DEF", output)  # Paladín: +2 DEF (mostrado como "Def")


# ─── CmdSubclase: elección ───────────────────────────────────────────────────

class TestCmdSubclaseEleccion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, clase="guerrero", nivel=5)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_elige_paladin(self):
        cmd = _make_cmd(CmdSubclase, self.char1, "paladin")
        cmd.func()
        self.assertEqual(self.char1.db.subclase, "paladin")

    def test_aplica_bonuses_paladin(self):
        def_antes = self.char1.db.defensa or 5
        cmd = _make_cmd(CmdSubclase, self.char1, "paladin")
        cmd.func()
        self.assertEqual(self.char1.db.defensa, def_antes + 2)
        self.assertEqual(self.char1.db.hp_max, (self.char1.db.hp_max or 100))

    def test_aplica_bonuses_berserker(self):
        fuerza_antes = self.char1.db.fuerza or 10
        cmd = _make_cmd(CmdSubclase, self.char1, "berserker")
        cmd.func()
        self.assertEqual(self.char1.db.fuerza, fuerza_antes + 4)

    def test_rechaza_nivel_insuficiente(self):
        self.char1.db.nivel = 4
        cmd = _make_cmd(CmdSubclase, self.char1, "paladin")
        cmd.func()
        self.assertIsNone(self.char1.db.subclase)

    def test_rechaza_sin_clase(self):
        self.char1.db.clase = None
        cmd = _make_cmd(CmdSubclase, self.char1, "paladin")
        cmd.func()
        self.assertIsNone(self.char1.db.subclase)

    def test_rechaza_subclase_incorrecta_para_clase(self):
        # guerrero intenta asesino (requiere explorador)
        cmd = _make_cmd(CmdSubclase, self.char1, "asesino")
        cmd.func()
        self.assertIsNone(self.char1.db.subclase)

    def test_no_puede_cambiar_subclase(self):
        self.char1.db.subclase = "paladin"
        cmd = _make_cmd(CmdSubclase, self.char1, "berserker")
        cmd.func()
        self.assertEqual(self.char1.db.subclase, "paladin")

    def test_subclase_inexistente_error(self):
        cmd = _make_cmd(CmdSubclase, self.char1, "druida")
        cmd.func()
        self.assertIsNone(self.char1.db.subclase)

    def test_explorador_elige_asesino(self):
        self.char1.db.clase = "explorador"
        cmd = _make_cmd(CmdSubclase, self.char1, "asesino")
        cmd.func()
        self.assertEqual(self.char1.db.subclase, "asesino")

    def test_mago_elige_hechicero(self):
        self.char1.db.clase = "mago"
        cmd = _make_cmd(CmdSubclase, self.char1, "hechicero")
        cmd.func()
        self.assertEqual(self.char1.db.subclase, "hechicero")

    def test_mensaje_confirmacion(self):
        cmd = _make_cmd(CmdSubclase, self.char1, "paladin")
        cmd.func()
        self.assertIn("Paladín", self.cap.all())


# ─── Aprender habilidades de subclase ────────────────────────────────────────

class TestAprenderHabilidadesSubclase(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, clase="guerrero", subclase="paladin", nivel=5)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _aprender(self, habilidad):
        from features.skills.commands import CmdAprender
        cmd = _make_cmd(CmdAprender, self.char1, habilidad)
        cmd.func()

    def test_aprende_escudo_divino(self):
        self._aprender("escudo divino")
        self.assertIn("escudo_divino", list(self.char1.db.habilidades_desbloqueadas))

    def test_escudo_divino_aplica_defensa(self):
        def_antes = self.char1.db.defensa or 5
        self._aprender("escudo divino")
        self.assertEqual(self.char1.db.defensa, def_antes + 3)

    def test_sin_subclase_no_aprende_pasiva(self):
        self.char1.db.subclase = None
        self._aprender("escudo divino")
        self.assertNotIn("escudo_divino", list(self.char1.db.habilidades_desbloqueadas))
        self.assertIn("Paladín", self.cap.all())

    def test_subclase_incorrecta_no_aprende(self):
        self.char1.db.subclase = "berserker"
        self._aprender("escudo divino")
        self.assertNotIn("escudo_divino", list(self.char1.db.habilidades_desbloqueadas))

    def test_activa_requiere_pasiva_primero(self):
        self._aprender("golpe sagrado")
        self.assertNotIn("golpe_sagrado", list(self.char1.db.habilidades_desbloqueadas))

    def test_activa_con_pasiva_aprendida(self):
        self.char1.db.nivel = 8
        self._aprender("escudo divino")
        self.cap.clear()
        self._aprender("golpe sagrado")
        self.assertIn("golpe_sagrado", list(self.char1.db.habilidades_desbloqueadas))

    def test_furia_berserker_aplica_fuerza(self):
        _init_char(self.char1, clase="guerrero", subclase="berserker", nivel=5)
        self.cap.clear()
        fuerza_antes = self.char1.db.fuerza or 10
        self._aprender("furia berserker")
        self.assertEqual(self.char1.db.fuerza, fuerza_antes + 3)

    def test_instinto_cazador_aplica_dos_stats(self):
        _init_char(self.char1, clase="explorador", subclase="cazador", nivel=5)
        self.cap.clear()
        des_antes = self.char1.db.destreza or 10
        con_antes = self.char1.db.constitucion or 10
        self._aprender("instinto cazador")
        self.assertEqual(self.char1.db.destreza, des_antes + 1)
        self.assertEqual(self.char1.db.constitucion, con_antes + 1)


# ─── Visualización del árbol con subclase ────────────────────────────────────

class TestArbolHabilidadesConSubclase(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, clase="guerrero", subclase="paladin", nivel=5)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _habilidades(self, args=""):
        from features.skills.commands import CmdHabilidades
        cmd = _make_cmd(CmdHabilidades, self.char1, args)
        cmd.func()

    def test_arbol_muestra_seccion_subclase(self):
        self._habilidades()
        self.assertIn("PALADÍN", self.cap.all().upper())

    def test_arbol_sin_subclase_muestra_prompt(self):
        self.char1.db.subclase = None
        self._habilidades()
        output = self.cap.all()
        self.assertIn("SUBCLASE", output.upper())

    def test_filtro_por_nombre_subclase(self):
        self._habilidades("paladin")
        output = self.cap.all()
        self.assertIn("Escudo Divino", output)
        self.assertIn("Golpe Sagrado", output)

    def test_habilidad_subclase_bloqueada_sin_subclase(self):
        self.char1.db.subclase = None
        self._habilidades()
        output = self.cap.all()
        self.assertIn("[S]", output)

    def test_habilidad_subclase_disponible_con_subclase(self):
        # La leyenda al pie ("[S]=subclase") siempre menciona el marcador
        # cuando el personaje tiene clase; lo que se comprueba aquí es que
        # ninguna fila de habilidad lo use realmente.
        self._habilidades()
        lineas = [l for l in self.cap.all().splitlines() if "=subclase" not in l]
        self.assertNotIn("[S]", "\n".join(lineas))


if __name__ == "__main__":
    unittest.main()
