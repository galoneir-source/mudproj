"""
tests/test_mascotas.py

Tests unitarios puros para el sistema de mascotas de combate (v0.32.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_mascotas.py
"""
import unittest

from systems.pets.pets import (
    CAPTURA_HP_PCT,
    COSTE_ALIMENTAR,
    NIVEL_MAX_MASCOTA,
    VINCULO_MAX,
    VINCULO_MIN,
    VINCULO_SUBE_ALIMENTAR,
    VINCULO_SUBE_VICTORIA,
    XP_NIVEL_2,
    XP_NIVEL_3,
    calcular_daño_mascota,
    calcular_evolucion,
    calcular_nuevo_vinculo,
    datos_mascota_desde_criatura,
    formatear_mascota,
    puede_capturar,
    vinculo_descripcion,
    xp_para_siguiente_nivel,
)


# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

class TestConstantes(unittest.TestCase):

    def test_vinculo_max_es_100(self):
        self.assertEqual(VINCULO_MAX, 100)

    def test_vinculo_min_es_0(self):
        self.assertEqual(VINCULO_MIN, 0)

    def test_captura_hp_pct_es_20(self):
        self.assertAlmostEqual(CAPTURA_HP_PCT, 0.20)

    def test_vinculo_sube_victoria_positivo(self):
        self.assertGreater(VINCULO_SUBE_VICTORIA, 0)

    def test_coste_alimentar_positivo(self):
        self.assertGreater(COSTE_ALIMENTAR, 0)

    def test_vinculo_sube_alimentar_positivo(self):
        self.assertGreater(VINCULO_SUBE_ALIMENTAR, 0)

    def test_xp_nivel_2_positivo(self):
        self.assertGreater(XP_NIVEL_2, 0)

    def test_xp_nivel_3_mayor_que_nivel_2(self):
        self.assertGreater(XP_NIVEL_3, XP_NIVEL_2)

    def test_nivel_max_es_3(self):
        self.assertEqual(NIVEL_MAX_MASCOTA, 3)


# --------------------------------------------------------------------------- #
#  puede_capturar
# --------------------------------------------------------------------------- #

class TestPuedeCapturar(unittest.TestCase):

    def test_hp_20_pct_exacto(self):
        self.assertTrue(puede_capturar(20, 100))

    def test_hp_por_debajo_del_umbral(self):
        self.assertTrue(puede_capturar(10, 100))

    def test_hp_1_de_100(self):
        self.assertTrue(puede_capturar(1, 100))

    def test_hp_21_pct_no_puede(self):
        self.assertFalse(puede_capturar(21, 100))

    def test_hp_50_pct_no_puede(self):
        self.assertFalse(puede_capturar(50, 100))

    def test_hp_100_pct_no_puede(self):
        self.assertFalse(puede_capturar(100, 100))

    def test_hp_max_cero_no_puede(self):
        self.assertFalse(puede_capturar(0, 0))

    def test_hp_igual_a_hp_max_no_puede(self):
        self.assertFalse(puede_capturar(40, 40))

    def test_valores_exactos_umbral(self):
        # 20% de 50 = 10
        self.assertTrue(puede_capturar(10, 50))
        self.assertFalse(puede_capturar(11, 50))


# --------------------------------------------------------------------------- #
#  calcular_daño_mascota
# --------------------------------------------------------------------------- #

class TestCalcularDañoMascota(unittest.TestCase):

    def test_vinculo_0_mitad_ataque(self):
        # 50% de 10 = 5
        self.assertEqual(calcular_daño_mascota(0, 10), 5)

    def test_vinculo_100_ataque_completo(self):
        # 100% de 10 = 10
        self.assertEqual(calcular_daño_mascota(100, 10), 10)

    def test_vinculo_50_tres_cuartos(self):
        # 75% de 20 = 15
        self.assertEqual(calcular_daño_mascota(50, 20), 15)

    def test_minimo_daño_es_1(self):
        # Incluso con ataque 0 o muy bajo, daño mínimo es 1
        self.assertGreaterEqual(calcular_daño_mascota(0, 0), 1)
        self.assertGreaterEqual(calcular_daño_mascota(0, 1), 1)

    def test_vinculo_negativo_equivale_a_0(self):
        daño_neg = calcular_daño_mascota(-10, 10)
        daño_0 = calcular_daño_mascota(0, 10)
        self.assertEqual(daño_neg, daño_0)

    def test_vinculo_sobre_max_equivale_a_max(self):
        daño_200 = calcular_daño_mascota(200, 10)
        daño_100 = calcular_daño_mascota(100, 10)
        self.assertEqual(daño_200, daño_100)

    def test_mayor_ataque_mayor_daño(self):
        self.assertGreater(
            calcular_daño_mascota(50, 20),
            calcular_daño_mascota(50, 10),
        )

    def test_mayor_vinculo_mayor_daño(self):
        self.assertGreater(
            calcular_daño_mascota(100, 10),
            calcular_daño_mascota(0, 10),
        )


# --------------------------------------------------------------------------- #
#  calcular_nuevo_vinculo
# --------------------------------------------------------------------------- #

