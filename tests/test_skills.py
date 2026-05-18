"""
tests/test_skills.py

Tests de integración para features/skills/commands.py.
Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test .
"""
from evennia.utils.test_resources import EvenniaTest

from systems.skills.trees import HABILIDADES, HABILIDADES_INICIALES
from systems.skills.engine import puntos_disponibles, puntos_gastados
from features.skills.commands import CmdHabilidades, CmdAprender


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


class SkillTestBase(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.jugador = self.char1
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES)
        self.jugador.db.nivel = 1
        self.msgs = []
        self.jugador.msg = lambda m, **kw: self.msgs.append(str(m))

    def _ultimo(self):
        return self.msgs[-1] if self.msgs else ""

    def _todos(self):
        return "\n".join(self.msgs)


# --------------------------------------------------------------------------- #
#  CmdHabilidades
# --------------------------------------------------------------------------- #

class TestCmdHabilidades(SkillTestBase):

    def test_muestra_arbol(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador)
        cmd.func()
        salida = self._todos()
        self.assertIn("Árbol de Habilidades", salida)
        self.assertIn("GUERRERO", salida)
        self.assertIn("EXPLORADOR", salida)
        self.assertIn("MAGO", salida)

    def test_muestra_puntos_disponibles(self):
        self.jugador.db.nivel = 3
        cmd = _make_cmd(CmdHabilidades, self.jugador)
        cmd.func()
        self.assertIn("Puntos disponibles: 2", self._todos())

    def test_habilidades_iniciales_marcadas(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador)
        cmd.func()
        salida = self._todos()
        self.assertIn("Golpe Fuerte", salida)
        self.assertIn("Golpe Rápido", salida)

    def test_rama_guerrero(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="guerrero")
        cmd.func()
        salida = self._todos()
        self.assertIn("GUERRERO", salida)
        self.assertIn("Golpe Fuerte", salida)
        self.assertIn("Embestida", salida)

    def test_rama_explorador(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="explorador")
        cmd.func()
        self.assertIn("EXPLORADOR", self._todos())

    def test_rama_mago(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="mago")
        cmd.func()
        self.assertIn("MAGO", self._todos())

    def test_detalle_habilidad(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="embestida")
        cmd.func()
        salida = self._todos()
        self.assertIn("Embestida", salida)
        self.assertIn("Guerrero", salida)

    def test_habilidad_inexistente_informa(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="xyz_fantasma")
        cmd.func()
        self.assertIn("No se encontró", self._todos())

    def test_habilidad_con_espacio(self):
        cmd = _make_cmd(CmdHabilidades, self.jugador, args="golpe fuerte")
        cmd.func()
        self.assertIn("Golpe Fuerte", self._todos())


# --------------------------------------------------------------------------- #
#  CmdAprender
# --------------------------------------------------------------------------- #

