"""
tests/test_logros.py

Tests de integración para el sistema de logros y títulos (v0.17.0).
Cubre: comprobar_y_notificar, CmdLogros, CmdTitulo.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_logros
"""
from evennia.utils.test_resources import EvenniaTest

from features.achievements.commands import (
    CmdLogros,
    CmdTitulo,
    comprobar_y_notificar,
    _extraer_datos,
)
from systems.achievements.achievements import LOGROS, JEFES


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


def _init_char(char):
    """Inicializa los atributos de logros en un personaje de test."""
    char.db.logros = []
    char.db.titulo_activo = None
    char.db.kills_totales = 0
    char.db.jefes_derrotados = []
    char.db.objetos_crafteados = 0
    char.db.encantamiento_max = 0
    char.db.banco_usado = False
    char.db.clase = None
    char.db.subclase = None
    char.db.mascota_nivel_max = 1
    char.db.gremios_fundados = 0
    char.db.gremio_banco_depositado = 0
    if not hasattr(char.db, "quests") or char.db.quests is None:
        char.db.quests = {}
    if not hasattr(char.db, "habilidades_desbloqueadas") or char.db.habilidades_desbloqueadas is None:
        char.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido"]
    if not hasattr(char.db, "reputacion") or char.db.reputacion is None:
        char.db.reputacion = {}
    if not hasattr(char.db, "nivel") or char.db.nivel is None:
        char.db.nivel = 1


class _MsgCapture:
    """Captura los mensajes enviados al jugador durante un test."""

    def __init__(self, char):
        self.msgs = []
        self.char = char
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))
        char.location.msg_contents = lambda m, **kw: None

    def all(self) -> str:
        return "\n".join(self.msgs)


# ─── _extraer_datos ──────────────────────────────────────────────────────────