class TestCalcularNuevoVinculo(unittest.TestCase):

    def test_suma_delta_positivo(self):
        self.assertEqual(calcular_nuevo_vinculo(30, 5), 35)

    def test_suma_delta_negativo(self):
        self.assertEqual(calcular_nuevo_vinculo(30, -10), 20)

    def test_no_supera_maximo(self):
        self.assertEqual(calcular_nuevo_vinculo(98, 10), 100)

    def test_no_baja_de_minimo(self):
        self.assertEqual(calcular_nuevo_vinculo(2, -10), 0)

    def test_exactamente_en_maximo(self):
        self.assertEqual(calcular_nuevo_vinculo(100, 5), 100)

    def test_exactamente_en_minimo(self):
        self.assertEqual(calcular_nuevo_vinculo(0, -5), 0)

    def test_delta_cero_no_cambia(self):
        self.assertEqual(calcular_nuevo_vinculo(50, 0), 50)


# --------------------------------------------------------------------------- #
#  vinculo_descripcion
# --------------------------------------------------------------------------- #

class TestVinculoDescripcion(unittest.TestCase):

    def test_0_es_indiferente(self):
        self.assertEqual(vinculo_descripcion(0), "Indiferente")

    def test_24_es_indiferente(self):
        self.assertEqual(vinculo_descripcion(24), "Indiferente")

    def test_25_es_amistoso(self):
        self.assertEqual(vinculo_descripcion(25), "Amistoso")

    def test_49_es_amistoso(self):
        self.assertEqual(vinculo_descripcion(49), "Amistoso")

    def test_50_es_leal(self):
        self.assertEqual(vinculo_descripcion(50), "Leal")

    def test_79_es_leal(self):
        self.assertEqual(vinculo_descripcion(79), "Leal")

    def test_80_es_devoto(self):
        self.assertEqual(vinculo_descripcion(80), "Devoto")

    def test_100_es_devoto(self):
        self.assertEqual(vinculo_descripcion(100), "Devoto")

    def test_devuelve_string(self):
        self.assertIsInstance(vinculo_descripcion(50), str)


# --------------------------------------------------------------------------- #
#  datos_mascota_desde_criatura
# --------------------------------------------------------------------------- #

class TestDatosMascota(unittest.TestCase):

    def setUp(self):
        self.m = datos_mascota_desde_criatura(
            nombre="lobo",
            especie="lobo gris",
            hp_max=40,
            ataque=8,
            defensa=3,
        )

    def test_nombre_correcto(self):
        self.assertEqual(self.m["nombre"], "lobo")

    def test_especie_correcta(self):
        self.assertEqual(self.m["especie"], "lobo gris")

    def test_hp_igual_a_hp_max(self):
        self.assertEqual(self.m["hp"], self.m["hp_max"])

    def test_hp_max_correcto(self):
        self.assertEqual(self.m["hp_max"], 40)

    def test_ataque_correcto(self):
        self.assertEqual(self.m["ataque"], 8)

    def test_defensa_correcta(self):
        self.assertEqual(self.m["defensa"], 3)

    def test_vinculo_inicial_positivo(self):
        self.assertGreater(self.m["vinculo"], 0)

    def test_vinculo_inicial_dentro_rango(self):
        self.assertGreaterEqual(self.m["vinculo"], VINCULO_MIN)
        self.assertLessEqual(self.m["vinculo"], VINCULO_MAX)

    def test_vinculo_inicial_personalizado(self):
        m = datos_mascota_desde_criatura("x", "x", 10, 5, 2, vinculo_inicial=30)
        self.assertEqual(m["vinculo"], 30)

    def test_es_dict(self):
        self.assertIsInstance(self.m, dict)

    def test_incluye_nivel_inicial_1(self):
        self.assertEqual(self.m["nivel"], 1)

    def test_incluye_xp_inicial_0(self):
        self.assertEqual(self.m["xp"], 0)

    def test_incluye_especie_base(self):
        self.assertEqual(self.m["especie_base"], "lobo gris")


# --------------------------------------------------------------------------- #
#  formatear_mascota
# --------------------------------------------------------------------------- #

class TestFormatearMascota(unittest.TestCase):

    def setUp(self):
        self.mascota = {
            "nombre": "Fang",
            "especie": "lobo",
            "especie_base": "lobo",
            "nivel": 1,
            "xp": 10,
            "vinculo": 50,
            "hp": 35,
            "hp_max": 40,
            "ataque": 8,
            "defensa": 3,
        }

    def test_devuelve_string(self):
        self.assertIsInstance(formatear_mascota(self.mascota), str)

    def test_contiene_nombre(self):
        self.assertIn("Fang", formatear_mascota(self.mascota))

    def test_contiene_especie(self):
        self.assertIn("lobo", formatear_mascota(self.mascota))

    def test_contiene_hp(self):
        self.assertIn("35", formatear_mascota(self.mascota))

    def test_contiene_vinculo(self):
        self.assertIn("50", formatear_mascota(self.mascota))

    def test_contiene_descripcion_vinculo(self):
        self.assertIn("Leal", formatear_mascota(self.mascota))

    def test_contiene_ataque(self):
        self.assertIn("8", formatear_mascota(self.mascota))

    def test_contiene_nivel(self):
        self.assertIn("Nivel", formatear_mascota(self.mascota))

    def test_contiene_xp(self):
        self.assertIn("10", formatear_mascota(self.mascota))

    def test_nivel_max_muestra_max(self):
        m = dict(self.mascota)
        m["nivel"] = 3
        m["xp"] = 200
        self.assertIn("MAX", formatear_mascota(m))


