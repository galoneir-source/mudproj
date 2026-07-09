"""
tests/test_mercado_system.py

Tests de integración Evennia para el sistema de mercado de jugadores (v0.25.0).
Cubre: MarketScript (publicar, comprar, retirar), CmdMercado (todos los
subcomandos), límites, comisión, notificación al vendedor.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_mercado_system
"""
from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from features.market.commands import CmdMercado
from features.market.market_script import MarketScript
from systems.market.market import (
    MAX_LISTINGS_POR_JUGADOR,
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
    return create_script(MarketScript, key="mercado_global", persistent=True)


def _crear_item(owner, nombre="espada de hierro"):
    return create_object("typeclasses.objects.Object", key=nombre, location=owner)


# --------------------------------------------------------------------------- #
#  MarketScript — lógica de datos
# --------------------------------------------------------------------------- #

class TestMarketScriptPublicar(EvenniaTest):

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

    def test_publicar_devuelve_true_y_lid(self):
        item = _crear_item(self.char1)
        ok, lid = self.script.publicar(self.char1, item, 100)
        self.assertTrue(ok)
        self.assertIsNotNone(lid)

    def test_lid_es_string(self):
        item = _crear_item(self.char1)
        ok, lid = self.script.publicar(self.char1, item, 100)
        self.assertTrue(ok)
        self.assertIsInstance(lid, str)

    def test_item_pasa_a_limbo(self):
        item = _crear_item(self.char1)
        self.script.publicar(self.char1, item, 100)
        self.assertIsNone(item.location)

    def test_listing_aparece_en_obtener(self):
        item = _crear_item(self.char1)
        ok, lid = self.script.publicar(self.char1, item, 100)
        listings = self.script.obtener_listings()
        self.assertIn(lid, listings)

    def test_listing_almacena_precio(self):
        item = _crear_item(self.char1)
        ok, lid = self.script.publicar(self.char1, item, 250)
        entry = self.script.obtener_listings()[lid]
        self.assertEqual(entry["precio"], 250)

    def test_listing_almacena_vendedor_dbref(self):
        item = _crear_item(self.char1)
        ok, lid = self.script.publicar(self.char1, item, 100)
        entry = self.script.obtener_listings()[lid]
        self.assertEqual(entry["vendedor_dbref"], self.char1.dbref)

    def test_listing_almacena_nombre_item(self):
        item = _crear_item(self.char1, nombre="vara arcana")
        ok, lid = self.script.publicar(self.char1, item, 100)
        entry = self.script.obtener_listings()[lid]
        self.assertEqual(entry["item_nombre"], "vara arcana")

    def test_ids_incrementales(self):
        item1 = _crear_item(self.char1, "a")
        item2 = _crear_item(self.char1, "b")
        _, lid1 = self.script.publicar(self.char1, item1, 100)
        _, lid2 = self.script.publicar(self.char1, item2, 100)
        self.assertNotEqual(lid1, lid2)
        self.assertGreater(int(lid2), int(lid1))

    def test_max_listings_bloqueado(self):
        for i in range(MAX_LISTINGS_POR_JUGADOR):
            item = _crear_item(self.char1, f"item_{i}")
            self.script.publicar(self.char1, item, 10)
        item_extra = _crear_item(self.char1, "extra")
        ok, msg = self.script.publicar(self.char1, item_extra, 10)
        self.assertFalse(ok)
        self.assertIn(str(MAX_LISTINGS_POR_JUGADOR), msg)

    def test_otro_jugador_no_afectado_por_limite_del_primero(self):
        for i in range(MAX_LISTINGS_POR_JUGADOR):
            item = _crear_item(self.char1, f"item_{i}")
            self.script.publicar(self.char1, item, 10)
        item2 = _crear_item(self.char2, "item_char2")
        ok, _ = self.script.publicar(self.char2, item2, 10)
        self.assertTrue(ok)


class TestMarketScriptRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.item = _crear_item(self.char1)
        _, self.lid = self.script.publicar(self.char1, self.item, 100)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_retirar_devuelve_true(self):
        ok, _ = self.script.retirar(self.lid, self.char1)
        self.assertTrue(ok)

    def test_item_vuelve_al_vendedor(self):
        self.script.retirar(self.lid, self.char1)
        self.assertEqual(self.item.location, self.char1)

    def test_listing_eliminado(self):
        self.script.retirar(self.lid, self.char1)
        self.assertNotIn(self.lid, self.script.obtener_listings())

    def test_otro_jugador_no_puede_retirar(self):
        ok, msg = self.script.retirar(self.lid, self.char2)
        self.assertFalse(ok)
        self.assertIn("vendedor", msg.lower())

    def test_lid_inexistente_falla(self):
        ok, msg = self.script.retirar("9999", self.char1)
        self.assertFalse(ok)
        self.assertTrue(msg)


class TestMarketScriptComprar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char1.db.monedas = 0
        self.char2.db.monedas = 1000
        self.item = _crear_item(self.char1, "daga de acero")
        _, self.lid = self.script.publicar(self.char1, self.item, 500)
        self.ganancia = calcular_ganancia(500)
        self.comision = calcular_comision(500)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_compra_exitosa(self):
        ok, msg = self.script.comprar(self.lid, self.char2)
        self.assertTrue(ok)
        self.assertEqual(msg, "daga de acero")

    def test_item_pasa_al_comprador(self):
        self.script.comprar(self.lid, self.char2)
        self.assertEqual(self.item.location, self.char2)

    def test_comprador_pierde_dinero(self):
        self.script.comprar(self.lid, self.char2)
        self.assertEqual(self.char2.db.monedas, 1000 - 500)

    def test_vendedor_recibe_ganancia(self):
        self.script.comprar(self.lid, self.char2)
        self.assertEqual(self.char1.db.monedas, self.ganancia)

    def test_listing_eliminado_tras_compra(self):
        self.script.comprar(self.lid, self.char2)
        self.assertNotIn(self.lid, self.script.obtener_listings())

    def test_sin_fondos_suficientes_falla(self):
        self.char2.db.monedas = 100  # precio es 500
        ok, msg = self.script.comprar(self.lid, self.char2)
        self.assertFalse(ok)
        self.assertIn("monedas", msg.lower())

    def test_sin_fondos_item_no_se_mueve(self):
        self.char2.db.monedas = 100
        self.script.comprar(self.lid, self.char2)
        self.assertIsNone(self.item.location)  # sigue en limbo

    def test_no_puede_comprar_propio_objeto(self):
        # Damos monedas a char1 para que no falle por saldo
        self.char1.db.monedas = 1000
        ok, msg = self.script.comprar(self.lid, self.char1)
        self.assertFalse(ok)
        self.assertIn("propio", msg.lower())

    def test_lid_inexistente_falla(self):
        ok, msg = self.script.comprar("9999", self.char2)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_vendedor_notificado_si_online(self):
        mensajes_vendedor = []
        self.char1.msg = lambda text=None, **kw: mensajes_vendedor.append(str(text))
        self.script.comprar(self.lid, self.char2)
        self.assertTrue(any("comprado" in m.lower() for m in mensajes_vendedor))


# --------------------------------------------------------------------------- #
#  CmdMercado — sin argumentos (listar)
# --------------------------------------------------------------------------- #

class TestCmdMercadoListar(EvenniaTest):

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

    def test_mercado_vacio_muestra_mensaje(self):
        cmd = _make_cmd(CmdMercado, self.char1, "")
        cmd.func()
        self.assertIn("no hay", self.cap.all().lower())

    def test_mercado_con_item_muestra_nombre(self):
        item = _crear_item(self.char1, "espada de prueba")
        self.script.publicar(self.char1, item, 300)
        cmd = _make_cmd(CmdMercado, self.char1, "")
        cmd.func()
        self.assertIn("espada de prueba", self.cap.all())

    def test_mercado_muestra_precio(self):
        item = _crear_item(self.char1, "daga")
        self.script.publicar(self.char1, item, 750)
        cmd = _make_cmd(CmdMercado, self.char1, "")
        cmd.func()
        self.assertIn("750", self.cap.all())

    def test_mercado_muestra_vendedor(self):
        item = _crear_item(self.char1)
        self.script.publicar(self.char1, item, 100)
        cmd = _make_cmd(CmdMercado, self.char1, "")
        cmd.func()
        self.assertIn(self.char1.key, self.cap.all())


# --------------------------------------------------------------------------- #
#  CmdMercado — vender
# --------------------------------------------------------------------------- #

class TestCmdMercadoVender(EvenniaTest):

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

    def test_vender_item_existente(self):
        _crear_item(self.char1, "poción de vida")
        cmd = _make_cmd(CmdMercado, self.char1, "vender poción de vida 100")
        cmd.func()
        self.assertIn("venta", self.cap.all().lower())

    def test_vender_muestra_id(self):
        _crear_item(self.char1, "daga")
        cmd = _make_cmd(CmdMercado, self.char1, "vender daga 50")
        cmd.func()
        self.assertIn("#", self.cap.all())

    def test_vender_item_no_existente_falla(self):
        cmd = _make_cmd(CmdMercado, self.char1, "vender dragón legendario 9999")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_vender_precio_invalido_falla(self):
        _crear_item(self.char1, "item")
        cmd = _make_cmd(CmdMercado, self.char1, "vender item abc")
        cmd.func()
        self.assertIn("precio", self.cap.all().lower())

    def test_vender_precio_cero_falla(self):
        _crear_item(self.char1, "item")
        cmd = _make_cmd(CmdMercado, self.char1, "vender item 0")
        cmd.func()
        self.assertIn("precio", self.cap.all().lower())

    def test_vender_muestra_comision(self):
        _crear_item(self.char1, "arma")
        cmd = _make_cmd(CmdMercado, self.char1, "vender arma 200")
        cmd.func()
        self.assertIn("comisión", self.cap.all().lower())

    def test_vender_sin_precio_muestra_uso(self):
        cmd = _make_cmd(CmdMercado, self.char1, "vender solo_nombre_sin_precio")
        cmd.func()
        texto = self.cap.all().lower()
        self.assertTrue("uso" in texto or "precio" in texto)


# --------------------------------------------------------------------------- #
#  CmdMercado — comprar
# --------------------------------------------------------------------------- #

class TestCmdMercadoComprar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.char1.db.monedas = 0
        self.char2.db.monedas = 2000
        self.item = _crear_item(self.char1, "espada rara")
        _, self.lid = self.script.publicar(self.char1, self.item, 400)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_comprar_exitoso(self):
        cmd = _make_cmd(CmdMercado, self.char2, f"comprar {self.lid}")
        cmd.func()
        self.assertIn("comprado", self.cap2.all().lower())

    def test_comprar_item_en_inventario(self):
        cmd = _make_cmd(CmdMercado, self.char2, f"comprar {self.lid}")
        cmd.func()
        self.assertEqual(self.item.location, self.char2)

    def test_comprar_descuenta_monedas(self):
        cmd = _make_cmd(CmdMercado, self.char2, f"comprar {self.lid}")
        cmd.func()
        self.assertEqual(self.char2.db.monedas, 1600)

    def test_comprar_sin_fondos_falla(self):
        self.char2.db.monedas = 50
        cmd = _make_cmd(CmdMercado, self.char2, f"comprar {self.lid}")
        cmd.func()
        self.assertIn("monedas", self.cap2.all().lower())

    def test_comprar_id_inexistente_falla(self):
        cmd = _make_cmd(CmdMercado, self.char2, "comprar 9999")
        cmd.func()
        self.assertIn("existe", self.cap2.all().lower())


# --------------------------------------------------------------------------- #
#  CmdMercado — retirar
# --------------------------------------------------------------------------- #

class TestCmdMercadoRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.item = _crear_item(self.char1, "escudo")
        _, self.lid = self.script.publicar(self.char1, self.item, 200)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_retirar_exitoso(self):
        cmd = _make_cmd(CmdMercado, self.char1, f"retirar {self.lid}")
        cmd.func()
        self.assertIn("retirado", self.cap1.all().lower())

    def test_retirar_devuelve_item(self):
        cmd = _make_cmd(CmdMercado, self.char1, f"retirar {self.lid}")
        cmd.func()
        self.assertEqual(self.item.location, self.char1)

    def test_otro_jugador_no_puede_retirar(self):
        cmd = _make_cmd(CmdMercado, self.char2, f"retirar {self.lid}")
        cmd.func()
        self.assertIn("vendedor", self.cap2.all().lower())

    def test_retirar_id_inexistente_falla(self):
        cmd = _make_cmd(CmdMercado, self.char1, "retirar 9999")
        cmd.func()
        self.assertIn("existe", self.cap1.all().lower())


# --------------------------------------------------------------------------- #
#  CmdMercado — mis ventas
# --------------------------------------------------------------------------- #

class TestCmdMercadoMisVentas(EvenniaTest):

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

    def test_sin_ventas_muestra_mensaje(self):
        cmd = _make_cmd(CmdMercado, self.char1, "mis ventas")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_con_ventas_muestra_item(self):
        item = _crear_item(self.char1, "amuleto")
        self.script.publicar(self.char1, item, 150)
        cmd = _make_cmd(CmdMercado, self.char1, "mis ventas")
        cmd.func()
        self.assertIn("amuleto", self.cap.all().lower())

    def test_no_muestra_ventas_de_otro(self):
        item2 = _crear_item(self.char2, "espada ajena")
        self.script.publicar(self.char2, item2, 300)
        cmd = _make_cmd(CmdMercado, self.char1, "mis ventas")
        cmd.func()
        self.assertNotIn("espada ajena", self.cap.all())

    def test_alias_mio_funciona(self):
        item = _crear_item(self.char1, "hacha")
        self.script.publicar(self.char1, item, 80)
        cmd = _make_cmd(CmdMercado, self.char1, "mio")
        cmd.func()
        self.assertIn("hacha", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  Comisión y transferencia de dinero
# --------------------------------------------------------------------------- #

class TestComisionYTransferencia(EvenniaTest):

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

    def test_vendedor_recibe_precio_menos_comision(self):
        precio = 1000
        self.char1.db.monedas = 0
        self.char2.db.monedas = precio + 100
        item = _crear_item(self.char1)
        _, lid = self.script.publicar(self.char1, item, precio)
        self.script.comprar(lid, self.char2)
        esperado = calcular_ganancia(precio)
        self.assertEqual(self.char1.db.monedas, esperado)

    def test_comprador_paga_precio_completo(self):
        precio = 500
        self.char1.db.monedas = 0
        self.char2.db.monedas = 1000
        item = _crear_item(self.char1)
        _, lid = self.script.publicar(self.char1, item, precio)
        self.script.comprar(lid, self.char2)
        self.assertEqual(self.char2.db.monedas, 1000 - precio)


if __name__ == "__main__":
    import unittest
    unittest.main()
