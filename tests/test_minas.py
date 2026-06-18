"""
tests/test_minas.py

Tests de integración para la zona Minas de Hierro Viejo (v0.14.0).
Cubre: spawn de NPCs, repoblación de zonas, quests de Torben y crafteo
con ingredientes de la mina.

Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_minas
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


class MinasTestBase(EvenniaTest):
    """Configuración base compartida para todos los tests de las minas."""

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
        self.jugador.msg = lambda m, **kw: self.msgs.append(str(m))
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

class TestSpawnNpcsMinas(MinasTestBase):

    def test_spawn_arana_cueva(self):
        npc = spawn_npc("ARANA_CUEVA", self.sala)
        self.assertIsNotNone(npc)
        self.assertIn(npc, self.sala.contents)
        self.assertEqual(npc.db.npc_prototipo, "ARANA_CUEVA")

    def test_spawn_arana_cueva_nivel(self):
        npc = spawn_npc("ARANA_CUEVA", self.sala)
        self.assertEqual(npc.db.nivel, 3)

    def test_spawn_arana_cueva_faccion(self):
        npc = spawn_npc("ARANA_CUEVA", self.sala)
        self.assertEqual(npc.db.faccion, "horda_salvaje")

    def test_spawn_minero_maldito(self):
        npc = spawn_npc("MINERO_MALDITO", self.sala)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.db.npc_prototipo, "MINERO_MALDITO")

    def test_spawn_minero_maldito_nivel(self):
        npc = spawn_npc("MINERO_MALDITO", self.sala)
        self.assertEqual(npc.db.nivel, 4)

    def test_spawn_minero_maldito_faccion(self):
        npc = spawn_npc("MINERO_MALDITO", self.sala)
        self.assertEqual(npc.db.faccion, "legion_oscura")

    def test_spawn_golem_piedra(self):
        npc = spawn_npc("GOLEM_PIEDRA", self.sala)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.db.npc_prototipo, "GOLEM_PIEDRA")

    def test_spawn_golem_piedra_nivel(self):
        npc = spawn_npc("GOLEM_PIEDRA", self.sala)
        self.assertEqual(npc.db.nivel, 7)

    def test_spawn_golem_piedra_stats(self):
        npc = spawn_npc("GOLEM_PIEDRA", self.sala)
        self.assertGreaterEqual(npc.db.hp, 200)
        self.assertGreaterEqual(npc.db.defensa, 16)

    def test_spawn_buscador_tesoros(self):
        npc = spawn_npc("BUSCADOR_TESOROS", self.sala)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.db.npc_prototipo, "BUSCADOR_TESOROS")

    def test_spawn_buscador_tesoros_faccion(self):
        npc = spawn_npc("BUSCADOR_TESOROS", self.sala)
        self.assertEqual(npc.db.faccion, "gremio_aventureros")

    def test_spawn_buscador_tesoros_tiene_tienda(self):
        npc = spawn_npc("BUSCADOR_TESOROS", self.sala)
        self.assertIsNotNone(npc.db.tienda)
        self.assertGreater(len(npc.db.tienda), 0)

    def test_spawn_buscador_tesoros_tiene_dialogo(self):
        npc = spawn_npc("BUSCADOR_TESOROS", self.sala)
        self.assertIsNotNone(npc.db.dialogo)
        self.assertIn("minas", npc.db.dialogo)


# --------------------------------------------------------------------------- #
#  Repoblación de zonas de la mina
# --------------------------------------------------------------------------- #

class TestRepoblarZonasMinas(MinasTestBase):

    def _repoblar(self, zona_id):
        self._limpiar_npcs()
        self.sala.db.zona = zona_id
        return repoblar_sala(self.sala)

    def test_repoblar_boca_mina_crea_dos_aranas(self):
        creados = self._repoblar("boca_mina")
        self.assertEqual(len(creados), 2)
        protos = {npc.db.npc_prototipo for npc in creados}
        self.assertEqual(protos, {"ARANA_CUEVA"})

    def test_repoblar_boca_mina_no_duplica(self):
        spawn_npc("ARANA_CUEVA", self.sala)
        spawn_npc("ARANA_CUEVA", self.sala)
        self.sala.db.zona = "boca_mina"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repoblar_boca_mina_parcial(self):
        spawn_npc("ARANA_CUEVA", self.sala)
        self.sala.db.zona = "boca_mina"
        creados = repoblar_sala(self.sala)
        self.assertEqual(len(creados), 1)

    def test_repoblar_galeria_principal_crea_dos_mineros(self):
        creados = self._repoblar("galeria_principal")
        self.assertEqual(len(creados), 2)
        protos = {npc.db.npc_prototipo for npc in creados}
        self.assertEqual(protos, {"MINERO_MALDITO"})

    def test_repoblar_galeria_no_duplica(self):
        spawn_npc("MINERO_MALDITO", self.sala)
        spawn_npc("MINERO_MALDITO", self.sala)
        self.sala.db.zona = "galeria_principal"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repoblar_caverna_coloso_crea_golem(self):
        creados = self._repoblar("caverna_coloso")
        self.assertEqual(len(creados), 1)
        self.assertEqual(creados[0].db.npc_prototipo, "GOLEM_PIEDRA")

    def test_repoblar_caverna_no_duplica(self):
        spawn_npc("GOLEM_PIEDRA", self.sala)
        self.sala.db.zona = "caverna_coloso"
        creados = repoblar_sala(self.sala)
        self.assertEqual(creados, [])

    def test_repoblar_mercado_incluye_buscador(self):
        creados = self._repoblar("mercado")
        protos = {npc.db.npc_prototipo for npc in creados}
        self.assertIn("BUSCADOR_TESOROS", protos)
        self.assertIn("MERCADER", protos)


# --------------------------------------------------------------------------- #
#  Quest: La Veta Perdida (fetch)
# --------------------------------------------------------------------------- #

class TestQuestVetaPerdida(MinasTestBase):

    def _torben(self):
        return self._crear_npc("Torben el buscador de tesoros")

    def test_aceptar_veta_sin_torben_da_error(self):
        cmd = _make_cmd(CmdAceptar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("Torben", self._todos_msgs())

    def test_aceptar_veta_con_torben_registra_quest(self):
        self._torben()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("veta_perdida", self.jugador.db.quests)
        self.assertEqual(self.jugador.db.quests["veta_perdida"]["estado"], "activa")

    def test_aceptar_veta_nivel_insuficiente(self):
        self.jugador.db.nivel = 2
        self._torben()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("nivel", self._todos_msgs())
        self.assertNotIn("veta_perdida", self.jugador.db.quests)

    def test_entregar_veta_sin_minerales_da_error(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("faltan", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["veta_perdida"]["estado"], "activa")

    def test_entregar_veta_con_un_mineral_insuficiente(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("faltan", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["veta_perdida"]["estado"], "activa")

    def test_entregar_veta_con_dos_minerales_entrega_quest(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        self._crear_objeto("mineral de hierro")
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertEqual(self.jugador.db.quests["veta_perdida"]["estado"], "entregada")

    def test_entregar_veta_otorga_xp(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        self._crear_objeto("mineral de hierro")
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertGreater(self.jugador.db.experiencia, 0)

    def test_entregar_veta_otorga_monedas(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        self._crear_objeto("mineral de hierro")
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertGreater(self.jugador.db.monedas, 0)

    def test_entregar_veta_consume_minerales(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._torben()
        self._crear_objeto("mineral de hierro")
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        minerales = [o for o in self.jugador.contents if o.key.lower() == "mineral de hierro"]
        self.assertEqual(len(minerales), 0)

    def test_entregar_veta_sin_torben_da_error(self):
        self.jugador.db.quests = {"veta_perdida": {"estado": "activa", "progreso": {}}}
        self._crear_objeto("mineral de hierro")
        self._crear_objeto("mineral de hierro")
        cmd = _make_cmd(CmdEntregar, self.jugador, args="veta perdida")
        cmd.func()
        self.assertIn("Torben", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["veta_perdida"]["estado"], "activa")


# --------------------------------------------------------------------------- #
#  Quest: El Coloso Despertado (kill)
# --------------------------------------------------------------------------- #

class TestQuestColosoDespertado(MinasTestBase):

    def _torben(self):
        return self._crear_npc("Torben el buscador de tesoros")

    def _npc_simple(self, key):
        return create_object("evennia.objects.objects.DefaultObject",
                             key=key, location=self.sala)

    def test_aceptar_coloso_con_torben_registra_quest(self):
        self._torben()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertIn("coloso_despertado", self.jugador.db.quests)
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "activa")

    def test_aceptar_coloso_nivel_insuficiente(self):
        self.jugador.db.nivel = 5
        self._torben()
        cmd = _make_cmd(CmdAceptar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertIn("nivel", self._todos_msgs())
        self.assertNotIn("coloso_despertado", self.jugador.db.quests)

    def test_on_npc_muerte_golem_registra_kill(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("gólem de piedra")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "completada")

    def test_on_npc_muerte_golem_notifica_completada(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("gólem de piedra")
        on_npc_muerte(self.jugador, npc)
        self.assertIn("completada", self._todos_msgs().lower())

    def test_on_npc_muerte_otro_npc_no_registra(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "activa", "progreso": {}}}
        npc = self._npc_simple("araña de cueva")
        on_npc_muerte(self.jugador, npc)
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "activa")

    def test_entregar_coloso_activa_no_completada(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "activa", "progreso": {"kills": 0}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertIn("completado", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "activa")

    def test_entregar_coloso_completada_cambia_estado(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "completada", "progreso": {"kills": 1}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "entregada")

    def test_entregar_coloso_otorga_xp_y_monedas(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "completada", "progreso": {"kills": 1}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertGreater(self.jugador.db.experiencia, 0)
        self.assertGreater(self.jugador.db.monedas, 0)

    def test_entregar_coloso_da_anillo_constitucion(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "completada", "progreso": {"kills": 1}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        anillos = [o for o in self.jugador.contents if "constitución" in o.key.lower()]
        self.assertEqual(len(anillos), 1)

    def test_entregar_coloso_mensaje_anillo(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "completada", "progreso": {"kills": 1}}}
        self._torben()
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertIn("anillo", self._todos_msgs().lower())

    def test_entregar_coloso_sin_torben_no_entrega(self):
        self.jugador.db.quests = {"coloso_despertado": {"estado": "completada", "progreso": {"kills": 1}}}
        cmd = _make_cmd(CmdEntregar, self.jugador, args="coloso despertado")
        cmd.func()
        self.assertIn("Torben", self._todos_msgs())
        self.assertEqual(self.jugador.db.quests["coloso_despertado"]["estado"], "completada")


# --------------------------------------------------------------------------- #
#  Crafteo con ingredientes de la mina
# --------------------------------------------------------------------------- #

class TestCrafteoMinas(MinasTestBase):

    def _craftear(self, args):
        _make_cmd(CmdCraftear, self.jugador, args).func()

    def test_antidoto_arana_sin_ingredientes_no_craftea(self):
        antes = len(self.jugador.contents)
        self._craftear("antídoto de araña")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_antidoto_arana_con_un_hilo_insuficiente(self):
        _item("hilo de araña", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("antídoto de araña")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_antidoto_arana_con_dos_hilos_crea_dos_antidotos(self):
        _item("hilo de araña", self.jugador)
        _item("hilo de araña", self.jugador)
        self._craftear("antídoto de araña")
        antidotos = [o for o in self.jugador.contents
                     if isinstance(o, Consumible) and o.key == "antídoto"]
        self.assertEqual(len(antidotos), 2)

    def test_antidoto_arana_consume_hilos(self):
        _item("hilo de araña", self.jugador)
        _item("hilo de araña", self.jugador)
        self._craftear("antídoto de araña")
        hilos = [o for o in self.jugador.contents if o.key == "hilo de araña"]
        self.assertEqual(len(hilos), 0)

    def test_antidoto_arana_busqueda_por_prefijo(self):
        _item("hilo de araña", self.jugador)
        _item("hilo de araña", self.jugador)
        self._craftear("antídoto de a")
        antidotos = [o for o in self.jugador.contents if isinstance(o, Consumible)]
        self.assertEqual(len(antidotos), 2)

    def test_tonico_piedra_sin_ingredientes_no_craftea(self):
        antes = len(self.jugador.contents)
        self._craftear("tónico de piedra")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_tonico_piedra_sin_gema_no_craftea(self):
        _item("mineral de hierro", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("tónico de piedra")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_tonico_piedra_sin_mineral_no_craftea(self):
        _item("gema en bruto", self.jugador)
        antes = len(self.jugador.contents)
        self._craftear("tónico de piedra")
        self.assertEqual(len(self.jugador.contents), antes)

    def test_tonico_piedra_con_ingredientes_crea_pocion(self):
        _item("mineral de hierro", self.jugador)
        _item("gema en bruto", self.jugador)
        self._craftear("tónico de piedra")
        pociones = [o for o in self.jugador.contents
                    if isinstance(o, Consumible) and "vida mayor" in o.key]
        self.assertEqual(len(pociones), 1)

    def test_tonico_piedra_consume_ambos_ingredientes(self):
        _item("mineral de hierro", self.jugador)
        _item("gema en bruto", self.jugador)
        self._craftear("tónico de piedra")
        minerales = [o for o in self.jugador.contents if o.key == "mineral de hierro"]
        gemas = [o for o in self.jugador.contents if o.key == "gema en bruto"]
        self.assertEqual(len(minerales), 0)
        self.assertEqual(len(gemas), 0)

