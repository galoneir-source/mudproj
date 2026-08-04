"""
tests/test_marriage.py

Tests de integración Evennia para el sistema de matrimonio entre jugadores
(v0.70.0). Cubre: CmdProponer, CmdAceptarBoda, CmdRechazarBoda,
CmdDivorciarse, CmdCasado, y la notificación al cónyuge al conectarse.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && evennia test --settings settings.py tests.test_marriage
"""
import time
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from evennia import create_object

from features.marriage.commands import (
    CmdProponer,
    CmdAceptarBoda,
    CmdRechazarBoda,
    CmdDivorciarse,
    CmdCasado,
)
from systems.marriage.marriage import TIMEOUT_PROPUESTA_SEGUNDOS


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


def _init_char(char):
    char.db.conyuge_dbref = None
    char.db.fecha_boda = None
    char.db.propuesta_matrimonio_pendiente = None
    char.db.propuesta_matrimonio_proponente_dbref = None


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


# ---------------------------------------------------------------------------
# CmdProponer
# ---------------------------------------------------------------------------

class TestCmdProponer(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def _proponer(self, args):
        cmd = _make_cmd(CmdProponer, self.char1, args)
        cmd.func()

    def test_sin_args_muestra_uso(self):
        self._proponer("")
        self.assertIn("Uso:", self.cap1.all())

    def test_jugador_inexistente(self):
        self._proponer("Nadie")
        self.assertIn("No se encontró", self.cap1.all())

    def test_propuesta_valida_crea_pendiente(self):
        self._proponer(self.char2.key)
        self.assertIsNotNone(self.char1.db.propuesta_matrimonio_pendiente)
        self.assertEqual(
            self.char1.db.propuesta_matrimonio_pendiente["objetivo_dbref"], self.char2.dbref
        )
        self.assertEqual(
            self.char2.db.propuesta_matrimonio_proponente_dbref, self.char1.dbref
        )

    def test_propuesta_notifica_a_ambos(self):
        self._proponer(self.char2.key)
        self.assertIn("propuesto matrimonio", self.cap1.all())
        self.assertIn("te propone matrimonio", self.cap2.all())

    def test_no_puede_proponerse_a_si_mismo(self):
        self._proponer(self.char1.key)
        self.assertIn("ti mismo", self.cap1.all())

    def test_no_puede_proponer_si_ya_casado(self):
        self.char1.db.conyuge_dbref = "#999"
        self._proponer(self.char2.key)
        self.assertIn("casado", self.cap1.all().lower())
        self.assertIsNone(self.char1.db.propuesta_matrimonio_pendiente)

    def test_no_puede_proponer_si_objetivo_ya_casado(self):
        self.char2.db.conyuge_dbref = "#999"
        self._proponer(self.char2.key)
        self.assertIn("casada", self.cap1.all().lower())

    def test_no_puede_proponer_con_pendiente_saliente(self):
        self._proponer(self.char2.key)
        self.cap1.msgs.clear()
        tercero = self.char2
        self._proponer(tercero.key)
        self.assertIn("pendiente", self.cap1.all().lower())

    def test_propuesta_saliente_caducada_permite_nueva(self):
        timestamp_vieja = time.time() - TIMEOUT_PROPUESTA_SEGUNDOS - 10
        self.char1.db.propuesta_matrimonio_pendiente = {
            "objetivo_dbref": self.char2.dbref,
            "timestamp": timestamp_vieja,
        }
        self.char2.db.propuesta_matrimonio_proponente_dbref = self.char1.dbref
        self._proponer(self.char2.key)
        self.assertIsNotNone(self.char1.db.propuesta_matrimonio_pendiente)
        self.assertGreater(
            self.char1.db.propuesta_matrimonio_pendiente["timestamp"], timestamp_vieja
        )


# ---------------------------------------------------------------------------
# CmdAceptarBoda
# ---------------------------------------------------------------------------

class TestCmdAceptarBoda(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def _proponer(self):
        cmd = _make_cmd(CmdProponer, self.char1, self.char2.key)
        cmd.func()

    def _aceptar(self):
        cmd = _make_cmd(CmdAceptarBoda, self.char2, "")
        cmd.func()

    def test_sin_pendiente(self):
        self._aceptar()
        self.assertIn("ninguna propuesta", self.cap2.all().lower())

    def test_aceptar_valido_casa_a_ambos(self):
        self._proponer()
        self._aceptar()
        self.assertEqual(self.char1.db.conyuge_dbref, self.char2.dbref)
        self.assertEqual(self.char2.db.conyuge_dbref, self.char1.dbref)
        self.assertIsNotNone(self.char1.db.fecha_boda)
        self.assertIsNotNone(self.char2.db.fecha_boda)

    def test_aceptar_limpia_pendientes(self):
        self._proponer()
        self._aceptar()
        self.assertIsNone(self.char1.db.propuesta_matrimonio_pendiente)
        self.assertIsNone(self.char2.db.propuesta_matrimonio_proponente_dbref)

    def test_aceptar_notifica_a_ambos(self):
        self._proponer()
        self.cap1.msgs.clear()
        self.cap2.msgs.clear()
        self._aceptar()
        self.assertIn("casado", self.cap1.all().lower())
        self.assertIn("casado", self.cap2.all().lower())

    def test_aceptar_propuesta_caducada(self):
        self._proponer()
        self.char1.db.propuesta_matrimonio_pendiente["timestamp"] = (
            time.time() - TIMEOUT_PROPUESTA_SEGUNDOS - 10
        )
        self._aceptar()
        self.assertIn("expirado", self.cap2.all().lower())
        self.assertIsNone(self.char1.db.conyuge_dbref)

    def test_aceptar_si_proponente_ya_casado_falla(self):
        self._proponer()
        self.char1.db.conyuge_dbref = "#999"
        self._aceptar()
        self.assertIn("ya está casado", self.cap2.all())
        self.assertIsNone(self.char2.db.conyuge_dbref)


# ---------------------------------------------------------------------------
# CmdRechazarBoda
# ---------------------------------------------------------------------------

class TestCmdRechazarBoda(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def _proponer(self):
        cmd = _make_cmd(CmdProponer, self.char1, self.char2.key)
        cmd.func()

    def test_sin_pendiente(self):
        cmd = _make_cmd(CmdRechazarBoda, self.char2, "")
        cmd.func()
        self.assertIn("ninguna propuesta", self.cap2.all().lower())

    def test_rechazar_limpia_ambos_lados(self):
        self._proponer()
        cmd = _make_cmd(CmdRechazarBoda, self.char2, "")
        cmd.func()
        self.assertIsNone(self.char2.db.propuesta_matrimonio_proponente_dbref)
        self.assertIsNone(self.char1.db.propuesta_matrimonio_pendiente)

    def test_rechazar_notifica_proponente(self):
        self._proponer()
        self.cap1.msgs.clear()
        cmd = _make_cmd(CmdRechazarBoda, self.char2, "")
        cmd.func()
        self.assertIn("rechazado", self.cap1.all().lower())


# ---------------------------------------------------------------------------
# CmdDivorciarse
# ---------------------------------------------------------------------------

class TestCmdDivorciarse(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char1.db.conyuge_dbref = self.char2.dbref
        self.char1.db.fecha_boda = time.time()
        self.char2.db.conyuge_dbref = self.char1.dbref
        self.char2.db.fecha_boda = time.time()
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def test_no_casado_falla(self):
        self.char1.db.conyuge_dbref = None
        cmd = _make_cmd(CmdDivorciarse, self.char1, "")
        cmd.func()
        self.assertIn("no estás casado", self.cap1.all().lower())

    def test_divorcio_limpia_ambos(self):
        cmd = _make_cmd(CmdDivorciarse, self.char1, "")
        cmd.func()
        self.assertIsNone(self.char1.db.conyuge_dbref)
        self.assertIsNone(self.char2.db.conyuge_dbref)
        self.assertIsNone(self.char1.db.fecha_boda)
        self.assertIsNone(self.char2.db.fecha_boda)

    def test_divorcio_notifica_al_conyuge(self):
        cmd = _make_cmd(CmdDivorciarse, self.char1, "")
        cmd.func()
        self.assertIn("divorciado", self.cap2.all().lower())

    def test_divorcio_con_conyuge_borrado_se_autorrepara(self):
        """
        Si el cónyuge fue eliminado (p. ej. @delete de un admin), conyuge_dbref
        queda apuntando a un objeto inexistente. divorciarse debe limpiar
        igualmente el propio slot en vez de bloquear al superviviente.
        """
        fantasma = create_object(
            "typeclasses.characters.Character", key="Fantasma", location=self.room1,
        )
        dbref_fantasma = fantasma.dbref
        fantasma.delete()

        self.char1.db.conyuge_dbref = dbref_fantasma
        cmd = _make_cmd(CmdDivorciarse, self.char1, "")
        cmd.func()

        self.assertIsNone(self.char1.db.conyuge_dbref)
        self.assertIsNone(self.char1.db.fecha_boda)
        self.assertIn("divorciado", self.cap1.all().lower())


# ---------------------------------------------------------------------------
# CmdCasado
# ---------------------------------------------------------------------------

class TestCmdCasado(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)

    def test_soltero(self):
        cmd = _make_cmd(CmdCasado, self.char1, "")
        cmd.func()
        self.assertIn("no estás casado", self.cap1.all().lower())

    def test_casado_muestra_nombre_conyuge(self):
        self.char1.db.conyuge_dbref = self.char2.dbref
        self.char1.db.fecha_boda = time.time()
        cmd = _make_cmd(CmdCasado, self.char1, "")
        cmd.func()
        self.assertIn(self.char2.key, self.cap1.all())


# ---------------------------------------------------------------------------
# Notificación de conexión/desconexión al cónyuge
# ---------------------------------------------------------------------------

class _FakeSession:
    """Simula una Session real solo en lo que _notificar_conyuge necesita."""
    def __init__(self, puppet):
        self._puppet = puppet

    def get_puppet(self):
        return self._puppet


class TestNotificarConyuge(EvenniaTest):
    """
    Igual que _notificar_amigos (ver tests/test_friends.py), _notificar_conyuge
    itera evennia.SESSION_HANDLER.get_sessions() en vez de mirar directamente
    char.sessions.count() — así se puede probar con una _FakeSession, sin
    necesitar una segunda sesión real (que además result irregular: la
    sesión de char.sessions es una property que crea un handler nuevo en
    cada acceso, no algo que se pueda parchear con una asignación directa).
    """

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char1.db.conyuge_dbref = self.char2.dbref
        self.char1.db.fecha_boda = time.time()

    def test_notifica_a_conyuge_conectado(self):
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char2)]):
            self.char1._notificar_conyuge("Char se ha conectado.")

        self.assertIn("Char se ha conectado.", capturado)

    def test_no_notifica_si_conyuge_no_esta_entre_las_sesiones(self):
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[]):
            self.char1._notificar_conyuge("Char se ha conectado.")

        self.assertEqual(capturado, [])

    def test_sin_conyuge_no_notifica_ni_falla(self):
        self.char1.db.conyuge_dbref = None
        capturado = []
        self.char2.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char2)]):
            self.char1._notificar_conyuge("Char se ha conectado.")

        self.assertEqual(capturado, [])

    def test_no_se_notifica_a_si_mismo(self):
        self.char1.db.conyuge_dbref = self.char1.dbref
        capturado = []
        self.char1.msg = lambda text=None, **kw: capturado.append(text)

        with patch("evennia.SESSION_HANDLER.get_sessions", return_value=[_FakeSession(self.char1)]):
            self.char1._notificar_conyuge("Char se ha conectado.")

        self.assertEqual(capturado, [])


