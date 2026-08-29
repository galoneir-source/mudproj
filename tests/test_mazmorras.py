"""
tests/test_mazmorras.py

Tests de integración Evennia para el sistema de mazmorras instanciadas (v0.38.0).
Cubre: CmdMazmorra (entrar/estado/salir), CmdAvanzar, MazmorraScript
(iniciar/avanzar/_completar/salir), soporte de grupo vía party y el fix de
creación del script (start_delay).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_mazmorras
"""
from evennia import create_script
from evennia.utils.test_resources import EvenniaTest

from features.dungeons.commands import (
    CmdAvanzar,
    CmdMazmorra,
    DungeonCmdSet,
    _instancia_del_jugador,
)
from features.dungeons.dungeon_script import MazmorraScript
from features.party.commands import _añadir_miembro, _crear_partido
from systems.dungeons.dungeons import SALA_PORTAL
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


def _init_char(char, nivel=5):
    char.db.nivel = nivel
    char.db.experiencia = 0
    char.db.monedas = 0
    char.msg = lambda text=None, **kw: None


class MazmorrasTestBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.vestibulo = self._crear_vestibulo()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.vestibulo, quiet=True)
        self.char2.move_to(self.vestibulo, quiet=True)

    def tearDown(self):
        # Limpiar cualquier instancia/script residual creado durante el test.
        for char in (self.char1, self.char2):
            instancia = _instancia_del_jugador(char)
            if instancia:
                try:
                    instancia.salir(char)
                except Exception:
                    pass
        super().tearDown()

    def _crear_vestibulo(self):
        from evennia import search_object
        existentes = search_object(SALA_PORTAL, typeclass="typeclasses.rooms.Room")
        if existentes:
            return existentes[0]
        from evennia.utils import create
        return create.create_object(Room, key=SALA_PORTAL)


# --------------------------------------------------------------------------- #
#  Creación del script: regresión del bug de auto-eliminación inmediata
# --------------------------------------------------------------------------- #

class TestMazmorraScriptCreation(MazmorrasTestBase):
    def test_create_script_no_devuelve_none(self):
        """
        Regresión: sin start_delay=True, el primer at_repeat() (pensado como
        timeout a 3600s) se disparaba de inmediato al crear el script, que se
        autoeliminaba durante su propio create_script() -> create_script()
        devolvía None y toda entrada a mazmorra fallaba con AttributeError.
        """
        script = create_script(
            "features.dungeons.dungeon_script.MazmorraScript",
            key="mazmorra_test_creation",
            obj=None,
            persistent=True,
            autostart=True,
        )
        self.assertIsNotNone(script)
        self.assertTrue(script.id)
        script.delete()


# --------------------------------------------------------------------------- #
#  CmdMazmorra: entrada en solitario (compatibilidad hacia atrás)
# --------------------------------------------------------------------------- #

class TestMazmorraEntradaSolo(MazmorrasTestBase):
    def test_entrar_solo_crea_instancia_y_teleporta(self):
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        instancia = _instancia_del_jugador(self.char1)
        self.assertIsNotNone(instancia)
        self.assertEqual(self.char1.location.key, "Entrada de la Cripta")

    def test_entrar_fuera_del_vestibulo_falla(self):
        self.char1.move_to(self.room1, quiet=True)
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        self.assertIsNone(_instancia_del_jugador(self.char1))

    def test_entrar_bajo_nivel_falla(self):
        self.char1.db.nivel = 1
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        self.assertIsNone(_instancia_del_jugador(self.char1))

    def test_salir_teleporta_al_vestibulo(self):
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        _make_cmd(CmdMazmorra, self.char1, "salir").func()
        self.assertEqual(self.char1.location, self.vestibulo)
        self.assertIsNone(_instancia_del_jugador(self.char1))


# --------------------------------------------------------------------------- #
#  CmdMazmorra: entrada en grupo
# --------------------------------------------------------------------------- #

class TestMazmorraEntradaGrupo(MazmorrasTestBase):
    def setUp(self):
        super().setUp()
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)

    def test_lider_entra_arrastra_al_grupo(self):
        # El miembro está en otra sala; debe ser teleportado igualmente.
        self.char2.move_to(self.room1, quiet=True)
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()

        inst_lider = _instancia_del_jugador(self.char1)
        inst_miembro = _instancia_del_jugador(self.char2)
        self.assertIsNotNone(inst_lider)
        self.assertIs(inst_lider, inst_miembro)
        self.assertEqual(self.char1.location, self.char2.location)
        self.assertEqual(set(inst_lider.db.jugadores), {self.char1.dbref, self.char2.dbref})

    def test_no_lider_no_puede_iniciar(self):
        _make_cmd(CmdMazmorra, self.char2, "entrar cripta_ceniza").func()
        self.assertIsNone(_instancia_del_jugador(self.char1))
        self.assertIsNone(_instancia_del_jugador(self.char2))

    def test_miembro_bajo_nivel_bloquea_a_todo_el_grupo(self):
        self.char2.db.nivel = 1
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        self.assertIsNone(_instancia_del_jugador(self.char1))

    def test_salir_de_un_miembro_no_afecta_al_resto(self):
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        instancia = _instancia_del_jugador(self.char1)
        instancia.salir(self.char2)
        self.assertIsNone(_instancia_del_jugador(self.char2))
        self.assertIsNotNone(_instancia_del_jugador(self.char1))
        self.assertEqual(instancia.db.jugadores, [self.char1.dbref])


