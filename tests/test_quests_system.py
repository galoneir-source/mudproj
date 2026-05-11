"""
tests/test_quests_system.py

Tests unitarios para systems/quests/quests.py.
No dependen de Evennia ni Django.
"""
import unittest

from systems.quests.quests import (
    QUESTS,
    buscar_quest,
    quest_disponible,
    quests_de_npc,
    quests_para_entregar,
    registrar_kill,
    verificar_fetch,
    kills_actuales,
    texto_progreso,
)


class TestBuscarQuest(unittest.TestCase):

    def test_exacto_por_id(self):
        qid, q = buscar_quest("problema_goblins")
        self.assertEqual(qid, "problema_goblins")

    def test_exacto_por_titulo(self):
        qid, q = buscar_quest("El Problema de los Goblins")
        self.assertEqual(qid, "problema_goblins")

    def test_titulo_case_insensitive(self):
        qid, _ = buscar_quest("el problema de los goblins")
        self.assertEqual(qid, "problema_goblins")

    def test_parcial_titulo(self):
        qid, _ = buscar_quest("Amenaza")
        self.assertEqual(qid, "amenaza_catacumbas")

    def test_parcial_id(self):
        qid, _ = buscar_quest("garra")
        self.assertEqual(qid, "garra_del_troll")

    def test_inexistente(self):
        qid, q = buscar_quest("misión inventada")
        self.assertIsNone(qid)
        self.assertIsNone(q)

    def test_ambiguo_devuelve_none(self):
        # "mercad" aparece en mercancia_robada y veneno_del_pantano (receptor)
        # pero no en el título de ninguna de forma única — usar un término realmente ambiguo
        qid, _ = buscar_quest("del")  # aparece en varios títulos
        self.assertIsNone(qid)

    def test_todas_buscables_por_id(self):
        for qid in QUESTS:
            found, _ = buscar_quest(qid)
            self.assertEqual(found, qid)


class TestQuestDisponible(unittest.TestCase):

    def test_disponible_ok(self):
        ok, _ = quest_disponible("problema_goblins", nivel=1, quests_personaje={})
        self.assertTrue(ok)

    def test_nivel_insuficiente(self):
        ok, motivo = quest_disponible("garra_del_troll", nivel=1, quests_personaje={})
        self.assertFalse(ok)
        self.assertIn("nivel", motivo)

    def test_ya_activa(self):
        quests = {"problema_goblins": {"estado": "activa"}}
        ok, motivo = quest_disponible("problema_goblins", nivel=5, quests_personaje=quests)
        self.assertFalse(ok)
        self.assertIn("curso", motivo)

    def test_ya_completada(self):
        quests = {"problema_goblins": {"estado": "completada"}}
        ok, motivo = quest_disponible("problema_goblins", nivel=5, quests_personaje=quests)
        self.assertFalse(ok)

    def test_ya_entregada(self):
        quests = {"problema_goblins": {"estado": "entregada"}}
        ok, motivo = quest_disponible("problema_goblins", nivel=5, quests_personaje=quests)
        self.assertFalse(ok)
        self.assertIn("completaste", motivo)

    def test_quest_inexistente(self):
        ok, _ = quest_disponible("no_existe", nivel=10, quests_personaje={})
        self.assertFalse(ok)


class TestQuestsDeNpc(unittest.TestCase):

    def test_guardia_tiene_quests(self):
        ids = quests_de_npc("guardia de la ciudad")
        self.assertIn("problema_goblins", ids)
        self.assertIn("amenaza_catacumbas", ids)

    def test_mercader_tiene_quests(self):
        ids = quests_de_npc("Mira la mercader")
        self.assertIn("mercancia_robada", ids)
        self.assertIn("veneno_del_pantano", ids)

    def test_mesonero_tiene_quests(self):
        ids = quests_de_npc("Gareth el mesonero")
        self.assertIn("garra_del_troll", ids)

    def test_npc_sin_quests(self):
        ids = quests_de_npc("goblin")
        self.assertEqual(ids, [])


