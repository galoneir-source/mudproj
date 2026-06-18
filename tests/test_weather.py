"""
tests/test_weather.py

Tests de integración para el sistema de clima dinámico.
Ejecutar con:
  evennia test tests.test_weather
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.weather.weather_script import (
    ClimaScript,
    clima_actual,
    obtener_clima_script,
)
from systems.weather.weather import CLIMAS
from commands.general_commands import CmdClima


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


# --------------------------------------------------------------------------- #
#  Script global
# --------------------------------------------------------------------------- #

class TestClimaScript(EvenniaTest):

    def test_obtener_script_crea_uno(self):
        script = obtener_clima_script()
        self.assertIsNotNone(script)

    def test_clima_inicial_es_valido(self):
        script = obtener_clima_script()
        self.assertIn(str(script.db.clima or "despejado"), CLIMAS)

    def test_at_repeat_mantiene_clima_valido(self):
        script = obtener_clima_script()
        script.at_repeat()
        self.assertIn(str(script.db.clima), CLIMAS)

    def test_at_repeat_multiple_veces(self):
        script = obtener_clima_script()
        for _ in range(5):
            script.at_repeat()
        self.assertIn(str(script.db.clima), CLIMAS)

    def test_idempotente_no_duplica(self):
        from evennia.scripts.models import ScriptDB
        obtener_clima_script()
        obtener_clima_script()
        count = ScriptDB.objects.filter(db_key="clima_mundial").count()
        self.assertLessEqual(count, 1)


# --------------------------------------------------------------------------- #
#  clima_actual()
# --------------------------------------------------------------------------- #

class TestClimaActual(EvenniaTest):

    def test_clima_actual_devuelve_string(self):
        clima = clima_actual()
        self.assertIsInstance(clima, str)

    def test_clima_actual_devuelve_clima_valido(self):
        obtener_clima_script()
        clima = clima_actual()
        self.assertIn(clima, CLIMAS)

    def test_clima_actual_sin_script_devuelve_despejado(self):
        from evennia.scripts.models import ScriptDB
        ScriptDB.objects.filter(db_key="clima_mundial").delete()
        clima = clima_actual()
        self.assertEqual(clima, "despejado")


# --------------------------------------------------------------------------- #
#  Comando clima
# --------------------------------------------------------------------------- #

class TestCmdClima(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.msgs = []
        self.char1.msg = lambda m, **kw: self.msgs.append(m)

    def test_cmd_no_lanza_excepcion(self):
        cmd = _make_cmd(CmdClima, self.char1)
        cmd.func()

    def test_cmd_envia_mensaje(self):
        cmd = _make_cmd(CmdClima, self.char1)
        cmd.func()
        self.assertTrue(len(self.msgs) > 0)

    def test_cmd_muestra_nombre_de_clima(self):
        cmd = _make_cmd(CmdClima, self.char1)
        cmd.func()
        output = "\n".join(self.msgs)
        nombres = [data["nombre"].lower() for data in CLIMAS.values()]
        self.assertTrue(any(n in output.lower() for n in nombres))

    def test_cmd_penalizacion_solo_con_clima_negativo(self):
        from evennia.scripts.models import ScriptDB
        ScriptDB.objects.filter(db_key="clima_mundial").delete()
        script = obtener_clima_script()
        script.db.clima = "niebla"
        cmd = _make_cmd(CmdClima, self.char1)
        cmd.func()
        output = "\n".join(self.msgs)
        self.assertIn("Percepción", output)

    def test_cmd_sin_penalizacion_con_despejado(self):
        from evennia.scripts.models import ScriptDB
        ScriptDB.objects.filter(db_key="clima_mundial").delete()
        script = obtener_clima_script()
        script.db.clima = "despejado"
        cmd = _make_cmd(CmdClima, self.char1)
        cmd.func()
        output = "\n".join(self.msgs)
        self.assertNotIn("Percepción", output)


# --------------------------------------------------------------------------- #
#  Integración con salas
# --------------------------------------------------------------------------- #

class TestClimaEnSalas(EvenniaTest):

    def test_sala_exterior_return_appearance_no_falla(self):
        room = create_object("typeclasses.rooms.Room", key="sala_ext_test")
        room.db.exterior = True
        room.db.tipo_ambiente = "exterior_natural"
        self.char1.location = room
        apariencia = room.return_appearance(self.char1)
        self.assertIsInstance(apariencia, str)
        self.assertIn("sala_ext_test", apariencia)

    def test_sala_interior_no_muestra_clima(self):
        from evennia.scripts.models import ScriptDB
        ScriptDB.objects.filter(db_key="clima_mundial").delete()
        script = obtener_clima_script()
        script.db.clima = "tormenta"

        room = create_object("typeclasses.rooms.Room", key="sala_int_test")
        room.db.exterior = False
        self.char1.location = room
        apariencia = room.return_appearance(self.char1)
        # Los textos de clima no deben aparecer en salas interiores
        from systems.weather.weather import texto_ambiente_clima
        texto_tormenta = texto_ambiente_clima("tormenta", "exterior_natural")
        self.assertNotIn(texto_tormenta, apariencia)

    def test_sala_exterior_contiene_texto_clima(self):
        from evennia.scripts.models import ScriptDB
        ScriptDB.objects.filter(db_key="clima_mundial").delete()
        script = obtener_clima_script()
        script.db.clima = "lluvia"

        room = create_object("typeclasses.rooms.Room", key="sala_lluvia_test")
        room.db.exterior = True
        room.db.tipo_ambiente = "exterior_natural"
        self.char1.location = room
        apariencia = room.return_appearance(self.char1)
        from systems.weather.weather import texto_ambiente_clima
        texto_lluvia = texto_ambiente_clima("lluvia", "exterior_natural")
        self.assertIn(texto_lluvia, apariencia)


# --------------------------------------------------------------------------- #
#  Integración con percepción
# --------------------------------------------------------------------------- #

class TestWeatherPercepcion(EvenniaTest):

    def test_nivel_percepcion_con_clima(self):
        from systems.perception.perception_manager import PerceptionManager
        pm = PerceptionManager()
        sin_clima = pm.nivel_percepcion(self.char1)
        con_niebla = pm.nivel_percepcion(self.char1, clima="niebla")
        self.assertLessEqual(con_niebla, sin_clima)

    def test_nivel_percepcion_despejado_igual_que_sin_clima(self):
        from systems.perception.perception_manager import PerceptionManager
        pm = PerceptionManager()
        sin_clima = pm.nivel_percepcion(self.char1)
        con_despejado = pm.nivel_percepcion(self.char1, clima="despejado")
        self.assertEqual(sin_clima, con_despejado)

    def test_nivel_percepcion_acumula_hora_y_clima(self):
        from systems.perception.perception_manager import PerceptionManager
        pm = PerceptionManager()
        base = pm.nivel_percepcion(self.char1)
        noche = pm.nivel_percepcion(self.char1, hora=23)
        noche_niebla = pm.nivel_percepcion(self.char1, hora=23, clima="niebla")
        self.assertLessEqual(noche_niebla, noche)
        self.assertLessEqual(noche, base)
