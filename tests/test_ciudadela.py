"""
tests/test_ciudadela.py

Tests unitarios puros para los contenidos de la v0.18.0 — Ciudadela Oscura.
Sin dependencias de Evennia.

Cubre: quests, recipes, spawn tables y achievements de la nueva zona.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_ciudadela.py
"""
import unittest

from systems.quests.quests import QUESTS, quest_disponible, quests_de_npc, registrar_kill
from systems.crafting.recipes import RECETAS, buscar_receta, verificar_ingredientes
from systems.spawn.tables import ZONAS
from systems.achievements.achievements import JEFES


# ---------------------------------------------------------------------------
# Quests: estructura
# ---------------------------------------------------------------------------

class TestNuevasQuests(unittest.TestCase):

    def test_liche_inmortal_existe(self):
        self.assertIn("liche_inmortal", QUESTS)

    def test_fragmentos_oscuridad_existe(self):
        self.assertIn("fragmentos_oscuridad", QUESTS)

    def test_liche_inmortal_es_kill(self):
        self.assertEqual(QUESTS["liche_inmortal"]["tipo"], "kill")

    def test_fragmentos_oscuridad_es_fetch(self):
        self.assertEqual(QUESTS["fragmentos_oscuridad"]["tipo"], "fetch")

    def test_liche_inmortal_objetivo_correcto(self):
        obj = QUESTS["liche_inmortal"]["objetivo"]
        self.assertEqual(obj["target"], "liche inmortal")
        self.assertEqual(obj["cantidad"], 1)

    def test_fragmentos_objetivo_correcto(self):
        obj = QUESTS["fragmentos_oscuridad"]["objetivo"]
        self.assertEqual(obj["target"], "fragmento de alma oscura")
        self.assertEqual(obj["cantidad"], 3)

    def test_liche_inmortal_nivel_minimo(self):
        self.assertEqual(QUESTS["liche_inmortal"]["nivel_minimo"], 9)

    def test_fragmentos_nivel_minimo(self):
        self.assertEqual(QUESTS["fragmentos_oscuridad"]["nivel_minimo"], 7)

    def test_liche_inmortal_recompensa_xp(self):
        self.assertEqual(QUESTS["liche_inmortal"]["recompensa"]["xp"], 900)

    def test_fragmentos_recompensa_monedas(self):
        self.assertEqual(QUESTS["fragmentos_oscuridad"]["recompensa"]["monedas"], 90)

    def test_todas_tienen_campos_obligatorios(self):
        for qid in ("liche_inmortal", "fragmentos_oscuridad"):
            q = QUESTS[qid]
            for campo in ("titulo", "descripcion", "tipo", "objetivo", "dador",
                          "receptor", "recompensa", "rep_reward",
                          "texto_oferta", "texto_progreso", "texto_entrega",
                          "nivel_minimo"):
                self.assertIn(campo, q, f"{qid} falta '{campo}'")

    def test_total_quests_aumentado(self):
        # 13 previas + 2 nuevas (v0.18) + 6 encadenadas (v0.20) = 21
        self.assertEqual(len(QUESTS), 21)


# ---------------------------------------------------------------------------
# Quests: lógica
# ---------------------------------------------------------------------------

