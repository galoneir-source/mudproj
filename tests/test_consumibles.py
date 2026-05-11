"""
tests/test_consumibles.py

Tests de integración para el sistema de consumibles.
Ejecutar con:
  evennia test --settings settings.py mygame.tests.test_consumibles
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.objects import Consumible
from commands.general_commands import CmdUsar


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _crear_consumible(location, efecto="curar_hp", potencia=30, usos=1):
    obj = create_object(Consumible, key="poción de prueba", location=location)
    obj.db.efecto = efecto
    obj.db.potencia = potencia
    obj.db.usos = usos
    return obj


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
#  Consumible.aplicar
# --------------------------------------------------------------------------- #

class TestConsumibleAplicar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.hp = 50
        self.char1.db.hp_max = 100

    def test_curar_hp_suma_potencia(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30)
        poc.aplicar(self.char1)
        self.assertEqual(self.char1.db.hp, 80)

    def test_curar_hp_no_supera_maximo(self):
        self.char1.db.hp = 90
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30)
        poc.aplicar(self.char1)
        self.assertEqual(self.char1.db.hp, 100)

    def test_curar_hp_lleno_devuelve_aviso(self):
        self.char1.db.hp = 100
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30)
        msg = poc.aplicar(self.char1)
        self.assertIn("perfectas condiciones", msg)
        self.assertEqual(self.char1.db.hp, 100)

    def test_curar_maximo_lleva_al_tope(self):
        poc = _crear_consumible(self.char1, "curar_maximo")
        poc.aplicar(self.char1)
        self.assertEqual(self.char1.db.hp, self.char1.db.hp_max)

    def test_curar_maximo_ya_lleno(self):
        self.char1.db.hp = 100
        poc = _crear_consumible(self.char1, "curar_maximo")
        msg = poc.aplicar(self.char1)
        self.assertIn("perfectas condiciones", msg)

    def test_curar_veneno_limpia_estado(self):
        self.char1.db.envenenado = True
        poc = _crear_consumible(self.char1, "curar_veneno")
        poc.aplicar(self.char1)
        self.assertFalse(self.char1.db.envenenado)

    def test_sin_stats_no_explota(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30)
        self.char1.db.hp = None
        msg = poc.aplicar(self.char1)
        self.assertIn("No tiene efecto", msg)


# --------------------------------------------------------------------------- #
#  Consumible.consumir — gestión de usos
# --------------------------------------------------------------------------- #

class TestConsumibleConsumir(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.hp = 50
        self.char1.db.hp_max = 100

    def test_uso_unico_devuelve_true(self):
        poc = _crear_consumible(self.char1, usos=1)
        eliminar = poc.consumir(self.char1)
        self.assertTrue(eliminar)

    def test_multiples_usos_decrementa(self):
        poc = _crear_consumible(self.char1, usos=3)
        eliminar = poc.consumir(self.char1)
        self.assertFalse(eliminar)
        self.assertEqual(poc.db.usos, 2)

    def test_usos_ilimitados_nunca_elimina(self):
        poc = _crear_consumible(self.char1, usos=-1)
        for _ in range(5):
            eliminar = poc.consumir(self.char1)
            self.assertFalse(eliminar)

    def test_ultimo_uso_devuelve_true(self):
        poc = _crear_consumible(self.char1, usos=2)
        poc.consumir(self.char1)   # usos → 1
        eliminar = poc.consumir(self.char1)  # usos → 0
        self.assertTrue(eliminar)


# --------------------------------------------------------------------------- #
#  Consumible.return_appearance
# --------------------------------------------------------------------------- #

class TestConsumibleApariencia(EvenniaTest):

    def test_muestra_efecto_y_usos(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30, usos=1)
        texto = poc.return_appearance(self.char1)
        self.assertIn("consumible", texto)
        self.assertIn("30", texto)
        self.assertIn("1 uso", texto)

    def test_usos_ilimitados_en_apariencia(self):
        poc = _crear_consumible(self.char1, usos=-1)
        texto = poc.return_appearance(self.char1)
        self.assertIn("ilimitados", texto)

    def test_curar_maximo_sin_potencia(self):
        poc = _crear_consumible(self.char1, "curar_maximo", potencia=0)
        texto = poc.return_appearance(self.char1)
        self.assertIn("máximo", texto)

    def test_curar_veneno_en_apariencia(self):
        poc = _crear_consumible(self.char1, "curar_veneno")
        texto = poc.return_appearance(self.char1)
        self.assertIn("envenenamiento", texto)


# --------------------------------------------------------------------------- #
#  CmdUsar
# --------------------------------------------------------------------------- #

class TestCmdUsar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.hp = 50
        self.char1.db.hp_max = 100

    def _usar(self, args):
        cmd = _make_cmd(CmdUsar, self.char1, args)
        cmd.func()

    def test_usar_sin_args_muestra_ayuda(self):
        self._usar("")
        # No debe lanzar excepción

    def test_usar_no_consumible_rechazado(self):
        from typeclasses.objects import Object
        obj = create_object(Object, key="piedra", location=self.char1)
        self._usar("piedra")
        self.assertEqual(self.char1.db.hp, 50)  # hp sin cambios

    def test_usar_pocion_cura(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=30, usos=1)
        self._usar("poción de prueba")
        self.assertEqual(self.char1.db.hp, 80)

    def test_usar_pocion_la_elimina_al_agotarse(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=10, usos=1)
        poc_id = poc.id
        self._usar("poción de prueba")
        from evennia import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=poc_id).exists())

    def test_usar_pocion_multiples_usos_no_elimina(self):
        poc = _crear_consumible(self.char1, "curar_hp", potencia=10, usos=3)
        poc_id = poc.id
        self._usar("poción de prueba")
        from evennia import ObjectDB
        self.assertTrue(ObjectDB.objects.filter(id=poc_id).exists())
        self.assertEqual(poc.db.usos, 2)

    def test_usar_elixir_maximo(self):
        poc = _crear_consumible(self.char1, "curar_maximo", usos=1)
        self._usar("poción de prueba")
        self.assertEqual(self.char1.db.hp, self.char1.db.hp_max)
