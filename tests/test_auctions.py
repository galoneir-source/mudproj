"""
tests/test_auctions.py

Tests de integración Evennia para la casa de subastas: AuctionScript
(publicar, pujar, retirar, cierre automático) y CmdSubasta.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_auctions
"""
from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from features.auctions.commands import CmdSubasta
from features.auctions.auction_script import AuctionScript
from systems.auctions.auctions import (
    MAX_SUBASTAS_POR_JUGADOR,
    DURACION_SEGUNDOS,
    puja_minima,
    calcular_comision,
    calcular_ganancia,
)


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


def _crear_script():
    return create_script(AuctionScript, key="subastas_global", persistent=True)


def _crear_item(owner, nombre="espada de hierro"):
    return create_object("typeclasses.objects.Object", key=nombre, location=owner)


# --------------------------------------------------------------------------- #
#  AuctionScript — publicar
# --------------------------------------------------------------------------- #

class TestAuctionScriptPublicar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_publicar_devuelve_true_y_aid(self):
        item = _crear_item(self.char1)
        ok, aid = self.script.publicar(self.char1, item, 100)
        self.assertTrue(ok)
        self.assertIsNotNone(aid)

    def test_item_pasa_a_limbo(self):
        item = _crear_item(self.char1)
        self.script.publicar(self.char1, item, 100)
        self.assertIsNone(item.location)

    def test_subasta_aparece_en_obtener(self):
        item = _crear_item(self.char1)
        ok, aid = self.script.publicar(self.char1, item, 100)
        subastas = self.script.obtener_subastas()
        self.assertIn(aid, subastas)
        self.assertEqual(subastas[aid]["precio_actual"], 100)
        self.assertIsNone(subastas[aid]["mejor_pujador_dbref"])

    def test_max_subastas_bloqueado(self):
        for i in range(MAX_SUBASTAS_POR_JUGADOR):
            item = _crear_item(self.char1, f"item_{i}")
            self.script.publicar(self.char1, item, 10)
        extra = _crear_item(self.char1, "extra")
        ok, msg = self.script.publicar(self.char1, extra, 10)
        self.assertFalse(ok)
        self.assertIn(str(MAX_SUBASTAS_POR_JUGADOR), msg)

    def test_otro_jugador_no_afectado_por_limite_del_primero(self):
        for i in range(MAX_SUBASTAS_POR_JUGADOR):
            item = _crear_item(self.char1, f"item_{i}")
            self.script.publicar(self.char1, item, 10)
        item2 = _crear_item(self.char2, "item_char2")
        ok, _ = self.script.publicar(self.char2, item2, 10)
        self.assertTrue(ok)


# --------------------------------------------------------------------------- #
#  AuctionScript — pujar
# --------------------------------------------------------------------------- #

class TestAuctionScriptPujar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.item = _crear_item(self.char1, "daga de acero")
        _, self.aid = self.script.publicar(self.char1, self.item, 100)
        self.char2.db.monedas = 1000

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_puja_exitosa(self):
        minimo = puja_minima(100)
        ok, _ = self.script.pujar(self.aid, self.char2, minimo)
        self.assertTrue(ok)

    def test_puja_actualiza_precio_y_mejor_pujador(self):
        minimo = puja_minima(100)
        self.script.pujar(self.aid, self.char2, minimo)
        entry = self.script.obtener_subastas()[self.aid]
        self.assertEqual(entry["precio_actual"], minimo)
        self.assertEqual(entry["mejor_pujador_dbref"], self.char2.dbref)

    def test_puja_descuenta_monedas_del_pujador(self):
        minimo = puja_minima(100)
        self.script.pujar(self.aid, self.char2, minimo)
        self.assertEqual(self.char2.db.monedas, 1000 - minimo)

    def test_puja_bajo_minimo_falla(self):
        ok, msg = self.script.pujar(self.aid, self.char2, puja_minima(100) - 1)
        self.assertFalse(ok)
        self.assertIn("mínima", msg.lower())

    def test_puja_sin_fondos_falla(self):
        self.char2.db.monedas = 1
        ok, msg = self.script.pujar(self.aid, self.char2, puja_minima(100))
        self.assertFalse(ok)
        self.assertIn("monedas", msg.lower())

    def test_vendedor_no_puede_pujar_en_su_propia_subasta(self):
        self.char1.db.monedas = 1000
        ok, msg = self.script.pujar(self.aid, self.char1, puja_minima(100))
        self.assertFalse(ok)
        self.assertIn("propia", msg.lower())

    def test_puja_id_inexistente_falla(self):
        ok, msg = self.script.pujar("9999", self.char2, 500)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_segunda_puja_reembolsa_a_la_primera(self):
        p1 = puja_minima(100)
        self.script.pujar(self.aid, self.char2, p1)

        char3 = create_object("typeclasses.characters.Character", key="Pujador3")
        char3.db.monedas = 1000
        p2 = puja_minima(p1)
        self.script.pujar(self.aid, char3, p2)

        self.assertEqual(self.char2.db.monedas, 1000)  # reembolsado íntegro

    def test_segunda_puja_notifica_reembolso_al_anterior(self):
        p1 = puja_minima(100)
        self.script.pujar(self.aid, self.char2, p1)
        cap2 = _MsgCapture(self.char2)

        char3 = create_object("typeclasses.characters.Character", key="Pujador3b")
        char3.db.monedas = 1000
        self.script.pujar(self.aid, char3, puja_minima(p1))

        self.assertIn("superado", cap2.all().lower())


