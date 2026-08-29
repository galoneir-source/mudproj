"""
tests/test_guild_wars.py

Tests de integración Evennia para las guerras entre gremios:
GuildWarScript (declarar, aceptar, rechazar, rendirse, cierre automático,
registro de bajas) y CmdGuerra. También cubre el gancho real en
CombatHandler._procesar_muerte que anota las bajas de guerra.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_guild_wars
"""
import time

from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from features.guild_wars.commands import CmdGuerra
from features.guild_wars.guild_war_script import GuildWarScript
from features.guilds.guild_script import GuildScript
from systems.guild_wars.guild_wars import TIMEOUT_RETO_SEGUNDOS, DURACION_GUERRA_SEGUNDOS
from systems.guilds.guilds import RANGO_LIDER, normalizar_nombre
from typeclasses.characters import Character


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

    def all(self):
        return "\n".join(self.msgs)


def _crear_guild(nombre, lider):
    guild = create_script(
        GuildScript, key=f"guild_{normalizar_nombre(nombre)}", persistent=True,
    )
    guild.db.nombre = nombre
    guild.db.fundado = time.time()
    guild.añadir_miembro(lider, RANGO_LIDER)
    return guild


def _crear_war_script():
    return create_script(GuildWarScript, key="guerras_gremios_global", persistent=True)


class JugadorFalso(Character):
    """
    has_account cuenta sesiones conectadas reales; para simular un segundo
    jugador (además de self.char1, que ya trae sesión real por defecto en
    esta versión de Evennia) sin montar una sesión real, se sobreescribe
    la propiedad — mismo truco ya usado en test_cartography.py.
    """
    @property
    def has_account(self):
        return True


# --------------------------------------------------------------------------- #
#  GuildWarScript — declarar
# --------------------------------------------------------------------------- #

class TestGuildWarScriptDeclarar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def test_declarar_exitoso(self):
        ok, _ = self.script.declarar("Los Lobos", "Cuervos Negros")
        self.assertTrue(ok)

    def test_declarar_crea_reto_pendiente(self):
        self.script.declarar("Los Lobos", "Cuervos Negros")
        reto = dict(self.script.db.retos)["Cuervos Negros"]
        self.assertEqual(reto["gremio_retador"], "Los Lobos")

    def test_declarar_a_uno_mismo_falla(self):
        ok, msg = self.script.declarar("Los Lobos", "Los Lobos")
        self.assertFalse(ok)
        self.assertIn("propio", msg.lower())

    def test_declarar_con_gremio_a_ya_en_guerra_falla(self):
        self.script.declarar("Los Lobos", "Cuervos Negros")
        self.script.aceptar("Cuervos Negros")
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            ok, msg = self.script.declarar("Los Lobos", "Tercer Gremio")
            self.assertFalse(ok)
            self.assertIn("guerra", msg.lower())
        finally:
            guild_c.delete()

    def test_declarar_no_sobrescribe_reto_pendiente_del_objetivo(self):
        """
        Si Cuervos Negros ya tiene un reto pendiente de un tercer gremio,
        Los Lobos no puede declararle también la guerra: eso sobrescribiría
        silenciosamente el reto del tercero sin avisarle.
        """
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            self.script.declarar("Tercer Gremio", "Cuervos Negros")
            ok, msg = self.script.declarar("Los Lobos", "Cuervos Negros")
            self.assertFalse(ok)
            self.assertIn("pendiente", msg.lower())
            reto = dict(self.script.db.retos)["Cuervos Negros"]
            self.assertEqual(reto["gremio_retador"], "Tercer Gremio")
        finally:
            guild_c.delete()

    def test_declarar_con_reto_saliente_pendiente_falla(self):
        """Un gremio no puede tener dos retos de guerra salientes a la vez."""
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            self.script.declarar("Los Lobos", "Cuervos Negros")
            ok, msg = self.script.declarar("Los Lobos", "Tercer Gremio")
            self.assertFalse(ok)
            self.assertIn("pendiente", msg.lower())
        finally:
            guild_c.delete()

    def test_declarar_contra_gremio_que_ya_es_retador_falla(self):
        """
        No se puede declarar la guerra a un gremio que ya está retando a
        otro (aunque él mismo no sea el objetivo de ningún reto): si se
        permitiera, podría acabar en dos guerras activas simultáneas para
        el mismo gremio en cuanto ambos retos fueran aceptados.
        """
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            self.script.declarar("Los Lobos", "Cuervos Negros")
            ok, msg = self.script.declarar("Tercer Gremio", "Los Lobos")
            self.assertFalse(ok)
            self.assertIn("pendiente", msg.lower())
        finally:
            guild_c.delete()


