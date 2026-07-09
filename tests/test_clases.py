"""
tests/test_clases.py

Tests de integración Evennia para el sistema de clases (v0.28.0).
Cubre: elegir clase, restricciones, bonuses, perfil, árbol de habilidades.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_clases
"""
from evennia.utils.test_resources import EvenniaTest

from features.classes.commands import CmdClase
from features.skills.commands import CmdHabilidades, CmdAprender
from commands.general_commands import CmdPerfil
from systems.classes.classes import CLASES
from systems.combat.engine import STAT_DEFAULTS


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
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)

    def last(self):
        return self.msgs[-1] if self.msgs else ""


def _init_char(char):
    char.db.clase = None
    char.db.nivel = 1
    char.db.fuerza = STAT_DEFAULTS["fuerza"]
    char.db.destreza = STAT_DEFAULTS["destreza"]
    char.db.constitucion = STAT_DEFAULTS["constitucion"]
    char.db.inteligencia = STAT_DEFAULTS["inteligencia"]
    char.db.defensa = STAT_DEFAULTS["defensa"]
    char.db.hp = STAT_DEFAULTS["hp"]
    char.db.hp_max = STAT_DEFAULTS["hp_max"]
    char.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido"]
    char.db.logros = []
    char.db.titulo_activo = None


# ---------------------------------------------------------------------------
# TestClaseSeleccion
# ---------------------------------------------------------------------------

class TestClaseSeleccion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def _run_clase(self, args=""):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdClase, self.char1, args)
        cmd.func()
        return cap

    # --- Mostrar clases ---

    def test_clase_sin_args_muestra_clases(self):
        cap = self._run_clase()
        self.assertIn("Clases de Personaje", cap.all())

    def test_clase_sin_args_muestra_tres_opciones(self):
        cap = self._run_clase()
        output = cap.all()
        self.assertIn("GUERRERO", output)
        self.assertIn("EXPLORADOR", output)
        self.assertIn("MAGO", output)

    def test_clase_sin_args_sin_clase_muestra_aviso(self):
        cap = self._run_clase()
        self.assertIn("no has elegido", cap.all().lower())

    # --- Elegir clase guerrero ---

    def test_elegir_guerrero_asigna_clase(self):
        self._run_clase("guerrero")
        self.assertEqual(self.char1.db.clase, "guerrero")

    def test_elegir_guerrero_aplica_bonus_fuerza(self):
        fuerza_base = self.char1.db.fuerza
        self._run_clase("guerrero")
        self.assertEqual(self.char1.db.fuerza, fuerza_base + 3)

    def test_elegir_guerrero_aplica_bonus_constitucion(self):
        con_base = self.char1.db.constitucion
        self._run_clase("guerrero")
        self.assertEqual(self.char1.db.constitucion, con_base + 2)

    def test_elegir_guerrero_aplica_bonus_defensa(self):
        def_base = self.char1.db.defensa
        self._run_clase("guerrero")
        self.assertEqual(self.char1.db.defensa, def_base + 1)

    def test_elegir_guerrero_aplica_bonus_hp_max(self):
        hp_max_base = self.char1.db.hp_max
        self._run_clase("guerrero")
        self.assertEqual(self.char1.db.hp_max, hp_max_base + 20)

    def test_elegir_guerrero_muestra_confirmacion(self):
        cap = self._run_clase("guerrero")
        self.assertIn("Guerrero", cap.all())

    # --- Elegir clase explorador ---

    def test_elegir_explorador_asigna_clase(self):
        self._run_clase("explorador")
        self.assertEqual(self.char1.db.clase, "explorador")

    def test_elegir_explorador_aplica_bonus_destreza(self):
        des_base = self.char1.db.destreza
        self._run_clase("explorador")
        self.assertEqual(self.char1.db.destreza, des_base + 4)

    def test_elegir_explorador_aplica_bonus_constitucion(self):
        con_base = self.char1.db.constitucion
        self._run_clase("explorador")
        self.assertEqual(self.char1.db.constitucion, con_base + 1)

    def test_elegir_explorador_no_cambia_fuerza(self):
        fuerza_base = self.char1.db.fuerza
        self._run_clase("explorador")
        self.assertEqual(self.char1.db.fuerza, fuerza_base)

    # --- Elegir clase mago ---

    def test_elegir_mago_asigna_clase(self):
        self._run_clase("mago")
        self.assertEqual(self.char1.db.clase, "mago")

    def test_elegir_mago_aplica_bonus_inteligencia(self):
        int_base = self.char1.db.inteligencia
        self._run_clase("mago")
        self.assertEqual(self.char1.db.inteligencia, int_base + 5)

    def test_elegir_mago_no_cambia_fuerza(self):
        fuerza_base = self.char1.db.fuerza
        self._run_clase("mago")
        self.assertEqual(self.char1.db.fuerza, fuerza_base)

    # --- Restricciones ---

    def test_no_puede_elegir_clase_dos_veces(self):
        self._run_clase("guerrero")
        self._run_clase("explorador")
        self.assertEqual(self.char1.db.clase, "guerrero")

    def test_no_puede_elegir_clase_dos_veces_mensaje_error(self):
        self._run_clase("guerrero")
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdClase, self.char1, "explorador")
        cmd.func()
        self.assertIn("Guerrero", cap.all())

    def test_no_puede_elegir_si_nivel_mayor_que_1(self):
        self.char1.db.nivel = 2
        self._run_clase("guerrero")
        self.assertIsNone(self.char1.db.clase)

    def test_no_puede_elegir_si_nivel_mayor_que_1_mensaje(self):
        self.char1.db.nivel = 2
        cap = self._run_clase("guerrero")
        self.assertIn("nivel 1", cap.all().lower())

    def test_clase_invalida_no_asigna_nada(self):
        self._run_clase("paladin")
        self.assertIsNone(self.char1.db.clase)

    def test_clase_invalida_muestra_error(self):
        cap = self._run_clase("paladin")
        self.assertIn("no existe", cap.all().lower())

    def test_clase_con_mayusculas_funciona(self):
        self._run_clase("GUERRERO")
        self.assertEqual(self.char1.db.clase, "guerrero")

    def test_clase_sin_args_muestra_clase_actual(self):
        self.char1.db.clase = "mago"
        cap = self._run_clase()
        output = cap.all()
        self.assertIn("Mago", output)
        self.assertIn("ACTUAL", output)

    def test_clase_sin_args_nivel_alto_sin_clase_muestra_aviso(self):
        self.char1.db.nivel = 5
        cap = self._run_clase()
        self.assertIn("nivel 1", cap.all().lower())


