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
from systems.arena.arena import siguiente_combate, campeon as get_campeon
from typeclasses.characters import Character
from typeclasses.rooms import Room


class JugadorDePruebaArena(Character):
    """
    has_account en Evennia cuenta sesiones conectadas (self.sessions.count()),
    no la mera asignación de account — igual que en test_jefes_mundo.py, este
    typeclass simula "hay un jugador real detrás" sin montar sesiones reales,
    necesario porque _resolver_jugador() del torneo filtra por has_account.
    """

    @property
    def has_account(self):
        return True


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

    def test_iniciar_reinicia_el_timer_real_al_timeout_de_combate(self):
        """
        Regresión: `iniciar()` hacía `self.interval = TIMEOUT_COMBATE`, que
        solo actualiza el campo db_interval persistido — el LoopingCall de
        Twisted ya en marcha (arrancado en at_script_creation con
        TIMEOUT_INSCRIPCION=600s) seguía corriendo con el intervalo viejo.
        Efecto real: cualquier torneo que siguiera "activo" 600s después de
        su creación se cancelaba de golpe (devolviendo cuotas) aunque hubiera
        combates en curso, porque el timeout de inscripción nunca se
        reemplazaba de verdad por el de combate (300s). Fix: usar
        `self.start(interval=...)`, que sí para y relanza el timer real.
        """
        from features.arena.tournament_script import TIMEOUT_COMBATE

        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char2, "inscribir").func()
        _make_cmd(CmdArena, self.char1, "iniciar").func()

        torneo = obtener_torneo_activo()
        self.assertEqual(torneo.ndb._task.interval, TIMEOUT_COMBATE)

    def test_siguiente_combate_reinicia_el_timer_de_combate(self):
        """
        Regresión: TIMEOUT_COMBATE se arrancaba una sola vez en iniciar() y
        nunca se reiniciaba entre rondas, así que era un presupuesto de 5 min
        para TODO el torneo (no "por combate" como dice el comentario). Un
        torneo de varias rondas cuyo tiempo total de combates sumara más de
        5 min se cancelaba entero (con devolución de cuotas) aunque los
        combates fueran avanzando con normalidad. Fix: _siguiente_combate()
        reinicia el timer real en cada ronda con self.start(interval=...).
        """
        from unittest.mock import patch
        from features.arena.tournament_script import TIMEOUT_COMBATE

        _make_cmd(CmdArena, self.char1, "inscribir").func()
        _make_cmd(CmdArena, self.char2, "inscribir").func()
        _make_cmd(CmdArena, self.char1, "iniciar").func()

        torneo = obtener_torneo_activo()
        with patch.object(torneo, "start") as mock_start:
            torneo._siguiente_combate()
            mock_start.assert_called_once_with(interval=TIMEOUT_COMBATE)

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


def _crear_jugador(key, monedas=1000):
    j = create.create_object(JugadorDePruebaArena, key=key)
    j.db.monedas = monedas
    j.msg = lambda text=None, **kw: None
    return j


def _avanzar_torneo(torneo, jugadores: dict):
    """
    Conduce el torneo turno a turno sin depender de delay() (no corre en
    el entorno de test): procesa los byes con _siguiente_combate() —
    exactamente el método que ejecuta ese mismo camino en producción — y
    resuelve cada combate real dando la victoria a p1 (determinista) vía
    registrar_resultado(), el mismo hook que usa
    CombatHandler._fin_duelo() al terminar un duelo real de torneo.
    """
    for _ in range(20):
        if not ScriptDB.objects.filter(id=torneo.id).exists():
            return
        bracket = dict(torneo.db.bracket or {})
        if get_campeon(bracket):
            # registrar_resultado() programa _declarar_campeon() vía
            # delay(), que no se ejecuta en el entorno de test — llamarlo
            # aquí directamente, igual que haría el reactor en producción.
            torneo._declarar_campeon(bracket)
            return
        combate = siguiente_combate(bracket)
        if combate is None:
            torneo._declarar_campeon(bracket)
            return
        p1_ref, p2_ref = combate
        if p2_ref is None:
            torneo._siguiente_combate()
        else:
            torneo.registrar_resultado(jugadores[p1_ref], jugadores[p2_ref])