# --------------------------------------------------------------------------- #
#  xp_para_siguiente_nivel
# --------------------------------------------------------------------------- #

class TestXpParaSiguienteNivel(unittest.TestCase):

    def test_nivel_1_retorna_xp_nivel_2(self):
        self.assertEqual(xp_para_siguiente_nivel(1), XP_NIVEL_2)

    def test_nivel_2_retorna_xp_nivel_3(self):
        self.assertEqual(xp_para_siguiente_nivel(2), XP_NIVEL_3)

    def test_nivel_3_retorna_none(self):
        self.assertIsNone(xp_para_siguiente_nivel(3))

    def test_nivel_invalido_retorna_none(self):
        self.assertIsNone(xp_para_siguiente_nivel(99))


# --------------------------------------------------------------------------- #
#  calcular_evolucion
# --------------------------------------------------------------------------- #

def _mascota_base(nivel=1, xp=0):
    return {
        "nombre": "Rex",
        "especie": "lobo" if nivel == 1 else f"lobo {'Mayor' if nivel == 2 else 'Élite'}",
        "especie_base": "lobo",
        "nivel": nivel,
        "xp": xp,
        "vinculo": 30,
        "hp": 40,
        "hp_max": 40,
        "ataque": 10,
        "defensa": 4,
    }


class TestCalcularEvolucion(unittest.TestCase):

    def test_sin_xp_suficiente_no_evoluciona(self):
        m, evoluciono = calcular_evolucion(_mascota_base(), 10)
        self.assertFalse(evoluciono)
        self.assertEqual(m["nivel"], 1)

    def test_xp_se_acumula(self):
        m, _ = calcular_evolucion(_mascota_base(xp=20), 15)
        self.assertEqual(m["xp"], 35)

    def test_alcanzar_umbral_evoluciona_a_nivel_2(self):
        m, evoluciono = calcular_evolucion(_mascota_base(xp=45), 5)
        self.assertTrue(evoluciono)
        self.assertEqual(m["nivel"], 2)

    def test_xp_exacto_umbral_evoluciona(self):
        m, evoluciono = calcular_evolucion(_mascota_base(), XP_NIVEL_2)
        self.assertTrue(evoluciono)
        self.assertEqual(m["nivel"], 2)

    def test_evolucion_nivel_2_aumenta_ataque(self):
        m_antes = _mascota_base()
        m, _ = calcular_evolucion(m_antes, XP_NIVEL_2)
        self.assertGreater(m["ataque"], m_antes["ataque"])

    def test_evolucion_nivel_2_aumenta_hp_max(self):
        m_antes = _mascota_base()
        m, _ = calcular_evolucion(m_antes, XP_NIVEL_2)
        self.assertGreater(m["hp_max"], m_antes["hp_max"])

    def test_evolucion_restaura_hp_al_maximo(self):
        m_baja_vida = dict(_mascota_base())
        m_baja_vida["hp"] = 5
        m, _ = calcular_evolucion(m_baja_vida, XP_NIVEL_2)
        self.assertEqual(m["hp"], m["hp_max"])

    def test_especie_cambia_a_mayor_en_nivel_2(self):
        m, _ = calcular_evolucion(_mascota_base(), XP_NIVEL_2)
        self.assertIn("Mayor", m["especie"])

    def test_especie_cambia_a_elite_en_nivel_3(self):
        m, _ = calcular_evolucion(_mascota_base(nivel=2, xp=100), XP_NIVEL_3 - 100)
        self.assertIn("Élite", m["especie"])

    def test_nivel_3_es_maximo_no_evoluciona_mas(self):
        m3 = _mascota_base(nivel=3, xp=XP_NIVEL_3)
        m, evoluciono = calcular_evolucion(m3, 1000)
        self.assertFalse(evoluciono)
        self.assertEqual(m["nivel"], 3)

    def test_xp_sigue_acumulandose_en_nivel_3(self):
        m3 = _mascota_base(nivel=3, xp=200)
        m, _ = calcular_evolucion(m3, 5)
        self.assertEqual(m["xp"], 205)

    def test_no_modifica_mascota_original(self):
        original = _mascota_base()
        calcular_evolucion(original, XP_NIVEL_2)
        self.assertEqual(original["nivel"], 1)

    def test_nombre_no_cambia_al_evolucionar(self):
        m, _ = calcular_evolucion(_mascota_base(), XP_NIVEL_2)
        self.assertEqual(m["nombre"], "Rex")

    def test_vinculo_no_cambia_al_evolucionar(self):
        m, _ = calcular_evolucion(_mascota_base(), XP_NIVEL_2)
        self.assertEqual(m["vinculo"], 30)


if __name__ == "__main__":
    unittest.main()