# ---------------------------------------------------------------------------
# TestClaseRestriccionHabilidades
# ---------------------------------------------------------------------------

class TestClaseRestriccionHabilidades(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.db.nivel = 5

    def _run_aprender(self, args):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdAprender, self.char1, args)
        cmd.func()
        return cap

    def test_guerrero_puede_aprender_su_rama(self):
        self.char1.db.clase = "guerrero"
        self._run_aprender("embestida")
        self.assertIn("embestida", self.char1.db.habilidades_desbloqueadas)

    def test_guerrero_no_puede_aprender_otra_rama(self):
        self.char1.db.clase = "guerrero"
        self._run_aprender("corte")
        self.assertNotIn("corte", self.char1.db.habilidades_desbloqueadas)

    def test_guerrero_no_puede_aprender_rama_mago(self):
        self.char1.db.clase = "guerrero"
        self._run_aprender("dardo magico")
        self.assertNotIn("dardo_magico", self.char1.db.habilidades_desbloqueadas)

    def test_explorador_puede_aprender_su_rama(self):
        self.char1.db.clase = "explorador"
        self._run_aprender("corte")
        self.assertIn("corte", self.char1.db.habilidades_desbloqueadas)

    def test_explorador_no_puede_aprender_otra_rama(self):
        self.char1.db.clase = "explorador"
        self._run_aprender("embestida")
        self.assertNotIn("embestida", self.char1.db.habilidades_desbloqueadas)

    def test_mago_puede_aprender_su_rama(self):
        self.char1.db.clase = "mago"
        self._run_aprender("dardo magico")
        self.assertIn("dardo_magico", self.char1.db.habilidades_desbloqueadas)

    def test_mago_no_puede_aprender_otra_rama(self):
        self.char1.db.clase = "mago"
        self._run_aprender("embestida")
        self.assertNotIn("embestida", self.char1.db.habilidades_desbloqueadas)

    def test_sin_clase_puede_aprender_cualquier_rama(self):
        self.char1.db.clase = None
        self._run_aprender("embestida")
        self.assertIn("embestida", self.char1.db.habilidades_desbloqueadas)

    def test_error_mensaje_menciona_clase(self):
        self.char1.db.clase = "mago"
        cap = self._run_aprender("embestida")
        self.assertIn("Mago", cap.all())

    def test_restriccion_no_afecta_habilidades_iniciales_ya_conocidas(self):
        self.char1.db.clase = "mago"
        cap = self._run_aprender("golpe fuerte")
        self.assertIn("Ya conoces", cap.all())


# ---------------------------------------------------------------------------
# TestClaseEnPerfil
# ---------------------------------------------------------------------------

class TestClaseEnPerfil(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def _run_perfil(self):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdPerfil, self.char1)
        cmd.func()
        return cap

    def test_perfil_sin_clase_no_muestra_linea_clase(self):
        self.char1.db.clase = None
        cap = self._run_perfil()
        self.assertNotIn("Clase:", cap.all())

    def test_perfil_con_clase_muestra_clase(self):
        self.char1.db.clase = "guerrero"
        cap = self._run_perfil()
        output = cap.all()
        self.assertIn("Clase:", output)
        self.assertIn("Guerrero", output)

    def test_perfil_con_clase_mago(self):
        self.char1.db.clase = "mago"
        cap = self._run_perfil()
        self.assertIn("Mago", cap.all())


# ---------------------------------------------------------------------------
# TestHabilidadesConClase
# ---------------------------------------------------------------------------

class TestHabilidadesConClase(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def _run_habilidades(self, args=""):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdHabilidades, self.char1, args)
        cmd.func()
        return cap

    def test_habilidades_sin_clase_no_muestra_bloqueadas_por_clase(self):
        self.char1.db.clase = None
        cap = self._run_habilidades()
        self.assertNotIn("[C]", cap.all())

    def test_habilidades_con_clase_muestra_bloqueadas_por_clase(self):
        self.char1.db.clase = "guerrero"
        cap = self._run_habilidades()
        self.assertIn("[C]", cap.all())

    def test_habilidades_muestra_nombre_clase(self):
        self.char1.db.clase = "mago"
        cap = self._run_habilidades()
        self.assertIn("Mago", cap.all())

    def test_leyenda_incluye_clase(self):
        self.char1.db.clase = "explorador"
        cap = self._run_habilidades()
        self.assertIn("[C]", cap.all())
