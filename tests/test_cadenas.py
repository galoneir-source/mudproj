"""
tests/test_cadenas.py

Tests unitarios puros para el sistema de misiones encadenadas (v0.20.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_cadenas.py
"""
import unittest

from systems.quests.quests import (
    QUESTS,
    quest_disponible,
    quests_de_npc,
    registrar_kill,
    verificar_fetch,
)


# ---------------------------------------------------------------------------
# Catálogo: nuevas quests existen
# ---------------------------------------------------------------------------

class TestNuevasQuests(unittest.TestCase):

    CADENA_1 = ["ecos_del_baron", "legion_en_marcha", "filo_del_abismo"]
    CADENA_2 = ["secretos_de_la_torre", "corazon_de_tinieblas", "esencia_del_poder"]

    def test_cadena_1_existe(self):
        for qid in self.CADENA_1:
            self.assertIn(qid, QUESTS, qid)

    def test_cadena_2_existe(self):
        for qid in self.CADENA_2:
            self.assertIn(qid, QUESTS, qid)

    def test_total_quests_aumentado(self):
        # 15 previas + 6 nuevas = 21
        self.assertEqual(len(QUESTS), 21)

    def test_todas_tienen_campo_requiere(self):
        for qid in self.CADENA_1 + self.CADENA_2:
            self.assertIn("requiere", QUESTS[qid], qid)
            self.assertIsNotNone(QUESTS[qid]["requiere"])

    def test_prerrequisitos_cadena_1(self):
        self.assertEqual(QUESTS["ecos_del_baron"]["requiere"],    "caballero_sombras")
        self.assertEqual(QUESTS["legion_en_marcha"]["requiere"],  "ecos_del_baron")
        self.assertEqual(QUESTS["filo_del_abismo"]["requiere"],   "legion_en_marcha")

    def test_prerrequisitos_cadena_2(self):
        self.assertEqual(QUESTS["secretos_de_la_torre"]["requiere"],  "archimago_caido")
        self.assertEqual(QUESTS["corazon_de_tinieblas"]["requiere"],  "secretos_de_la_torre")
        self.assertEqual(QUESTS["esencia_del_poder"]["requiere"],     "corazon_de_tinieblas")

    def test_tipos_cadena_1(self):
        self.assertEqual(QUESTS["ecos_del_baron"]["tipo"],   "fetch")
        self.assertEqual(QUESTS["legion_en_marcha"]["tipo"], "kill")
        self.assertEqual(QUESTS["filo_del_abismo"]["tipo"],  "kill")

    def test_tipos_cadena_2(self):
        self.assertEqual(QUESTS["secretos_de_la_torre"]["tipo"],  "fetch")
        self.assertEqual(QUESTS["corazon_de_tinieblas"]["tipo"],  "kill")
        self.assertEqual(QUESTS["esencia_del_poder"]["tipo"],     "fetch")

    def test_niveles_minimos_cadena_1(self):
        self.assertEqual(QUESTS["ecos_del_baron"]["nivel_minimo"],   6)
        self.assertEqual(QUESTS["legion_en_marcha"]["nivel_minimo"], 7)
        self.assertEqual(QUESTS["filo_del_abismo"]["nivel_minimo"],  8)

    def test_niveles_minimos_cadena_2(self):
        self.assertEqual(QUESTS["secretos_de_la_torre"]["nivel_minimo"],  7)
        self.assertEqual(QUESTS["corazon_de_tinieblas"]["nivel_minimo"],  8)
        self.assertEqual(QUESTS["esencia_del_poder"]["nivel_minimo"],     9)

    def test_recompensa_final_cadena_1(self):
        self.assertEqual(QUESTS["filo_del_abismo"]["recompensa"]["prototipo"], "TUNICA_LICHE")

    def test_recompensa_final_cadena_2(self):
        self.assertEqual(QUESTS["esencia_del_poder"]["recompensa"]["prototipo"], "BACULO_ARCHIMAGO")

    def test_campos_obligatorios_todos(self):
        for qid in self.CADENA_1 + self.CADENA_2:
            q = QUESTS[qid]
            for campo in ("titulo", "descripcion", "tipo", "objetivo", "dador",
                          "receptor", "recompensa", "rep_reward",
                          "texto_oferta", "texto_progreso", "texto_entrega",
                          "nivel_minimo", "requiere"):
                self.assertIn(campo, q, f"{qid} falta '{campo}'")


