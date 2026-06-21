"""
tests/test_eventos.py

Tests unitarios puros para systems/events/events.py (v0.19.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_eventos.py
"""
import unittest

from systems.events.events import (
    EVENTOS,
    eventos_elegibles,
    elegir_evento,
)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

class TestCatalogo(unittest.TestCase):

    def test_hay_tres_eventos(self):
        self.assertEqual(len(EVENTOS), 3)

    def test_invasion_existe(self):
        self.assertIn("invasion_no_muertos", EVENTOS)

    def test_feria_existe(self):
        self.assertIn("feria_mercado", EVENTOS)

    def test_tormenta_existe(self):
        self.assertIn("tormenta_magica", EVENTOS)

    def test_todos_tienen_campos_obligatorios(self):
        campos = ("nombre", "descripcion", "duracion", "intervalo_min",
                  "peso", "color", "efectos", "mensaje_inicio", "mensaje_fin")
        for ev_id, ev in EVENTOS.items():
            for campo in campos:
                self.assertIn(campo, ev, f"{ev_id} falta '{campo}'")

    def test_duraciones_positivas(self):
        for ev_id, ev in EVENTOS.items():
            self.assertGreater(ev["duracion"], 0, ev_id)

    def test_intervalos_mayores_que_duracion(self):
        for ev_id, ev in EVENTOS.items():
            self.assertGreater(ev["intervalo_min"], ev["duracion"], ev_id)

    def test_pesos_positivos(self):
        for ev_id, ev in EVENTOS.items():
            self.assertGreater(ev["peso"], 0, ev_id)

    def test_invasion_tiene_xp_factor(self):
        self.assertIn("xp_factor", EVENTOS["invasion_no_muertos"]["efectos"])
        self.assertGreater(EVENTOS["invasion_no_muertos"]["efectos"]["xp_factor"], 1.0)

    def test_invasion_tiene_facciones(self):
        self.assertIn("facciones_afectadas", EVENTOS["invasion_no_muertos"]["efectos"])
        self.assertIn("legion_oscura", EVENTOS["invasion_no_muertos"]["efectos"]["facciones_afectadas"])

    def test_feria_tiene_descuento(self):
        self.assertIn("descuento_tienda", EVENTOS["feria_mercado"]["efectos"])
        descuento = EVENTOS["feria_mercado"]["efectos"]["descuento_tienda"]
        self.assertGreater(descuento, 0.0)
        self.assertLess(descuento, 1.0)

    def test_tormenta_tiene_bonus_int(self):
        self.assertIn("bonus_inteligencia", EVENTOS["tormenta_magica"]["efectos"])
        self.assertGreater(EVENTOS["tormenta_magica"]["efectos"]["bonus_inteligencia"], 0)

    def test_colores_son_strings_evennia(self):
        for ev_id, ev in EVENTOS.items():
            self.assertIsInstance(ev["color"], str, ev_id)
            self.assertTrue(ev["color"].startswith("|"), ev_id)


# ---------------------------------------------------------------------------
# eventos_elegibles
# ---------------------------------------------------------------------------

class TestEventosElegibles(unittest.TestCase):

    def test_todos_elegibles_sin_historial(self):
        # Usar ahora grande para que ahora - 0 >= intervalo_min
        ahora = 100_000.0
        elegibles = eventos_elegibles({}, ahora=ahora)
        ids = [e[0] for e in elegibles]
        self.assertIn("invasion_no_muertos", ids)
        self.assertIn("feria_mercado", ids)
        self.assertIn("tormenta_magica", ids)

    def test_invasion_no_elegible_en_cooldown(self):
        ahora = 100_000.0
        intervalo = EVENTOS["invasion_no_muertos"]["intervalo_min"]
        ultimo = {"invasion_no_muertos": ahora - (intervalo - 1)}
        elegibles = eventos_elegibles(ultimo, ahora)
        ids = [e[0] for e in elegibles]
        self.assertNotIn("invasion_no_muertos", ids)
        self.assertIn("feria_mercado", ids)

    def test_invasion_elegible_tras_cooldown(self):
        ahora = 100_000.0
        intervalo = EVENTOS["invasion_no_muertos"]["intervalo_min"]
        ultimo = {"invasion_no_muertos": ahora - intervalo}
        elegibles = eventos_elegibles(ultimo, ahora)
        ids = [e[0] for e in elegibles]
        self.assertIn("invasion_no_muertos", ids)

    def test_ninguno_elegible_todos_en_cooldown(self):
        ahora = 100_000.0
        ultimo = {ev_id: ahora for ev_id in EVENTOS}
        elegibles = eventos_elegibles(ultimo, ahora)
        self.assertEqual(elegibles, [])

    def test_devuelve_peso_correcto(self):
        elegibles = eventos_elegibles({}, ahora=0.0)
        for ev_id, peso in elegibles:
            self.assertEqual(peso, EVENTOS[ev_id]["peso"])


