"""
tests/test_crafteo.py

Tests de integración para features/crafting/commands.py.
Ejecutar con:
  evennia test --settings settings.py tests.test_crafteo
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.crafting.commands import CmdCraftear, CmdRecetas
from typeclasses.objects import Object, Consumible


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

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


def _item(nombre, location):
    return create_object(Object, key=nombre, location=location)


# --------------------------------------------------------------------------- #
#  CmdCraftear — casos básicos
# --------------------------------------------------------------------------- #

class TestCmdCraftear(EvenniaTest):

    def _craftear(self, args):
        _make_cmd(CmdCraftear, self.char1, args).func()

    def test_sin_args_no_explota(self):
        self._craftear("")

    def test_receta_inexistente(self):
        self._craftear("poción mágica inventada")
        # No debe crear nada en el inventario
        self.assertEqual(len(self.char1.contents), 0)

    def test_sin_ingredientes_no_craftea(self):
        self._craftear("poción de vida")
        self.assertEqual(len(self.char1.contents), 0)

    def test_ingredientes_insuficientes_no_craftea(self):
        # Necesita 2 escamas; solo tiene 1
        _item("escama de lagarto", self.char1)
        _item("fragmento de alma", self.char1)
        antes = len(self.char1.contents)
        self._craftear("elixir de restauración")
        # Ingredientes no consumidos
        self.assertEqual(len(self.char1.contents), antes)

    def test_crafteo_basico_crea_consumible(self):
        _item("piel de serpiente", self.char1)
        self._craftear("poción de vida")
        consumibles = [o for o in self.char1.contents if isinstance(o, Consumible)]
        self.assertEqual(len(consumibles), 1)
        self.assertEqual(consumibles[0].key, "poción de vida")

    def test_crafteo_consume_ingredientes(self):
        _item("piel de serpiente", self.char1)
        self._craftear("poción de vida")
        pieles = [o for o in self.char1.contents if o.key == "piel de serpiente"]
        self.assertEqual(len(pieles), 0)

    def test_crafteo_multiples_ingredientes(self):
        _item("piel de serpiente", self.char1)
        _item("veneno de pantano", self.char1)
        self._craftear("antídoto")
        consumibles = [o for o in self.char1.contents if isinstance(o, Consumible)]
        self.assertEqual(len(consumibles), 2)  # antídoto produce 2

    def test_crafteo_antidoto_consume_ambos_ingredientes(self):
        _item("piel de serpiente", self.char1)
        _item("veneno de pantano", self.char1)
        self._craftear("antídoto")
        self.assertEqual(
            len([o for o in self.char1.contents if o.key == "piel de serpiente"]), 0
        )
        self.assertEqual(
            len([o for o in self.char1.contents if o.key == "veneno de pantano"]), 0
        )

    def test_crafteo_elixir_requiere_dos_escamas(self):
        _item("escama de lagarto", self.char1)
        _item("escama de lagarto", self.char1)
        _item("fragmento de alma", self.char1)
        self._craftear("elixir de restauración")
        consumibles = [o for o in self.char1.contents if isinstance(o, Consumible)]
        self.assertEqual(len(consumibles), 1)
        self.assertEqual(consumibles[0].key, "elixir de restauración")

    def test_crafteo_no_consume_items_equipados(self):
        piel = _item("piel de serpiente", self.char1)
        # Simular que está equipado
        self.char1.db.equipamiento = {"arma": piel}
        self._craftear("poción de vida")
        # La piel no debe haberse consumido
        self.assertIn(piel, self.char1.contents)

    def test_crafteo_parcial_nombre(self):
        # "elixir" debería encontrar "elixir de restauración"
        _item("escama de lagarto", self.char1)
        _item("escama de lagarto", self.char1)
        _item("fragmento de alma", self.char1)
        self._craftear("elixir")
        consumibles = [o for o in self.char1.contents if isinstance(o, Consumible)]
        self.assertEqual(len(consumibles), 1)

    def test_ingredientes_sobrantes_no_consumidos(self):
        # Tiene 3 pieles, solo necesita 1
        for _ in range(3):
            _item("piel de serpiente", self.char1)
        self._craftear("poción de vida")
        pieles = [o for o in self.char1.contents if o.key == "piel de serpiente"]
        self.assertEqual(len(pieles), 2)

    def test_crafteo_pocion_vida_mayor(self):
        _item("garra de troll", self.char1)
        _item("piel de serpiente", self.char1)
        self._craftear("poción de vida mayor")
        consumibles = [o for o in self.char1.contents if isinstance(o, Consumible)]
        self.assertEqual(len(consumibles), 1)
        self.assertEqual(consumibles[0].db.potencia, 60)


# --------------------------------------------------------------------------- #
#  CmdRecetas — listado y consulta
# --------------------------------------------------------------------------- #

class TestCmdRecetas(EvenniaTest):

    def _recetas(self, args=""):
        _make_cmd(CmdRecetas, self.char1, args).func()

    def test_listar_no_explota(self):
        self._recetas()

    def test_consulta_especifica_no_explota(self):
        self._recetas("antídoto")

    def test_consulta_inexistente_no_explota(self):
        self._recetas("ingrediente fantasma")
