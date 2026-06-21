"""
tests/test_mercado.py

Tests unitarios puros para el sistema de mercado de jugadores (v0.25.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_mercado.py
"""
import unittest

from systems.market.market import (
    MAX_LISTINGS_POR_JUGADOR,
    PRECIO_MAX,
    PRECIO_MIN,
    COMISION_PCT,
    calcular_comision,
    calcular_ganancia,
    formatear_listing,
    validar_precio,
    _fmt,
)


# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

class TestConstantes(unittest.TestCase):

    def test_max_listings_positivo(self):
        self.assertGreater(MAX_LISTINGS_POR_JUGADOR, 0)

    def test_precio_min_es_uno(self):
        self.assertEqual(PRECIO_MIN, 1)

    def test_precio_max_mayor_que_min(self):
        self.assertGreater(PRECIO_MAX, PRECIO_MIN)

    def test_comision_pct_entre_0_y_100(self):
        self.assertGreater(COMISION_PCT, 0)
        self.assertLess(COMISION_PCT, 100)


# --------------------------------------------------------------------------- #
#  validar_precio
# --------------------------------------------------------------------------- #

class TestValidarPrecio(unittest.TestCase):

    def test_precio_minimo_valido(self):
        ok, _ = validar_precio(PRECIO_MIN)
        self.assertTrue(ok)

    def test_precio_maximo_valido(self):
        ok, _ = validar_precio(PRECIO_MAX)
        self.assertTrue(ok)

    def test_precio_normal_valido(self):
        ok, _ = validar_precio(500)
        self.assertTrue(ok)

    def test_precio_cero_invalido(self):
        ok, msg = validar_precio(0)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_precio_negativo_invalido(self):
        ok, msg = validar_precio(-10)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_precio_sobre_maximo_invalido(self):
        ok, msg = validar_precio(PRECIO_MAX + 1)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_precio_string_numero_valido(self):
        ok, _ = validar_precio("200")
        self.assertTrue(ok)

    def test_precio_string_invalido(self):
        ok, msg = validar_precio("mucho")
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_precio_none_invalido(self):
        ok, msg = validar_precio(None)
        self.assertFalse(ok)
        self.assertTrue(msg)

    def test_precio_float_string_invalido(self):
        ok, _ = validar_precio("9.99")
        self.assertFalse(ok)

    def test_precio_uno_valido(self):
        ok, _ = validar_precio(1)
        self.assertTrue(ok)

    def test_error_contiene_info(self):
        _, msg = validar_precio(-5)
        self.assertIsInstance(msg, str)
        self.assertGreater(len(msg), 0)


# --------------------------------------------------------------------------- #
#  calcular_comision
# --------------------------------------------------------------------------- #

class TestCalcularComision(unittest.TestCase):

    def test_comision_100_es_5(self):
        self.assertEqual(calcular_comision(100), 5)

    def test_comision_200_es_10(self):
        self.assertEqual(calcular_comision(200), 10)

    def test_comision_1_redondea_arriba(self):
        # 5% de 1 = 0.05 → ceil → 1
        self.assertEqual(calcular_comision(1), 1)

    def test_comision_10_es_1(self):
        # 5% de 10 = 0.5 → ceil → 1
        self.assertEqual(calcular_comision(10), 1)

    def test_comision_20_es_1(self):
        self.assertEqual(calcular_comision(20), 1)

    def test_comision_21_es_2(self):
        # 5% de 21 = 1.05 → ceil → 2
        self.assertEqual(calcular_comision(21), 2)

    def test_comision_1000_es_50(self):
        self.assertEqual(calcular_comision(1000), 50)

    def test_comision_no_supera_precio(self):
        for p in [1, 10, 100, 1000, 99999]:
            self.assertLessEqual(calcular_comision(p), p)

    def test_comision_siempre_positiva(self):
        for p in [1, 5, 100, 999]:
            self.assertGreater(calcular_comision(p), 0)


# --------------------------------------------------------------------------- #
#  calcular_ganancia
# --------------------------------------------------------------------------- #

class TestCalcularGanancia(unittest.TestCase):

    def test_ganancia_100(self):
        self.assertEqual(calcular_ganancia(100), 95)

    def test_ganancia_200(self):
        self.assertEqual(calcular_ganancia(200), 190)

    def test_ganancia_1000(self):
        self.assertEqual(calcular_ganancia(1000), 950)

    def test_ganancia_menor_que_precio(self):
        for p in [10, 100, 500]:
            self.assertLess(calcular_ganancia(p), p)

    def test_ganancia_mas_comision_igual_precio(self):
        for p in [100, 200, 500, 1000]:
            self.assertEqual(calcular_ganancia(p) + calcular_comision(p), p)

    def test_ganancia_no_negativa(self):
        for p in [1, 2, 10, 100]:
            self.assertGreaterEqual(calcular_ganancia(p), 0)


# --------------------------------------------------------------------------- #
#  formatear_listing
# --------------------------------------------------------------------------- #

class TestFormatearListing(unittest.TestCase):

    def test_devuelve_string(self):
        self.assertIsInstance(formatear_listing("1", "Aragorn", "espada", 100), str)

    def test_contiene_id(self):
        linea = formatear_listing("5", "A", "espada", 100)
        self.assertIn("5", linea)

    def test_contiene_vendedor(self):
        linea = formatear_listing("1", "Gandalf", "vara arcana", 200)
        self.assertIn("Gandalf", linea)

    def test_contiene_item(self):
        linea = formatear_listing("1", "V", "daga de acero", 50)
        self.assertIn("daga de acero", linea)

    def test_contiene_precio(self):
        linea = formatear_listing("1", "V", "item", 999)
        self.assertIn("999", linea)

    def test_precio_con_separador_miles(self):
        linea = formatear_listing("1", "V", "item", 1500)
        self.assertIn("1.500", linea)

    def test_precio_mas_de_un_millon(self):
        linea = formatear_listing("2", "V", "item", 1_000_000)
        self.assertIn("1.000.000", linea)


# --------------------------------------------------------------------------- #
#  _fmt (helper de formateo)
# --------------------------------------------------------------------------- #

class TestFmt(unittest.TestCase):

    def test_cero(self):
        self.assertEqual(_fmt(0), "0")

    def test_menos_de_mil(self):
        self.assertEqual(_fmt(999), "999")

    def test_exactamente_mil(self):
        self.assertEqual(_fmt(1000), "1.000")

    def test_millon(self):
        self.assertEqual(_fmt(1_000_000), "1.000.000")

    def test_usa_punto_como_separador(self):
        self.assertIn(".", _fmt(10000))

    def test_no_usa_coma(self):
        self.assertNotIn(",", _fmt(10000))


if __name__ == "__main__":
    unittest.main()