# --------------------------------------------------------------------------- #
#  GuildWarScript — aceptar / rechazar
# --------------------------------------------------------------------------- #

class TestGuildWarScriptAceptarRechazar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)
        self.script.declarar("Los Lobos", "Cuervos Negros")

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def test_aceptar_exitoso(self):
        ok, _ = self.script.aceptar("Cuervos Negros")
        self.assertTrue(ok)

    def test_aceptar_crea_guerra_activa(self):
        self.script.aceptar("Cuervos Negros")
        war_id, entry = self.script.guerra_de("Los Lobos")
        self.assertIsNotNone(war_id)
        self.assertEqual(entry["gremio_b"], "Cuervos Negros")
        self.assertEqual(entry["kills_a"], 0)

    def test_aceptar_borra_el_reto(self):
        self.script.aceptar("Cuervos Negros")
        self.assertNotIn("Cuervos Negros", dict(self.script.db.retos))

    def test_aceptar_sin_reto_falla(self):
        ok, msg = self.script.aceptar("Gremio Sin Reto")
        self.assertFalse(ok)
        self.assertIn("pendiente", msg.lower())

    def test_aceptar_reto_expirado_falla(self):
        retos = dict(self.script.db.retos)
        retos["Cuervos Negros"]["timestamp"] -= TIMEOUT_RETO_SEGUNDOS + 10
        self.script.db.retos = retos
        ok, msg = self.script.aceptar("Cuervos Negros")
        self.assertFalse(ok)
        self.assertIn("expirado", msg.lower())

    def test_rechazar_exitoso(self):
        ok, _ = self.script.rechazar("Cuervos Negros")
        self.assertTrue(ok)
        self.assertNotIn("Cuervos Negros", dict(self.script.db.retos))

    def test_rechazar_sin_reto_falla(self):
        ok, msg = self.script.rechazar("Gremio Sin Reto")
        self.assertFalse(ok)
        self.assertIn("pendiente", msg.lower())

    def test_rechazar_no_crea_guerra(self):
        self.script.rechazar("Cuervos Negros")
        war_id, _ = self.script.guerra_de("Los Lobos")
        self.assertIsNone(war_id)

    def test_aceptar_falla_si_retador_ya_esta_en_guerra(self):
        """
        Revalidación defensiva en el momento de aceptar: si el retador
        (Los Lobos) ya entró en una guerra activa por otra vía mientras su
        reto a Cuervos Negros seguía pendiente (invariante rota, no
        alcanzable ya con las comprobaciones de declarar() pero cubierta
        igualmente como red de seguridad, mismo patrón que la revalidación
        de casado en el sistema de matrimonio), aceptar debe fallar en vez
        de crear una segunda guerra activa para Los Lobos.
        """
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            guerras = dict(self.script.db.guerras)
            guerras["99"] = {
                "gremio_a": "Los Lobos",
                "gremio_b": "Tercer Gremio",
                "kills_a": 0,
                "kills_b": 0,
                "timestamp_inicio": time.time(),
            }
            self.script.db.guerras = guerras

            ok, msg = self.script.aceptar("Cuervos Negros")
            self.assertFalse(ok)
            self.assertIn("guerra", msg.lower())
            self.assertNotIn("Cuervos Negros", dict(self.script.db.retos))
        finally:
            guild_c.delete()


# --------------------------------------------------------------------------- #
#  GuildWarScript — rendirse
# --------------------------------------------------------------------------- #

class TestGuildWarScriptRendirse(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)
        self.script.declarar("Los Lobos", "Cuervos Negros")
        self.script.aceptar("Cuervos Negros")

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def test_rendirse_exitoso(self):
        ok, _ = self.script.rendirse("Los Lobos")
        self.assertTrue(ok)

    def test_rendirse_termina_la_guerra(self):
        self.script.rendirse("Los Lobos")
        war_id, _ = self.script.guerra_de("Los Lobos")
        self.assertIsNone(war_id)

    def test_rendirse_sin_guerra_falla(self):
        guild_c = _crear_guild("Tercer Gremio", self.char1)
        try:
            ok, msg = self.script.rendirse("Tercer Gremio")
            self.assertFalse(ok)
            self.assertIn("guerra", msg.lower())
        finally:
            guild_c.delete()