# ---------------------------------------------------------------------------
# quest_disponible: prerrequisito
# ---------------------------------------------------------------------------

class TestPrerrequisito(unittest.TestCase):

    def _quests(self, **kwargs):
        """Crea un dict de quests con estados dados."""
        return {qid: {"estado": estado} for qid, estado in kwargs.items()}

    def test_ecos_bloqueada_sin_prerrequisito(self):
        ok, motivo = quest_disponible("ecos_del_baron", nivel=10, quests_personaje={})
        self.assertFalse(ok)
        # El motivo debe mencionar el título del prerrequisito (sin tags de color)
        motivo_clean = motivo.replace("|c", "").replace("|n", "").lower()
        self.assertIn("caballero", motivo_clean)

    def test_ecos_bloqueada_si_prereq_activo(self):
        quests = self._quests(caballero_sombras="activa")
        ok, _ = quest_disponible("ecos_del_baron", nivel=10, quests_personaje=quests)
        self.assertFalse(ok)

    def test_ecos_bloqueada_si_prereq_completado(self):
        quests = self._quests(caballero_sombras="completada")
        ok, _ = quest_disponible("ecos_del_baron", nivel=10, quests_personaje=quests)
        self.assertFalse(ok)

    def test_ecos_disponible_si_prereq_entregado(self):
        quests = self._quests(caballero_sombras="entregada")
        ok, _ = quest_disponible("ecos_del_baron", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)

    def test_legion_bloqueada_sin_ecos(self):
        quests = self._quests(caballero_sombras="entregada")
        ok, _ = quest_disponible("legion_en_marcha", nivel=10, quests_personaje=quests)
        self.assertFalse(ok)

    def test_legion_disponible_con_ecos_entregado(self):
        quests = self._quests(caballero_sombras="entregada", ecos_del_baron="entregada")
        ok, _ = quest_disponible("legion_en_marcha", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)

    def test_filo_disponible_solo_al_final_de_cadena(self):
        quests = self._quests(
            caballero_sombras="entregada",
            ecos_del_baron="entregada",
            legion_en_marcha="entregada",
        )
        ok, _ = quest_disponible("filo_del_abismo", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)

    def test_secretos_bloqueado_sin_archimago(self):
        ok, _ = quest_disponible("secretos_de_la_torre", nivel=10, quests_personaje={})
        self.assertFalse(ok)

    def test_secretos_disponible_con_archimago(self):
        quests = self._quests(archimago_caido="entregada")
        ok, _ = quest_disponible("secretos_de_la_torre", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)

    def test_esencia_disponible_solo_con_cadena_completa(self):
        quests = self._quests(
            archimago_caido="entregada",
            secretos_de_la_torre="entregada",
            corazon_de_tinieblas="entregada",
        )
        ok, _ = quest_disponible("esencia_del_poder", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)

    def test_nivel_check_tras_prereq(self):
        # Prereq cumplido pero nivel bajo → error de nivel
        quests = self._quests(caballero_sombras="entregada")
        ok, motivo = quest_disponible("ecos_del_baron", nivel=5, quests_personaje=quests)
        self.assertFalse(ok)
        self.assertIn("nivel", motivo.lower())

    def test_quests_sin_requiere_no_afectadas(self):
        # Las quests originales sin 'requiere' siguen funcionando igual
        ok, _ = quest_disponible("problema_goblins", nivel=1, quests_personaje={})
        self.assertTrue(ok)

    def test_motivo_menciona_titulo_prereq(self):
        _, motivo = quest_disponible("ecos_del_baron", nivel=10, quests_personaje={})
        # El motivo debe mencionar el título del prerrequisito (sin formato Evennia)
        motivo_clean = motivo.replace("|c", "").replace("|n", "")
        self.assertIn("Caballero", motivo_clean)


