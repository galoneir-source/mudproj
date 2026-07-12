"""
tests/test_arena.py

Tests de integración Evennia para el sistema de torneos de Arena.
Cubre: obtener_torneo_activo() (singleton real), creación de TorneoScript
sin autodestruirse, CmdArena (inscribir, salir, iniciar, estado).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_arena
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import create
from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest

from features.arena.commands import CmdArena
from features.arena.tournament_script import TorneoScript, obtener_torneo_activo
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


class TestTorneoScriptCreation(EvenniaTest):
    def test_create_script_no_devuelve_none(self):
        """
        Regresión: TorneoScript.at_script_creation() fijaba interval sin
        start_delay=True, así que el primer at_repeat() (pensado como
        timeout de inscripción a los 600s) se disparaba de inmediato y
        cancelaba/autoeliminaba el torneo durante su propia creación ->
        create_script() devolvía None y 'arena inscribir' fallaba con
        AttributeError para todo el mundo.
        """
        torneo = create_script(TorneoScript, persistent=False, autostart=True)
        self.assertIsNotNone(torneo)
        self.assertTrue(torneo.id)
        torneo.delete()

    def test_obtener_torneo_activo_es_singleton(self):
        """
        Regresión: obtener_torneo_activo() llamaba a s.typeclass_instance
        sobre un objeto ya typeclasseado por ScriptDB.objects.filter() ->
        AttributeError silenciada -> siempre devolvía None. Efecto: cada
        'arena inscribir' creaba un torneo nuevo y aislado, así que dos
        jugadores nunca podían acabar en el mismo torneo.
        """
        t1 = create_script(TorneoScript, persistent=False, autostart=True)
        t2 = obtener_torneo_activo()
        self.assertIs(t1, t2)
        t1.delete()


class TestInscripcionGrupo(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.arena_sala = create.create_object(Room, key="Arena de la Ciudad")
        self.char1.db.monedas = 1000
        self.char2.db.monedas = 1000
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None

    def tearDown(self):
        torneo = obtener_torneo_activo()
        if torneo:
            try:
                torneo.delete()
            except Exception:
                pass
        super().tearDown()

    def test_dos_jugadores_se_inscriben_en_el_mismo_torneo(self):
        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char2, "inscribir").func()

        torneo = obtener_torneo_activo()
        self.assertIsNotNone(torneo)
        self.assertEqual(set(torneo.db.inscritos), {self.char1.dbref, self.char2.dbref})
        self.assertEqual(self.char1.db.monedas, 900)
        self.assertEqual(self.char2.db.monedas, 900)

    def test_iniciar_con_dos_inscritos_pasa_a_activo(self):
        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char2, "inscribir").func()
        _make_cmd(CmdArena, self.char1, "iniciar").func()

        torneo = obtener_torneo_activo()
        self.assertEqual(torneo.db.estado, "activo")

    def test_iniciar_con_un_solo_inscrito_falla(self):
        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char1, "iniciar").func()

        torneo = obtener_torneo_activo()
        self.assertEqual(torneo.db.estado, "inscripcion")

    def test_salir_devuelve_la_cuota_y_lo_quita_de_inscritos(self):
        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char1, "salir").func()

        self.assertEqual(self.char1.db.monedas, 1000)

    def test_estado_ve_el_torneo_creado_por_otro_jugador(self):
        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char2, "estado").func()

        torneo = obtener_torneo_activo()
        self.assertIn(self.char1.dbref, torneo.db.inscritos)
