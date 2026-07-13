"""
tests/test_shop.py

Tests de integración para features/shop/commands.py.
Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_shop
"""
from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.shop.commands import (
    _buscar_comerciante,
    CmdTienda,
    CmdComprar,
    CmdVender,
    PRECIO_VENTA_DEFAULT,
)
from features.equipment.commands import SLOTS


def _make_cmd(CmdClass, caller, args=""):
    """Instancia un comando listo para llamar a func() en tests."""
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


def _tienda_basica():
    return [
        {"key": "pocion de vida", "precio": 10, "cantidad": -1, "valor": 10},
        {"key": "pocion rara",    "precio": 30, "cantidad":  2, "valor": 30},
    ]


# --------------------------------------------------------------------------- #
#  _buscar_comerciante
# --------------------------------------------------------------------------- #

class TestBuscarComerciante(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(text)

    def test_sin_sala_da_error(self):
        caller = MagicMock()
        caller.location = None
        comerciante, error = _buscar_comerciante(caller)
        self.assertIsNone(comerciante)
        self.assertIsNotNone(error)
        self.assertIn("lugar", error.lower())

    def test_sin_comerciante_en_sala_da_error(self):
        comerciante, error = _buscar_comerciante(self.jugador)
        self.assertIsNone(comerciante)
        self.assertIsNotNone(error)

    def test_un_comerciante_encontrado(self):
        npc = create_object("typeclasses.npc.NPC", key="Mercader", location=self.sala)
        npc.db.tienda = [{"key": "espada", "precio": 10}]
        comerciante, error = _buscar_comerciante(self.jugador)
        self.assertEqual(comerciante, npc)
        self.assertIsNone(error)

    def test_varios_comerciantes_da_ambiguedad(self):
        npc1 = create_object("typeclasses.npc.NPC", key="Herrero", location=self.sala)
        npc1.db.tienda = [{"key": "hacha", "precio": 15}]
        npc2 = create_object("typeclasses.npc.NPC", key="Alquimista", location=self.sala)
        npc2.db.tienda = [{"key": "pocion", "precio": 5}]
        comerciante, error = _buscar_comerciante(self.jugador)
        self.assertIsNone(comerciante)
        self.assertIn("varios", error.lower())

    def test_npc_sin_tienda_no_es_comerciante(self):
        obj = create_object("typeclasses.objects.Object", key="piedra", location=self.sala)
        comerciante, error = _buscar_comerciante(self.jugador, "piedra")
        self.assertIsNone(comerciante)
        self.assertIn("comerciante", error.lower())


# --------------------------------------------------------------------------- #
#  CmdTienda
# --------------------------------------------------------------------------- #

class TestCmdTienda(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.monedas = 50
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(text)

        self.npc = create_object("typeclasses.npc.NPC", key="Vendedor", location=self.sala)
        self.npc.db.tienda = [
            {"key": "pocion de vida", "precio": 10, "cantidad": -1, "desc": "Restaura HP."},
        ]

    def test_muestra_nombre_del_comerciante(self):
        cmd = _make_cmd(CmdTienda, self.jugador)
        cmd.func()
        self.assertIn("Vendedor", "\n".join(self.msgs))

    def test_muestra_items_y_precios(self):
        cmd = _make_cmd(CmdTienda, self.jugador)
        cmd.func()
        output = "\n".join(self.msgs)
        self.assertIn("pocion de vida", output)
        self.assertIn("10", output)

    def test_muestra_monedas_del_jugador(self):
        cmd = _make_cmd(CmdTienda, self.jugador)
        cmd.func()
        self.assertIn("50", "\n".join(self.msgs))

    def test_tienda_vacia_muestra_sin_articulos(self):
        self.npc.db.tienda = []
        cmd = _make_cmd(CmdTienda, self.jugador)
        cmd.func()
        self.assertIn("artículos", "\n".join(self.msgs).lower())


# --------------------------------------------------------------------------- #
#  CmdComprar
# --------------------------------------------------------------------------- #

class TestCmdComprar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.monedas = 50
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(text)

        self.npc = create_object("typeclasses.npc.NPC", key="Mercader", location=self.sala)
        self.npc.db.tienda = _tienda_basica()

    def test_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="")
        cmd.func()
        self.assertTrue(any("comprar" in m.lower() for m in self.msgs))

    def test_item_inexistente_da_error(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="arma mitica")
        cmd.func()
        self.assertTrue(any("no vende" in m.lower() for m in self.msgs))

    def test_monedas_insuficientes_da_error(self):
        self.jugador.db.monedas = 5
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        self.assertTrue(any("suficientes" in m.lower() for m in self.msgs))

    def test_compra_descuenta_monedas(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        self.assertEqual(self.jugador.db.monedas, 40)

    def test_compra_coloca_item_en_inventario(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        nombres = [o.key for o in self.jugador.contents]
        self.assertIn("pocion de vida", nombres)

    def test_stock_finito_se_decrementa(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion rara")
        cmd.func()
        entrada = next(e for e in self.npc.db.tienda if "rara" in e.get("key", ""))
        self.assertEqual(entrada["cantidad"], 1)

    def test_stock_ilimitado_no_se_decrementa(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        entrada = next(e for e in self.npc.db.tienda if "vida" in e.get("key", ""))
        self.assertEqual(entrada["cantidad"], -1)

    def test_stock_agotado_da_error(self):
        self.npc.db.tienda = [
            {"key": "pocion de vida", "precio": 10, "cantidad": -1, "valor": 10},
            {"key": "pocion rara",    "precio": 30, "cantidad":  0, "valor": 30},
        ]
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion rara")
        cmd.func()
        self.assertTrue(any("no tiene" in m.lower() for m in self.msgs))

    def test_compra_especificando_npc_por_nombre(self):
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida de Mercader")
        cmd.func()

    def test_nombre_exacto_prioriza_sobre_parcial(self):
        """
        Regresión: la búsqueda del artículo era un substring match que
        devolvía el primer resultado del catálogo, sin priorizar una
        coincidencia exacta. Si "poción de vida mayor" aparecía antes que
        "poción de vida" en la lista, "comprar poción de vida" compraba
        la versión "mayor" en su lugar (mismo defecto que tenía retirar
        del banco, arreglado en 609bbea).
        """
        self.npc.db.tienda = [
            {"key": "pocion de vida mayor", "precio": 30, "cantidad": -1, "valor": 30},
            {"key": "pocion de vida",       "precio": 10, "cantidad": -1, "valor": 10},
        ]
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        nombres = [o.key for o in self.jugador.contents]
        self.assertIn("pocion de vida", nombres)
        self.assertNotIn("pocion de vida mayor", nombres)
        self.assertEqual(self.jugador.db.monedas, 40)

    def test_ambiguo_sin_coincidencia_exacta_avisa(self):
        self.npc.db.tienda = [
            {"key": "pocion de vida mayor", "precio": 30, "cantidad": -1, "valor": 30},
            {"key": "pocion de vida suprema", "precio": 60, "cantidad": -1, "valor": 60},
        ]
        cmd = _make_cmd(CmdComprar, self.jugador, args="pocion de vida")
        cmd.func()
        self.assertTrue(any("ambiguo" in m.lower() for m in self.msgs))
        self.assertEqual(self.jugador.db.monedas, 50)


# --------------------------------------------------------------------------- #
#  CmdVender
# --------------------------------------------------------------------------- #

class TestCmdVender(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.monedas = 20
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(text)

        self.npc = create_object("typeclasses.npc.NPC", key="Comprador", location=self.sala)
        self.npc.db.tienda = [{"key": "algo", "precio": 5}]

        self.item = create_object(
            "typeclasses.objects.Object", key="garra de troll", location=self.jugador
        )
        self.item.db.valor = 10

    def test_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdVender, self.jugador, args="")
        cmd.func()
        self.assertTrue(any("vender" in m.lower() for m in self.msgs))

    def test_venta_añade_monedas(self):
        cmd = _make_cmd(CmdVender, self.jugador, args="garra de troll")
        cmd.func()
        self.assertEqual(self.jugador.db.monedas, 25)  # 20 + 50% de 10 = 5

    def test_venta_elimina_item_del_inventario(self):
        cmd = _make_cmd(CmdVender, self.jugador, args="garra de troll")
        cmd.func()
        self.assertNotIn("garra de troll", [o.key for o in self.jugador.contents])

    def test_precio_minimo_es_uno(self):
        self.item.db.valor = 1
        cmd = _make_cmd(CmdVender, self.jugador, args="garra de troll")
        cmd.func()
        # max(1, int(1) // 2) = 1
        self.assertEqual(self.jugador.db.monedas, 21)

    def test_item_sin_valor_usa_precio_por_defecto(self):
        self.item.db.valor = None
        cmd = _make_cmd(CmdVender, self.jugador, args="garra de troll")
        cmd.func()
        ganancia = max(1, PRECIO_VENTA_DEFAULT // 2)
        self.assertEqual(self.jugador.db.monedas, 20 + ganancia)

    def test_item_equipado_no_se_puede_vender(self):
        anillo = create_object(
            "typeclasses.objects.Equipo", key="anillo test", location=self.jugador
        )
        anillo.db.slot = "accesorio"
        anillo.db.bonuses = {}
        anillo.db.valor = 20
        self.jugador.db.equipamiento = {"arma": None, "armadura": None, "accesorio": anillo}

        cmd = _make_cmd(CmdVender, self.jugador, args="anillo test")
        cmd.func()
        self.assertTrue(any("equipado" in m.lower() for m in self.msgs))
        self.assertIn(anillo, self.jugador.contents)

    def test_item_no_en_inventario_no_da_monedas(self):
        cmd = _make_cmd(CmdVender, self.jugador, args="espada inexistente")
        cmd.func()
        self.assertEqual(self.jugador.db.monedas, 20)