class TestQuestsParaEntregar(unittest.TestCase):

    def test_quest_completada_para_npc(self):
        quests = {"problema_goblins": {"estado": "completada"}}
        ids = quests_para_entregar("guardia de la ciudad", quests)
        self.assertIn("problema_goblins", ids)

    def test_quest_activa_no_aparece(self):
        quests = {"problema_goblins": {"estado": "activa"}}
        ids = quests_para_entregar("guardia de la ciudad", quests)
        self.assertNotIn("problema_goblins", ids)

    def test_quest_entregada_no_aparece(self):
        quests = {"problema_goblins": {"estado": "entregada"}}
        ids = quests_para_entregar("guardia de la ciudad", quests)
        self.assertNotIn("problema_goblins", ids)

    def test_npc_incorrecto_no_aparece(self):
        quests = {"problema_goblins": {"estado": "completada"}}
        ids = quests_para_entregar("Gareth el mesonero", quests)
        self.assertNotIn("problema_goblins", ids)


class TestRegistrarKill(unittest.TestCase):

    def _quests_activa(self):
        return {"problema_goblins": {"estado": "activa", "progreso": {}}}

    def test_incrementa_contador(self):
        quests = self._quests_activa()
        quests = registrar_kill("problema_goblins", quests)
        self.assertEqual(kills_actuales("problema_goblins", quests), 1)

    def test_acumula_kills(self):
        quests = self._quests_activa()
        for _ in range(2):
            quests = registrar_kill("problema_goblins", quests)
        self.assertEqual(kills_actuales("problema_goblins", quests), 2)

    def test_completa_al_llegar_al_objetivo(self):
        quests = self._quests_activa()
        objetivo = QUESTS["problema_goblins"]["objetivo"]["cantidad"]
        for _ in range(objetivo):
            quests = registrar_kill("problema_goblins", quests)
        self.assertEqual(quests["problema_goblins"]["estado"], "completada")

    def test_no_muta_original(self):
        original = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        registrar_kill("problema_goblins", original)
        self.assertEqual(original["problema_goblins"]["progreso"], {})


class TestVerificarFetch(unittest.TestCase):

    def test_suficiente(self):
        inv = {"veneno de pantano": 2}
        ok, actual = verificar_fetch("veneno_del_pantano", inv)
        self.assertTrue(ok)
        self.assertEqual(actual, 2)

    def test_insuficiente(self):
        inv = {"veneno de pantano": 1}
        ok, actual = verificar_fetch("veneno_del_pantano", inv)
        self.assertFalse(ok)
        self.assertEqual(actual, 1)

    def test_sin_items(self):
        ok, actual = verificar_fetch("veneno_del_pantano", {})
        self.assertFalse(ok)
        self.assertEqual(actual, 0)

    def test_de_mas_ok(self):
        inv = {"veneno de pantano": 5}
        ok, _ = verificar_fetch("veneno_del_pantano", inv)
        self.assertTrue(ok)

    def test_quest_kill_devuelve_false(self):
        ok, _ = verificar_fetch("problema_goblins", {"goblin": 5})
        self.assertFalse(ok)


class TestTextoProgreso(unittest.TestCase):

    def test_kill_con_progreso(self):
        quests = {"problema_goblins": {"estado": "activa", "progreso": {"kills": 2}}}
        txt = texto_progreso("problema_goblins", quests)
        self.assertIn("2", txt)
        self.assertIn("3", txt)

    def test_fetch_con_inventario(self):
        quests = {"veneno_del_pantano": {"estado": "activa", "progreso": {}}}
        inv = {"veneno de pantano": 1}
        txt = texto_progreso("veneno_del_pantano", quests, inv)
        self.assertIn("1", txt)

    def test_quest_inexistente(self):
        txt = texto_progreso("no_existe", {})
        self.assertEqual(txt, "")


if __name__ == "__main__":
    unittest.main()