# --------------------------------------------------------------------------- #
#  AuctionScript — retirar
# --------------------------------------------------------------------------- #

class TestAuctionScriptRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.item = _crear_item(self.char1, "escudo")
        _, self.aid = self.script.publicar(self.char1, self.item, 200)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_retirar_sin_pujas_devuelve_item(self):
        ok, _ = self.script.retirar(self.aid, self.char1)
        self.assertTrue(ok)
        self.assertEqual(self.item.location, self.char1)
        self.assertNotIn(self.aid, self.script.obtener_subastas())

    def test_otro_jugador_no_puede_retirar(self):
        ok, msg = self.script.retirar(self.aid, self.char2)
        self.assertFalse(ok)
        self.assertIn("vendedor", msg.lower())

    def test_no_se_puede_retirar_con_puja_activa(self):
        self.char2.db.monedas = 1000
        self.script.pujar(self.aid, self.char2, puja_minima(200))
        ok, msg = self.script.retirar(self.aid, self.char1)
        self.assertFalse(ok)
        self.assertIn("puja", msg.lower())

    def test_id_inexistente_falla(self):
        ok, msg = self.script.retirar("9999", self.char1)
        self.assertFalse(ok)
        self.assertTrue(msg)


# --------------------------------------------------------------------------- #
#  AuctionScript — cierre automático (at_repeat)
# --------------------------------------------------------------------------- #