# ---------------------------------------------------------------------------
# NPC assignments
# ---------------------------------------------------------------------------

class TestNpcAsignaciones(unittest.TestCase):

    def test_aldric_da_cadena_1(self):
        ids = quests_de_npc("Hermano Aldric el sacerdote")
        for qid in ("ecos_del_baron", "legion_en_marcha", "filo_del_abismo"):
            self.assertIn(qid, ids, qid)

    def test_mira_da_cadena_2(self):
        ids = quests_de_npc("Mira la mercader")
        for qid in ("secretos_de_la_torre", "corazon_de_tinieblas", "esencia_del_poder"):
            self.assertIn(qid, ids, qid)


# ---------------------------------------------------------------------------
# Objetivos de quests
# ---------------------------------------------------------------------------

class TestObjetivosQuests(unittest.TestCase):

    def test_ecos_objetivo_fragmento(self):
        obj = QUESTS["ecos_del_baron"]["objetivo"]
        self.assertEqual(obj["target"], "fragmento de alma oscura")
        self.assertEqual(obj["cantidad"], 2)

    def test_legion_objetivo_caballero(self):
        obj = QUESTS["legion_en_marcha"]["objetivo"]
        self.assertEqual(obj["target"], "caballero de la muerte")
        self.assertEqual(obj["cantidad"], 3)

    def test_filo_objetivo_hechicero(self):
        obj = QUESTS["filo_del_abismo"]["objetivo"]
        self.assertEqual(obj["target"], "hechicero sombrío")
        self.assertEqual(obj["cantidad"], 2)

    def test_secretos_objetivo_cenizas(self):
        obj = QUESTS["secretos_de_la_torre"]["objetivo"]
        self.assertEqual(obj["target"], "cenizas sombrías")
        self.assertEqual(obj["cantidad"], 3)

    def test_corazon_objetivo_hechicero(self):
        obj = QUESTS["corazon_de_tinieblas"]["objetivo"]
        self.assertEqual(obj["target"], "hechicero sombrío")
        self.assertEqual(obj["cantidad"], 2)

    def test_esencia_objetivo_liche(self):
        obj = QUESTS["esencia_del_poder"]["objetivo"]
        self.assertEqual(obj["target"], "esencia del liche")
        self.assertEqual(obj["cantidad"], 1)

    def test_kill_legion_progresa(self):
        quests = {"legion_en_marcha": {"estado": "activa", "progreso": {}}}
        quests = registrar_kill("legion_en_marcha", quests)
        self.assertEqual(quests["legion_en_marcha"]["progreso"]["kills"], 1)

    def test_kill_legion_completa_a_3(self):
        quests = {"legion_en_marcha": {"estado": "activa", "progreso": {"kills": 2}}}
        quests = registrar_kill("legion_en_marcha", quests)
        self.assertEqual(quests["legion_en_marcha"]["estado"], "completada")

    def test_fetch_secretos_ok(self):
        inventario = {"cenizas sombrías": 3}
        ok, actual = verificar_fetch("secretos_de_la_torre", inventario)
        self.assertTrue(ok)
        self.assertEqual(actual, 3)

    def test_fetch_secretos_incompleto(self):
        inventario = {"cenizas sombrías": 1}
        ok, actual = verificar_fetch("secretos_de_la_torre", inventario)
        self.assertFalse(ok)
        self.assertEqual(actual, 1)

    def test_fetch_esencia_ok(self):
        inventario = {"esencia del liche": 1}
        ok, actual = verificar_fetch("esencia_del_poder", inventario)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
