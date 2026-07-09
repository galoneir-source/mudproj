"""
tests/test_spawn.py

Tests de integración para features/spawn/manager.py, features/spawn/commands.py
y features/respawn/respawn.py.
Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test .
"""
import time

from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.spawn.manager import (
    spawn_npc,
    _contar_npcs_por_prototipo,
    repoblar_sala,
)
from features.spawn.commands import CmdSpawn, CmdRepoblar
from features.respawn.respawn import RespawnScript, programar_respawn
from systems.spawn.tables import ZONAS


def _make_cmd(CmdClass, caller, args="", switches=None):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = switches or []
    cmd.lhs = args
    cmd.rhs = ""
    return cmd


class SpawnTestBase(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.builder = self.char1
        self.builder.move_to(self.sala, quiet=True)
        self.msgs = []
        self.builder.msg = lambda text=None, **kw: self.msgs.append(str(text))
        self.sala.msg_contents = lambda m, **kw: None

    def _ultimo_msg(self):
        return self.msgs[-1] if self.msgs else ""

    def _todos_msgs(self):
        return "\n".join(self.msgs)

    def _npcs_en_sala(self):
        return [o for o in self.sala.contents
                if getattr(o.db, "npc_prototipo", None)]


# --------------------------------------------------------------------------- #
#  spawn_npc
# --------------------------------------------------------------------------- #

class TestSpawnNpc(SpawnTestBase):

    def test_crea_npc_en_sala(self):
        npc = spawn_npc("GOBLIN", self.sala)
        self.assertIsNotNone(npc)
        self.assertIn(npc, self.sala.contents)

    def test_npc_tiene_prototipo_correcto(self):
        npc = spawn_npc("GOBLIN", self.sala)
        self.assertEqual(npc.db.npc_prototipo, "GOBLIN")

    def test_npc_tiene_stats(self):
        npc = spawn_npc("GOBLIN", self.sala)
        self.assertIsNotNone(npc.db.hp)
        self.assertGreater(npc.db.hp, 0)

    def test_npc_key_override(self):
        npc = spawn_npc("GOBLIN", self.sala, key_npc="goblin espía")
        self.assertEqual(npc.key, "goblin espía")

    def test_npc_oculto(self):
        npc = spawn_npc("GOBLIN", self.sala, oculto=True, nivel_sigilo=13)
        self.assertTrue(npc.db.oculto)
        self.assertEqual(npc.db.nivel_sigilo, 13)

    def test_prototipo_inexistente_devuelve_none(self):
        npc = spawn_npc("PROTOTIPO_QUE_NO_EXISTE_XYZ", self.sala)
        self.assertIsNone(npc)

    def test_varios_tipos_de_npc(self):
        for proto in ("GOBLIN", "BANDIDO", "SERPIENTE_PANTANO"):
            npc = spawn_npc(proto, self.sala)
            self.assertIsNotNone(npc, f"Fallo al crear {proto}")
            npc.delete()


# --------------------------------------------------------------------------- #
#  _contar_npcs_por_prototipo
# --------------------------------------------------------------------------- #

class TestContarNpcs(SpawnTestBase):

    def test_sala_vacia(self):
        conteo = _contar_npcs_por_prototipo(self.sala)
        self.assertEqual(conteo.get("GOBLIN", 0), 0)

    def test_un_npc(self):
        spawn_npc("GOBLIN", self.sala)
        conteo = _contar_npcs_por_prototipo(self.sala)
        self.assertEqual(conteo["GOBLIN"], 1)

    def test_dos_npcs_mismo_prototipo(self):
        spawn_npc("GOBLIN", self.sala)
        spawn_npc("GOBLIN", self.sala)
        conteo = _contar_npcs_por_prototipo(self.sala)
        self.assertEqual(conteo["GOBLIN"], 2)

    def test_distintos_prototipos(self):
        spawn_npc("GOBLIN", self.sala)
        spawn_npc("BANDIDO", self.sala)
        conteo = _contar_npcs_por_prototipo(self.sala)
        self.assertEqual(conteo["GOBLIN"], 1)
        self.assertEqual(conteo["BANDIDO"], 1)

    def test_jugador_no_cuenta(self):
        conteo = _contar_npcs_por_prototipo(self.sala)
        self.assertNotIn("CHARACTER", conteo)


# --------------------------------------------------------------------------- #
#  repoblar_sala
# --------------------------------------------------------------------------- #

class TestRepoblarSala(SpawnTestBase):

    def test_sala_sin_zona_devuelve_vacio(self):
        self.sala.db.zona = None
        resultado = repoblar_sala(self.sala)
        self.assertEqual(resultado, [])

    def test_sala_zona_inexistente_devuelve_vacio(self):
        self.sala.db.zona = "zona_inventada_xyz"
        resultado = repoblar_sala(self.sala)
        self.assertEqual(resultado, [])

    def test_repobla_sala_vacia(self):
        self.sala.db.zona = "guarida_troll"
        creados = repoblar_sala(self.sala)
        self.assertEqual(len(creados), 1)
        self.assertEqual(creados[0].db.npc_prototipo, "TROLL")

    def test_sala_ya_poblada_no_duplica(self):
        self.sala.db.zona = "guardia_troll"
        spawn_npc("TROLL", self.sala)
        self.sala.db.zona = "guarida_troll"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repobla_parcialmente(self):
        self.sala.db.zona = "sala_tumbas"
        spawn_npc("ESQUELETO", self.sala)    # 1 de 2
        creados = repoblar_sala(self.sala)
        self.assertEqual(len(creados), 1)   # solo falta 1 más

    def test_repobla_dos_tipos(self):
        self.sala.db.zona = "pantano_cenagoso"
        creados = repoblar_sala(self.sala)
        self.assertEqual(len(creados), 2)
        protos = {npc.db.npc_prototipo for npc in creados}
        self.assertIn("SERPIENTE_PANTANO", protos)
        self.assertIn("HOMBRE_LAGARTO", protos)

    def test_todos_las_zonas_repoblables(self):
        for zona_id in ZONAS:
            self.sala.db.zona = zona_id
            # Limpiar NPCs previos
            for obj in list(self.sala.contents):
                if getattr(obj.db, "npc_prototipo", None):
                    obj.delete()
            creados = repoblar_sala(self.sala)
            esperados = sum(e["cantidad"] for e in ZONAS[zona_id])
            self.assertEqual(
                len(creados), esperados,
                f"Zona '{zona_id}': esperados {esperados}, creados {len(creados)}"
            )


# --------------------------------------------------------------------------- #
#  CmdSpawn
# --------------------------------------------------------------------------- #

class TestCmdSpawn(SpawnTestBase):

    def test_sin_args_da_error(self):
        cmd = _make_cmd(CmdSpawn, self.builder, args="")
        cmd.func()
        self.assertIn("Uso:", self._todos_msgs())

    def test_spawn_goblin(self):
        npcs_antes = len(self._npcs_en_sala())
        cmd = _make_cmd(CmdSpawn, self.builder, args="GOBLIN")
        cmd.func()
        self.assertEqual(len(self._npcs_en_sala()), npcs_antes + 1)

    def test_spawn_con_cantidad(self):
        npcs_antes = len(self._npcs_en_sala())
        cmd = _make_cmd(CmdSpawn, self.builder, args="GOBLIN 3")
        cmd.func()
        self.assertEqual(len(self._npcs_en_sala()), npcs_antes + 3)

    def test_spawn_prototipo_invalido(self):
        cmd = _make_cmd(CmdSpawn, self.builder, args="PROTOTIPO_INVALIDO_XYZ")
        cmd.func()
        self.assertIn("No se pudo", self._todos_msgs())

    def test_spawn_cantidad_invalida(self):
        cmd = _make_cmd(CmdSpawn, self.builder, args="GOBLIN abc")
        cmd.func()
        self.assertIn("inválida", self._todos_msgs())

    def test_spawn_cantidad_excesiva(self):
        cmd = _make_cmd(CmdSpawn, self.builder, args="GOBLIN 99")
        cmd.func()
        self.assertIn("entre 1 y 20", self._todos_msgs())

    def test_spawn_confirma_creacion(self):
        cmd = _make_cmd(CmdSpawn, self.builder, args="GOBLIN")
        cmd.func()
        self.assertIn("creados", self._todos_msgs())


# --------------------------------------------------------------------------- #
#  CmdRepoblar
# --------------------------------------------------------------------------- #

class TestCmdRepoblar(SpawnTestBase):

    def test_sala_sin_zona_informa(self):
        self.sala.db.zona = None
        cmd = _make_cmd(CmdRepoblar, self.builder)
        cmd.func()
        self.assertIn("no tiene zona", self._todos_msgs())

    def test_sala_con_zona_repuebla(self):
        self.sala.db.zona = "guarida_troll"
        cmd = _make_cmd(CmdRepoblar, self.builder)
        cmd.func()
        npcs = self._npcs_en_sala()
        self.assertEqual(len(npcs), 1)
        self.assertIn("creados", self._todos_msgs())

    def test_sala_ya_poblada_informa(self):
        self.sala.db.zona = "guarida_troll"
        spawn_npc("TROLL", self.sala)
        cmd = _make_cmd(CmdRepoblar, self.builder)
        cmd.func()
        self.assertIn("correctamente poblada", self._todos_msgs())


# --------------------------------------------------------------------------- #
#  RespawnScript
# --------------------------------------------------------------------------- #

class TestRespawnScript(SpawnTestBase):

    def test_programar_respawn_crea_script(self):
        npc = spawn_npc("GOBLIN", self.sala)
        programar_respawn(self.sala, npc)
        scripts = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        self.assertGreater(len(scripts), 0)

    def test_npc_sin_prototipo_no_programa_respawn(self):
        npc = create_object("typeclasses.npc.NPC", key="npc huerfano", location=self.sala)
        npc.db.npc_prototipo = None
        programar_respawn(self.sala, npc)
        scripts = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        self.assertEqual(len(scripts), 0)

    def test_respawn_inmediato(self):
        npc = spawn_npc("GOBLIN", self.sala)
        programar_respawn(self.sala, npc)
        npc.delete()

        # Forzar respawn con timestamp en el pasado
        scripts = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        self.assertEqual(len(scripts), 1)
        script = scripts[0]
        script.db.respawn_at = time.time() - 1
        script.at_repeat()

        # NPC reaparecido
        nuevos = [o for o in self.sala.contents
                  if getattr(o.db, "npc_prototipo", None) == "GOBLIN"]
        self.assertEqual(len(nuevos), 1)

    def test_respawn_no_dispara_antes_de_tiempo(self):
        npc = spawn_npc("GOBLIN", self.sala)
        programar_respawn(self.sala, npc)
        npc.delete()

        scripts = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        script = scripts[0]
        script.db.respawn_at = time.time() + 9999   # muy en el futuro
        script.at_repeat()

        nuevos = [o for o in self.sala.contents
                  if getattr(o.db, "npc_prototipo", None) == "GOBLIN"]
        self.assertEqual(len(nuevos), 0)

    def test_respawn_elimina_script_tras_ejecutarse(self):
        npc = spawn_npc("GOBLIN", self.sala)
        programar_respawn(self.sala, npc)
        npc.delete()

        scripts = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        script = scripts[0]
        script.db.respawn_at = time.time() - 1
        script.at_repeat()

        scripts_post = [s for s in self.sala.scripts.all() if s.key == "respawn_script"]
        self.assertEqual(len(scripts_post), 0)
