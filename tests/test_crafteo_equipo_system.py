"""
tests/test_crafteo_equipo_system.py

Tests unitarios puros para el sistema de calidades de equipo crafteado (v0.24.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_crafteo_equipo_system.py
"""
import unittest

from systems.crafting.equipment import (
    CALIDADES,
    NOMBRES_CALIDAD,
    aplicar_bonuses_calidad,
    calcular_calidad,
    nombre_con_calidad,
)
from systems.crafting.recipes import RECETAS, buscar_receta


# --------------------------------------------------------------------------- #
#  Calidades: umbrales y constantes
# --------------------------------------------------------------------------- #

class TestConstantesCalidad(unittest.TestCase):

    def test_existen_tres_calidades(self):
        self.assertEqual(len(CALIDADES), 3)

    def test_nombres_calidad_contiene_normal(self):
        self.assertIn("Normal", NOMBRES_CALIDAD)

    def test_nombres_calidad_contiene_fino(self):
        self.assertIn("Fino", NOMBRES_CALIDAD)

    def test_nombres_calidad_contiene_magistral(self):
        self.assertIn("Magistral", NOMBRES_CALIDAD)

    def test_bonus_normal_es_cero(self):
        _, _, _, bonus = next(c for c in CALIDADES if c[2] == "Normal")
        self.assertEqual(bonus, 0)

    def test_bonus_fino_es_uno(self):
        _, _, _, bonus = next(c for c in CALIDADES if c[2] == "Fino")
        self.assertEqual(bonus, 1)

    def test_bonus_magistral_es_dos(self):
        _, _, _, bonus = next(c for c in CALIDADES if c[2] == "Magistral")
        self.assertEqual(bonus, 2)


# --------------------------------------------------------------------------- #
#  calcular_calidad
# --------------------------------------------------------------------------- #

class TestCalcularCalidad(unittest.TestCase):

    def test_cero_objetos_normal(self):
        nombre, bonus = calcular_calidad(0)
        self.assertEqual(nombre, "Normal")
        self.assertEqual(bonus, 0)

    def test_catorce_objetos_normal(self):
        nombre, bonus = calcular_calidad(14)
        self.assertEqual(nombre, "Normal")
        self.assertEqual(bonus, 0)

    def test_quince_objetos_fino(self):
        nombre, bonus = calcular_calidad(15)
        self.assertEqual(nombre, "Fino")
        self.assertEqual(bonus, 1)

    def test_veintinueve_objetos_fino(self):
        nombre, bonus = calcular_calidad(29)
        self.assertEqual(nombre, "Fino")
        self.assertEqual(bonus, 1)

    def test_treinta_objetos_magistral(self):
        nombre, bonus = calcular_calidad(30)
        self.assertEqual(nombre, "Magistral")
        self.assertEqual(bonus, 2)

    def test_cien_objetos_magistral(self):
        nombre, bonus = calcular_calidad(100)
        self.assertEqual(nombre, "Magistral")
        self.assertEqual(bonus, 2)

    def test_none_equivale_a_cero(self):
        nombre, bonus = calcular_calidad(None)
        self.assertEqual(nombre, "Normal")
        self.assertEqual(bonus, 0)

    def test_negativo_equivale_a_cero(self):
        nombre, bonus = calcular_calidad(-5)
        self.assertEqual(nombre, "Normal")
        self.assertEqual(bonus, 0)

    def test_devuelve_tupla(self):
        resultado = calcular_calidad(0)
        self.assertIsInstance(resultado, tuple)
        self.assertEqual(len(resultado), 2)


# --------------------------------------------------------------------------- #
#  aplicar_bonuses_calidad
# --------------------------------------------------------------------------- #

