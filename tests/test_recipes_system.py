"""
tests/test_recipes_system.py

Tests unitarios para systems/crafting/recipes.py.
No dependen de Evennia ni Django — se ejecutan con unittest estándar.
"""
import unittest

from systems.crafting.recipes import RECETAS, buscar_receta, verificar_ingredientes


class TestBuscarReceta(unittest.TestCase):

    def test_exacto(self):
        nombre, receta = buscar_receta("poción de vida")
        self.assertEqual(nombre, "poción de vida")
        self.assertIsNotNone(receta)

    def test_exacto_case_insensitive(self):
        nombre, receta = buscar_receta("POCIÓN DE VIDA")
        self.assertEqual(nombre, "poción de vida")

    def test_parcial_startswith(self):
        nombre, receta = buscar_receta("antí")
        self.assertEqual(nombre, "antídoto")

    def test_parcial_contains(self):
        nombre, receta = buscar_receta("restauración")
        self.assertEqual(nombre, "elixir de restauración")

    def test_inexistente_devuelve_none(self):
        nombre, receta = buscar_receta("receta inventada")
        self.assertIsNone(nombre)
        self.assertIsNone(receta)

    def test_ambiguo_devuelve_none(self):
        # "vida" aparece en "poción de vida" y "poción de vida mayor"
        nombre, receta = buscar_receta("vida")
        self.assertIsNone(nombre)

    def test_exacto_no_ambiguo(self):
        # "poción de vida" exacto no debe resolver como "poción de vida mayor"
        nombre, receta = buscar_receta("poción de vida")
        self.assertEqual(nombre, "poción de vida")

    def test_todas_las_recetas_son_buscables(self):
        for nombre in RECETAS:
            found_nombre, found_receta = buscar_receta(nombre)
            self.assertEqual(found_nombre, nombre, f"Receta '{nombre}' no encontrada")


class TestVerificarIngredientes(unittest.TestCase):

    def _receta(self, nombre):
        return RECETAS[nombre]

    def test_ingredientes_exactos_ok(self):
        inventario = {"piel de serpiente": 1}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("poción de vida"))
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_ingredientes_de_mas_ok(self):
        inventario = {"piel de serpiente": 5}
        ok, _ = verificar_ingredientes(inventario, self._receta("poción de vida"))
        self.assertTrue(ok)

    def test_ingrediente_faltante(self):
        inventario = {}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("poción de vida"))
        self.assertFalse(ok)
        self.assertIn("piel de serpiente", faltantes)
        self.assertEqual(faltantes["piel de serpiente"], 1)

    def test_faltante_parcial(self):
        # Necesita 2 escamas, solo tiene 1
        inventario = {"escama de lagarto": 1, "fragmento de alma": 1}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("elixir de restauración"))
        self.assertFalse(ok)
        self.assertEqual(faltantes["escama de lagarto"], 1)

    def test_multiples_ingredientes_ok(self):
        inventario = {"piel de serpiente": 1, "veneno de pantano": 1}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("antídoto"))
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_multiples_ingredientes_falta_uno(self):
        inventario = {"piel de serpiente": 1}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("antídoto"))
        self.assertFalse(ok)
        self.assertIn("veneno de pantano", faltantes)

    def test_inventario_vacio_todo_falta(self):
        inventario = {}
        ok, faltantes = verificar_ingredientes(inventario, self._receta("elixir de restauración"))
        self.assertFalse(ok)
        self.assertEqual(len(faltantes), 2)

    def test_case_insensitive_inventario(self):
        # El inventario normalizado a lowercase debe funcionar
        inventario = {"piel de serpiente": 1}
        ok, _ = verificar_ingredientes(inventario, self._receta("poción de vida"))
        self.assertTrue(ok)


class TestEstructuraRecetas(unittest.TestCase):

    def test_todas_tienen_campos_requeridos(self):
        for nombre, receta in RECETAS.items():
            self.assertIn("ingredientes", receta, f"{nombre} sin 'ingredientes'")
            self.assertIn("resultado_prototipo", receta, f"{nombre} sin 'resultado_prototipo'")
            self.assertIn("cantidad", receta, f"{nombre} sin 'cantidad'")
            self.assertIn("desc_receta", receta, f"{nombre} sin 'desc_receta'")

    def test_ingredientes_son_positivos(self):
        for nombre, receta in RECETAS.items():
            for ingr, cant in receta["ingredientes"].items():
                self.assertGreater(cant, 0, f"{nombre}: ingrediente '{ingr}' con cantidad <= 0")

    def test_cantidad_resultado_positivo(self):
        for nombre, receta in RECETAS.items():
            self.assertGreater(receta["cantidad"], 0, f"{nombre}: cantidad resultado <= 0")


if __name__ == "__main__":
    unittest.main()
