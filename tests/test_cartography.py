"""
tests/test_cartography.py

Tests de integración Evennia para el sistema de cartografía (v0.46.0).
Cubre: _zonas_a_dbref() contra salas reales de la base de datos, CmdMapa.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_cartography
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from features.cartography.commands import CmdMapa, _zonas_a_dbref
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


class TestZonasADbref(EvenniaTest):
    def test_encuentra_salas_reales_con_zona(self):
        """
        Regresión: _zonas_a_dbref() llamaba a sala_db.typeclass_instance
        sobre objetos ya typeclasseados por ObjectDB.objects.filter() ->
        AttributeError silenciada -> devolvía siempre {}. Efecto: 'mapa'
        mostraba siempre "0/0 salas exploradas" pese a que las 29 zonas
        del mundo estaban realmente construidas.
        """
        sala = create.create_object(Room, key="Sala de zona de prueba")
        sala.db.zona = "zona_de_prueba"

        zonas = _zonas_a_dbref()

        self.assertIn("zona_de_prueba", zonas)
        self.assertEqual(zonas["zona_de_prueba"], sala.dbref)

    def test_excluye_salas_de_mazmorra_y_vivienda(self):
        sala_maz = create.create_object(Room, key="Sala mazmorra")
        sala_maz.db.zona = "zona_maz"
        sala_maz.db.es_mazmorra = True

        sala_viv = create.create_object(Room, key="Sala vivienda")
        sala_viv.db.zona = "zona_viv"
        sala_viv.db.es_vivienda = True

        zonas = _zonas_a_dbref()

        self.assertNotIn("zona_maz", zonas)
        self.assertNotIn("zona_viv", zonas)


class TestCmdMapa(EvenniaTest):
    character_typeclass = Character

    def test_mapa_refleja_exploracion_real(self):
        sala = create.create_object(Room, key="Sala explorada de prueba")
        sala.db.zona = "zona_explorada_prueba"
        self.char1.db.salas_exploradas = [sala.dbref]

        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(texto=text)

        _make_cmd(CmdMapa, self.char1).func()

        self.assertIn("1/1", capturado["texto"])