class TestHooksConexionConyuge(EvenniaTest):
    """
    Verifica que at_post_puppet/at_post_unpuppet llaman a _notificar_conyuge
    con el mensaje correcto (mismo patrón que TestHooksConexion en
    tests/test_friends.py para _notificar_amigos).
    """

    def setUp(self):
        super().setUp()
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None

    def test_at_post_puppet_notifica_conyuge(self):
        self.account.unpuppet_object(self.session)
        with patch.object(self.char1, "_notificar_conyuge") as mock_notif:
            self.account.puppet_object(self.session, self.char1)
        mock_notif.assert_called_once()
        self.assertIn("conectado", mock_notif.call_args[0][0])

    def test_at_post_unpuppet_notifica_conyuge(self):
        with patch.object(self.char1, "_notificar_conyuge") as mock_notif:
            self.account.unpuppet_object(self.session)
        mock_notif.assert_called_once()
        self.assertIn("desconectado", mock_notif.call_args[0][0])


# ---------------------------------------------------------------------------
# Propuesta saliente y entrante son independientes
#
# Un personaje puede tener a la vez una propuesta que él mismo lanzó
# (slot saliente, db.propuesta_matrimonio_pendiente) y una que recibió de
# otra persona (slot entrante, db.propuesta_matrimonio_proponente_dbref):
# son atributos distintos y `puede_proponer` no impide que coexistan.
# Resolver una (aceptar/rechazar) no debe tocar la otra.
# ---------------------------------------------------------------------------