class TestFlujoDeTorneo(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.arena_sala = create.create_object(Room, key="Arena de la Ciudad")

    def tearDown(self):
        torneo = obtener_torneo_activo()
        if torneo:
            try:
                torneo.delete()
            except Exception:
                pass
        super().tearDown()

    def _torneo_con(self, n):
        jugadores = {}
        torneo = create_script(TorneoScript, persistent=False, autostart=True)
        for i in range(n):
            j = _crear_jugador(f"J{i}")
            torneo.inscribir(j)
            jugadores[j.dbref] = j
        ok, msg = torneo.iniciar()
        self.assertTrue(ok, msg)
        return torneo, jugadores

    def test_bye_avanza_sin_combate_real(self):
        """3 jugadores: una pareja real + un bye. El torneo debe
        completarse con exactamente un campeón."""
        torneo, jugadores = self._torneo_con(3)
        _avanzar_torneo(torneo, jugadores)
        ganadores = [j for j in jugadores.values() if j.db.torneos_ganados == 1]
        self.assertEqual(len(ganadores), 1)

    def test_cinco_jugadores_completa_sin_combate_fantasma(self):
        """
        Regresión end-to-end del bug de bracket (None, None) (ver
        systems/arena/arena.py::generar_bracket): con 5 jugadores, antes
        del fix una de las parejas de la primera ronda no tenía ningún
        jugador real, así que _siguiente_combate() la trataba como un
        bye protagonizado por None y avanzaba "???" a la ronda siguiente,
        regalándole a su rival un bye extra e injusto. Conducir el
        torneo entero debe completarse con exactamente un campeón real,
        sin ninguna referencia a un dbref None colándose en el bracket.
        """
        torneo, jugadores = self._torneo_con(5)
        _avanzar_torneo(torneo, jugadores)
        self.assertFalse(ScriptDB.objects.filter(db_key="torneo_arena").exists())
        ganadores = [j for j in jugadores.values() if j.db.torneos_ganados == 1]
        self.assertEqual(len(ganadores), 1)

    def test_seis_jugadores_completa_sin_combate_fantasma(self):
        """Mismo bug con 6 jugadores (2 byes)."""
        torneo, jugadores = self._torneo_con(6)
        _avanzar_torneo(torneo, jugadores)
        ganadores = [j for j in jugadores.values() if j.db.torneos_ganados == 1]
        self.assertEqual(len(ganadores), 1)

    def test_campeon_recibe_el_pot_completo(self):
        torneo, jugadores = self._torneo_con(4)
        pot_esperado = 4 * 100
        _avanzar_torneo(torneo, jugadores)
        ganadores = [j for j in jugadores.values() if j.db.torneos_ganados == 1]
        self.assertEqual(len(ganadores), 1)
        campeon_obj = ganadores[0]
        # Empezó con 1000, pagó 100 de inscripción (900) y cobra el pot.
        self.assertEqual(campeon_obj.db.monedas, 900 + pot_esperado)

    def test_forfeit_si_jugador_no_esta_disponible(self):
        """Un jugador sin sesión activa en el momento del combate (p.ej.
        se desconectó tras inscribirse) no debe bloquear el torneo — el
        rival avanza por forfeit."""
        disponible = _crear_jugador("Disponible")
        desconectado = create.create_object(Character, key="Desconectado")
        desconectado.db.monedas = 1000

        torneo = create_script(TorneoScript, persistent=False, autostart=True)
        torneo.inscribir(disponible)
        torneo.inscribir(desconectado)
        torneo.iniciar()

        torneo._siguiente_combate()

        bracket = dict(torneo.db.bracket or {})
        self.assertEqual(get_campeon(bracket), disponible.dbref)