class TestAplicarBonusesCalidad(unittest.TestCase):

    def test_bonus_cero_no_modifica(self):
        bonuses = {"fuerza": 3, "destreza": 2}
        resultado = aplicar_bonuses_calidad(bonuses, 0)
        self.assertEqual(resultado, {"fuerza": 3, "destreza": 2})

    def test_bonus_uno_suma_uno(self):
        bonuses = {"fuerza": 3, "destreza": 2}
        resultado = aplicar_bonuses_calidad(bonuses, 1)
        self.assertEqual(resultado, {"fuerza": 4, "destreza": 3})

    def test_bonus_dos_suma_dos(self):
        bonuses = {"fuerza": 3, "destreza": 2}
        resultado = aplicar_bonuses_calidad(bonuses, 2)
        self.assertEqual(resultado, {"fuerza": 5, "destreza": 4})

    def test_bonus_aplicado_a_todos_los_stats(self):
        bonuses = {"fuerza": 1, "destreza": 1, "defensa": 1, "inteligencia": 1}
        resultado = aplicar_bonuses_calidad(bonuses, 1)
        for stat, val in resultado.items():
            self.assertEqual(val, 2, f"Stat {stat} debería ser 2")

    def test_no_modifica_dict_original(self):
        bonuses = {"fuerza": 5}
        aplicar_bonuses_calidad(bonuses, 1)
        self.assertEqual(bonuses["fuerza"], 5)

    def test_devuelve_nuevo_dict(self):
        bonuses = {"fuerza": 5}
        resultado = aplicar_bonuses_calidad(bonuses, 0)
        self.assertIsNot(resultado, bonuses)

    def test_dict_vacio_no_falla(self):
        resultado = aplicar_bonuses_calidad({}, 2)
        self.assertEqual(resultado, {})

    def test_valores_negativos_mejoran(self):
        bonuses = {"destreza": -2}
        resultado = aplicar_bonuses_calidad(bonuses, 1)
        self.assertEqual(resultado["destreza"], -1)

    def test_un_solo_stat(self):
        resultado = aplicar_bonuses_calidad({"inteligencia": 5}, 2)
        self.assertEqual(resultado["inteligencia"], 7)


# --------------------------------------------------------------------------- #
#  nombre_con_calidad
# --------------------------------------------------------------------------- #

class TestNombreConCalidad(unittest.TestCase):

    def test_normal_no_añade_sufijo(self):
        self.assertEqual(nombre_con_calidad("daga de acero", "Normal"), "daga de acero")

    def test_fino_añade_sufijo(self):
        self.assertEqual(nombre_con_calidad("daga de acero", "Fino"), "daga de acero (Fino)")

    def test_magistral_añade_sufijo(self):
        self.assertEqual(nombre_con_calidad("espada del cazador", "Magistral"), "espada del cazador (Magistral)")

    def test_sufijo_entre_paréntesis(self):
        resultado = nombre_con_calidad("vara arcana", "Fino")
        self.assertIn("(Fino)", resultado)

    def test_nombre_base_preservado(self):
        nombre = "coraza de hierro"
        resultado = nombre_con_calidad(nombre, "Magistral")
        self.assertTrue(resultado.startswith(nombre))

    def test_string_vacio_funciona(self):
        resultado = nombre_con_calidad("", "Fino")
        self.assertIn("Fino", resultado)


# --------------------------------------------------------------------------- #
#  Recetas de equipo en RECETAS
# --------------------------------------------------------------------------- #

RECETAS_EQUIPO_ESPERADAS = [
    "daga de acero",
    "espada del cazador",
    "vara arcana",
    "hacha tallada",
    "coraza de hierro",
    "túnica del mago",
    "amuleto de combate",
    "anillo de sombras",
]

PROTOTIPOS_EQUIPO_ESPERADOS = {
    "daga de acero": "DAGA_ACERO",
    "espada del cazador": "ESPADA_CAZADOR",
    "vara arcana": "VARA_ARCANA",
    "hacha tallada": "HACHA_TALLADA",
    "coraza de hierro": "CORAZA_HIERRO",
    "túnica del mago": "TUNICA_MAGO",
    "amuleto de combate": "AMULETO_COMBATE",
    "anillo de sombras": "ANILLO_SOMBRAS",
}