# --------------------------------------------------------------------------- #
#  MazmorraScript: avance y finalización
# --------------------------------------------------------------------------- #

class TestMazmorraCompletar(MazmorrasTestBase):
    def _entrar_solo(self):
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        return _instancia_del_jugador(self.char1)

    def _limpiar_sala_actual(self, instancia):
        """Elimina cualquier NPC vivo de la sala actual para poder avanzar."""
        sala = instancia.db.salas[instancia.db.sala_actual]
        for obj in list(sala.contents):
            if type(obj).__name__ == "NPC":
                obj.delete()

    def test_completar_reparte_recompensas_solo_a_jugadores_activos(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        instancia = _instancia_del_jugador(self.char1)

        # El miembro abandona antes de terminar -> no debería cobrar recompensa.
        instancia.salir(self.char2)
        xp_char2_antes = self.char2.db.experiencia

        # Avanzar manualmente hasta el jefe y completar.
        while instancia.db.estado == "activa":
            self._limpiar_sala_actual(instancia)
            instancia.avanzar(self.char1)

        self.assertEqual(self.char2.db.experiencia, xp_char2_antes)
        self.assertGreater(self.char1.db.experiencia, 0)
        self.assertIsNone(_instancia_del_jugador(self.char1))

    def test_completar_no_recompensa_a_quien_se_fue_sin_usar_salir(self):
        """
        Regresión candidata: a diferencia de 'mazmorra salir' (que sí depura
        db.jugadores), CUALQUIER otro modo de abandonar la mazmorra -viajar,
        una muerte que manda a casa, etc.- solo mueve al personaje con
        move_to() sin pasar por MazmorraScript.salir(). ¿_completar() sigue
        recompensando a quien ya no está físicamente dentro?
        """
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _make_cmd(CmdMazmorra, self.char1, "entrar cripta_ceniza").func()
        instancia = _instancia_del_jugador(self.char1)

        # char2 abandona la instancia SIN llamar a instancia.salir() -- p.ej.
        # exactamente lo que hace 'viajar' (features/fast_travel/commands.py):
        # un move_to() plano que nunca toca db.jugadores.
        self.char2.move_to(self.vestibulo, quiet=True)
        xp_char2_antes = self.char2.db.experiencia

        while instancia.db.estado == "activa":
            self._limpiar_sala_actual(instancia)
            instancia.avanzar(self.char1)

        self.assertEqual(self.char2.db.experiencia, xp_char2_antes)

    def test_completar_procesa_subida_de_nivel(self):
        """
        Regresión: a diferencia de quests/contratos/expediciones (que llaman
        a procesar_subida_de_nivel() justo después de otorgar XP),
        _completar() solo escribía char.db.experiencia directamente. El
        personaje acumulaba XP por encima del umbral de nivel sin subir de
        nivel de verdad -stats, HP máximo y mensaje incluidos- hasta su
        siguiente kill de combate normal.
        """
        instancia = self._entrar_solo()
        # Nivel 5 -> umbral de nivel 6 son 1400 XP (XP_POR_NIVEL). La cripta
        # de ceniza en dificultad normal da 150 XP: con 1300 de partida cruza
        # el umbral exactamente al completarla.
        self.char1.db.experiencia = 1300
        fuerza_antes = self.char1.db.fuerza

        while instancia.db.estado == "activa":
            self._limpiar_sala_actual(instancia)
            instancia.avanzar(self.char1)

        self.assertEqual(self.char1.db.nivel, 6)
        self.assertEqual(self.char1.db.fuerza, fuerza_antes + 1)

    def test_completar_marca_mazmorra_completada_en_char(self):
        instancia = self._entrar_solo()
        while instancia.db.estado == "activa":
            self._limpiar_sala_actual(instancia)
            instancia.avanzar(self.char1)
        self.assertEqual(
            dict(self.char1.db.mazmorras_completadas or {}).get("cripta_ceniza"), 1
        )


# --------------------------------------------------------------------------- #
#  DungeonCmdSet: sin colisiones con otros comandos
# --------------------------------------------------------------------------- #

class TestDungeonCmdSet(MazmorrasTestBase):
    def test_cmdset_se_construye_sin_error(self):
        cs = DungeonCmdSet()
        cs.at_cmdset_creation()
        keys = {cmd.key for cmd in cs.commands}
        self.assertIn("mazmorra", keys)
        self.assertIn("avanzar", keys)


# --------------------------------------------------------------------------- #
#  at_server_cold_start: limpieza de salas huérfanas
# --------------------------------------------------------------------------- #

class TestLimpiezaColdStart(MazmorrasTestBase):
    def test_limpia_salas_de_mazmorra_huerfanas(self):
        """
        Regresión: at_server_cold_start() llamaba a search_object(typeclass=...,
        attribute_name=..., attribute_value=True) — 'attribute_value' no es
        un kwarg válido de ObjectDBManager.search_object() -> TypeError,
        atrapada por un try/except Exception: pass que envuelve toda la
        función. La limpieza de salas de mazmorra huérfanas tras un reinicio
        en frío nunca ha hecho nada, en silencio, desde que se escribió.
        """
        from evennia.utils import create
        from server.conf.at_server_startstop import at_server_cold_start

        sala_huerfana = create.create_object(Room, key="Mazmorra huérfana de prueba")
        sala_huerfana.db.es_mazmorra = True

        at_server_cold_start()

        from evennia import search_object
        self.assertEqual(len(search_object("Mazmorra huérfana de prueba")), 0)
        self.assertEqual(len(search_object(self.vestibulo.key)), 1)