class TestCmdAprender(SkillTestBase):

    def test_sin_args_pide_argumento(self):
        cmd = _make_cmd(CmdAprender, self.jugador)
        cmd.func()
        self.assertIn("¿Qué habilidad", self._todos())

    def test_habilidad_inexistente(self):
        cmd = _make_cmd(CmdAprender, self.jugador, args="xyz_no_existe")
        cmd.func()
        self.assertIn("No se encontró", self._todos())

    def test_ya_conocida(self):
        cmd = _make_cmd(CmdAprender, self.jugador, args="golpe fuerte")
        cmd.func()
        self.assertIn("Ya conoces", self._todos())

    def test_nivel_insuficiente(self):
        self.jugador.db.nivel = 1
        cmd = _make_cmd(CmdAprender, self.jugador, args="embestida")
        cmd.func()
        self.assertIn("Necesitas nivel", self._todos())

    def test_sin_puntos(self):
        # nivel 2 = 1 punto; gastar en embestida; sin puntos para corte
        self.jugador.db.nivel = 2
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES) + ["embestida"]
        cmd = _make_cmd(CmdAprender, self.jugador, args="corte")
        cmd.func()
        self.assertIn("Puntos insuficientes", self._todos())

    def test_requisito_faltante(self):
        self.jugador.db.nivel = 5
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES)
        cmd = _make_cmd(CmdAprender, self.jugador, args="embestida")
        # embestida req: golpe_fuerte (que tenemos), OK
        # Pero corte req: golpe_rapido, OK también. Probemos escudo_fe req: embestida
        cmd2 = _make_cmd(CmdAprender, self.jugador, args="escudo de fe")
        cmd2.func()
        self.assertIn("Requiere aprender primero", self._todos())

    def test_aprende_embestida(self):
        self.jugador.db.nivel = 3
        cmd = _make_cmd(CmdAprender, self.jugador, args="embestida")
        cmd.func()
        salida = self._todos()
        self.assertIn("¡Has aprendido Embestida!", salida)
        self.assertIn("embestida", self.jugador.db.habilidades_desbloqueadas)

    def test_aprende_corte(self):
        self.jugador.db.nivel = 3
        cmd = _make_cmd(CmdAprender, self.jugador, args="corte")
        cmd.func()
        self.assertIn("corte", self.jugador.db.habilidades_desbloqueadas)

    def test_aprende_dardo_magico(self):
        self.jugador.db.nivel = 2
        cmd = _make_cmd(CmdAprender, self.jugador, args="dardo magico")
        cmd.func()
        self.assertIn("dardo_magico", self.jugador.db.habilidades_desbloqueadas)

    def test_pasiva_aplica_defensa(self):
        self.jugador.db.nivel = 5
        self.jugador.db.defensa = 5
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES) + ["embestida"]
        cmd = _make_cmd(CmdAprender, self.jugador, args="escudo de fe")
        cmd.func()
        self.assertIn("escudo_fe", self.jugador.db.habilidades_desbloqueadas)
        self.assertEqual(self.jugador.db.defensa, 7)  # +2 de escudo_fe

    def test_pasiva_escudo_arcano_aplica_defensa(self):
        self.jugador.db.nivel = 5
        self.jugador.db.defensa = 5
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES) + ["dardo_magico"]
        cmd = _make_cmd(CmdAprender, self.jugador, args="escudo arcano")
        cmd.func()
        self.assertIn("escudo_arcano", self.jugador.db.habilidades_desbloqueadas)
        self.assertEqual(self.jugador.db.defensa, 8)  # +3 de escudo_arcano

    def test_puntos_se_gastan(self):
        self.jugador.db.nivel = 5
        inicial = set(HABILIDADES_INICIALES)
        # Gastamos 1 punto en embestida → quedan 3 de 4
        cmd = _make_cmd(CmdAprender, self.jugador, args="embestida")
        cmd.func()
        desbloqueadas = set(self.jugador.db.habilidades_desbloqueadas)
        gastados = puntos_gastados(desbloqueadas)
        disponibles = puntos_disponibles(5, gastados)
        self.assertEqual(disponibles, 3)

    def test_cadena_guerrero(self):
        self.jugador.db.nivel = 10
        self.jugador.db.defensa = 5
        for hab in ("embestida", "escudo de fe", "golpe maestro"):
            self.msgs.clear()
            cmd = _make_cmd(CmdAprender, self.jugador, args=hab)
            cmd.func()
            self.assertNotIn("No puedes", self._todos(), f"falló al aprender '{hab}'")
        self.assertIn("golpe_maestro", self.jugador.db.habilidades_desbloqueadas)

    def test_cadena_mago(self):
        self.jugador.db.nivel = 10
        self.jugador.db.defensa = 5
        for hab in ("dardo magico", "escudo arcano"):
            self.msgs.clear()
            cmd = _make_cmd(CmdAprender, self.jugador, args=hab)
            cmd.func()
            self.assertNotIn("No puedes", self._todos(), f"falló al aprender '{hab}'")

    def test_aprende_por_nombre_display(self):
        self.jugador.db.nivel = 3
        cmd = _make_cmd(CmdAprender, self.jugador, args="Golpe Rápido")
        cmd.func()
        self.assertIn("Ya conoces", self._todos())


# --------------------------------------------------------------------------- #
#  Integración: habilidades_desbloqueadas → CmdHabilidad (combate)
# --------------------------------------------------------------------------- #

class TestHabilidadEnCombate(SkillTestBase):

    def test_no_puede_usar_habilidad_no_aprendida(self):
        from features.combat.commands import CmdHabilidad
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES)

        cmd = CmdHabilidad()
        cmd.caller = self.jugador
        cmd.args = "embestida goblin"
        cmd.cmdstring = "habilidad"
        cmd.session = None
        cmd.obj = self.jugador
        cmd.raw_string = "habilidad embestida goblin"
        cmd.switches = []
        cmd.lhs = "embestida goblin"
        cmd.rhs = ""
        cmd.func()
        self.assertIn("No conoces", self._todos())

    def test_puede_usar_habilidad_aprendida(self):
        from features.combat.commands import CmdHabilidad
        self.jugador.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES) + ["embestida"]

        cmd = CmdHabilidad()
        cmd.caller = self.jugador
        cmd.args = "embestida objetivoinexistente"
        cmd.cmdstring = "habilidad"
        cmd.session = None
        cmd.obj = self.jugador
        cmd.raw_string = "habilidad embestida objetivoinexistente"
        cmd.switches = []
        cmd.lhs = "embestida objetivoinexistente"
        cmd.rhs = ""
        cmd.func()
        # No debería decir "No conoces"; puede fallar por objetivo no encontrado
        self.assertNotIn("No conoces", self._todos())
