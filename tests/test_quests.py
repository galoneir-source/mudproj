"""
tests/test_quests.py

Tests de integración para features/quests/commands.py y features/quests/hooks.py.
Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_quests
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.quests.commands import CmdMisiones, CmdAceptar, CmdEntregar
from features.quests.hooks import on_npc_muerte
from systems.quests.quests import QUESTS


def _make_cmd(CmdClass, caller, args=""):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = []
    cmd.lhs = args
    cmd.rhs = ""
    return cmd


class QuestTestBase(EvenniaTest):
    """Configuración base compartida."""

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.quests = {}
        self.jugador.db.nivel = 10
        self.jugador.db.monedas = 0
        self.jugador.db.experiencia = 0
        self.msgs = []
        self.jugador.msg = lambda m, **kw: self.msgs.append(str(m))
        # Silenciar msg_contents de la sala
        self.sala.msg_contents = lambda m, **kw: None

    def _ultimo_msg(self):
        return self.msgs[-1] if self.msgs else ""

    def _todos_msgs(self):
        return "\n".join(self.msgs)

    def _crear_npc(self, key):
        return create_object("typeclasses.npc.NPC", key=key, location=self.sala)


# --------------------------------------------------------------------------- #
#  CmdMisiones
# --------------------------------------------------------------------------- #

class TestCmdMisiones(QuestTestBase):

    def test_sin_misiones_mensaje_vacio(self):
        cmd = _make_cmd(CmdMisiones, self.jugador)
        cmd.func()
        self.assertIn("No tienes misiones", self._todos_msgs())

    def test_con_mision_activa_aparece_en_log(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        cmd = _make_cmd(CmdMisiones, self.jugador)
        cmd.func()
        self.assertIn("Problema de los Goblins", self._todos_msgs())

    def test_con_varias_estados_aparecen_secciones(self):
        self.jugador.db.quests = {
            "problema_goblins": {"estado": "activa", "progreso": {}},
            "veneno_del_pantano": {"estado": "completada", "progreso": {}},
        }
        cmd = _make_cmd(CmdMisiones, self.jugador)
        cmd.func()
        txt = self._todos_msgs()
        self.assertIn("Activas", txt)
        self.assertIn("Completadas", txt)

    def test_detalle_por_nombre(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {"kills": 1}}}
        cmd = _make_cmd(CmdMisiones, self.jugador, args="problema goblins")
        cmd.func()
        txt = self._todos_msgs()
        self.assertIn("Problema de los Goblins", txt)
        self.assertIn("Activa", txt)

    def test_detalle_nombre_inexistente(self):
        cmd = _make_cmd(CmdMisiones, self.jugador, args="misión inventada xyz")
        cmd.func()
        self.assertIn("No se encontró", self._todos_msgs())


# --------------------------------------------------------------------------- #
#  CmdAceptar
# --------------------------------------------------------------------------- #

class TestCmdAceptar(QuestTestBase):

    def test_sin_args_da_error(self):
        cmd = _make_cmd(CmdAceptar, self.jugador, args="")
        cmd.func()
        self.assertIn("Uso:", self._todos_msgs())

    def test_quest_inexistente_da_error(self):
        cmd = _make_cmd(CmdAceptar, self.jugador, args="misión inventada xyz")
        cmd.func()
        self.assertIn("No se encontró", self._todos_msgs())

    def test_npc_ausente_da_error(self):
        cmd = _make_cmd(CmdAceptar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("guardia", self._todos_msgs())

    def test_nivel_insuficiente_da_error(self):
        self.jugador.db.nivel = 1
        self._crear_npc("Gareth el mesonero")
        cmd = _make_cmd(CmdAceptar, self.jugador, args="garra del troll")
        cmd.func()
        self.assertIn("nivel", self._todos_msgs())

    def test_aceptar_ok_registra_quest(self):
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdAceptar, self.jugador, args="problema goblins")
        cmd.func()
        quests = self.jugador.db.quests
        self.assertIn("problema_goblins", quests)
        self.assertEqual(quests["problema_goblins"]["estado"], "activa")

    def test_aceptar_ok_muestra_oferta(self):
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdAceptar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("¡Misión aceptada!", self._todos_msgs())

    def test_ya_activa_da_error(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdAceptar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("curso", self._todos_msgs())
        # No debe duplicar
        self.assertEqual(self.jugador.db.quests["problema_goblins"]["estado"], "activa")

    def test_ya_entregada_da_error(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "entregada"}}
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdAceptar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("completaste", self._todos_msgs())


# --------------------------------------------------------------------------- #
#  CmdEntregar
# --------------------------------------------------------------------------- #

class TestCmdEntregar(QuestTestBase):

    def test_sin_args_da_error(self):
        cmd = _make_cmd(CmdEntregar, self.jugador, args="")
        cmd.func()
        self.assertIn("Uso:", self._todos_msgs())

    def test_quest_inexistente_da_error(self):
        cmd = _make_cmd(CmdEntregar, self.jugador, args="misión inventada xyz")
        cmd.func()
        self.assertIn("No se encontró", self._todos_msgs())

    def test_sin_mision_activa_da_error(self):
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("No tienes esta misión", self._todos_msgs())

    def test_quest_kill_activa_no_completada_da_error(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {"kills": 1}}}
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("completado", self._todos_msgs())

    def test_quest_kill_completada_ok_da_recompensa(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "completada", "progreso": {"kills": 3}}}
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="problema goblins")
        cmd.func()
        # Estado cambiado a entregada
        self.assertEqual(self.jugador.db.quests["problema_goblins"]["estado"], "entregada")
        # Recibió XP y monedas
        self.assertGreater(self.jugador.db.experiencia, 0)
        self.assertGreater(self.jugador.db.monedas, 0)

    def test_quest_kill_completada_npc_ausente_da_error(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "completada", "progreso": {"kills": 3}}}
        cmd = _make_cmd(CmdEntregar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("guardia", self._todos_msgs())
        # Estado no cambia
        self.assertEqual(self.jugador.db.quests["problema_goblins"]["estado"], "completada")

    def test_ya_entregada_da_error(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "entregada"}}
        self._crear_npc("guardia de la ciudad")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="problema goblins")
        cmd.func()
        self.assertIn("Ya entregaste", self._todos_msgs())

    def test_fetch_sin_items_da_error(self):
        self.jugador.db.quests = {"veneno_del_pantano": {"estado": "activa", "progreso": {}}}
        self._crear_npc("Mira la mercader")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veneno del pantano")
        cmd.func()
        self.assertIn("faltan", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["veneno_del_pantano"]["estado"], "activa")

    def test_fetch_con_items_ok_entrega_y_consume(self):
        self.jugador.db.quests = {"veneno_del_pantano": {"estado": "activa", "progreso": {}}}
        self._crear_npc("Mira la mercader")
        # Crear 2 items en el inventario del jugador
        for _ in range(2):
            create_object("evennia.objects.objects.DefaultObject",
                          key="veneno de pantano", location=self.jugador)
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veneno del pantano")
        cmd.func()
        # Estado entregada
        self.assertEqual(self.jugador.db.quests["veneno_del_pantano"]["estado"], "entregada")
        # Items consumidos
        items = [o for o in self.jugador.contents if o.key.lower() == "veneno de pantano"]
        self.assertEqual(len(items), 0)
        # XP otorgada
        self.assertGreater(self.jugador.db.experiencia, 0)

    def test_fetch_items_insuficientes_da_error(self):
        self.jugador.db.quests = {"veneno_del_pantano": {"estado": "activa", "progreso": {}}}
        self._crear_npc("Mira la mercader")
        create_object("evennia.objects.objects.DefaultObject",
                      key="veneno de pantano", location=self.jugador)
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veneno del pantano")
        cmd.func()
        self.assertIn("faltan", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["veneno_del_pantano"]["estado"], "activa")


# --------------------------------------------------------------------------- #
#  Hook on_npc_muerte
# --------------------------------------------------------------------------- #

class TestOnNpcMuerte(QuestTestBase):

    def _crear_npc_simple(self, key):
        return create_object("evennia.objects.objects.DefaultObject", key=key, location=self.sala)

    def test_sin_quests_no_falla(self):
        self.jugador.db.quests = {}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        # Sin excepción y sin mensajes de quest
        quest_msgs = [m for m in self.msgs if "Misión" in m]
        self.assertEqual(quest_msgs, [])

    def test_kill_quest_activa_incrementa_kills(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        quests = self.jugador.db.quests
        kills = quests["problema_goblins"]["progreso"].get("kills", 0)
        self.assertEqual(kills, 1)

    def test_kill_quest_activa_notifica_progreso(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        txt = self._todos_msgs()
        self.assertIn("1/3", txt)

    def test_kill_quest_target_no_coincide_no_incrementa(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {}}}
        npc = self._crear_npc_simple("liche menor")
        on_npc_muerte(self.jugador, npc)
        quests = self.jugador.db.quests
        kills = quests["problema_goblins"]["progreso"].get("kills", 0)
        self.assertEqual(kills, 0)

    def test_kill_quest_completa_al_llegar_objetivo(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {"kills": 2}}}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["problema_goblins"]["estado"], "completada")

    def test_kill_quest_completa_notifica_completion(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "activa", "progreso": {"kills": 2}}}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        self.assertIn("completada", self._todos_msgs().lower())

    def test_quest_no_activa_no_se_modifica(self):
        self.jugador.db.quests = {"problema_goblins": {"estado": "completada", "progreso": {"kills": 3}}}
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["problema_goblins"]["progreso"]["kills"], 3)

    def test_asesino_sin_cuenta_ignorado(self):
        from unittest.mock import MagicMock
        asesino = MagicMock()
        asesino.has_account = False
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(asesino, npc)
        asesino.msg.assert_not_called()

    def test_multiples_kill_quests_independientes(self):
        self.jugador.db.quests = {
            "problema_goblins": {"estado": "activa", "progreso": {}},
            "amenaza_catacumbas": {"estado": "activa", "progreso": {}},
        }
        npc = self._crear_npc_simple("goblin")
        on_npc_muerte(self.jugador, npc)
        quests = self.jugador.db.quests
        self.assertEqual(quests["problema_goblins"]["progreso"]["kills"], 1)
        # liche menor no coincide con "goblin"
        self.assertEqual(quests["amenaza_catacumbas"]["progreso"].get("kills", 0), 0)