# --------------------------------------------------------------------------- #
#  GuildWarScript — registrar_kill_si_en_guerra
# --------------------------------------------------------------------------- #

class TestGuildWarScriptRegistrarKill(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)
        self.script.declarar("Los Lobos", "Cuervos Negros")
        self.script.aceptar("Cuervos Negros")

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def test_kill_entre_gremios_en_guerra_se_registra(self):
        registrado = self.script.registrar_kill_si_en_guerra(self.char1, self.char2)
        self.assertTrue(registrado)
        _, entry = self.script.guerra_de("Los Lobos")
        self.assertEqual(entry["kills_a"], 1)
        self.assertEqual(entry["kills_b"], 0)

    def test_kill_incrementa_el_bando_correcto(self):
        self.script.registrar_kill_si_en_guerra(self.char2, self.char1)
        _, entry = self.script.guerra_de("Los Lobos")
        self.assertEqual(entry["kills_b"], 1)
        self.assertEqual(entry["kills_a"], 0)

    def test_kill_sin_gremio_no_se_registra(self):
        char3 = create_object("typeclasses.characters.Character", key="SinGremio")
        registrado = self.script.registrar_kill_si_en_guerra(char3, self.char2)
        self.assertFalse(registrado)

    def test_kill_entre_gremios_no_enfrentados_no_se_registra(self):
        char3 = create_object("typeclasses.characters.Character", key="Neutral")
        guild_c = _crear_guild("Tercer Gremio", char3)
        try:
            # self.char1 (Los Lobos) está en guerra con Cuervos Negros, no
            # con Tercer Gremio: la baja no debe contar.
            registrado = self.script.registrar_kill_si_en_guerra(self.char1, char3)
            self.assertFalse(registrado)
        finally:
            guild_c.delete()

    def test_gremio_disuelto_y_refundado_con_el_mismo_nombre_no_hereda_la_guerra(self):
        """
        Regresión candidata: la guerra referencia a los gremios por su
        nombre (string), no por el GuildScript en sí. disolver() borra el
        script de "Los Lobos" sin avisar a GuildWarScript, así que la
        entrada de guerra en self.db.guerras sigue diciendo
        gremio_a="Los Lobos" -- y como el nombre ya ha quedado libre,
        cualquiera puede fundar un gremio nuevo con el mismo nombre
        (obtener_gremio_por_nombre ya no encuentra colisión) y heredar,
        sin haberla declarado ni aceptado, una guerra activa ajena.
        """
        char3 = create_object("typeclasses.characters.Character", key="Refundador")
        self.guild_a.disolver(devolver_banco_a=self.char1)

        guild_a_nueva = _crear_guild("Los Lobos", char3)
        try:
            registrado = self.script.registrar_kill_si_en_guerra(char3, self.char2)
            self.assertFalse(
                registrado,
                "El gremio 'Los Lobos' refundado heredó una guerra que nunca declaró.",
            )
        finally:
            guild_a_nueva.delete()


# --------------------------------------------------------------------------- #
#  GuildWarScript — cierre automático (at_repeat)
# --------------------------------------------------------------------------- #

class TestGuildWarScriptCierre(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)
        self.script.declarar("Los Lobos", "Cuervos Negros")
        self.script.aceptar("Cuervos Negros")

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def _expirar(self):
        war_id, _ = self.script.guerra_de("Los Lobos")
        guerras = dict(self.script.db.guerras)
        guerras[war_id]["timestamp_inicio"] -= DURACION_GUERRA_SEGUNDOS + 10
        self.script.db.guerras = guerras

    def test_guerra_expirada_se_cierra(self):
        self._expirar()
        self.script.at_repeat()
        war_id, _ = self.script.guerra_de("Los Lobos")
        self.assertIsNone(war_id)

    def test_guerra_no_expirada_sigue_activa(self):
        self.script.at_repeat()
        war_id, _ = self.script.guerra_de("Los Lobos")
        self.assertIsNotNone(war_id)

    def test_cierre_notifica_a_los_conectados(self):
        # notificar_miembros() solo llega a sesiones conectadas; self.char2
        # (gremio B) no trae sesión real por defecto en EvenniaTest, solo
        # self.char1 (gremio A) — ver feedback_evennia_test_char1_has_session_by_default.
        cap1 = _MsgCapture(self.char1)
        self._expirar()
        self.script.at_repeat()
        self.assertTrue(any("terminada" in m.lower() for m in cap1.msgs))