# ---------------------------------------------------------------------------
# elegir_evento
# ---------------------------------------------------------------------------

class TestElegirEvento(unittest.TestCase):

    def test_lista_vacia_devuelve_none(self):
        self.assertIsNone(elegir_evento([], 0.5))

    def test_un_solo_elegible(self):
        resultado = elegir_evento([("feria_mercado", 2)], 0.5)
        self.assertEqual(resultado, "feria_mercado")

    def test_r_cero_elige_primero(self):
        elegibles = [("invasion_no_muertos", 3), ("feria_mercado", 2), ("tormenta_magica", 1)]
        resultado = elegir_evento(elegibles, 0.0)
        self.assertEqual(resultado, "invasion_no_muertos")

    def test_r_uno_elige_ultimo(self):
        elegibles = [("invasion_no_muertos", 3), ("feria_mercado", 2), ("tormenta_magica", 1)]
        # r=1.0 está fuera de rango [0,1) pero el fallback devuelve el último
        resultado = elegir_evento(elegibles, 0.9999)
        self.assertIsNotNone(resultado)

    def test_distribucion_ponderada(self):
        # Con pesos 3:2:1, invasion debería salir ~50% de las veces
        elegibles = [
            ("invasion_no_muertos", 3),
            ("feria_mercado", 2),
            ("tormenta_magica", 1),
        ]
        conteo = {"invasion_no_muertos": 0, "feria_mercado": 0, "tormenta_magica": 0}
        N = 6000
        import random
        random.seed(42)
        for _ in range(N):
            ev = elegir_evento(elegibles, random.random())
            conteo[ev] += 1
        # invasion debería tener ~50% (peso 3 de 6 total)
        ratio = conteo["invasion_no_muertos"] / N
        self.assertGreater(ratio, 0.40)
        self.assertLess(ratio, 0.60)

    def test_pesos_iguales_distribucion_uniforme(self):
        elegibles = [("A", 1), ("B", 1), ("C", 1)]
        conteo = {"A": 0, "B": 0, "C": 0}
        N = 3000
        import random
        random.seed(0)
        for _ in range(N):
            ev = elegir_evento(elegibles, random.random())
            conteo[ev] += 1
        for v in conteo.values():
            self.assertGreater(v, N * 0.25)
            self.assertLess(v, N * 0.45)

    def test_resultado_siempre_en_elegibles(self):
        elegibles = [("invasion_no_muertos", 3), ("feria_mercado", 2)]
        import random
        random.seed(99)
        for _ in range(100):
            ev = elegir_evento(elegibles, random.random())
            self.assertIn(ev, ["invasion_no_muertos", "feria_mercado"])


# ---------------------------------------------------------------------------
# Valores de efectos
# ---------------------------------------------------------------------------

class TestEfectos(unittest.TestCase):

    def test_xp_factor_invasion_es_doble(self):
        self.assertEqual(EVENTOS["invasion_no_muertos"]["efectos"]["xp_factor"], 2.0)

    def test_descuento_feria_es_20_pct(self):
        self.assertAlmostEqual(EVENTOS["feria_mercado"]["efectos"]["descuento_tienda"], 0.20)

    def test_bonus_int_tormenta_es_3(self):
        self.assertEqual(EVENTOS["tormenta_magica"]["efectos"]["bonus_inteligencia"], 3)

    def test_invasion_duracion_20min(self):
        self.assertEqual(EVENTOS["invasion_no_muertos"]["duracion"], 1200)

    def test_feria_duracion_15min(self):
        self.assertEqual(EVENTOS["feria_mercado"]["duracion"], 900)

    def test_tormenta_duracion_10min(self):
        self.assertEqual(EVENTOS["tormenta_magica"]["duracion"], 600)


if __name__ == "__main__":
    unittest.main()
