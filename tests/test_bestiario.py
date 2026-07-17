"""
tests/test_bestiario.py

Tests de integración para el sistema de Bestiario: CmdBestiario (lista,
detalle, búsqueda por nombre) y el registro real de bajas desde
CombatHandler._procesar_muerte().

No existía ningún test de integración para este sistema (solo
tests/test_bestiary_system.py, puro sobre el catálogo) — el mismo hueco de
cobertura visto en mascotas/monturas/percepción/runas/profesiones esta sesión.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_bestiario
"""
from unittest.mock import patch

from evennia import create_object
from evennia.prototypes import spawner
from evennia.utils.test_resources import EvenniaTest

from features.bestiary.commands import CmdBestiario
from features.combat.handler import CombatHandler
from systems.combat.engine import STAT_DEFAULTS


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


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        cap = self

        def _capture(m=None, **kw):
            text = m
            if text is None:
                text = kw.get("text", "")
            if isinstance(text, tuple):
                text = text[0]
            cap.msgs.append(str(text or ""))

        char.msg = _capture

    def all(self):
        return "\n".join(self.msgs)


def _set_stats(obj, **overrides):
    for k, v in STAT_DEFAULTS.items():
        setattr(obj.db, k, overrides.get(k, v))


class TestCmdBestiarioLista(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.bestiary = {}
        self.cap = _MsgCapture(self.char1)

    def _bestiario(self, args=""):
        cmd = _make_cmd(CmdBestiario, self.char1, args)
        cmd.func()

    def test_lista_sin_registros_marca_cero(self):
        self._bestiario("")
        self.assertIn("0/", self.cap.all())

    def test_lista_con_un_registro_marca_uno(self):
        self.char1.db.bestiary = {"GOBLIN": {"kills": 3, "primera_vez": 100}}
        self._bestiario("")
        self.assertIn("1/", self.cap.all())
        self.assertIn("Goblin", self.cap.all())


class TestCmdBestiarioDetalle(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.db.bestiary = {}
        self.cap = _MsgCapture(self.char1)

    def _bestiario(self, args=""):
        cmd = _make_cmd(CmdBestiario, self.char1, args)
        cmd.func()

    def test_criatura_no_derrotada_lo_indica(self):
        self._bestiario("goblin")
        self.assertIn("Aún no has derrotado", self.cap.all())

    def test_criatura_derrotada_muestra_bajas(self):
        self.char1.db.bestiary = {"GOBLIN": {"kills": 2, "primera_vez": 100}}
        self._bestiario("goblin")
        self.assertIn("2 bajas", self.cap.all())

    def test_sin_coincidencias_avisa(self):
        self._bestiario("criatura_inexistente_xyz")
        self.assertIn("No se encontró", self.cap.all())

    def test_ambiguedad_lista_opciones(self):
        # "Guardián" coincide con "Guardián Arcano" y "Guardián de la Forja"
        self._bestiario("Guardián")
        self.assertIn("específico", self.cap.all().lower())

    def test_ambiguedad_resuelta_por_nombre_exacto(self):
        # "Gólem de Piedra" es coincidencia exacta única aunque "golem" u
        # otras búsquedas parciales pudieran devolver más de un resultado.
        self._bestiario("Gólem de Piedra")
        self.assertIn("Gólem de Piedra", self.cap.all())
        self.assertNotIn("específico", self.cap.all().lower())


class TestRegistroRealDesdeCombate(EvenniaTest):
    """
    Ejercita el camino real: CombatHandler._procesar_muerte() -> registrar_kill().
    """

    def setUp(self):
        super().setUp()
        self.sala = create_object("typeclasses.rooms.Room", key="Arena")
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        _set_stats(self.jugador, hp=100, hp_max=100, nivel=1)
        self.jugador.db.bestiary = {}
        self.jugador.db.jefes_derrotados = []

    def _handler(self, *npcs):
        handler = self.sala.scripts.add(CombatHandler)
        handler.iniciar([self.jugador, *npcs])
        return handler

    def test_npc_normal_registra_en_bestiario(self):
        npc = spawner.spawn("GOBLIN")[0]
        npc.location = self.sala
        _set_stats(npc, hp=1, hp_max=30, nivel=1)
        handler = self._handler(npc)
        with patch("features.respawn.respawn.programar_respawn"):
            handler._procesar_muerte(npc, asesino=self.jugador)
        self.assertEqual(self.jugador.db.bestiary["GOBLIN"]["kills"], 1)

    def test_jefe_de_mundo_con_npc_prototipo_none_registra_en_bestiario(self):
        """
        Regresión: los jefes de mundo (y los enemigos de mazmorra) ponen
        npc.db.npc_prototipo = None a propósito para desactivar el respawn
        automático genérico (features/respawn/respawn.py depende de ese
        campo). Como CombatHandler._procesar_muerte() leía el prototipo de
        ese mismo campo para el bestiario, matar cualquiera de los 6 jefes
        de mundo/mazmorra (SENOR_CENIZAS, MAESTRO_FORJADOR, SENOR_ABISMO,
        TITAN_PANTANO, GUARDIAN_FORJA, DRAGON_CENIZA) nunca se registraba en
        el bestiario — dejando el logro "enciclopedista" (100% del
        bestiario) permanentemente inalcanzable. Fix: fallback al tag
        'from_prototype' que el spawner de Evennia añade siempre al crear
        el objeto, que sobrevive a ese None.
        """
        npc = spawner.spawn("DRAGON_CENIZA")[0]
        npc.location = self.sala
        npc.db.npc_prototipo = None  # como hace world_boss_script.py
        _set_stats(npc, hp=1, hp_max=100, nivel=1)
        handler = self._handler(npc)
        with patch("features.respawn.respawn.programar_respawn"):
            handler._procesar_muerte(npc, asesino=self.jugador)
        self.assertEqual(self.jugador.db.bestiary["DRAGON_CENIZA"]["kills"], 1)

    def test_jefe_de_mazmorra_con_npc_prototipo_none_registra_en_bestiario(self):
        npc = spawner.spawn("SENOR_ABISMO")[0]
        npc.location = self.sala
        npc.db.npc_prototipo = None  # como hace dungeon_script.py
        _set_stats(npc, hp=1, hp_max=100, nivel=1)
        handler = self._handler(npc)
        with patch("features.respawn.respawn.programar_respawn"):
            handler._procesar_muerte(npc, asesino=self.jugador)
        self.assertEqual(self.jugador.db.bestiary["SENOR_ABISMO"]["kills"], 1)

    def test_npc_prototipo_none_no_dispara_respawn(self):
        """El fix del bestiario no debe reactivar el respawn automático."""
        from evennia.scripts.models import ScriptDB

        npc = spawner.spawn("TITAN_PANTANO")[0]
        npc.location = self.sala
        npc.db.npc_prototipo = None
        _set_stats(npc, hp=1, hp_max=100, nivel=1)
        handler = self._handler(npc)
        # Sin mockear programar_respawn: debe ejecutarse pero no crear nada,
        # porque internamente comprueba npc.db.npc_prototipo y sale si es None.
        handler._procesar_muerte(npc, asesino=self.jugador)
        self.assertEqual(
            ScriptDB.objects.filter(db_key="respawn_script").count(), 0
        )

    def test_kills_totales_no_afectado_por_el_fallback(self):
        """El fallback solo debe alimentar el bestiario, no is_boss/jefes_derrotados
        (esos ya se rastrean aparte para jefes de mundo, vía jefes_mundo_derrotados)."""
        npc = spawner.spawn("DRAGON_CENIZA")[0]
        npc.location = self.sala
        npc.db.npc_prototipo = None
        _set_stats(npc, hp=1, hp_max=100, nivel=1)
        handler = self._handler(npc)
        with patch("features.respawn.respawn.programar_respawn"):
            handler._procesar_muerte(npc, asesino=self.jugador)
        self.assertEqual(self.jugador.db.jefes_derrotados, [])


if __name__ == "__main__":
    import unittest
    unittest.main()