# --------------------------------------------------------------------------- #
#  CmdGuerra
# --------------------------------------------------------------------------- #

class TestCmdGuerra(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()
        self.guild_a = _crear_guild("Los Lobos", self.char1)
        self.guild_b = _crear_guild("Cuervos Negros", self.char2)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def test_sin_gremio_muestra_mensaje(self):
        char3 = create_object("typeclasses.characters.Character", key="SinGremio")
        char3.msg = lambda text=None, **kw: None
        cap3 = _MsgCapture(char3)
        _make_cmd(CmdGuerra, char3, "").func()
        self.assertIn("no perteneces", cap3.all().lower())

    def test_estado_sin_guerra_ni_reto(self):
        _make_cmd(CmdGuerra, self.char1, "").func()
        self.assertIn("no está en guerra", self.cap1.all().lower())

    def test_declarar_exitoso(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Cuervos Negros").func()
        self.assertIn("has declarado", self.cap1.all().lower())

    def test_declarar_sin_ser_lider_falla(self):
        char3 = create_object("typeclasses.characters.Character", key="Miembro")
        char3.msg = lambda text=None, **kw: None
        self.guild_a.añadir_miembro(char3)
        cap3 = _MsgCapture(char3)
        _make_cmd(CmdGuerra, char3, "declarar Cuervos Negros").func()
        self.assertIn("líder", cap3.all().lower())

    def test_declarar_gremio_inexistente_falla(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Gremio Fantasma").func()
        self.assertIn("no existe", self.cap1.all().lower())

    def test_aceptar_exitoso(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Cuervos Negros").func()
        _make_cmd(CmdGuerra, self.char2, "aceptar").func()
        self.assertIn("aceptado", self.cap2.all().lower())

    def test_rechazar_exitoso(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Cuervos Negros").func()
        _make_cmd(CmdGuerra, self.char2, "rechazar").func()
        self.assertIn("rechazado", self.cap2.all().lower())

    def test_rendirse_exitoso(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Cuervos Negros").func()
        _make_cmd(CmdGuerra, self.char2, "aceptar").func()
        _make_cmd(CmdGuerra, self.char1, "rendirse").func()
        self.assertIn("rendido", self.cap1.all().lower())

    def test_estado_muestra_marcador_en_guerra_activa(self):
        _make_cmd(CmdGuerra, self.char1, "declarar Cuervos Negros").func()
        _make_cmd(CmdGuerra, self.char2, "aceptar").func()
        _make_cmd(CmdGuerra, self.char1, "").func()
        self.assertIn("Cuervos Negros", self.cap1.all())


# --------------------------------------------------------------------------- #
#  Gancho real en CombatHandler._procesar_muerte
# --------------------------------------------------------------------------- #

class TestCombatHandlerGuildWarHook(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_war_script()

        self.sala = create_object("typeclasses.rooms.Room", key="Campo de batalla")
        self.atacante = create_object(JugadorFalso, key="Atacante")
        self.victima = create_object(JugadorFalso, key="Victima")
        self.atacante.msg = lambda text=None, **kw: None
        self.victima.msg = lambda text=None, **kw: None

        self.guild_a = _crear_guild("Los Lobos", self.atacante)
        self.guild_b = _crear_guild("Cuervos Negros", self.victima)
        self.script.declarar("Los Lobos", "Cuervos Negros")
        self.script.aceptar("Cuervos Negros")

    def tearDown(self):
        for obj in (self.script, self.guild_a, self.guild_b):
            try:
                obj.delete()
            except Exception:
                pass
        super().tearDown()

    def _crear_handler(self):
        from features.combat.handler import CombatHandler
        handler = self.sala.scripts.add(CombatHandler)
        handler.db.participantes = [self.atacante, self.victima]
        handler.db.activo = True
        return handler

    def test_muerte_entre_gremios_en_guerra_incrementa_marcador(self):
        handler = self._crear_handler()
        handler._procesar_muerte(self.victima, asesino=self.atacante)
        _, entry = self.script.guerra_de("Los Lobos")
        self.assertEqual(entry["kills_a"], 1)

    def test_muerte_sin_guerra_no_incrementa_marcador(self):
        self.script.rendirse("Los Lobos")
        handler = self._crear_handler()
        handler._procesar_muerte(self.victima, asesino=self.atacante)
        war_id, _ = self.script.guerra_de("Los Lobos")
        self.assertIsNone(war_id)
