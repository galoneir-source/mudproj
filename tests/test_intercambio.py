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
    _buscar_jugador,
    _buscar_objeto_inventario,
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

    def test_no_se_puede_ofrecer_un_objeto_equipado(self):
        """
        Regresión candidata: ofrecer_objeto() solo comprobaba
        obj.location == jugador (un objeto equipado sigue teniendo esa
        location, equipar no la cambia) -- a diferencia de banco, mercado,
        subastas y crafteo, que excluyen explícitamente los objetos
        equipados vía _get_equipamiento(). Ofrecer y transferir un arma
        equipada dejaba sus bonuses aplicados de forma permanente en las
        stats del que la dio (equipamiento nunca se actualizaba) mientras
        el objeto físico pasaba de verdad al otro jugador -- que podía
        equiparlo también y duplicar el bonus entre dos personajes.
        """
        self.char1.db.equipamiento = {
            "arma": self.espada, "armadura": None, "accesorio": None,
        }
        self.espada.db.bonuses = {"fuerza": 5}

        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "aceptar").func()
        _make_cmd(CmdOfrecer, self.char1, "espada de prueba").func()

        sesion = self.char1.ndb.trade_session
        self.assertEqual(sesion.db.lado_a["objetos"], [])

    def test_objeto_equipado_no_se_duplica_tras_ejecutar_el_intercambio(self):
        """
        Mismo bug que arriba, verificado de punta a punta: si de alguna
        forma un objeto equipado llegara a ejecutarse en un intercambio,
        el dueño original seguiría disfrutando sus bonuses (equipamiento
        nunca se actualiza) mientras el objeto pasa de verdad al otro
        jugador -- que podría equiparlo y duplicar el bonus. Con el fix,
        ofrecerlo ya falla, así que el intercambio se ejecuta vacío y el
        arma se queda donde estaba, equipada y con sus bonuses intactos
        para su único dueño real.
        """
        self.char1.db.equipamiento = {
            "arma": self.espada, "armadura": None, "accesorio": None,
        }
        self.espada.db.bonuses = {"fuerza": 5}
        fuerza_antes = self.char1.db.fuerza

        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "aceptar").func()
        _make_cmd(CmdOfrecer, self.char1, "espada de prueba").func()
        _make_cmd(CmdConfirmarIntercambio, self.char1).func()
        _make_cmd(CmdConfirmarIntercambio, self.char2).func()

        self.assertEqual(self.espada.location, self.char1)
        self.assertEqual(self.char1.db.fuerza, fuerza_antes)

    def test_equipar_el_objeto_ofrecido_despues_de_confirmar_no_lo_duplica(self):
        """
        Regresión: ofrecer_objeto() sí excluye un objeto YA equipado en el
        momento de ofrecerlo, pero _ejecutar() -- disparado por la
        confirmación del OTRO jugador, que puede tardar cualquier tiempo
        en llegar -- solo revalida que el objeto siga existiendo y siga en
        el inventario (obj.location == jugador), no que siga
        DESEQUIPADO. Si el oferente ofrece el objeto, confirma, y LUEGO
        se lo equipa antes de que el otro confirme, el intercambio se
        ejecutaba igualmente: el objeto pasaba de verdad al receptor
        mientras el equipamiento y los bonuses de stats del oferente
        original seguían intactos -- el mismo bug de duplicación que ya
        se corrige al ofrecer, pero sin cubrir esta ventana entre ofrecer
        y ejecutar.
        """
        self.espada.db.bonuses = {"fuerza": 5}
        fuerza_antes = self.char1.db.fuerza

        _make_cmd(CmdIntercambiar, self.char1, self.char2.key).func()
        _make_cmd(CmdIntercambiar, self.char2, "aceptar").func()
        _make_cmd(CmdOfrecer, self.char1, "espada de prueba").func()
        _make_cmd(CmdConfirmarIntercambio, self.char1).func()

        # El oferente se equipa el objeto ya ofrecido antes de que el
        # receptor confirme (el fuerza+5 queda aplicado a sus stats, como
        # haría el comando 'equipar' real).
        self.char1.db.equipamiento = {
            "arma": self.espada, "armadura": None, "accesorio": None,
        }
        self.char1.db.fuerza = fuerza_antes + 5

        _make_cmd(CmdConfirmarIntercambio, self.char2).func()

        # El intercambio debe cancelarse al detectar en la ejecución que
        # el objeto ofrecido se ha equipado mientras tanto -- el arma se
        # queda donde estaba, equipada y con su bonus intacto para su
        # único dueño real, igual que si se hubiera intentado ofrecer ya
        # equipada desde el principio.
        self.assertEqual(self.espada.location, self.char1)
        self.assertEqual(self.char1.db.fuerza, fuerza_antes + 5)


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


class TestBusquedaExactaSobreParcial(TradeTestBase):
    """
    Regresión: _buscar_jugador() y _buscar_objeto_inventario()
    (features/trade/commands.py) hacían coincidencia por substring puro y
    rechazaban como "ambiguo" en cuanto había 2+ coincidencias parciales,
    sin priorizar nunca una coincidencia exacta — mismo patrón ya corregido
    en banco (609bbea), tienda (98d67ae), grupo (e56b9aa), equipamiento
    (155cbb3) y correo (9d11590). Un jugador con "daga" y "daga oxidada" en
    el inventario no podía ofrecer la "daga" exacta en un intercambio.
    """

    def setUp(self):
        super().setUp()
        self.daga = create.create_object(Object, key="daga", location=self.char1)
        self.daga_oxidada = create.create_object(
            Object, key="daga oxidada", location=self.char1
        )

    def test_objeto_nombre_exacto_no_es_ambiguo_pese_a_substring_de_otro(self):
        obj, err = _buscar_objeto_inventario(self.char1, "daga")
        self.assertEqual(obj, self.daga)
        self.assertEqual(err, "")

    def test_jugador_nombre_exacto_no_es_ambiguo_pese_a_substring_de_otro(self):
        self.char2.key = "Ana"
        anabella = create.create_object(
            Character, key="Anabella", location=self.char1.location
        )
        anabella.account = self.char2.account

        obj, err = _buscar_jugador(self.char1, "Ana")

        self.assertEqual(obj, self.char2)
        self.assertEqual(err, "")
