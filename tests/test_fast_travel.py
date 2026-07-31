"""
tests/test_fast_travel.py

Tests de integración Evennia para el sistema de viaje rápido:
comando 'viajar' contra salas reales del catálogo de cartografía.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_fast_travel
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from features.fast_travel.commands import CmdViajar
from systems.fast_travel.fast_travel import COSTE_VIAJE
from typeclasses.characters import Character
from typeclasses.rooms import Room


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


class TestFastTravelBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char1.msg = lambda text=None, **kw: None
        self.capturado = {}
        self.char1.msg = lambda text=None, **kw: self.capturado.update(t=text)


class TestCmdViajarSinArgumentos(TestFastTravelBase):

    def test_lista_vacia_sin_exploracion(self):
        _make_cmd(CmdViajar, self.char1).func()
        self.assertIn("no tienes ningún destino", self.capturado["t"].lower())

    def test_lista_destinos_explorados(self):
        # formatear_destinos() muestra el nombre del catálogo (ZONAS_INFO),
        # no la key real de la sala construida en el mundo.
        sala = create.create_object(Room, key="Plaza real de prueba")
        sala.db.zona = "plaza_ciudad"
        self.char1.db.salas_exploradas = [sala.dbref]

        _make_cmd(CmdViajar, self.char1).func()

        self.assertIn("Plaza de la Ciudad", self.capturado["t"])


class TestCmdViajarConDestino(TestFastTravelBase):

    def setUp(self):
        super().setUp()
        self.sala = create.create_object(Room, key="Taberna El Jabalí Borracho")
        self.sala.db.zona = "taberna"
        self.char1.db.salas_exploradas = [self.sala.dbref]
        self.char1.db.monedas = COSTE_VIAJE

    def test_viaja_a_destino_valido(self):
        _make_cmd(CmdViajar, self.char1, "Taberna El Jabalí Borracho").func()
        self.assertEqual(self.char1.location, self.sala)
        self.assertEqual(self.char1.db.monedas, 0)

    def test_destino_no_encontrado(self):
        _make_cmd(CmdViajar, self.char1, "Catacumbas Inexistentes").func()
        self.assertIn("no tienes un destino explorado", self.capturado["t"].lower())
        self.assertNotEqual(self.char1.location, self.sala)

    def test_fondos_insuficientes(self):
        self.char1.db.monedas = COSTE_VIAJE - 1
        _make_cmd(CmdViajar, self.char1, "Taberna El Jabalí Borracho").func()
        self.assertIn("monedas", self.capturado["t"].lower())
        self.assertNotEqual(self.char1.location, self.sala)

    def test_bloqueado_en_combate(self):
        self.char1.db.en_combate = True
        _make_cmd(CmdViajar, self.char1, "Taberna El Jabalí Borracho").func()
        self.assertIn("combate", self.capturado["t"].lower())
        self.assertNotEqual(self.char1.location, self.sala)
        self.assertEqual(self.char1.db.monedas, COSTE_VIAJE)

    def test_ya_esta_ahi(self):
        self.char1.move_to(self.sala, quiet=True)
        monedas_antes = self.char1.db.monedas
        _make_cmd(CmdViajar, self.char1, "Taberna El Jabalí Borracho").func()
        self.assertIn("ya estás ahí", self.capturado["t"].lower())
        self.assertEqual(self.char1.db.monedas, monedas_antes)

    def test_cooldown_bloquea_segundo_viaje_inmediato(self):
        otra_sala = create.create_object(Room, key="Plaza de la Ciudad")
        otra_sala.db.zona = "plaza_ciudad"
        self.char1.db.salas_exploradas = [self.sala.dbref, otra_sala.dbref]
        self.char1.db.monedas = COSTE_VIAJE * 2

        _make_cmd(CmdViajar, self.char1, "Taberna El Jabalí Borracho").func()
        self.assertEqual(self.char1.location, self.sala)

        _make_cmd(CmdViajar, self.char1, "Plaza de la Ciudad").func()
        self.assertIn("esperar", self.capturado["t"].lower())
        self.assertEqual(self.char1.location, self.sala)
