"""
tests/test_friends.py

Tests de integración Evennia para el sistema de lista de amigos: comandos
(agregar/quitar/listar), estado en línea vía sesión real, y las notificaciones
de conexión/desconexión conectadas en typeclasses/characters.py.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_friends
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from features.friends.commands import CmdAgregarAmigo, CmdQuitarAmigo, CmdAmigos
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


class _FakeSession:
    """Simula una Session real solo en lo que _notificar_amigos necesita."""
    def __init__(self, puppet):
        self._puppet = puppet

    def get_puppet(self):
        return self._puppet


class TestFriendsBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None


# --------------------------------------------------------------------------- #
#  agregar amigo
# --------------------------------------------------------------------------- #

class TestCmdAgregarAmigo(TestFriendsBase):

    def test_agrega_por_nombre(self):
        _make_cmd(CmdAgregarAmigo, self.char1, self.char2.key).func()
        self.assertIn(self.char2.dbref, self.char1.db.amigos)

    def test_jugador_no_encontrado(self):
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdAgregarAmigo, self.char1, "NoExiste").func()
        self.assertIn("No se encontró", capturado["t"])

    def test_no_puede_agregarse_a_si_mismo(self):
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdAgregarAmigo, self.char1, self.char1.key).func()
        self.assertIn("a ti mismo", capturado["t"])
        self.assertEqual(self.char1.db.amigos, [])

    def test_no_duplica(self):
        self.char1.db.amigos = [self.char2.dbref]
        _make_cmd(CmdAgregarAmigo, self.char1, self.char2.key).func()
        self.assertEqual(self.char1.db.amigos, [self.char2.dbref])

    def test_sin_argumentos(self):
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdAgregarAmigo, self.char1, "").func()
        self.assertIn("Uso:", capturado["t"])
        self.assertEqual(self.char1.db.amigos, [])


# --------------------------------------------------------------------------- #
#  quitar amigo
# --------------------------------------------------------------------------- #

class TestCmdQuitarAmigo(TestFriendsBase):

    def setUp(self):
        super().setUp()
        self.char1.db.amigos = [self.char2.dbref]

    def test_quita(self):
        _make_cmd(CmdQuitarAmigo, self.char1, self.char2.key).func()
        self.assertEqual(self.char1.db.amigos, [])

    def test_no_estaba_en_la_lista(self):
        self.char1.db.amigos = []
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdQuitarAmigo, self.char1, self.char2.key).func()
        self.assertIn("no está en tu lista", capturado["t"])


# --------------------------------------------------------------------------- #
#  amigos (listado + estado en línea real)
# --------------------------------------------------------------------------- #

class TestCmdAmigos(TestFriendsBase):

    def test_lista_vacia(self):
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdAmigos, self.char1).func()
        self.assertIn("no tienes amigos", capturado["t"].lower())

    def test_muestra_desconectado_por_defecto(self):
        self.char1.db.amigos = [self.char2.dbref]
        capturado = {}
        self.char1.msg = lambda text=None, **kw: capturado.update(t=text)
        _make_cmd(CmdAmigos, self.char1).func()
        self.assertIn(self.char2.key, capturado["t"])
        self.assertIn("Desconectado", capturado["t"])

    def test_muestra_en_linea_con_sesion_real(self):
        """
        EvenniaTest ya deja self.char1 puppeteado por self.session por
        defecto (a diferencia de lo documentado para versiones anteriores
        de Evennia en test_cartography.py/test_arena.py, verificado
        empíricamente en este entorno) — así que ya arranca "en línea" sin
        necesidad de puppetear nada a mano.
        """
        self.char2.db.amigos = [self.char1.dbref]
        capturado = {}
        self.char2.msg = lambda text=None, **kw: capturado.update(t=text)

        _make_cmd(CmdAmigos, self.char2).func()
        self.assertIn("En línea", capturado["t"])

        self.account.unpuppet_object(self.session)
        capturado2 = {}
        self.char2.msg = lambda text=None, **kw: capturado2.update(t=text)
        _make_cmd(CmdAmigos, self.char2).func()
        self.assertIn("Desconectado", capturado2["t"])


# --------------------------------------------------------------------------- #
#  _notificar_amigos (lógica de filtrado, sesiones simuladas)
# --------------------------------------------------------------------------- #

class TestNotificarAmigos(TestFriendsBase):

    def test_notifica_a_quien_lo_tiene_como_amigo(self):
        self.char2.db.amigos = [self.char1.dbref]
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char2)]):
            self.char1._notificar_amigos("Char se ha conectado.")

        self.assertIn("Char se ha conectado.", capturado)

    def test_no_notifica_a_quien_no_lo_tiene_como_amigo(self):
        self.char2.db.amigos = []
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char2)]):
            self.char1._notificar_amigos("Char se ha conectado.")

        self.assertEqual(capturado, [])

    def test_no_se_notifica_a_si_mismo(self):
        capturado = []
        self.char1.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char1)]):
            self.char1._notificar_amigos("Char se ha conectado.")

        self.assertEqual(capturado, [])


# --------------------------------------------------------------------------- #
#  Hooks de conexión/desconexión (verifica que están conectados)
# --------------------------------------------------------------------------- #

class TestHooksConexion(TestFriendsBase):
    """
    EvenniaTest ya deja self.char1 con una sesión real activa por defecto
    (self.session, logueada en self.account cuyo último puppet es char1) —
    a diferencia de lo documentado en test_cartography.py/test_arena.py para
    versiones anteriores de Evennia, self.char1.sessions.count() ya es 1 sin
    ningún puppet_object() explícito (verificado empíricamente). Por eso
    estos tests usan el flujo real de puppet_object()/unpuppet_object() en
    vez de llamar los hooks a mano — así el estado de sesiones es siempre
    el que el hook realmente ve en producción, sin asumir un punto de
    partida "desconectado" que aquí no existe.
    """

    def test_at_post_puppet_notifica_conexion(self):
        # puppet_object() sobre una sesión que ya puppetea ese mismo objeto
        # es un no-op (no vuelve a disparar el hook) — hay que desconectar
        # primero para probar la conexión desde un estado limpio.
        self.account.unpuppet_object(self.session)
        with patch.object(self.char1, "_notificar_amigos") as mock_notif:
            self.account.puppet_object(self.session, self.char1)
        mock_notif.assert_called_once()
        self.assertIn("conectado", mock_notif.call_args[0][0])

    def test_at_post_unpuppet_notifica_desconexion_si_ya_no_hay_sesiones(self):
        # self.char1 ya está puppeteado por self.session por defecto.
        with patch.object(self.char1, "_notificar_amigos") as mock_notif:
            self.account.unpuppet_object(self.session)
        mock_notif.assert_called_once()
        self.assertIn("desconectado", mock_notif.call_args[0][0])
