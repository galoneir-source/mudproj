"""
tests/test_bank_system.py

Tests unitarios puros para systems/bank/bank.py.
No requieren Evennia ni Django.
Ejecutar con: python -m pytest tests/test_bank_system.py
"""
import unittest
from unittest.mock import MagicMock


class _DeadItem:
    """Simula un objeto Evennia eliminado: acceder a .key lanza AttributeError."""
    @property
    def key(self):
        raise AttributeError("Object deleted")


def _item(nombre="espada de hierro"):
    obj = MagicMock()
    obj.key = nombre
    return obj


class TestPuedeDepositar(unittest.TestCase):

    def test_item_normal_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        item = _item()
        eq = {"arma": None, "armadura": None, "accesorio": None}
        puede, razon = puede_depositar(item, eq)
        self.assertTrue(puede)
        self.assertEqual(razon, "")

    def test_item_none_no_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        puede, razon = puede_depositar(None, {})
        self.assertFalse(puede)
        self.assertIn("existe", razon)

    def test_item_equipado_en_arma_no_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        item = _item()
        eq = {"arma": item, "armadura": None, "accesorio": None}
        puede, razon = puede_depositar(item, eq)
        self.assertFalse(puede)
        self.assertIn("equipado", razon)

    def test_item_equipado_en_armadura_no_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        item = _item("cota de malla")
        eq = {"arma": None, "armadura": item, "accesorio": None}
        puede, razon = puede_depositar(item, eq)
        self.assertFalse(puede)

    def test_item_equipado_en_accesorio_no_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        item = _item("anillo de destreza")
        eq = {"arma": None, "armadura": None, "accesorio": item}
        puede, razon = puede_depositar(item, eq)
        self.assertFalse(puede)

    def test_otro_item_equipado_no_bloquea(self):
        from systems.bank.bank import puede_depositar
        item1 = _item("espada")
        item2 = _item("daga")
        eq = {"arma": item1, "armadura": None, "accesorio": None}
        puede, razon = puede_depositar(item2, eq)
        self.assertTrue(puede)
        self.assertEqual(razon, "")

    def test_equipo_vacio_puede_depositar(self):
        from systems.bank.bank import puede_depositar
        item = _item()
        puede, razon = puede_depositar(item, {})
        self.assertTrue(puede)

    def test_mensaje_error_incluye_nombre_item(self):
        from systems.bank.bank import puede_depositar
        item = _item("báculo arcano antiguo")
        eq = {"arma": item}
        puede, razon = puede_depositar(item, eq)
        self.assertFalse(puede)
        self.assertIn("báculo arcano antiguo", razon)


class TestLimpiarBanco(unittest.TestCase):

    def test_lista_vacia(self):
        from systems.bank.bank import limpiar_banco
        self.assertEqual(limpiar_banco([]), [])

    def test_items_validos_se_mantienen(self):
        from systems.bank.bank import limpiar_banco
        item1 = _item("espada")
        item2 = _item("daga")
        result = limpiar_banco([item1, item2])
        self.assertEqual(len(result), 2)
        self.assertIn(item1, result)
        self.assertIn(item2, result)

    def test_items_muertos_se_eliminan(self):
        from systems.bank.bank import limpiar_banco
        item_vivo = _item("espada")
        item_muerto = _DeadItem()
        result = limpiar_banco([item_vivo, item_muerto])
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], item_vivo)

    def test_todos_muertos_devuelve_vacio(self):
        from systems.bank.bank import limpiar_banco
        result = limpiar_banco([_DeadItem()])
        self.assertEqual(result, [])

    def test_devuelve_nueva_lista(self):
        from systems.bank.bank import limpiar_banco
        original = [_item()]
        result = limpiar_banco(original)
        self.assertIsNot(result, original)

    def test_orden_se_preserva(self):
        from systems.bank.bank import limpiar_banco
        items = [_item(f"item{i}") for i in range(5)]
        result = limpiar_banco(items)
        self.assertEqual(result, items)

    def test_item_muerto_en_medio(self):
        from systems.bank.bank import limpiar_banco
        a = _item("a")
        b = _item("b")
        result = limpiar_banco([a, _DeadItem(), b])
        self.assertEqual(len(result), 2)
        self.assertEqual(result, [a, b])


if __name__ == "__main__":
    unittest.main()