class TestExtraerDatos(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def test_extrae_nivel(self):
        self.char1.db.nivel = 5
        datos = _extraer_datos(self.char1)
        self.assertEqual(datos["nivel"], 5)

    def test_extrae_quests_entregadas(self):
        self.char1.db.quests = {
            "q1": {"estado": "entregada"},
            "q2": {"estado": "activa"},
            "q3": {"estado": "entregada"},
        }
        datos = _extraer_datos(self.char1)
        self.assertEqual(datos["quests_entregadas"], 2)

    def test_extrae_kills(self):
        self.char1.db.kills_totales = 25
        datos = _extraer_datos(self.char1)
        self.assertEqual(datos["kills_totales"], 25)

    def test_extrae_encantamiento_max(self):
        self.char1.db.encantamiento_max = 2
        datos = _extraer_datos(self.char1)
        self.assertEqual(datos["encantamiento_max"], 2)

    def test_extrae_banco_usado(self):
        self.char1.db.banco_usado = True
        datos = _extraer_datos(self.char1)
        self.assertTrue(datos["banco_usado"])

    def test_defaults_sin_atributos(self):
        datos = _extraer_datos(self.char1)
        self.assertEqual(datos["nivel"], 1)
        self.assertEqual(datos["kills_totales"], 0)
        self.assertFalse(datos["banco_usado"])


# ─── comprobar_y_notificar ───────────────────────────────────────────────────

class TestComprobarYNotificar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_condiciones_cumplidas_no_notifica(self):
        comprobar_y_notificar(self.char1)
        self.assertEqual(list(self.char1.db.logros), [])

    def test_notifica_nivel_2(self):
        self.char1.db.nivel = 2
        comprobar_y_notificar(self.char1)
        self.assertIn("nivel_2", self.char1.db.logros)

    def test_mensaje_contiene_nombre_logro(self):
        self.char1.db.nivel = 2
        comprobar_y_notificar(self.char1)
        self.assertIn("Primer Paso", self.cap.all())

    def test_mensaje_contiene_titulo_si_lo_hay(self):
        self.char1.db.nivel = 2
        comprobar_y_notificar(self.char1)
        self.assertIn("el Novato", self.cap.all())

    def test_notifica_primera_mision(self):
        self.char1.db.quests = {"q1": {"estado": "entregada"}}
        comprobar_y_notificar(self.char1)
        self.assertIn("primera_mision", self.char1.db.logros)

    def test_no_repite_logros_ya_desbloqueados(self):
        self.char1.db.logros = ["nivel_2"]
        self.char1.db.nivel = 2
        comprobar_y_notificar(self.char1)
        self.assertEqual(list(self.char1.db.logros).count("nivel_2"), 1)

    def test_desbloquea_multiples_en_una_llamada(self):
        self.char1.db.nivel = 5
        self.char1.db.kills_totales = 10
        comprobar_y_notificar(self.char1)
        logros = list(self.char1.db.logros)
        self.assertIn("nivel_2", logros)
        self.assertIn("nivel_5", logros)
        self.assertIn("diez_kills", logros)

    def test_desbloquea_kills(self):
        self.char1.db.kills_totales = 50
        comprobar_y_notificar(self.char1)
        self.assertIn("diez_kills", self.char1.db.logros)
        self.assertIn("cincuenta_kills", self.char1.db.logros)

    def test_desbloquea_tres_jefes(self):
        self.char1.db.jefes_derrotados = list(JEFES)[:3]
        comprobar_y_notificar(self.char1)
        self.assertIn("tres_jefes", self.char1.db.logros)

    def test_desbloquea_todos_jefes(self):
        self.char1.db.jefes_derrotados = list(JEFES)
        comprobar_y_notificar(self.char1)
        self.assertIn("todos_jefes", self.char1.db.logros)

    def test_desbloquea_primer_encantamiento(self):
        self.char1.db.encantamiento_max = 1
        comprobar_y_notificar(self.char1)
        self.assertIn("primer_encantamiento", self.char1.db.logros)

    def test_desbloquea_encantamiento_max(self):
        self.char1.db.encantamiento_max = 3
        comprobar_y_notificar(self.char1)
        self.assertIn("primer_encantamiento", self.char1.db.logros)
        self.assertIn("encantamiento_max", self.char1.db.logros)

    def test_desbloquea_primer_deposito(self):
        self.char1.db.banco_usado = True
        comprobar_y_notificar(self.char1)
        self.assertIn("primer_deposito", self.char1.db.logros)

    def test_desbloquea_primer_crafteo(self):
        self.char1.db.objetos_crafteados = 1
        comprobar_y_notificar(self.char1)
        self.assertIn("primer_crafteo", self.char1.db.logros)

    def test_desbloquea_habilidad_extra(self):
        self.char1.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido", "embestida"]
        comprobar_y_notificar(self.char1)
        self.assertIn("primera_habilidad", self.char1.db.logros)

    def test_desbloquea_rama_completa(self):
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_fuerte", "embestida", "escudo_fe", "golpe_maestro"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("rama_completa", self.char1.db.logros)

    def test_desbloquea_reputacion_honrado(self):
        self.char1.db.reputacion = {"ciudadanos": 3000}
        comprobar_y_notificar(self.char1)
        self.assertIn("honrado_ciudadanos", self.char1.db.logros)

    def test_desbloquea_diplomatico(self):
        self.char1.db.reputacion = {
            "ciudadanos": 1000,
            "gremio_aventureros": 1500,
            "horda_salvaje": 2000,
        }
        comprobar_y_notificar(self.char1)
        self.assertIn("diplomatico", self.char1.db.logros)


# ─── CmdLogros ───────────────────────────────────────────────────────────────

class TestCmdLogros(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _run(self, args=""):
        cmd = _make_cmd(CmdLogros, self.char1, args)
        cmd.func()

    def test_muestra_sin_logros(self):
        self.char1.db.logros = []
        self._run()
        self.assertIn("0/81", self.cap.all())

    def test_muestra_logros_desbloqueados(self):
        self.char1.db.logros = ["nivel_2", "primera_mision"]
        self._run()
        texto = self.cap.all()
        self.assertIn("Primer Paso", texto)
        self.assertIn("Aventurero", texto)
        self.assertIn("2/81", texto)

    def test_filtra_por_categoria(self):
        self.char1.db.logros = ["nivel_2"]
        self._run("progresion")
        texto = self.cap.all()
        self.assertIn("Progresión", texto)
        self.assertIn("Primer Paso", texto)

    def test_muestra_titulo_activo(self):
        self.char1.db.logros = ["nivel_2"]
        self.char1.db.titulo_activo = "el Novato"
        self._run()
        self.assertIn("el Novato", self.cap.all())

    def test_muestra_titulos_disponibles(self):
        self.char1.db.logros = ["nivel_5", "cinco_misiones"]
        self._run()
        texto = self.cap.all()
        self.assertIn("el Veterano", texto)
        self.assertIn("el Héroe", texto)

    def test_contador_correcto_con_varios(self):
        self.char1.db.logros = list(LOGROS.keys())[:7]
        self._run()
        self.assertIn("7/81", self.cap.all())


# ─── CmdTitulo ───────────────────────────────────────────────────────────────

class TestCmdTitulo(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _run(self, args=""):
        cmd = _make_cmd(CmdTitulo, self.char1, args)
        cmd.func()

    def test_sin_logros_no_puede_poner_titulo(self):
        self._run("el Héroe")
        self.assertIn("ningún título", self.cap.all())

    def test_pone_titulo_desbloqueado(self):
        self.char1.db.logros = ["nivel_2"]
        self._run("el Novato")
        self.assertEqual(self.char1.db.titulo_activo, "el Novato")

    def test_titulo_case_insensitive(self):
        self.char1.db.logros = ["nivel_2"]
        self._run("EL NOVATO")
        self.assertEqual(self.char1.db.titulo_activo, "el Novato")

    def test_titulo_no_desbloqueado_falla(self):
        self.char1.db.logros = ["nivel_2"]
        self._run("la Leyenda")
        self.assertIn("No tienes el título", self.cap.all())
        self.assertIsNone(self.char1.db.titulo_activo)

    def test_sin_argumento_elimina_titulo(self):
        self.char1.db.titulo_activo = "el Novato"
        self._run("")
        self.assertIsNone(self.char1.db.titulo_activo)
        self.assertIn("eliminado", self.cap.all())

    def test_muestra_titulos_disponibles_al_fallar(self):
        self.char1.db.logros = ["nivel_5"]
        self._run("titulo inexistente")
        self.assertIn("el Veterano", self.cap.all())


# ─── Logros de clase ────────────────────────────────────────────────────────

class TestLogrosClaseIntegracion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_elegir_clase_desbloquea_vocacion_elegida(self):
        self.char1.db.clase = "guerrero"
        comprobar_y_notificar(self.char1)
        self.assertIn("vocacion_elegida", list(self.char1.db.logros))

    def test_sin_clase_no_desbloquea_vocacion(self):
        self.char1.db.clase = None
        comprobar_y_notificar(self.char1)
        self.assertNotIn("vocacion_elegida", list(self.char1.db.logros))

    def test_guerrero_rama_completa_desbloquea_maestro(self):
        self.char1.db.clase = "guerrero"
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_fuerte", "embestida", "escudo_fe", "golpe_maestro"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_guerrero", list(self.char1.db.logros))

    def test_guerrero_rama_incompleta_no_desbloquea_maestro(self):
        self.char1.db.clase = "guerrero"
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_fuerte", "embestida", "escudo_fe"
        ]
        comprobar_y_notificar(self.char1)
        self.assertNotIn("maestro_guerrero", list(self.char1.db.logros))

    def test_explorador_rama_completa_desbloquea_maestro(self):
        self.char1.db.clase = "explorador"
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_rapido", "corte", "veneno", "ejecutar"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_explorador", list(self.char1.db.logros))

    def test_mago_rama_completa_desbloquea_maestro(self):
        self.char1.db.clase = "mago"
        self.char1.db.habilidades_desbloqueadas = [
            "dardo_magico", "escudo_arcano", "bola_fuego", "drenar_vida"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_mago", list(self.char1.db.logros))

    def test_maestro_clase_incorrecta_no_desbloquea(self):
        self.char1.db.clase = "mago"
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_fuerte", "embestida", "escudo_fe", "golpe_maestro"
        ]
        comprobar_y_notificar(self.char1)
        self.assertNotIn("maestro_guerrero", list(self.char1.db.logros))

    def test_maestro_guerrero_da_titulo_caballero(self):
        self.char1.db.clase = "guerrero"
        self.char1.db.habilidades_desbloqueadas = [
            "golpe_fuerte", "embestida", "escudo_fe", "golpe_maestro"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("el Caballero", self.cap.all())

    def test_maestro_mago_da_titulo_archimago(self):
        self.char1.db.clase = "mago"
        self.char1.db.habilidades_desbloqueadas = [
            "dardo_magico", "escudo_arcano", "bola_fuego", "drenar_vida"
        ]
        comprobar_y_notificar(self.char1)
        self.assertIn("el Archimago", self.cap.all())

    def test_logros_muestra_categoria_clase(self):
        cmd = _make_cmd(CmdLogros, self.char1)
        cmd.func()
        self.assertIn("Clase", self.cap.all())

    def test_logros_filtra_por_clase(self):
        cmd = _make_cmd(CmdLogros, self.char1, "clase")
        cmd.func()
        output = self.cap.all()
        self.assertIn("Llamado", output)
        self.assertIn("Caballero de Hierro", output)


# ─── Logros de subclase ──────────────────────────────────────────────────────

class TestLogrosSubclaseIntegracion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_elegir_subclase_desbloquea_especializacion_elegida(self):
        self.char1.db.subclase = "paladin"
        comprobar_y_notificar(self.char1)
        self.assertIn("especializacion_elegida", list(self.char1.db.logros))

    def test_sin_subclase_no_desbloquea_especializacion(self):
        self.char1.db.subclase = None
        comprobar_y_notificar(self.char1)
        self.assertNotIn("especializacion_elegida", list(self.char1.db.logros))

    def test_paladin_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "paladin"
        self.char1.db.habilidades_desbloqueadas = ["escudo_divino", "golpe_sagrado"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_paladin", list(self.char1.db.logros))

    def test_paladin_habilidades_incompletas_no_desbloquea_maestro(self):
        self.char1.db.subclase = "paladin"
        self.char1.db.habilidades_desbloqueadas = ["escudo_divino"]
        comprobar_y_notificar(self.char1)
        self.assertNotIn("maestro_paladin", list(self.char1.db.logros))

    def test_berserker_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "berserker"
        self.char1.db.habilidades_desbloqueadas = ["furia_berserker", "golpe_demoledor"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_berserker", list(self.char1.db.logros))

    def test_asesino_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "asesino"
        self.char1.db.habilidades_desbloqueadas = ["golpe_certero", "golpe_letal"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_asesino", list(self.char1.db.logros))

    def test_cazador_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "cazador"
        self.char1.db.habilidades_desbloqueadas = ["instinto_cazador", "trampa_mortal"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_cazador", list(self.char1.db.logros))

    def test_hechicero_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "hechicero"
        self.char1.db.habilidades_desbloqueadas = ["concentracion_arcana", "nova_arcana"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_hechicero", list(self.char1.db.logros))

    def test_nigromante_habilidades_completas_desbloquea_maestro(self):
        self.char1.db.subclase = "nigromante"
        self.char1.db.habilidades_desbloqueadas = ["escudo_sombrio", "drenar_esencia"]
        comprobar_y_notificar(self.char1)
        self.assertIn("maestro_nigromante", list(self.char1.db.logros))

    def test_subclase_incorrecta_no_desbloquea_maestro(self):
        self.char1.db.subclase = "berserker"
        self.char1.db.habilidades_desbloqueadas = ["escudo_divino", "golpe_sagrado"]
        comprobar_y_notificar(self.char1)
        self.assertNotIn("maestro_paladin", list(self.char1.db.logros))
        self.assertNotIn("maestro_berserker", list(self.char1.db.logros))

    def test_maestro_paladin_da_titulo(self):
        self.char1.db.subclase = "paladin"
        self.char1.db.habilidades_desbloqueadas = ["escudo_divino", "golpe_sagrado"]
        comprobar_y_notificar(self.char1)
        self.assertIn("el Paladín", self.cap.all())

    def test_maestro_nigromante_da_titulo(self):
        self.char1.db.subclase = "nigromante"
        self.char1.db.habilidades_desbloqueadas = ["escudo_sombrio", "drenar_esencia"]
        comprobar_y_notificar(self.char1)
        self.assertIn("el Nigromante", self.cap.all())

    def test_logros_muestra_categoria_subclase(self):
        cmd = _make_cmd(CmdLogros, self.char1)
        cmd.func()
        self.assertIn("Subclase", self.cap.all())

    def test_logros_filtra_por_subclase(self):
        cmd = _make_cmd(CmdLogros, self.char1, "subclase")
        cmd.func()
        output = self.cap.all()
        self.assertIn("Elegido", output)
        self.assertIn("Escudo Sagrado", output)


# ─── Logros de mascotas ──────────────────────────────────────────────────────

class TestLogrosMascotasIntegracion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_mascota_nivel_1_no_desbloquea_logro(self):
        self.char1.db.mascota_nivel_max = 1
        comprobar_y_notificar(self.char1)
        self.assertNotIn("mascota_nivel_2", list(self.char1.db.logros))

    def test_mascota_nivel_2_desbloquea_logro(self):
        self.char1.db.mascota_nivel_max = 2
        comprobar_y_notificar(self.char1)
        self.assertIn("mascota_nivel_2", list(self.char1.db.logros))

    def test_mascota_nivel_2_no_desbloquea_nivel_3(self):
        self.char1.db.mascota_nivel_max = 2
        comprobar_y_notificar(self.char1)
        self.assertNotIn("mascota_nivel_3", list(self.char1.db.logros))

    def test_mascota_nivel_3_desbloquea_ambos_logros(self):
        self.char1.db.mascota_nivel_max = 3
        comprobar_y_notificar(self.char1)
        logros = list(self.char1.db.logros)
        self.assertIn("mascota_nivel_2", logros)
        self.assertIn("mascota_nivel_3", logros)

    def test_mascota_nivel_3_da_titulo_domador(self):
        self.char1.db.mascota_nivel_max = 3
        comprobar_y_notificar(self.char1)
        self.assertIn("el Domador", self.cap.all())

    def test_logros_muestra_categoria_mascotas(self):
        cmd = _make_cmd(CmdLogros, self.char1)
        cmd.func()
        self.assertIn("Mascotas", self.cap.all())

    def test_logros_filtra_por_mascotas(self):
        cmd = _make_cmd(CmdLogros, self.char1, "mascotas")
        cmd.func()
        output = self.cap.all()
        self.assertIn("Primer Compañero", output)
        self.assertIn("Domador", output)


# ─── Logros de gremio ────────────────────────────────────────────────────────

class TestLogrosGremioIntegracion(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_gremio_fundado_no_logro(self):
        self.char1.db.gremios_fundados = 0
        comprobar_y_notificar(self.char1)
        self.assertNotIn("gremio_fundado", list(self.char1.db.logros))

    def test_gremio_fundado_desbloquea_logro(self):
        self.char1.db.gremios_fundados = 1
        comprobar_y_notificar(self.char1)
        self.assertIn("gremio_fundado", list(self.char1.db.logros))

    def test_depositar_500_desbloquea_tesorero(self):
        self.char1.db.gremio_banco_depositado = 500
        comprobar_y_notificar(self.char1)
        self.assertIn("gremio_tesorero", list(self.char1.db.logros))

    def test_depositar_499_no_desbloquea_tesorero(self):
        self.char1.db.gremio_banco_depositado = 499
        comprobar_y_notificar(self.char1)
        self.assertNotIn("gremio_tesorero", list(self.char1.db.logros))

    def test_depositar_2000_desbloquea_mecenas_y_tesorero(self):
        self.char1.db.gremio_banco_depositado = 2000
        comprobar_y_notificar(self.char1)
        logros = list(self.char1.db.logros)
        self.assertIn("gremio_tesorero", logros)
        self.assertIn("gremio_mecenas", logros)

    def test_mecenas_da_titulo(self):
        self.char1.db.gremio_banco_depositado = 2000
        comprobar_y_notificar(self.char1)
        self.assertIn("el Mecenas", self.cap.all())

    def test_logros_muestra_categoria_gremio(self):
        cmd = _make_cmd(CmdLogros, self.char1)
        cmd.func()
        self.assertIn("Gremio", self.cap.all())

    def test_logros_filtra_por_gremio(self):
        cmd = _make_cmd(CmdLogros, self.char1, "gremio")
        cmd.func()
        output = self.cap.all()
        self.assertIn("Fundador", output)
        self.assertIn("Tesorero", output)
        self.assertIn("Mecenas", output)
