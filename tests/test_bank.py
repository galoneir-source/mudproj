"""
tests/test_bank.py

Tests de integración para features/bank/commands.py.
Ejecutar con:
  cd mygame && ../venv/bin/evennia test --settings settings.py tests.test_bank
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.bank.commands import CmdBanco, CmdDepositar, CmdRetirar
from typeclasses.objects import Object, Equipo


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


def _item(nombre, location, typeclass=None):
    tc = typeclass or Object
    return create_object(tc, key=nombre, location=location)


def _banquero(location):
    npc = create_object("typeclasses.npc.NPC", key="Cornelio el Banquero", location=location)
    npc.db.es_banquero = True
    npc.db.temperamento = "neutral"
    npc.db.nivel = 1
    npc.db.hp = 50
    npc.db.hp_max = 50
    return npc


# --------------------------------------------------------------------------- #
#  CmdBanco
# --------------------------------------------------------------------------- #

class TestCmdBanco(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.banquero = _banquero(self.room1)

    def test_banco_vacio_no_explota(self):
        _make_cmd(CmdBanco, self.char1).func()

    def test_banco_muestra_items_depositados(self):
        item = _item("espada de hierro", self.char1)
        _make_cmd(CmdDepositar, self.char1, "espada de hierro").func()
        _make_cmd(CmdBanco, self.char1).func()
        # Item debe estar en banco
        banco = list(self.char1.db.banco or [])
        self.assertIn(item, banco)

    def test_banco_sin_banquero_no_funciona(self):
        self.banquero.location = None
        _make_cmd(CmdBanco, self.char1).func()
        # Debe ignorarse silenciosamente (no crashear)


# --------------------------------------------------------------------------- #
#  CmdDepositar
# --------------------------------------------------------------------------- #

class TestCmdDepositar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.banquero = _banquero(self.room1)

    def test_depositar_item_sale_del_inventario(self):
        item = _item("poción de vida", self.char1)
        _make_cmd(CmdDepositar, self.char1, "poción de vida").func()
        self.assertNotIn(item, self.char1.contents)

    def test_depositar_item_va_al_banco(self):
        item = _item("daga", self.char1)
        _make_cmd(CmdDepositar, self.char1, "daga").func()
        banco = list(self.char1.db.banco or [])
        self.assertIn(item, banco)

    def test_depositar_item_location_es_none(self):
        item = _item("poción", self.char1)
        _make_cmd(CmdDepositar, self.char1, "poción").func()
        self.assertIsNone(item.location)

    def test_depositar_item_equipado_falla(self):
        item = _item("espada de hierro", self.char1)
        self.char1.db.equipamiento = {"arma": item, "armadura": None, "accesorio": None}
        _make_cmd(CmdDepositar, self.char1, "espada de hierro").func()
        self.assertIn(item, self.char1.contents)
        banco = list(self.char1.db.banco or [])
        self.assertNotIn(item, banco)

    def test_depositar_sin_banquero_falla(self):
        self.banquero.location = None
        item = _item("daga", self.char1)
        _make_cmd(CmdDepositar, self.char1, "daga").func()
        self.assertIn(item, self.char1.contents)
        banco = list(self.char1.db.banco or [])
        self.assertNotIn(item, banco)

    def test_depositar_sin_args_no_explota(self):
        _make_cmd(CmdDepositar, self.char1, "").func()

    def test_depositar_item_inexistente_no_explota(self):
        _make_cmd(CmdDepositar, self.char1, "objeto que no existe").func()

    def test_depositar_multiples_items(self):
        _item("espada", self.char1)
        _item("daga", self.char1)
        _make_cmd(CmdDepositar, self.char1, "espada").func()
        _make_cmd(CmdDepositar, self.char1, "daga").func()
        banco = list(self.char1.db.banco or [])
        self.assertEqual(len(banco), 2)

    def test_depositar_marca_propietario(self):
        item = _item("espada", self.char1)
        _make_cmd(CmdDepositar, self.char1, "espada").func()
        self.assertEqual(item.db.banco_propietario, self.char1.id)


# --------------------------------------------------------------------------- #
#  CmdRetirar
# --------------------------------------------------------------------------- #

class TestCmdRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.banquero = _banquero(self.room1)

    def _depositar(self, nombre):
        item = _item(nombre, self.char1)
        _make_cmd(CmdDepositar, self.char1, nombre).func()
        return item

    def test_retirar_item_vuelve_al_inventario(self):
        item = self._depositar("poción de vida")
        _make_cmd(CmdRetirar, self.char1, "poción de vida").func()
        self.assertIn(item, self.char1.contents)

    def test_retirar_item_sale_del_banco(self):
        self._depositar("espada")
        _make_cmd(CmdRetirar, self.char1, "espada").func()
        banco = list(self.char1.db.banco or [])
        self.assertEqual(len(banco), 0)

    def test_retirar_limpia_propietario(self):
        item = self._depositar("espada")
        _make_cmd(CmdRetirar, self.char1, "espada").func()
        self.assertIsNone(item.db.banco_propietario)

    def test_retirar_banco_vacio_no_explota(self):
        _make_cmd(CmdRetirar, self.char1, "algo").func()

    def test_retirar_sin_banquero_falla(self):
        item = self._depositar("daga")
        self.banquero.location = None
        _make_cmd(CmdRetirar, self.char1, "daga").func()
        banco = list(self.char1.db.banco or [])
        self.assertIn(item, banco)

    def test_retirar_item_inexistente_no_explota(self):
        self._depositar("espada")
        _make_cmd(CmdRetirar, self.char1, "poción inventada").func()
        banco = list(self.char1.db.banco or [])
        self.assertEqual(len(banco), 1)

    def test_retirar_sin_args_no_explota(self):
        _make_cmd(CmdRetirar, self.char1, "").func()

    def test_retirar_uno_de_varios(self):
        self._depositar("espada")
        self._depositar("daga")
        self._depositar("poción")
        _make_cmd(CmdRetirar, self.char1, "daga").func()
        banco = list(self.char1.db.banco or [])
        self.assertEqual(len(banco), 2)

    def test_retirar_parcial_nombre(self):
        item = self._depositar("poción de vida mayor")
        _make_cmd(CmdRetirar, self.char1, "poción").func()
        self.assertIn(item, self.char1.contents)

    def test_retirar_exacto_prioriza_sobre_parcial_aunque_llegue_despues(self):
        """
        Regresión: el matching original solo hacía substring
        (args_lower in it.key.lower()) y devolvía el primer resultado en
        orden de lista, sin priorizar una coincidencia exacta. Si el
        objeto de nombre más largo se depositaba primero, "retirar poción
        de vida" devolvía "poción de vida mayor" en su lugar — el jugador
        pedía un objeto exacto y recibía uno distinto (más valioso o no)
        según el orden de depósito, no según lo que escribió.
        """
        mayor = self._depositar("poción de vida mayor")
        normal = self._depositar("poción de vida")
        _make_cmd(CmdRetirar, self.char1, "poción de vida").func()
        self.assertIn(normal, self.char1.contents)
        self.assertNotIn(mayor, self.char1.contents)

    def test_retirar_dos_items_con_nombre_identico(self):
        """
        Regresión candidata: si hay DOS objetos con el mismo nombre exacto
        en el banco (p.ej. dos pociones de vida idénticas), 'exactas' tiene
        longitud 2 -> no entra por la rama de coincidencia única y cae al
        fallback de 'parciales', que también encuentra las mismas 2
        coincidencias (el nombre exacto siempre es substring de sí mismo)
        -> siempre se considera ambiguo. Como ambas se llaman igual, no hay
        ninguna forma de "ser más específico": el jugador no puede volver
        a sacar NINGUNA de las dos del banco.
        """
        item1 = self._depositar("poción de vida")
        item2 = _item("poción de vida", self.char1)
        _make_cmd(CmdDepositar, self.char1, "poción de vida").func()

        _make_cmd(CmdRetirar, self.char1, "poción de vida").func()

        self.assertTrue(
            item1 in self.char1.contents or item2 in self.char1.contents,
            "Ninguna de las dos pociones idénticas pudo retirarse del banco.",
        )

    def test_retirar_ambiguo_sin_coincidencia_exacta_avisa_y_no_retira(self):
        mayor = self._depositar("poción de vida mayor")
        suprema = self._depositar("poción de vida suprema")
        _make_cmd(CmdRetirar, self.char1, "poción de vida").func()
        banco = list(self.char1.db.banco or [])
        self.assertEqual(len(banco), 2)
        self.assertNotIn(mayor, self.char1.contents)
        self.assertNotIn(suprema, self.char1.contents)