class TestRecetasEquipo(unittest.TestCase):

    def test_existen_diez_recetas_equipo(self):
        # 8 de v0.24 + 2 de recetas posteriores con materiales de profesión
        recetas_equipo = [k for k, v in RECETAS.items() if v.get("tipo") == "equipo"]
        self.assertEqual(len(recetas_equipo), 10)

    def test_todas_recetas_equipo_presentes(self):
        for nombre in RECETAS_EQUIPO_ESPERADAS:
            self.assertIn(nombre, RECETAS, f"Falta receta: {nombre}")

    def test_todas_tienen_tipo_equipo(self):
        for nombre in RECETAS_EQUIPO_ESPERADAS:
            receta = RECETAS[nombre]
            self.assertEqual(receta.get("tipo"), "equipo", f"{nombre} debería ser tipo equipo")

    def test_todas_tienen_cantidad_uno(self):
        for nombre in RECETAS_EQUIPO_ESPERADAS:
            receta = RECETAS[nombre]
            self.assertEqual(receta.get("cantidad", 1), 1, f"{nombre} debería ser cantidad 1")

    def test_prototipos_correctos(self):
        for nombre, prototipo in PROTOTIPOS_EQUIPO_ESPERADOS.items():
            receta = RECETAS[nombre]
            self.assertEqual(receta["resultado_prototipo"], prototipo)

    def test_todas_tienen_ingredientes(self):
        for nombre in RECETAS_EQUIPO_ESPERADAS:
            receta = RECETAS[nombre]
            self.assertIn("ingredientes", receta)
            self.assertGreater(len(receta["ingredientes"]), 0, f"{nombre} sin ingredientes")

    def test_todas_tienen_desc_receta(self):
        for nombre in RECETAS_EQUIPO_ESPERADAS:
            receta = RECETAS[nombre]
            self.assertIn("desc_receta", receta)
            self.assertTrue(receta["desc_receta"])

    def test_daga_acero_ingredientes(self):
        receta = RECETAS["daga de acero"]
        self.assertIn("mineral de hierro", receta["ingredientes"])
        self.assertIn("piel de serpiente", receta["ingredientes"])

    def test_espada_cazador_usa_garra_troll(self):
        receta = RECETAS["espada del cazador"]
        self.assertIn("garra de troll", receta["ingredientes"])

    def test_vara_arcana_usa_cenizas_arcanas(self):
        receta = RECETAS["vara arcana"]
        self.assertIn("cenizas arcanas", receta["ingredientes"])

    def test_coraza_hierro_usa_mineral_abundante(self):
        receta = RECETAS["coraza de hierro"]
        self.assertGreaterEqual(receta["ingredientes"]["mineral de hierro"], 3)

    def test_anillo_sombras_usa_cristal_oscuridad(self):
        receta = RECETAS["anillo de sombras"]
        self.assertIn("cristal de oscuridad", receta["ingredientes"])

    def test_buscar_receta_daga_acero(self):
        nombre, receta = buscar_receta("daga de acero")
        self.assertIsNotNone(receta)
        self.assertEqual(nombre, "daga de acero")

    def test_buscar_receta_parcial_vara(self):
        nombre, receta = buscar_receta("vara")
        self.assertIsNotNone(receta)
        self.assertIn("arcana", nombre)


# --------------------------------------------------------------------------- #
#  Integración mínima: flujo completo sin Evennia
# --------------------------------------------------------------------------- #

class TestFlujoCalidadCompleto(unittest.TestCase):
    """Simula el flujo de calidad sin instanciar Evennia."""

    def _craftear_equipo(self, objetos_crafteados, receta_nombre="daga de acero"):
        nombre, receta = buscar_receta(receta_nombre)
        calidad_nombre, bonus_stat = calcular_calidad(objetos_crafteados)
        bonuses_base = {"fuerza": 3, "destreza": 2}
        bonuses_finales = aplicar_bonuses_calidad(bonuses_base, bonus_stat)
        nombre_item = nombre_con_calidad(nombre, calidad_nombre)
        return nombre_item, bonuses_finales, calidad_nombre

    def test_crafteo_normal_no_cambia_bonuses(self):
        nombre_item, bonuses, calidad = self._craftear_equipo(0)
        self.assertEqual(bonuses["fuerza"], 3)
        self.assertEqual(bonuses["destreza"], 2)
        self.assertEqual(calidad, "Normal")

    def test_crafteo_fino_suma_uno(self):
        nombre_item, bonuses, calidad = self._craftear_equipo(15)
        self.assertEqual(bonuses["fuerza"], 4)
        self.assertEqual(bonuses["destreza"], 3)
        self.assertEqual(calidad, "Fino")

    def test_crafteo_magistral_suma_dos(self):
        nombre_item, bonuses, calidad = self._craftear_equipo(30)
        self.assertEqual(bonuses["fuerza"], 5)
        self.assertEqual(bonuses["destreza"], 4)
        self.assertEqual(calidad, "Magistral")

    def test_nombre_normal_sin_sufijo(self):
        nombre_item, _, _ = self._craftear_equipo(0)
        self.assertNotIn("(", nombre_item)

    def test_nombre_fino_con_sufijo(self):
        nombre_item, _, _ = self._craftear_equipo(15)
        self.assertIn("(Fino)", nombre_item)

    def test_nombre_magistral_con_sufijo(self):
        nombre_item, _, _ = self._craftear_equipo(30)
        self.assertIn("(Magistral)", nombre_item)


if __name__ == "__main__":
    unittest.main()