class TestAuctionScriptCierre(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def _expirar(self, aid):
        subastas = dict(self.script.db.subastas)
        subastas[aid]["timestamp_inicio"] -= DURACION_SEGUNDOS + 10
        self.script.db.subastas = subastas

    def test_cierre_con_puja_transfiere_item_al_ganador(self):
        item = _crear_item(self.char1, "vara arcana")
        _, aid = self.script.publicar(self.char1, item, 100)
        self.char2.db.monedas = 1000
        minimo = puja_minima(100)
        self.script.pujar(aid, self.char2, minimo)
        self._expirar(aid)

        self.script.at_repeat()

        self.assertEqual(item.location, self.char2)
        self.assertNotIn(aid, self.script.obtener_subastas())

    def test_cierre_con_puja_paga_al_vendedor_su_ganancia(self):
        item = _crear_item(self.char1, "vara arcana")
        _, aid = self.script.publicar(self.char1, item, 100)
        self.char1.db.monedas = 0
        self.char2.db.monedas = 1000
        minimo = puja_minima(100)
        self.script.pujar(aid, self.char2, minimo)
        self._expirar(aid)

        self.script.at_repeat()

        self.assertEqual(self.char1.db.monedas, calcular_ganancia(minimo))

    def test_cierre_sin_pujas_devuelve_item_al_vendedor(self):
        item = _crear_item(self.char1, "objeto sin pujas")
        _, aid = self.script.publicar(self.char1, item, 100)
        self._expirar(aid)

        self.script.at_repeat()

        self.assertEqual(item.location, self.char1)
        self.assertNotIn(aid, self.script.obtener_subastas())

    def test_subasta_no_expirada_no_se_cierra(self):
        item = _crear_item(self.char1, "objeto reciente")
        _, aid = self.script.publicar(self.char1, item, 100)

        self.script.at_repeat()

        self.assertIn(aid, self.script.obtener_subastas())
        self.assertIsNone(item.location)


# --------------------------------------------------------------------------- #
#  CmdSubasta — listar / mis subastas
# --------------------------------------------------------------------------- #

class TestCmdSubastaListar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_subasta_vacia_muestra_mensaje(self):
        _make_cmd(CmdSubasta, self.char1, "").func()
        self.assertIn("no hay subastas", self.cap.all().lower())

    def test_subasta_con_item_muestra_nombre_y_precio(self):
        item = _crear_item(self.char1, "espada de prueba")
        self.script.publicar(self.char1, item, 300)
        _make_cmd(CmdSubasta, self.char1, "").func()
        texto = self.cap.all()
        self.assertIn("espada de prueba", texto)
        self.assertIn("300", texto)

    def test_mis_subastas_sin_ventas(self):
        _make_cmd(CmdSubasta, self.char1, "mis subastas").func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_mis_subastas_no_muestra_las_de_otro(self):
        item2 = _crear_item(self.char2, "objeto ajeno")
        self.script.publicar(self.char2, item2, 50)
        _make_cmd(CmdSubasta, self.char1, "mis subastas").func()
        self.assertNotIn("objeto ajeno", self.cap.all())


# --------------------------------------------------------------------------- #
#  CmdSubasta — publicar
# --------------------------------------------------------------------------- #

class TestCmdSubastaPublicar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_publicar_item_existente(self):
        _crear_item(self.char1, "poción de vida")
        _make_cmd(CmdSubasta, self.char1, "publicar poción de vida 100").func()
        self.assertIn("subasta", self.cap.all().lower())
        self.assertEqual(len(self.script.obtener_subastas()), 1)

    def test_publicar_item_no_existente_falla(self):
        _make_cmd(CmdSubasta, self.char1, "publicar dragón legendario 9999").func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_publicar_precio_invalido_falla(self):
        _crear_item(self.char1, "item")
        _make_cmd(CmdSubasta, self.char1, "publicar item abc").func()
        self.assertIn("número", self.cap.all().lower())

    def test_publicar_sin_precio_muestra_uso(self):
        _make_cmd(CmdSubasta, self.char1, "publicar solo_nombre").func()
        self.assertIn("uso", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdSubasta — pujar
# --------------------------------------------------------------------------- #

class TestCmdSubastaPujar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char2.db.monedas = 1000
        self.item = _crear_item(self.char1, "espada rara")
        _, self.aid = self.script.publicar(self.char1, self.item, 100)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_pujar_exitoso(self):
        minimo = puja_minima(100)
        _make_cmd(CmdSubasta, self.char2, f"pujar {self.aid} {minimo}").func()
        self.assertIn("pujado", self.cap2.all().lower())

    def test_pujar_id_inexistente_falla(self):
        _make_cmd(CmdSubasta, self.char2, "pujar 9999 500").func()
        self.assertIn("existe", self.cap2.all().lower())

    def test_pujar_sin_monto_muestra_uso(self):
        _make_cmd(CmdSubasta, self.char2, f"pujar {self.aid}").func()
        self.assertIn("uso", self.cap2.all().lower())


# --------------------------------------------------------------------------- #
#  CmdSubasta — retirar
# --------------------------------------------------------------------------- #

class TestCmdSubastaRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.item = _crear_item(self.char1, "hacha")
        _, self.aid = self.script.publicar(self.char1, self.item, 80)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_retirar_exitoso(self):
        _make_cmd(CmdSubasta, self.char1, f"retirar {self.aid}").func()
        self.assertIn("retirado", self.cap1.all().lower())
        self.assertEqual(self.item.location, self.char1)

    def test_otro_jugador_no_puede_retirar(self):
        _make_cmd(CmdSubasta, self.char2, f"retirar {self.aid}").func()
        self.assertIn("vendedor", self.cap2.all().lower())
