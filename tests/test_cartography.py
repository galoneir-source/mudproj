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


class JugadorDePruebaCartografia(Character):
    """
    has_account en Evennia cuenta sesiones conectadas (self.sessions.count()),
    no la mera asignación de account — EvenniaTest conecta una sesión real
    al Account (self.account) pero no la puppetea sobre self.char1, así que
    self.char1.has_account sigue siendo False por defecto (mismo gotcha ya
    documentado en test_jefes_mundo.py/test_arena.py). Room.at_object_receive()
    filtra por has_account antes de registrar exploración, así que hace
    falta este typeclass para simular "hay un jugador real detrás" sin
    montar una sesión real.
    """

    @property
    def has_account(self):
        return True


class TestRoomAtObjectReceiveRegistraExploracion(EvenniaTest):
    """
    Tests de integración del punto de entrada real de producción:
    Room.at_object_receive() (typeclasses/rooms.py), que es lo que de
    verdad dispara el registro de una sala cuando un jugador entra
    caminando — no _zonas_a_dbref() ni CmdMapa directamente. Ninguno de
    los tests previos de este archivo ejercitaba este hook; solo el
    catálogo puro y las funciones ya llamadas a mano.
    """
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char1 = create.create_object(JugadorDePruebaCartografia, key="JugadorCarto")
        self.char1.db.salas_exploradas = []
        self.char1.msg = lambda text=None, **kw: None

    def test_entrar_a_sala_con_zona_valida_la_registra(self):
        # es_zona_explorable() exige que la zona esté en el catálogo real
        # (ZONAS_VALIDAS) — usar un id inventado no dispara el registro.
        sala = create.create_object(Room, key="Sala real de zona válida")
        sala.db.zona = "plaza_ciudad"

        self.char1.move_to(sala, quiet=True)

        self.assertIn(sala.dbref, list(self.char1.db.salas_exploradas))

    def test_entrar_dos_veces_no_duplica(self):
        sala = create.create_object(Room, key="Sala real revisitada")
        sala.db.zona = "taberna"

        self.char1.move_to(sala, quiet=True)
        otra = create.create_object(Room, key="Sala intermedia")
        otra.db.zona = "mercado"
        self.char1.move_to(otra, quiet=True)
        self.char1.move_to(sala, quiet=True)

        exploradas = list(self.char1.db.salas_exploradas)
        self.assertEqual(exploradas.count(sala.dbref), 1)

    def test_sala_sin_zona_no_se_registra(self):
        sala = create.create_object(Room, key="Sala sin zona")

        self.char1.move_to(sala, quiet=True)

        self.assertEqual(list(self.char1.db.salas_exploradas), [])

    def test_zona_inventada_no_se_registra(self):
        """Solo cuentan las zonas del catálogo real (ZONAS_VALIDAS) — una
        zona con id arbitrario no lo dispara aunque exista en db.zona."""
        sala = create.create_object(Room, key="Sala con zona inventada")
        sala.db.zona = "zona_que_no_existe_en_el_catalogo"

        self.char1.move_to(sala, quiet=True)

        self.assertEqual(list(self.char1.db.salas_exploradas), [])

    def test_sala_mazmorra_no_se_registra_aunque_tenga_zona(self):
        sala = create.create_object(Room, key="Sala mazmorra real")
        sala.db.zona = "plaza_ciudad"
        sala.db.es_mazmorra = True

        self.char1.move_to(sala, quiet=True)

        self.assertEqual(list(self.char1.db.salas_exploradas), [])

    def test_sala_vivienda_no_se_registra_aunque_tenga_zona(self):
        sala = create.create_object(Room, key="Sala vivienda real")
        sala.db.zona = "barrio_residencial"
        sala.db.es_vivienda = True

        self.char1.move_to(sala, quiet=True)

        self.assertEqual(list(self.char1.db.salas_exploradas), [])

    def test_npc_sin_cuenta_no_registra_exploracion(self):
        from typeclasses.npc import NPC

        sala = create.create_object(Room, key="Sala visitada por NPC")
        sala.db.zona = "mercado"
        npc = create.create_object(NPC, key="Goblin de prueba")

        npc.move_to(sala, quiet=True)

        # El NPC no tiene el atributo salas_exploradas inicializado en
        # absoluto (solo Character lo inicializa en at_object_creation).
        self.assertIsNone(getattr(npc.db, "salas_exploradas", None))

    def test_primera_visita_real_dispara_logro_primer_viaje(self):
        sala = create.create_object(Room, key="Sala del primer viaje")
        sala.db.zona = "bosque_norte"

        self.char1.move_to(sala, quiet=True)

        self.assertIn("primer_viaje", list(self.char1.db.logros or []))
