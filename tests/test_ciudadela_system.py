"""
tests/test_ciudadela_system.py

Tests de integración Evennia para los contenidos de la v0.18.0 — Ciudadela Oscura.
Cubre: prototipos de NPCs/items y quests desde la perspectiva del personaje.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_ciudadela_system
"""
from evennia.utils.test_resources import EvenniaTest

from systems.quests.quests import QUESTS, quest_disponible, quests_para_entregar
from systems.crafting.recipes import RECETAS, buscar_receta, verificar_ingredientes
from systems.achievements.achievements import JEFES


def _init_char(char, nivel=10):
    char.db.nivel = nivel
    char.db.quests = {}
    char.db.monedas = 0
    char.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido"]
    char.db.reputacion = {}
    char.db.logros = []
    char.db.titulo_activo = None
    char.db.kills_totales = 0
    char.db.jefes_derrotados = []
    char.db.objetos_crafteados = 0
    char.db.encantamiento_max = 0
    char.db.banco_usado = False


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda m, **kw: self.msgs.append(str(m))
        char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


# ---------------------------------------------------------------------------
# Tests de quests con personaje Evennia
# ---------------------------------------------------------------------------

class TestQuestsCiudadelaEvenniaChar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)

    def test_liche_inmortal_disponible_para_nivel_alto(self):
        self.char1.db.nivel = 10
        ok, _ = quest_disponible("liche_inmortal", nivel=10, quests_personaje={})
        self.assertTrue(ok)

    def test_liche_inmortal_bloqueada_nivel_8(self):
        ok, motivo = quest_disponible("liche_inmortal", nivel=8, quests_personaje={})
        self.assertFalse(ok)
        self.assertIn("nivel", motivo.lower())

    def test_fragmentos_disponible_nivel_7(self):
        ok, _ = quest_disponible("fragmentos_oscuridad", nivel=7, quests_personaje={})
        self.assertTrue(ok)

    def test_quest_liche_aceptada_en_quests_char(self):
        self.char1.db.quests["liche_inmortal"] = {"estado": "activa", "progreso": {}}
        estado = self.char1.db.quests["liche_inmortal"]["estado"]
        self.assertEqual(estado, "activa")

    def test_fragmentos_completada_con_items(self):
        from systems.quests.quests import verificar_fetch
        inventario = {"fragmento de alma oscura": 3}
        completada, actual = verificar_fetch("fragmentos_oscuridad", inventario)
        self.assertTrue(completada)
        self.assertEqual(actual, 3)

    def test_fragmentos_no_completada_incompleta(self):
        from systems.quests.quests import verificar_fetch
        inventario = {"fragmento de alma oscura": 2}
        completada, actual = verificar_fetch("fragmentos_oscuridad", inventario)
        self.assertFalse(completada)
        self.assertEqual(actual, 2)

    def test_mira_recibe_fragmentos(self):
        self.char1.db.quests["fragmentos_oscuridad"] = {"estado": "completada"}
        para_entregar = quests_para_entregar("Mira la mercader", self.char1.db.quests)
        self.assertIn("fragmentos_oscuridad", para_entregar)

    def test_aldric_recibe_liche(self):
        self.char1.db.quests["liche_inmortal"] = {"estado": "completada"}
        para_entregar = quests_para_entregar("Hermano Aldric el sacerdote", self.char1.db.quests)
        self.assertIn("liche_inmortal", para_entregar)

    def test_texto_progreso_kill_quest(self):
        from systems.quests.quests import texto_progreso
        quests = {"liche_inmortal": {"estado": "activa", "progreso": {"kills": 0}}}
        texto = texto_progreso("liche_inmortal", quests)
        self.assertIn("liche", texto.lower())

    def test_texto_progreso_fetch_quest(self):
        from systems.quests.quests import texto_progreso
        quests = {"fragmentos_oscuridad": {"estado": "activa", "progreso": {}}}
        inventario = {"fragmento de alma oscura": 1}
        texto = texto_progreso("fragmentos_oscuridad", quests, inventario)
        self.assertIn("2", texto)  # faltante = 3 - 1 = 2


# ---------------------------------------------------------------------------
# Tests de crafteo con materiales de la ciudadela
# ---------------------------------------------------------------------------

class TestCrafteoCiudadelaEvenniaChar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)

    def test_buscar_elixir_sombrio(self):
        nombre, receta = buscar_receta("elixir sombrío")
        self.assertIsNotNone(receta)
        self.assertEqual(nombre, "elixir sombrío")

    def test_buscar_elixir_por_prefijo(self):
        nombre, receta = buscar_receta("elixir som")
        self.assertIsNotNone(receta)

    def test_elixir_sombrio_falta_ingrediente(self):
        inventario = {"cenizas sombrías": 2}  # falta alma oscura
        ok, faltantes = verificar_ingredientes(inventario, RECETAS["elixir sombrío"])
        self.assertFalse(ok)
        self.assertIn("fragmento de alma oscura", faltantes)

    def test_tonico_sombras_ok(self):
        inventario = {"cristal de oscuridad": 1, "cenizas sombrías": 1}
        ok, faltantes = verificar_ingredientes(inventario, RECETAS["tónico de las sombras"])
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_tonico_produce_dos_pociones(self):
        self.assertEqual(RECETAS["tónico de las sombras"]["cantidad"], 2)


# ---------------------------------------------------------------------------
# Tests de logros con LICHE_INMORTAL
# ---------------------------------------------------------------------------

class TestLogrosConLicheEvenniaChar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_matar_liche_incrementa_kills_y_jefes(self):
        self.char1.db.kills_totales = 0
        self.char1.db.jefes_derrotados = []
        self.char1.db.kills_totales += 1
        jefes = list(self.char1.db.jefes_derrotados)
        jefes.append("LICHE_INMORTAL")
        self.char1.db.jefes_derrotados = jefes
        self.assertEqual(self.char1.db.kills_totales, 1)
        self.assertIn("LICHE_INMORTAL", self.char1.db.jefes_derrotados)

    def test_todos_jefes_no_cumple_sin_liche(self):
        from features.achievements.commands import comprobar_y_notificar
        self.char1.db.jefes_derrotados = [j for j in JEFES if j != "LICHE_INMORTAL"]
        comprobar_y_notificar(self.char1)
        self.assertNotIn("todos_jefes", list(self.char1.db.logros))

    def test_todos_jefes_cumple_con_liche(self):
        from features.achievements.commands import comprobar_y_notificar
        self.char1.db.jefes_derrotados = list(JEFES)
        comprobar_y_notificar(self.char1)
        self.assertIn("todos_jefes", list(self.char1.db.logros))

    def test_tres_jefes_cumple_con_liche_entre_ellos(self):
        from features.achievements.commands import comprobar_y_notificar
        tres = ["LICHE_INMORTAL", "GOBLIN_JEFE", "TROLL"]
        self.char1.db.jefes_derrotados = tres
        comprobar_y_notificar(self.char1)
        self.assertIn("tres_jefes", list(self.char1.db.logros))

    def test_notificacion_todos_jefes_contiene_titulo(self):
        from features.achievements.commands import comprobar_y_notificar
        self.char1.db.jefes_derrotados = list(JEFES)
        comprobar_y_notificar(self.char1)
        self.assertIn("el Terror", self.cap.all())


if __name__ == "__main__":
    import unittest
    unittest.main()
