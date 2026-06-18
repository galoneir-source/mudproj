"""
tests/test_torre_system.py

Tests unitarios para la zona Torre del Mago Caído (v0.15.0).
Verifica quests, spawn tables y recetas nuevas. Sin dependencias de Evennia.
"""
import unittest

from systems.quests.quests import (
    QUESTS,
    buscar_quest,
    quest_disponible,
    quests_de_npc,
    verificar_fetch,
    registrar_kill,
    kills_actuales,
)
from systems.spawn.tables import ZONAS, npcs_necesarios, calcular_faltantes
from systems.crafting.recipes import RECETAS, buscar_receta, verificar_ingredientes


class TestZonasTorre(unittest.TestCase):

    def test_zonas_torre_presentes(self):
        for z in ("base_torre", "biblioteca_archimago", "camara_ritual"):
            self.assertIn(z, ZONAS, f"Zona '{z}' no está en ZONAS")

    def test_base_torre_tiene_guardian(self):
        resultado = npcs_necesarios("base_torre")
        self.assertEqual(resultado, {"GUARDIAN_ARCANO": 1})

    def test_biblioteca_tiene_dos_aprendices(self):
        resultado = npcs_necesarios("biblioteca_archimago")
        self.assertEqual(resultado, {"APRENDIZ_CORRUPTO": 2})

    def test_camara_tiene_archimago(self):
        resultado = npcs_necesarios("camara_ritual")
        self.assertEqual(resultado, {"ARCHIMAGO_VEXTHAR": 1})

    def test_faltantes_biblioteca_vacia(self):
        faltantes = calcular_faltantes("biblioteca_archimago", {})
        self.assertEqual(faltantes, {"APRENDIZ_CORRUPTO": 2})

    def test_faltantes_biblioteca_parcial(self):
        faltantes = calcular_faltantes("biblioteca_archimago", {"APRENDIZ_CORRUPTO": 1})
        self.assertEqual(faltantes, {"APRENDIZ_CORRUPTO": 1})

    def test_faltantes_biblioteca_completa(self):
        faltantes = calcular_faltantes("biblioteca_archimago", {"APRENDIZ_CORRUPTO": 2})
        self.assertEqual(faltantes, {})

    def test_faltantes_camara_vacia(self):
        faltantes = calcular_faltantes("camara_ritual", {})
        self.assertEqual(faltantes, {"ARCHIMAGO_VEXTHAR": 1})

    def test_faltantes_camara_completa(self):
        faltantes = calcular_faltantes("camara_ritual", {"ARCHIMAGO_VEXTHAR": 1})
        self.assertEqual(faltantes, {})

    def test_faltantes_base_vacia(self):
        faltantes = calcular_faltantes("base_torre", {})
        self.assertEqual(faltantes, {"GUARDIAN_ARCANO": 1})


class TestQuestsTorre(unittest.TestCase):

    def test_quests_torre_presentes(self):
        self.assertIn("aprendices_torre", QUESTS)
        self.assertIn("archimago_caido", QUESTS)

    def test_aprendices_es_kill(self):
        q = QUESTS["aprendices_torre"]
        self.assertEqual(q["tipo"], "kill")
        self.assertEqual(q["objetivo"]["target"], "aprendiz corrompido")
        self.assertEqual(q["objetivo"]["cantidad"], 3)

    def test_archimago_es_kill(self):
        q = QUESTS["archimago_caido"]
        self.assertEqual(q["tipo"], "kill")
        self.assertEqual(q["objetivo"]["target"], "archimago vexthar")
        self.assertEqual(q["objetivo"]["cantidad"], 1)

    def test_nivel_minimo_aprendices(self):
        self.assertEqual(QUESTS["aprendices_torre"]["nivel_minimo"], 4)

    def test_nivel_minimo_archimago(self):
        self.assertEqual(QUESTS["archimago_caido"]["nivel_minimo"], 7)

    def test_dador_aprendices_es_aldric(self):
        q = QUESTS["aprendices_torre"]
        self.assertIn("Aldric", q["dador"])

    def test_dador_archimago_es_mira(self):
        q = QUESTS["archimago_caido"]
        self.assertIn("Mira", q["dador"])

    def test_recompensa_archimago_tiene_prototipo(self):
        q = QUESTS["archimago_caido"]
        self.assertEqual(q["recompensa"].get("prototipo"), "MANTO_ARCANO")

    def test_recompensa_aprendices_sin_prototipo(self):
        q = QUESTS["aprendices_torre"]
        self.assertNotIn("prototipo", q["recompensa"])

    def test_xp_archimago_mayor_que_aprendices(self):
        xp_arch = QUESTS["archimago_caido"]["recompensa"]["xp"]
        xp_apr = QUESTS["aprendices_torre"]["recompensa"]["xp"]
        self.assertGreater(xp_arch, xp_apr)

    def test_buscar_aprendices_por_nombre_parcial(self):
        qid, q = buscar_quest("aprendices")
        self.assertEqual(qid, "aprendices_torre")
        self.assertIsNotNone(q)

    def test_buscar_archimago_por_nombre_parcial(self):
        qid, q = buscar_quest("archimago caído")
        self.assertEqual(qid, "archimago_caido")
        self.assertIsNotNone(q)

    def test_quest_disponible_aprendices_nivel_ok(self):
        ok, _ = quest_disponible("aprendices_torre", 4, {})
        self.assertTrue(ok)

    def test_quest_no_disponible_aprendices_nivel_bajo(self):
        ok, msg = quest_disponible("aprendices_torre", 3, {})
        self.assertFalse(ok)
        self.assertIn("nivel", msg)

    def test_quest_disponible_archimago_nivel_ok(self):
        ok, _ = quest_disponible("archimago_caido", 7, {})
        self.assertTrue(ok)

    def test_quest_no_disponible_archimago_nivel_bajo(self):
        ok, msg = quest_disponible("archimago_caido", 6, {})
        self.assertFalse(ok)
        self.assertIn("nivel", msg)

    def test_registrar_kill_aprendiz_progresa(self):
        quests = {"aprendices_torre": {"estado": "activa", "progreso": {}}}
        quests = registrar_kill("aprendices_torre", quests)
        self.assertEqual(kills_actuales("aprendices_torre", quests), 1)
        self.assertEqual(quests["aprendices_torre"]["estado"], "activa")

    def test_registrar_kill_aprendiz_completa_en_tres(self):
        quests = {"aprendices_torre": {"estado": "activa", "progreso": {}}}
        for _ in range(3):
            quests = registrar_kill("aprendices_torre", quests)
        self.assertEqual(quests["aprendices_torre"]["estado"], "completada")

    def test_registrar_kill_archimago_completa_en_uno(self):
        quests = {"archimago_caido": {"estado": "activa", "progreso": {}}}
        quests = registrar_kill("archimago_caido", quests)
        self.assertEqual(quests["archimago_caido"]["estado"], "completada")

    def test_quests_de_npc_aldric_incluye_aprendices(self):
        quests_aldric = quests_de_npc("Hermano Aldric el sacerdote")
        self.assertIn("aprendices_torre", quests_aldric)

    def test_quests_de_npc_mira_incluye_archimago(self):
        quests_mira = quests_de_npc("Mira la mercader")
        self.assertIn("archimago_caido", quests_mira)

    def test_rep_reward_aprendices_penaliza_legion(self):
        rep = QUESTS["aprendices_torre"]["rep_reward"]
        self.assertLess(rep.get("legion_oscura", 0), 0)

    def test_rep_reward_archimago_penaliza_legion(self):
        rep = QUESTS["archimago_caido"]["rep_reward"]
        self.assertLess(rep.get("legion_oscura", 0), 0)