class TestPropuestaSalienteEntranteIndependientes(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char3 = create_object("typeclasses.characters.Character", key="Tercero")
        _init_char(self.char3)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char3.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)
        self.cap3 = _MsgCapture(self.char3)

    def _proponer(self, caller, objetivo_key):
        cmd = _make_cmd(CmdProponer, caller, objetivo_key)
        cmd.func()

    def _preparar_saliente_y_entrante(self):
        # char1 propone a char2: char1 queda con propuesta saliente.
        self._proponer(self.char1, self.char2.key)
        # char3 propone a char1: char1 queda ADEMÁS con propuesta entrante,
        # sin que la saliente hacia char2 se lo impida.
        self._proponer(self.char3, self.char1.key)
        self.assertIsNotNone(self.char1.db.propuesta_matrimonio_pendiente)
        self.assertEqual(
            self.char1.db.propuesta_matrimonio_proponente_dbref, self.char3.dbref
        )

    def test_rechazar_entrante_no_cancela_saliente(self):
        self._preparar_saliente_y_entrante()

        cmd = _make_cmd(CmdRechazarBoda, self.char1, "")
        cmd.func()

        # La propuesta saliente de char1 hacia char2 sigue intacta.
        self.assertIsNotNone(self.char1.db.propuesta_matrimonio_pendiente)
        self.assertEqual(
            self.char1.db.propuesta_matrimonio_pendiente["objetivo_dbref"], self.char2.dbref
        )
        self.assertEqual(
            self.char2.db.propuesta_matrimonio_proponente_dbref, self.char1.dbref
        )

        # y char2 todavía puede aceptarla con normalidad.
        cmd = _make_cmd(CmdAceptarBoda, self.char2, "")
        cmd.func()
        self.assertEqual(self.char1.db.conyuge_dbref, self.char2.dbref)
        self.assertEqual(self.char2.db.conyuge_dbref, self.char1.dbref)

    def test_aceptar_entrante_no_borra_saliente_a_ciegas(self):
        self._preparar_saliente_y_entrante()

        # char1 acepta la propuesta de char3: se casan.
        cmd = _make_cmd(CmdAceptarBoda, self.char1, "")
        cmd.func()
        self.assertEqual(self.char1.db.conyuge_dbref, self.char3.dbref)

        # char2 intenta aceptar la propuesta (ya obsoleta) de char1: debe
        # fallar con el motivo real -- char1 ya está casado -- y no con el
        # mensaje engañoso de "expirado" que daba el bug (la propuesta
        # saliente de char1 se borraba a ciegas al resolver la entrante).
        self.cap2.msgs.clear()
        cmd = _make_cmd(CmdAceptarBoda, self.char2, "")
        cmd.func()
        self.assertIn("ya está casado", self.cap2.all())
        self.assertNotIn("expirado", self.cap2.all().lower())
        self.assertIsNone(self.char2.db.conyuge_dbref)