class TestQuestLogica(unittest.TestCase):

    def test_liche_inmortal_bloqueada_nivel_bajo(self):
        ok, motivo = quest_disponible("liche_inmortal", nivel=8, quests_personaje={})
        self.assertFalse(ok)
        self.assertIn("nivel", motivo.lower())

    def test_liche_inmortal_disponible_nivel_9(self):
        ok, _ = quest_disponible("liche_inmortal", nivel=9, quests_personaje={})
        self.assertTrue(ok)

    def test_fragmentos_bloqueada_nivel_bajo(self):
        ok, _ = quest_disponible("fragmentos_oscuridad", nivel=6, quests_personaje={})
        self.assertFalse(ok)

    def test_fragmentos_disponible_nivel_7(self):
        ok, _ = quest_disponible("fragmentos_oscuridad", nivel=7, quests_personaje={})
        self.assertTrue(ok)

    def test_liche_inmortal_no_disponible_si_activa(self):
        quests = {"liche_inmortal": {"estado": "activa"}}
        ok, _ = quest_disponible("liche_inmortal", nivel=10, quests_personaje=quests)
        self.assertFalse(ok)

    def test_liche_inmortal_no_disponible_si_entregada(self):
        quests = {"liche_inmortal": {"estado": "entregada"}}
        ok, _ = quest_disponible("liche_inmortal", nivel=10, quests_personaje=quests)
        self.assertFalse(ok)

    def test_aldric_da_liche_inmortal(self):
        qids = quests_de_npc("Hermano Aldric el sacerdote")
        self.assertIn("liche_inmortal", qids)

    def test_mira_da_fragmentos_oscuridad(self):
        qids = quests_de_npc("Mira la mercader")
        self.assertIn("fragmentos_oscuridad", qids)

    def test_kill_liche_progresa_quest(self):
        quests = {"liche_inmortal": {"estado": "activa", "progreso": {}}}
        resultado = registrar_kill("liche_inmortal", quests)
        self.assertEqual(resultado["liche_inmortal"]["estado"], "completada")

    def test_kill_liche_progreso_correcto(self):
        quests = {"liche_inmortal": {"estado": "activa", "progreso": {}}}
        resultado = registrar_kill("liche_inmortal", quests)
        self.assertEqual(resultado["liche_inmortal"]["progreso"]["kills"], 1)


# ---------------------------------------------------------------------------
# Recetas
# ---------------------------------------------------------------------------

class TestNuevasRecetas(unittest.TestCase):

    def test_elixir_sombrio_existe(self):
        self.assertIn("elixir sombrío", RECETAS)

    def test_tonico_sombras_existe(self):
        self.assertIn("tónico de las sombras", RECETAS)

    def test_elixir_sombrio_ingredientes(self):
        r = RECETAS["elixir sombrío"]
        self.assertIn("cenizas sombrías", r["ingredientes"])
        self.assertIn("fragmento de alma oscura", r["ingredientes"])
        self.assertEqual(r["ingredientes"]["cenizas sombrías"], 2)
        self.assertEqual(r["ingredientes"]["fragmento de alma oscura"], 1)

    def test_tonico_sombras_ingredientes(self):
        r = RECETAS["tónico de las sombras"]
        self.assertIn("cristal de oscuridad", r["ingredientes"])
        self.assertIn("cenizas sombrías", r["ingredientes"])
        self.assertEqual(r["ingredientes"]["cristal de oscuridad"], 1)
        self.assertEqual(r["ingredientes"]["cenizas sombrías"], 1)

    def test_elixir_sombrio_resultado(self):
        self.assertEqual(RECETAS["elixir sombrío"]["resultado_prototipo"], "ELIXIR_RESTAURACION")
        self.assertEqual(RECETAS["elixir sombrío"]["cantidad"], 1)

    def test_tonico_sombras_resultado(self):
        self.assertEqual(RECETAS["tónico de las sombras"]["resultado_prototipo"], "POCION_VIDA_MAYOR")
        self.assertEqual(RECETAS["tónico de las sombras"]["cantidad"], 2)

    def test_total_recetas_aumentado(self):
        # 12 previas + 8 equipo (v0.24) = 20
        self.assertEqual(len(RECETAS), 20)

    def test_buscar_elixir_sombrio(self):
        nombre, receta = buscar_receta("elixir sombrío")
        self.assertIsNotNone(receta)
        self.assertEqual(nombre, "elixir sombrío")

    def test_buscar_tonico_sombras_parcial(self):
        nombre, receta = buscar_receta("tónico de las")
        self.assertIsNotNone(receta)
        self.assertEqual(nombre, "tónico de las sombras")


# ---------------------------------------------------------------------------
# Recetas: verificar ingredientes
# ---------------------------------------------------------------------------