class TestRecetasTorre(unittest.TestCase):

    def test_recetas_torre_presentes(self):
        self.assertIn("esencia de ceniza", RECETAS)
        self.assertIn("elixir arcano", RECETAS)

    def test_esencia_ceniza_ingredientes(self):
        r = RECETAS["esencia de ceniza"]
        self.assertEqual(r["ingredientes"], {"cenizas arcanas": 2})

    def test_esencia_ceniza_resultado(self):
        r = RECETAS["esencia de ceniza"]
        self.assertEqual(r["resultado_prototipo"], "POCION_VIDA_MAYOR")
        self.assertEqual(r["cantidad"], 1)

    def test_elixir_arcano_ingredientes(self):
        r = RECETAS["elixir arcano"]
        self.assertEqual(r["ingredientes"], {"cenizas arcanas": 1, "fragmento arcano": 1})

    def test_elixir_arcano_resultado(self):
        r = RECETAS["elixir arcano"]
        self.assertEqual(r["resultado_prototipo"], "ELIXIR_RESTAURACION")
        self.assertEqual(r["cantidad"], 1)

    def test_buscar_esencia_por_prefijo(self):
        nombre, receta = buscar_receta("esencia")
        self.assertEqual(nombre, "esencia de ceniza")
        self.assertIsNotNone(receta)

    def test_buscar_elixir_arcano_por_nombre_parcial(self):
        nombre, receta = buscar_receta("elixir arcano")
        self.assertEqual(nombre, "elixir arcano")
        self.assertIsNotNone(receta)

    def test_verificar_esencia_sin_cenizas_falla(self):
        ok, faltantes = verificar_ingredientes({}, RECETAS["esencia de ceniza"])
        self.assertFalse(ok)
        self.assertIn("cenizas arcanas", faltantes)

    def test_verificar_esencia_con_una_ceniza_insuficiente(self):
        ok, faltantes = verificar_ingredientes({"cenizas arcanas": 1}, RECETAS["esencia de ceniza"])
        self.assertFalse(ok)
        self.assertEqual(faltantes["cenizas arcanas"], 1)

    def test_verificar_esencia_con_dos_cenizas_ok(self):
        ok, faltantes = verificar_ingredientes({"cenizas arcanas": 2}, RECETAS["esencia de ceniza"])
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_verificar_elixir_sin_fragmento_falla(self):
        ok, faltantes = verificar_ingredientes(
            {"cenizas arcanas": 1}, RECETAS["elixir arcano"]
        )
        self.assertFalse(ok)
        self.assertIn("fragmento arcano", faltantes)

    def test_verificar_elixir_con_ambos_ingredientes_ok(self):
        ok, faltantes = verificar_ingredientes(
            {"cenizas arcanas": 1, "fragmento arcano": 1}, RECETAS["elixir arcano"]
        )
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})


if __name__ == "__main__":
    unittest.main()
