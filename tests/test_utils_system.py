"""
tests/test_utils_system.py

Tests unitarios para systems/utils.py (barra de progreso).
No dependen de Evennia.
"""
import unittest

from systems.utils import barra


class TestBarra(unittest.TestCase):

    def test_llena(self):
        resultado = barra(20, 20, 20)
        self.assertIn("█" * 20, resultado)
        self.assertNotIn("░", resultado)

    def test_vacia(self):
        resultado = barra(0, 20, 20)
        self.assertIn("░" * 20, resultado)
        self.assertNotIn("█", resultado)

    def test_mitad(self):
        resultado = barra(10, 20, 20)
        self.assertIn("█" * 10, resultado)
        self.assertIn("░" * 10, resultado)

    def test_maximo_cero_no_explota(self):
        resultado = barra(0, 0, 20)
        self.assertIsInstance(resultado, str)

    def test_actual_mayor_que_maximo(self):
        # No debe lanzar excepción ni dar barras negativas
        resultado = barra(30, 20, 20)
        self.assertIsInstance(resultado, str)
        self.assertNotIn("░", resultado)

    def test_color_explicito(self):
        resultado = barra(10, 20, 20, "|r")
        self.assertIn("|r", resultado)

    def test_color_automatico_verde_mayoritario(self):
        resultado = barra(16, 20, 20)  # 80 % → verde
        self.assertIn("|g", resultado)

    def test_color_automatico_amarillo(self):
        resultado = barra(7, 20, 20)  # 35 % → amarillo
        self.assertIn("|y", resultado)

    def test_color_automatico_rojo(self):
        resultado = barra(2, 20, 20)  # 10 % → rojo
        self.assertIn("|r", resultado)

    def test_largo_personalizado(self):
        resultado = barra(5, 10, largo=10)
        # 5 llenas + 5 vacías
        self.assertIn("█" * 5, resultado)
        self.assertIn("░" * 5, resultado)

    def test_formato_corchetes(self):
        resultado = barra(10, 20, 20)
        self.assertTrue(resultado.strip().startswith("["))
        self.assertTrue(resultado.strip().endswith("]"))


if __name__ == "__main__":
    unittest.main()
