"""
tests/test_intercambio.py

Tests de integración Evennia para el sistema de intercambio entre jugadores
(v0.39.0). Cubre: creación de TradeSession sin autodestruirse, flujo
completo (proponer/aceptar/ofrecer/confirmar/ejecutar), rechazo de una
propuesta pendiente, y el bug de "swap tras confirmar".

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_intercambio
"""
from evennia.utils import create
from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest

from features.trade.commands import (
    CmdConfirmarIntercambio,
    CmdIntercambiar,
    CmdOfrecer,
    CmdRetirarOferta,
)
from features.trade.trade_session import TradeSession
from typeclasses.characters import Character
from typeclasses.objects import Object


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


class TestTradeSessionCreation(EvenniaTest):
    def test_create_script_no_devuelve_none(self):
        """
        Regresión: TradeSession.at_script_creation() fijaba interval=120
        (auto-cancela tras 2 min de inactividad) sin start_delay=True, así
        que el primer at_repeat() se disparaba de inmediato y cancelaba/
        autoeliminaba la sesión durante su propia creación -> create_script()
        devolvía None y 'intercambiar <jugador>' fallaba con AttributeError
        para todo el mundo, siempre.
        """
        sesion = create_script(
            "features.trade.trade_session.TradeSession",
            key="trade_test", persistent=False, autostart=True,
        )
        self.assertIsNotNone(sesion)
        self.assertTrue(sesion.id)
        sesion.delete()


class TradeTestBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char2.move_to(self.char1.location, quiet=True)
        self.char1.db.monedas = 100
        self.char2.db.monedas = 50
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None

    def tearDown(self):
        for char in (self.char1, self.char2):
            sesion = getattr(char.ndb, "trade_session", None) or getattr(
                char.ndb, "trade_pending", None
            )
            if sesion:
                try:
                    sesion.delete()
                except Exception:
                    pass
        super().tearDown()


class TestFlujoCompleto(TradeTestBase):
    def setUp(self):
        super().setUp()
        self.espada = create.create_object(
            Object, key="espada de prueba", location=self.char1
        )

    def test_proponer_ofrecer_confirmar_ejecuta_el_intercambio(self):
        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "aceptar").func()
        _make_cmd(CmdOfrecer, self.char1, "espada de prueba").func()
        _make_cmd(CmdOfrecer, self.char2, "30 monedas").func()
        _make_cmd(CmdConfirmarIntercambio, self.char1).func()
        _make_cmd(CmdConfirmarIntercambio, self.char2).func()

        self.assertEqual(self.char1.db.monedas, 130)
        self.assertEqual(self.char2.db.monedas, 20)
        self.assertEqual(self.espada.location, self.char2)
        self.assertIsNone(getattr(self.char1.ndb, "trade_session", None))
        self.assertIsNone(getattr(self.char2.ndb, "trade_session", None))

    def test_retirar_oferta_antes_de_confirmar(self):
        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "aceptar").func()
        _make_cmd(CmdOfrecer, self.char1, "espada de prueba").func()
        _make_cmd(CmdRetirarOferta, self.char1, "espada de prueba").func()
        _make_cmd(CmdConfirmarIntercambio, self.char1).func()
        _make_cmd(CmdConfirmarIntercambio, self.char2).func()

        self.assertEqual(self.espada.location, self.char1)


class TestRechazoYCancelacion(TradeTestBase):
    def test_receptor_puede_declinar_una_propuesta_pendiente(self):
        """
        Regresión: el mensaje de propuesta le dice al receptor "usa
        intercambiar cancelar para rechazar", pero 'cancelar' solo miraba
        ndb.trade_session (que el receptor nunca tiene mientras está
        pendiente, solo ndb.trade_pending) -> "No tienes ningún intercambio
        activo." y la propuesta quedaba huérfana, bloqueando a ambos
        jugadores hasta que expirase el timeout de 2 minutos.
        """
        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        self.assertIsNotNone(getattr(self.char2.ndb, "trade_pending", None))

        _make_cmd(CmdIntercambiar, self.char2, "cancelar").func()

        self.assertIsNone(getattr(self.char1.ndb, "trade_session", None))
        self.assertIsNone(getattr(self.char2.ndb, "trade_pending", None))

    def test_tras_declinar_ambos_pueden_iniciar_otro_intercambio(self):
        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "cancelar").func()

        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        self.assertIsNotNone(getattr(self.char2.ndb, "trade_pending", None))


class TestSwapTrasConfirmar(TradeTestBase):
    def test_cambiar_oferta_desconfirma_al_otro(self):
        """
        Regresión: agregar_objeto/retirar_objeto/establecer_monedas solo
        desconfirmaban el lado del jugador que mutaba su propia oferta,
        nunca al otro. Un jugador podía confirmar, ver cómo el otro
        cambiaba (empeoraba) su oferta sin perder la confirmación previa,
        y el intercambio se ejecutaba sobre los nuevos términos sin que el
        primero volviera a confirmar — vector de estafa real.
        """
        sesion = create_script(
            "features.trade.trade_session.TradeSession",
            key="trade_swap_test", persistent=False, autostart=True,
        )
        sesion.iniciar(self.char1, self.char2)
        sesion.aceptar(self.char2)

        sesion.ofrecer_monedas(self.char2, 40)
        sesion.confirmar_jugador(self.char1)
        self.assertTrue(sesion.db.lado_a["confirmado"])

        # char2 cambia los términos tras la confirmación de char1
        sesion.ofrecer_monedas(self.char2, 0)

        self.assertFalse(sesion.db.lado_a["confirmado"])

        sesion.confirmar_jugador(self.char2)
        self.assertEqual(sesion.db.estado, "activa")
        self.assertEqual(self.char1.db.monedas, 100)
        self.assertEqual(self.char2.db.monedas, 50)

        sesion.delete()
