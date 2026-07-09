"""
tests/test_torre.py

Tests de integración para la zona Torre del Mago Caído (v0.15.0).
Cubre: spawn de NPCs, repoblación de zonas, quests y crafteo con
ingredientes de la torre.

Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_torre
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.spawn.manager import spawn_npc, repoblar_sala
from features.quests.commands import CmdAceptar, CmdEntregar
from features.quests.hooks import on_npc_muerte
from features.crafting.commands import CmdCraftear
from typeclasses.objects import Object, Consumible


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


def _item(nombre, location):
    return create_object(Object, key=nombre, location=location)


class TorreTestBase(EvenniaTest):
    """Configuración base compartida para todos los tests de la torre."""

    def setUp(self):
        super().setUp()
        self.sala = self.room1
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        self.jugador.db.quests = {}
        self.jugador.db.nivel = 10
        self.jugador.db.monedas = 0
        self.jugador.db.experiencia = 0
        self.jugador.db.reputacion = {}
        self.msgs = []
        self.jugador.msg = lambda text=None, **kw: self.msgs.append(str(text))
        self.sala.msg_contents = lambda m, **kw: None

    def _todos_msgs(self):
        return "\n".join(self.msgs)

    def _crear_npc(self, key):
        return create_object("typeclasses.npc.NPC", key=key, location=self.sala)

    def _crear_objeto(self, key):
        return create_object("evennia.objects.objects.DefaultObject",
                             key=key, location=self.jugador)

    def _limpiar_npcs(self):
        for obj in list(self.sala.contents):
            if getattr(obj.db, "npc_prototipo", None):
                obj.delete()


# --------------------------------------------------------------------------- #
#  Spawn de NPCs nuevos
# --------------------------------------------------------------------------- #

class TestSpawnNpcsTorre(TorreTestBase):

    def test_spawn_aprendiz_corrupto(self):
        npc = spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.assertIsNotNone(npc)
        self.assertIn(npc, self.sala.contents)
        self.assertEqual(npc.db.npc_prototipo, "APRENDIZ_CORRUPTO")

    def test_spawn_aprendiz_nivel(self):
        npc = spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.assertEqual(npc.db.nivel, 5)

    def test_spawn_aprendiz_faccion(self):
        npc = spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.assertEqual(npc.db.faccion, "legion_oscura")

    def test_spawn_aprendiz_inteligencia_alta(self):
        npc = spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.assertGreaterEqual(npc.db.inteligencia, 16)

    def test_spawn_guardian_arcano(self):
        npc = spawn_npc("GUARDIAN_ARCANO", self.sala)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.db.npc_prototipo, "GUARDIAN_ARCANO")

    def test_spawn_guardian_nivel(self):
        npc = spawn_npc("GUARDIAN_ARCANO", self.sala)
        self.assertEqual(npc.db.nivel, 6)

    def test_spawn_guardian_defensa_alta(self):
        npc = spawn_npc("GUARDIAN_ARCANO", self.sala)
        self.assertGreaterEqual(npc.db.defensa, 13)

    def test_spawn_guardian_faccion(self):
        npc = spawn_npc("GUARDIAN_ARCANO", self.sala)
        self.assertEqual(npc.db.faccion, "legion_oscura")

    def test_spawn_archimago_vexthar(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.db.npc_prototipo, "ARCHIMAGO_VEXTHAR")

    def test_spawn_archimago_nivel(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertEqual(npc.db.nivel, 9)

    def test_spawn_archimago_inteligencia_maxima(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertGreaterEqual(npc.db.inteligencia, 24)

    def test_spawn_archimago_hp_alto(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertGreaterEqual(npc.db.hp, 260)

    def test_spawn_archimago_tiene_dialogo(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertIsNotNone(npc.db.dialogo)
        self.assertIn("poder", npc.db.dialogo)

    def test_spawn_archimago_faccion(self):
        npc = spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.assertEqual(npc.db.faccion, "legion_oscura")


# --------------------------------------------------------------------------- #
#  Repoblación de zonas de la torre
# --------------------------------------------------------------------------- #

class TestRepoblarZonasTorre(TorreTestBase):

    def _repoblar(self, zona_id):
        self._limpiar_npcs()
        self.sala.db.zona = zona_id
        return repoblar_sala(self.sala)

    def test_repoblar_base_torre_crea_guardian(self):
        creados = self._repoblar("base_torre")
        self.assertEqual(len(creados), 1)
        self.assertEqual(creados[0].db.npc_prototipo, "GUARDIAN_ARCANO")

    def test_repoblar_base_torre_no_duplica(self):
        spawn_npc("GUARDIAN_ARCANO", self.sala)
        self.sala.db.zona = "base_torre"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repoblar_biblioteca_crea_dos_aprendices(self):
        creados = self._repoblar("biblioteca_archimago")
        self.assertEqual(len(creados), 2)
        protos = {npc.db.npc_prototipo for npc in creados}
        self.assertEqual(protos, {"APRENDIZ_CORRUPTO"})

    def test_repoblar_biblioteca_no_duplica(self):
        spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.sala.db.zona = "biblioteca_archimago"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repoblar_biblioteca_parcial(self):
        spawn_npc("APRENDIZ_CORRUPTO", self.sala)
        self.sala.db.zona = "biblioteca_archimago"
        creados = repoblar_sala(self.sala)
        self.assertEqual(len(creados), 1)

    def test_repoblar_camara_crea_archimago(self):
        creados = self._repoblar("camara_ritual")
        self.assertEqual(len(creados), 1)
        self.assertEqual(creados[0].db.npc_prototipo, "ARCHIMAGO_VEXTHAR")

    def test_repoblar_camara_no_duplica(self):
        spawn_npc("ARCHIMAGO_VEXTHAR", self.sala)
        self.sala.db.zona = "camara_ritual"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])


# --------------------------------------------------------------------------- #
#  Quest: Los Aprendices de la Torre (kill)
# --------------------------------------------------------------------------- #

class TestQuestAprendicesTorre(TorreTestBase):

    def _aldric(self):
        return self._crear_npc("Hermano Aldric el sacerdote")

    def _npc_simple(self, key):
        return create_object("evennia.objects.objects.DefaultObject",
                             key=key, location=self.sala)

    def test_aceptar_aprendices_sin_aldric_da_error(self):
        cmd = _make_cmd(CmdAceptar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertIn("Aldric", self._todos_msgs())

    def test_aceptar_aprendices_con_aldric_registra_quest(self):
        self._aldric()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertIn("aprendices_torre", self.jugador.db.quests)
        self.assertEqual(self.jugador.db.quests["aprendices_torre"]["estado"], "activa")

    def test_aceptar_aprendices_nivel_insuficiente(self):
        self.jugador.db.nivel = 3
        self._aldric()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertIn("nivel", self._todos_msgs())
        self.assertNotIn("aprendices_torre", self.jugador.db.quests)

    def test_on_npc_muerte_aprendiz_registra_kill(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("aprendiz corrompido")
        on_npc_muerte(self.jugador, npc)
        from systems.quests.quests import kills_actuales
        self.assertEqual(kills_actuales("aprendices_torre", self.jugador.db.quests), 1)

    def test_on_npc_muerte_tres_aprendices_completa(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "activa", "progreso": {}}}
        for _ in range(3):
            npc = self._npc_simple("aprendiz corrompido")
            on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["aprendices_torre"]["estado"], "completada")

    def test_on_npc_muerte_guardian_no_registra_en_aprendices(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("guardián arcano")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["aprendices_torre"]["estado"], "activa")

    def test_entregar_aprendices_completada_cambia_estado(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "completada", "progreso": {"kills": 3}}}
        self._aldric()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertEqual(self.jugador.db.quests["aprendices_torre"]["estado"], "entregada")

    def test_entregar_aprendices_otorga_xp(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "completada", "progreso": {"kills": 3}}}
        self._aldric()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertGreater(self.jugador.db.experiencia, 0)

    def test_entregar_aprendices_otorga_monedas(self):
        self.jugador.db.quests = {"aprendices_torre": {"estado": "completada", "progreso": {"kills": 3}}}
        self._aldric()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="aprendices de la torre")
        cmd.func()
        self.assertGreater(self.jugador.db.monedas, 0)


# --------------------------------------------------------------------------- #
#  Quest: El Archimago Caído (kill, con recompensa de ítem)
# --------------------------------------------------------------------------- #

class TestQuestArchimagoCaido(TorreTestBase):

    def _mira(self):
        return self._crear_npc("Mira la mercader")

    def _npc_simple(self, key):
        return create_object("evennia.objects.objects.DefaultObject",
                             key=key, location=self.sala)

    def test_aceptar_archimago_con_mira_registra_quest(self):
        self._mira()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertIn("archimago_caido", self.jugador.db.quests)
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "activa")

    def test_aceptar_archimago_nivel_insuficiente(self):
        self.jugador.db.nivel = 6
        self._mira()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertIn("nivel", self._todos_msgs())
        self.assertNotIn("archimago_caido", self.jugador.db.quests)

    def test_on_npc_muerte_archimago_completa_quest(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("archimago Vexthar")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "completada")

    def test_on_npc_muerte_aprendiz_no_completa_archimago(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("aprendiz corrompido")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "activa")

    def test_entregar_archimago_da_manto_arcano(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "completada", "progreso": {"kills": 1}}}
        self._mira()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="archimago caído")
        cmd.func()
        mantos = [o for o in self.jugador.contents if "manto" in o.key.lower()]
        self.assertEqual(len(mantos), 1)

    def test_entregar_archimago_otorga_xp_y_monedas(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "completada", "progreso": {"kills": 1}}}
        self._mira()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertGreater(self.jugador.db.experiencia, 0)
        self.assertGreater(self.jugador.db.monedas, 0)

    def test_entregar_archimago_estado_entregada(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "completada", "progreso": {"kills": 1}}}
        self._mira()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "entregada")

    def test_entregar_archimago_sin_mira_no_entrega(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "completada", "progreso": {"kills": 1}}}
        cmd = _make_cmd(CmdEntregar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertIn("Mira", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "completada")

    def test_entregar_archimago_activa_no_entrega(self):
        self.jugador.db.quests = {"archimago_caido": {"estado": "activa", "progreso": {"kills": 0}}}
        self._mira()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="archimago caído")
        cmd.func()
        self.assertIn("completado", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["archimago_caido"]["estado"], "activa")


# --------------------------------------------------------------------------- #
#  Crafteo con ingredientes de la torre
# --------------------------------------------------------------------------- #

class TestCrafteoTorre(TorreTestBase):

    def _craftear(self, args):
        _make_cmd(CmdCraftear, self.jugador, args).func()

    def test_esencia_ceniza_sin_ingredientes_no_craftea(self):
        antes = len(self.jugador.contents)
        self._craftear("esencia de ceniza")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_esencia_ceniza_con_una_ceniza_insuficiente(self):
        _item("cenizas arcanas", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("esencia de ceniza")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_esencia_ceniza_con_dos_cenizas_crea_pocion(self):
        _item("cenizas arcanas", self.jugador)
        _item("cenizas arcanas", self.jugador)
        self._craftear("esencia de ceniza")
        pociones = [o for o in self.jugador.contents
                    if isinstance(o, Consumible) and "vida mayor" in o.key]
        self.assertEqual(len(pociones), 1)

    def test_esencia_ceniza_consume_cenizas(self):
        _item("cenizas arcanas", self.jugador)
        _item("cenizas arcanas", self.jugador)
        self._craftear("esencia de ceniza")
        cenizas = [o for o in self.jugador.contents if o.key == "cenizas arcanas"]
        self.assertEqual(len(cenizas), 0)

    def test_esencia_ceniza_busqueda_por_prefijo(self):
        _item("cenizas arcanas", self.jugador)
        _item("cenizas arcanas", self.jugador)
        self._craftear("esencia")
        pociones = [o for o in self.jugador.contents if isinstance(o, Consumible)]
        self.assertEqual(len(pociones), 1)

    def test_elixir_arcano_sin_fragmento_no_craftea(self):
        _item("cenizas arcanas", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("elixir arcano")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_elixir_arcano_sin_cenizas_no_craftea(self):
        _item("fragmento arcano", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("elixir arcano")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_elixir_arcano_con_ingredientes_crea_elixir(self):
        _item("cenizas arcanas", self.jugador)
        _item("fragmento arcano", self.jugador)
        self._craftear("elixir arcano")
        elixires = [o for o in self.jugador.contents
                    if isinstance(o, Consumible) and "restauración" in o.key]
        self.assertEqual(len(elixires), 1)

    def test_elixir_arcano_consume_ambos_ingredientes(self):
        _item("cenizas arcanas", self.jugador)
        _item("fragmento arcano", self.jugador)
        self._craftear("elixir arcano")
        cenizas = [o for o in self.jugador.contents if o.key == "cenizas arcanas"]
        fragmentos = [o for o in self.jugador.contents if o.key == "fragmento arcano"]
        self.assertEqual(len(cenizas), 0)
        self.assertEqual(len(fragmentos), 0)