class TestIngredientesNuevosRecetas(unittest.TestCase):

    def test_elixir_sombrio_ok(self):
        inventario = {"cenizas sombrías": 2, "fragmento de alma oscura": 1}
        ok, faltantes = verificar_ingredientes(inventario, RECETAS["elixir sombrío"])
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_elixir_sombrio_falta_cenizas(self):
        inventario = {"cenizas sombrías": 1, "fragmento de alma oscura": 1}
        ok, faltantes = verificar_ingredientes(inventario, RECETAS["elixir sombrío"])
        self.assertFalse(ok)
        self.assertEqual(faltantes["cenizas sombrías"], 1)

    def test_tonico_sombras_ok(self):
        inventario = {"cristal de oscuridad": 1, "cenizas sombrías": 1}
        ok, faltantes = verificar_ingredientes(inventario, RECETAS["tónico de las sombras"])
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_tonico_sombras_vacio_falla(self):
        ok, faltantes = verificar_ingredientes({}, RECETAS["tónico de las sombras"])
        self.assertFalse(ok)
        self.assertIn("cristal de oscuridad", faltantes)
        self.assertIn("cenizas sombrías", faltantes)


# ---------------------------------------------------------------------------
# Spawn tables
# ---------------------------------------------------------------------------

class TestZonasCiudadela(unittest.TestCase):

    def test_portal_ciudadela_existe(self):
        self.assertIn("portal_ciudadela", ZONAS)

    def test_salon_trono_existe(self):
        self.assertIn("salon_trono", ZONAS)

    def test_altar_liche_existe(self):
        self.assertIn("altar_liche", ZONAS)

    def test_portal_tiene_caballeros(self):
        protos = [e["prototipo"] for e in ZONAS["portal_ciudadela"]]
        self.assertIn("CABALLERO_MUERTE", protos)

    def test_salon_tiene_hechicero(self):
        protos = [e["prototipo"] for e in ZONAS["salon_trono"]]
        self.assertIn("HECHICERO_SOMBRIO", protos)

    def test_altar_tiene_liche_inmortal(self):
        protos = [e["prototipo"] for e in ZONAS["altar_liche"]]
        self.assertIn("LICHE_INMORTAL", protos)

    def test_portal_cantidad_caballeros(self):
        entrada = next(e for e in ZONAS["portal_ciudadela"] if e["prototipo"] == "CABALLERO_MUERTE")
        self.assertEqual(entrada["cantidad"], 2)

    def test_altar_solo_un_liche(self):
        entrada = ZONAS["altar_liche"][0]
        self.assertEqual(entrada["cantidad"], 1)


# ---------------------------------------------------------------------------
# Achievements: LICHE_INMORTAL en JEFES
# ---------------------------------------------------------------------------

class TestAchievementsConNuevoJefe(unittest.TestCase):

    def test_liche_inmortal_en_jefes(self):
        self.assertIn("LICHE_INMORTAL", JEFES)

    def test_total_jefes_7(self):
        self.assertEqual(len(JEFES), 7)

    def test_todos_jefes_requiere_7(self):
        todos = list(JEFES)
        # Con 6 jefes no basta
        from systems.achievements.achievements import _cumple
        datos_6 = {
            "nivel": 1, "quests_entregadas": 0, "habilidades": [],
            "reputacion": {}, "kills_totales": 0, "jefes_derrotados": todos[:-1],
            "objetos_crafteados": 0, "encantamiento_max": 0, "banco_usado": False,
        }
        self.assertFalse(_cumple("todos_jefes", datos_6))

    def test_todos_jefes_cumple_con_7(self):
        from systems.achievements.achievements import _cumple
        datos_7 = {
            "nivel": 1, "quests_entregadas": 0, "habilidades": [],
            "reputacion": {}, "kills_totales": 0, "jefes_derrotados": list(JEFES),
            "objetos_crafteados": 0, "encantamiento_max": 0, "banco_usado": False,
        }
        self.assertTrue(_cumple("todos_jefes", datos_7))


if __name__ == "__main__":
    unittest.main()
