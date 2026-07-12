"""
tests/test_duelos_system.py

Tests unitarios puros para el sistema de duelos entre jugadores (v0.21.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_duelos_system.py
"""
import unittest

from systems.duels.duels import (
    DUEL_TIMEOUT,
    HP_DUEL_MIN_PCT,
    calcular_hp_umbral,
    formatear_resultado,
    reto_expirado,
    validar_apuesta,
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

class TestConstantes(unittest.TestCase):

    def test_timeout_es_positivo(self):
        self.assertGreater(DUEL_TIMEOUT, 0)

    def test_timeout_es_entero(self):
        self.assertIsInstance(DUEL_TIMEOUT, int)

    def test_hp_min_pct_en_rango(self):
        self.assertGreater(HP_DUEL_MIN_PCT, 0.0)
        self.assertLess(HP_DUEL_MIN_PCT, 1.0)

    def test_hp_min_pct_es_10_pct(self):
        self.assertAlmostEqual(HP_DUEL_MIN_PCT, 0.10)


# ---------------------------------------------------------------------------
# validar_apuesta
# ---------------------------------------------------------------------------

class TestValidarApuesta(unittest.TestCase):

    def test_apuesta_cero_siempre_valida(self):
        ok, _ = validar_apuesta(0, 0, 0)
        self.assertTrue(ok)

    def test_apuesta_cero_fondos_suficientes(self):
        ok, _ = validar_apuesta(100, 100, 0)
        self.assertTrue(ok)

    def test_ambos_con_fondos_suficientes(self):
        ok, _ = validar_apuesta(50, 50, 30)
        self.assertTrue(ok)

    def test_apuesta_exacta_al_limite_retador(self):
        ok, _ = validar_apuesta(30, 100, 30)
        self.assertTrue(ok)

    def test_apuesta_exacta_al_limite_retado(self):
        ok, _ = validar_apuesta(100, 30, 30)
        self.assertTrue(ok)

    def test_ambos_exactamente_al_limite(self):
        ok, _ = validar_apuesta(30, 30, 30)
        self.assertTrue(ok)

    def test_retador_sin_fondos(self):
        ok, motivo = validar_apuesta(10, 100, 30)
        self.assertFalse(ok)
        self.assertIn("30", motivo)

    def test_retado_sin_fondos(self):
        ok, motivo = validar_apuesta(100, 10, 30)
        self.assertFalse(ok)
        self.assertIn("30", motivo)

    def test_apuesta_negativa_invalida(self):
        ok, _ = validar_apuesta(100, 100, -1)
        self.assertFalse(ok)

    def test_mensaje_vacio_cuando_valido(self):
        _, motivo = validar_apuesta(50, 50, 20)
        self.assertEqual(motivo, "")

    def test_mensaje_menciona_cantidad_retador(self):
        _, motivo = validar_apuesta(5, 100, 50)
        self.assertIn("50", motivo)

    def test_mensaje_menciona_cantidad_retado(self):
        _, motivo = validar_apuesta(100, 5, 50)
        self.assertIn("50", motivo)

    def test_retador_con_cero_monedas_y_apuesta_positiva(self):
        ok, _ = validar_apuesta(0, 100, 1)
        self.assertFalse(ok)

    def test_retado_con_cero_monedas_y_apuesta_positiva(self):
        ok, _ = validar_apuesta(100, 0, 1)
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# calcular_hp_umbral
# ---------------------------------------------------------------------------

class TestCalcularHpUmbral(unittest.TestCase):

    def test_hp_100_da_10(self):
        self.assertEqual(calcular_hp_umbral(100), 10)

    def test_hp_200_da_20(self):
        self.assertEqual(calcular_hp_umbral(200), 20)

    def test_hp_50_da_5(self):
        self.assertEqual(calcular_hp_umbral(50), 5)

    def test_hp_10_da_1(self):
        self.assertEqual(calcular_hp_umbral(10), 1)

    def test_hp_9_da_1_por_floor(self):
        # int(9 * 0.10) = 0 → max(1, 0) = 1
        self.assertEqual(calcular_hp_umbral(9), 1)

    def test_hp_11_da_1_por_floor(self):
        # int(11 * 0.10) = int(1.1) = 1
        self.assertEqual(calcular_hp_umbral(11), 1)

    def test_hp_20_da_2(self):
        self.assertEqual(calcular_hp_umbral(20), 2)

    def test_hp_1_da_1_minimo(self):
        self.assertEqual(calcular_hp_umbral(1), 1)

    def test_resultado_siempre_positivo(self):
        for hp in range(1, 201):
            self.assertGreater(calcular_hp_umbral(hp), 0)

    def test_nunca_devuelve_cero(self):
        self.assertGreater(calcular_hp_umbral(5), 0)
        self.assertGreater(calcular_hp_umbral(1), 0)


# ---------------------------------------------------------------------------
# formatear_resultado
# ---------------------------------------------------------------------------

class TestFormatearResultado(unittest.TestCase):

    def test_devuelve_string(self):
        resultado = formatear_resultado("Alfa", "Beta", 0)
        self.assertIsInstance(resultado, str)

    def test_contiene_nombre_ganador(self):
        resultado = formatear_resultado("Gandalf", "Saruman", 0)
        self.assertIn("Gandalf", resultado)

    def test_contiene_nombre_perdedor(self):
        resultado = formatear_resultado("Gandalf", "Saruman", 0)
        self.assertIn("Saruman", resultado)

    def test_sin_apuesta_no_menciona_pago(self):
        resultado = formatear_resultado("A", "B", 0)
        self.assertNotIn("monedas", resultado)
        self.assertNotIn("paga", resultado)

    def test_con_apuesta_menciona_monto(self):
        resultado = formatear_resultado("A", "B", 50)
        self.assertIn("50", resultado)

    def test_con_apuesta_menciona_pago(self):
        resultado = formatear_resultado("A", "B", 50)
        self.assertIn("paga", resultado)

    def test_contiene_marcador_visual(self):
        resultado = formatear_resultado("A", "B", 0)
        self.assertIn("DUELO", resultado.upper())

    def test_apuesta_cero_equivalente_a_sin_apuesta(self):
        r1 = formatear_resultado("A", "B", 0)
        r2 = formatear_resultado("A", "B", None)  # None también es falsy
        # Ambas no deben mencionar monedas
        self.assertNotIn("monedas", r1)
        self.assertNotIn("monedas", r2)


# ---------------------------------------------------------------------------
# reto_expirado
# ---------------------------------------------------------------------------

class TestRetoExpirado(unittest.TestCase):

    def test_reciente_no_expirado(self):
        self.assertFalse(reto_expirado(1000.0, 1050.0))

    def test_justo_antes_no_expirado(self):
        # 59 segundos → no expirado
        self.assertFalse(reto_expirado(1000.0, 1059.0))

    def test_exactamente_en_limite_expirado(self):
        # >= DUEL_TIMEOUT → expirado
        self.assertTrue(reto_expirado(1000.0, 1000.0 + DUEL_TIMEOUT))

    def test_pasado_expirado(self):
        self.assertTrue(reto_expirado(1000.0, 1100.0))

    def test_muy_viejo_expirado(self):
        self.assertTrue(reto_expirado(0.0, 100_000.0))

    def test_mismo_instante_no_expirado(self):
        # 0 segundos transcurridos → no expirado
        self.assertFalse(reto_expirado(5000.0, 5000.0))

    def test_negativo_no_expirado(self):
        # ahora < timestamp (reloj adelantado) → no expirado
        self.assertFalse(reto_expirado(5000.0, 4999.0))


if __name__ == "__main__":
    unittest.main()
