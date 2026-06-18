"""
tests/test_minas_system.py

Tests unitarios para la zona Minas de Hierro Viejo (v0.14.0).
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


class TestZonasMinas(unittest.TestCase):

    def test_zonas_minas_presentes(self):
        for z in ("boca_mina", "galeria_principal", "caverna_coloso"):
            self.assertIn(z, ZONAS, f"Zona '{z}' no está en ZONAS")

    def test_boca_mina_tiene_aranas(self):
        resultado = npcs_necesarios("boca_mina")
        self.assertEqual(resultado, {"ARANA_CUEVA": 2})

    def test_galeria_tiene_mineros(self):
        resultado = npcs_necesarios("galeria_principal")
        self.assertEqual(resultado, {"MINERO_MALDITO": 2})

    def test_caverna_tiene_golem(self):
        resultado = npcs_necesarios("caverna_coloso")
        self.assertEqual(resultado, {"GOLEM_PIEDRA": 1})

    def test_mercado_tiene_buscador(self):
        resultado = npcs_necesarios("mercado")
        self.assertIn("BUSCADOR_TESOROS", resultado)

    def test_faltantes_galeria_parcial(self):
        faltantes = calcular_faltantes("galeria_principal", {"MINERO_MALDITO": 1})
        self.assertEqual(faltantes, {"MINERO_MALDITO": 1})

    def test_faltantes_caverna_completa(self):
        faltantes = calcular_faltantes("caverna_coloso", {"GOLEM_PIEDRA": 1})
        self.assertEqual(faltantes, {})

    def test_faltantes_boca_vacia(self):
        faltantes = calcular_faltantes("boca_mina", {})
        self.assertEqual(faltantes, {"ARANA_CUEVA": 2})


class TestQuestsMinas(unittest.TestCase):

    def test_quests_presentes(self):
        self.assertIn("veta_perdida", QUESTS)
        self.assertIn("coloso_despertado", QUESTS)

    def test_veta_es_fetch(self):
        q = QUESTS["veta_perdida"]
        self.assertEqual(q["tipo"], "fetch")
        self.assertEqual(q["objetivo"]["target"], "mineral de hierro")
        self.assertEqual(q["objetivo"]["cantidad"], 2)

    def test_coloso_es_kill(self):
        q = QUESTS["coloso_despertado"]
        self.assertEqual(q["tipo"], "kill")
        self.assertEqual(q["objetivo"]["target"], "gólem de piedra")
        self.assertEqual(q["objetivo"]["cantidad"], 1)

    def test_nivel_minimo_veta(self):
        self.assertEqual(QUESTS["veta_perdida"]["nivel_minimo"], 3)

    def test_nivel_minimo_coloso(self):
        self.assertEqual(QUESTS["coloso_despertado"]["nivel_minimo"], 6)

    def test_recompensa_veta(self):
        r = QUESTS["veta_perdida"]["recompensa"]
        self.assertIn("xp", r)
        self.assertIn("monedas", r)
        self.assertGreater(r["xp"], 0)
        self.assertGreater(r["monedas"], 0)

    def test_recompensa_coloso_tiene_prototipo(self):
        r = QUESTS["coloso_despertado"]["recompensa"]
        self.assertIn("prototipo", r)
        self.assertEqual(r["prototipo"], "ANILLO_CONSTITUCION")

    def test_rep_reward_gremio(self):
        for qid in ("veta_perdida", "coloso_despertado"):
            self.assertIn("gremio_aventureros", QUESTS[qid]["rep_reward"])
            self.assertGreater(QUESTS[qid]["rep_reward"]["gremio_aventureros"], 0)

    def test_buscar_veta_por_titulo(self):
        qid, _ = buscar_quest("La Veta Perdida")
        self.assertEqual(qid, "veta_perdida")

    def test_buscar_coloso_por_id(self):
        qid, _ = buscar_quest("coloso_despertado")
        self.assertEqual(qid, "coloso_despertado")

    def test_buscar_coloso_por_titulo_parcial(self):
        qid, _ = buscar_quest("Coloso")
        self.assertEqual(qid, "coloso_despertado")

    def test_torben_tiene_ambas_quests(self):
        ids = quests_de_npc("Torben el buscador de tesoros")
        self.assertIn("veta_perdida", ids)
        self.assertIn("coloso_despertado", ids)

    def test_torben_no_tiene_quests_ajenas(self):
        ids = quests_de_npc("Torben el buscador de tesoros")
        self.assertNotIn("problema_goblins", ids)
        self.assertNotIn("amenaza_catacumbas", ids)

    def test_veta_disponible_nivel_correcto(self):
        ok, _ = quest_disponible("veta_perdida", nivel=3, quests_personaje={})
        self.assertTrue(ok)

    def test_veta_no_disponible_nivel_bajo(self):
        ok, motivo = quest_disponible("veta_perdida", nivel=2, quests_personaje={})
        self.assertFalse(ok)
        self.assertIn("nivel", motivo)

    def test_coloso_disponible_nivel_correcto(self):
        ok, _ = quest_disponible("coloso_despertado", nivel=6, quests_personaje={})
        self.assertTrue(ok)

    def test_coloso_no_disponible_nivel_bajo(self):
        ok, motivo = quest_disponible("coloso_despertado", nivel=5, quests_personaje={})
        self.assertFalse(ok)
        self.assertIn("nivel", motivo)

    def test_fetch_veta_completa(self):
        ok, actual = verificar_fetch("veta_perdida", {"mineral de hierro": 2})
        self.assertTrue(ok)
        self.assertEqual(actual, 2)

    def test_fetch_veta_incompleta(self):
        ok, actual = verificar_fetch("veta_perdida", {"mineral de hierro": 1})
        self.assertFalse(ok)
        self.assertEqual(actual, 1)

    def test_fetch_veta_sin_items(self):
        ok, actual = verificar_fetch("veta_perdida", {})
        self.assertFalse(ok)
        self.assertEqual(actual, 0)

    def test_kill_coloso_registrar(self):
        quests = {"coloso_despertado": {"estado": "activa", "progreso": {}}}
        quests = registrar_kill("coloso_despertado", quests)
        self.assertEqual(quests["coloso_despertado"]["estado"], "completada")
        self.assertEqual(kills_actuales("coloso_despertado", quests), 1)

    def test_todos_campos_requeridos_veta(self):
        q = QUESTS["veta_perdida"]
        for campo in ("titulo", "descripcion", "tipo", "objetivo", "dador",
                      "receptor", "recompensa", "texto_oferta", "texto_progreso",
                      "texto_entrega", "nivel_minimo"):
            self.assertIn(campo, q, f"Falta campo '{campo}' en veta_perdida")

    def test_todos_campos_requeridos_coloso(self):
        q = QUESTS["coloso_despertado"]
        for campo in ("titulo", "descripcion", "tipo", "objetivo", "dador",
                      "receptor", "recompensa", "texto_oferta", "texto_progreso",
                      "texto_entrega", "nivel_minimo"):
            self.assertIn(campo, q, f"Falta campo '{campo}' en coloso_despertado")


class TestRecetasMinas(unittest.TestCase):

    def test_receta_antidoto_arana_existe(self):
        nombre, receta = buscar_receta("antídoto de araña")
        self.assertIsNotNone(nombre)
        self.assertIsNotNone(receta)

    def test_antidoto_arana_ingredientes(self):
        _, receta = buscar_receta("antídoto de araña")
        self.assertIn("hilo de araña", receta["ingredientes"])
        self.assertEqual(receta["ingredientes"]["hilo de araña"], 2)

    def test_antidoto_arana_produce_dos(self):
        _, receta = buscar_receta("antídoto de araña")
        self.assertEqual(receta["cantidad"], 2)

    def test_antidoto_arana_resultado(self):
        _, receta = buscar_receta("antídoto de araña")
        self.assertEqual(receta["resultado_prototipo"], "ANTIDOTO")

    def test_antidoto_arana_verificar_ok(self):
        _, receta = buscar_receta("antídoto de araña")
        ok, faltantes = verificar_ingredientes({"hilo de araña": 2}, receta)
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_antidoto_arana_verificar_fallo(self):
        _, receta = buscar_receta("antídoto de araña")
        ok, faltantes = verificar_ingredientes({"hilo de araña": 1}, receta)
        self.assertFalse(ok)
        self.assertIn("hilo de araña", faltantes)

    def test_receta_tonico_piedra_existe(self):
        nombre, receta = buscar_receta("tónico de piedra")
        self.assertIsNotNone(nombre)
        self.assertIsNotNone(receta)

    def test_tonico_piedra_ingredientes(self):
        _, receta = buscar_receta("tónico de piedra")
        self.assertIn("mineral de hierro", receta["ingredientes"])
        self.assertIn("gema en bruto", receta["ingredientes"])

    def test_tonico_piedra_resultado(self):
        _, receta = buscar_receta("tónico de piedra")
        self.assertEqual(receta["resultado_prototipo"], "POCION_VIDA_MAYOR")

    def test_tonico_piedra_verificar_ok(self):
        _, receta = buscar_receta("tónico de piedra")
        ok, faltantes = verificar_ingredientes(
            {"mineral de hierro": 1, "gema en bruto": 1}, receta
        )
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_tonico_piedra_sin_gema_falla(self):
        _, receta = buscar_receta("tónico de piedra")
        ok, faltantes = verificar_ingredientes({"mineral de hierro": 1}, receta)
        self.assertFalse(ok)
        self.assertIn("gema en bruto", faltantes)

    def test_total_recetas_aumentado(self):
        self.assertGreaterEqual(len(RECETAS), 8)


if __name__ == "__main__":
    unittest.main()
