"""
tests/test_duelos_system.py

Tests de integración Evennia para el sistema de duelos entre jugadores (v0.21.0).
Cubre: CmdRetar, CmdAceptarDuelo, CmdRechazarDuelo, CmdRendirse, _fin_duelo.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_duelos_system
"""
import time

from evennia.utils.test_resources import EvenniaTest

from features.duels.commands import (
    CmdAceptarDuelo,
    CmdRechazarDuelo,
    CmdRetar,
    CmdRendirse,
    _limpiar_duelo,
)
from systems.duels.duels import DUEL_TIMEOUT


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


def _init_char(char, nivel=5, monedas=100):
    char.db.nivel = nivel
    char.db.hp = 100
    char.db.hp_max = 100
    char.db.fuerza = 10
    char.db.destreza = 10
    char.db.constitucion = 10
    char.db.inteligencia = 10
    char.db.defensa = 5
    char.db.experiencia = 0
    char.db.monedas = monedas
    char.db.en_combate = False
    char.db.duelo_pendiente = None
    char.db.duelo_retador_dbref = None
    char.db.duelo_apuesta_pendiente = 0
    char.db.apuesta_duelo = 0
    char.db.duelos_ganados = 0
    char.db.duelos_perdidos = 0
    char.db.habilidades_desbloqueadas = []
    char.db.estados = {}


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


# ---------------------------------------------------------------------------
# CmdRetar
# ---------------------------------------------------------------------------

class TestCmdRetar(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def _retar(self, args):
        cmd = _make_cmd(CmdRetar, self.char1, args)
        cmd.func()

    def test_retar_valido_crea_pendiente(self):
        self._retar(self.char2.key)
        self.assertIsNotNone(self.char1.db.duelo_pendiente)

    def test_retar_notifica_retador(self):
        self._retar(self.char2.key)
        self.assertIn("retado", self.cap1.all().lower())

    def test_retar_notifica_retado(self):
        self._retar(self.char2.key)
        self.assertIn("duelo", self.cap2.all().lower())

    def test_retar_guarda_dbref_en_retado(self):
        self._retar(self.char2.key)
        self.assertEqual(self.char2.db.duelo_retador_dbref, self.char1.dbref)

    def test_retar_npc_rechazado(self):
        # Crear un objeto sin cuenta de jugador (NPC)
        import evennia
        npc = evennia.create_object("typeclasses.objects.Object",
                                    key="goblin", location=self.room1)
        self.cap1.msgs.clear()
        cmd = _make_cmd(CmdRetar, self.char1, "goblin")
        cmd.func()
        self.assertIn("no es un jugador", self.cap1.all())
        npc.delete()

    def test_retar_a_si_mismo_rechazado(self):
        cmd = _make_cmd(CmdRetar, self.char1, self.char1.key)
        cmd.func()
        self.assertIn("mismo", self.cap1.all().lower())
        self.assertIsNone(self.char1.db.duelo_pendiente)

    def test_retar_en_combate_bloqueado(self):
        self.char1.db.en_combate = True
        self._retar(self.char2.key)
        self.assertIsNone(self.char1.db.duelo_pendiente)
        self.assertIn("combate", self.cap1.all().lower())

    def test_retar_objetivo_en_combate_bloqueado(self):
        self.char2.db.en_combate = True
        self._retar(self.char2.key)
        self.assertIsNone(self.char1.db.duelo_pendiente)
        self.assertIn("combate", self.cap1.all().lower())

    def test_retar_con_apuesta_valida(self):
        self._retar(f"{self.char2.key} = 50")
        pendiente = self.char1.db.duelo_pendiente or {}
        self.assertEqual(pendiente.get("apuesta"), 50)

    def test_retar_apuesta_sin_fondos_rechazado(self):
        self.char1.db.monedas = 10
        self._retar(f"{self.char2.key} = 50")
        self.assertIsNone(self.char1.db.duelo_pendiente)
        self.assertIn("monedas", self.cap1.all().lower())

    def test_retar_ya_tiene_pendiente(self):
        self.char1.db.duelo_pendiente = {"timestamp": time.time()}
        self._retar(self.char2.key)
        self.assertIn("pendiente", self.cap1.all().lower())

    def test_retar_objetivo_ya_tiene_pendiente(self):
        self.char2.db.duelo_retador_dbref = "#999"
        self._retar(self.char2.key)
        self.assertIn("pendiente", self.cap1.all().lower())

    def test_retar_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdRetar, self.char1, "")
        cmd.func()
        self.assertIn("Uso", self.cap1.all())


# ---------------------------------------------------------------------------
# CmdRechazarDuelo
# ---------------------------------------------------------------------------

class TestCmdRechazarDuelo(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def test_rechazar_sin_pendiente(self):
        cmd = _make_cmd(CmdRechazarDuelo, self.char2, "")
        cmd.func()
        self.assertIn("pendiente", self.cap2.all().lower())

    def test_rechazar_limpia_retado(self):
        # char2 tiene reto de char1
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        cmd = _make_cmd(CmdRechazarDuelo, self.char2, "")
        cmd.func()
        self.assertIsNone(self.char2.db.duelo_retador_dbref)

    def test_rechazar_limpia_retador(self):
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        cmd = _make_cmd(CmdRechazarDuelo, self.char2, "")
        cmd.func()
        self.assertIsNone(self.char1.db.duelo_pendiente)

    def test_rechazar_notifica_retador(self):
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        cmd = _make_cmd(CmdRechazarDuelo, self.char2, "")
        cmd.func()
        self.assertIn("rechazado", self.cap1.all().lower())


# ---------------------------------------------------------------------------
# CmdAceptarDuelo
# ---------------------------------------------------------------------------

class TestCmdAceptarDuelo(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def test_aceptar_sin_pendiente_falla(self):
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        cmd.func()
        self.assertIn("pendiente", self.cap2.all().lower())

    def test_aceptar_reto_expirado_falla(self):
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": 0.0,  # muy viejo
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        cmd.func()
        self.assertIn("expirado", self.cap2.all().lower())

    def test_aceptar_crea_handler_modo_duelo(self):
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        # Permitir que sala reciba mensajes
        self.room1.msg_contents = lambda m, **kw: None
        cmd.func()
        # Buscar handler activo en la sala
        handler = None
        for script in self.room1.scripts.all():
            if script.key == "combat_handler":
                handler = script
                break
        self.assertIsNotNone(handler, "Handler de combate no creado")
        self.assertTrue(getattr(handler.db, "modo_duelo", False))

    def test_aceptar_ambos_en_combate_tras_duelo(self):
        self.char1.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = self.char1.dbref
        self.room1.msg_contents = lambda m, **kw: None
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        cmd.func()
        self.assertTrue(self.char1.db.en_combate)
        self.assertTrue(self.char2.db.en_combate)


# ---------------------------------------------------------------------------
# _fin_duelo (directo sobre handler)
# ---------------------------------------------------------------------------

class TestFinDuelo(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, monedas=100)
        _init_char(self.char2, monedas=100)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.room1.msg_contents = lambda m, **kw: None
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

        from features.combat.handler import CombatHandler
        self.handler = self.room1.scripts.add(CombatHandler)
        self.handler.db.modo_duelo = True
        self.handler.iniciar([self.char1, self.char2])

    def test_fin_duelo_incrementa_ganados(self):
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertEqual(self.char1.db.duelos_ganados, 1)

    def test_fin_duelo_incrementa_perdidos(self):
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertEqual(self.char2.db.duelos_perdidos, 1)

    def test_fin_duelo_sin_apuesta_no_transfiere(self):
        self.char1.db.apuesta_duelo = 0
        self.char2.db.apuesta_duelo = 0
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertEqual(self.char1.db.monedas, 100)
        self.assertEqual(self.char2.db.monedas, 100)

    def test_fin_duelo_transfiere_apuesta(self):
        self.char1.db.apuesta_duelo = 40
        self.char2.db.apuesta_duelo = 40
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertEqual(self.char1.db.monedas, 140)
        self.assertEqual(self.char2.db.monedas, 60)

    def test_fin_duelo_pago_parcial_si_pocos_fondos(self):
        self.char1.db.apuesta_duelo = 200
        self.char2.db.monedas = 30
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        # Paga lo que tiene
        self.assertEqual(self.char2.db.monedas, 0)
        self.assertEqual(self.char1.db.monedas, 130)

    def test_fin_duelo_limpia_apuesta(self):
        self.char1.db.apuesta_duelo = 50
        self.char2.db.apuesta_duelo = 50
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertEqual(self.char1.db.apuesta_duelo, 0)
        self.assertEqual(self.char2.db.apuesta_duelo, 0)

    def test_fin_duelo_limpia_estado_combate(self):
        self.handler._fin_duelo(ganador=self.char1, perdedor=self.char2)
        self.assertFalse(self.char1.db.en_combate)
        self.assertFalse(self.char2.db.en_combate)


# ---------------------------------------------------------------------------
# CmdRendirse
# ---------------------------------------------------------------------------

class TestCmdRendirse(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def test_rendirse_fuera_combate_falla(self):
        cmd = _make_cmd(CmdRendirse, self.char1, "")
        cmd.func()
        self.assertIn("combate", self.cap1.all().lower())

    def test_rendirse_en_combate_normal_falla(self):
        from features.combat.handler import CombatHandler
        self.room1.msg_contents = lambda m, **kw: None
        handler = self.room1.scripts.add(CombatHandler)
        handler.db.modo_duelo = False  # combate normal
        handler.iniciar([self.char1, self.char2])
        self.cap1.msgs.clear()
        cmd = _make_cmd(CmdRendirse, self.char1, "")
        cmd.func()
        self.assertIn("normal", self.cap1.all().lower())

    def test_rendirse_en_duelo_termina(self):
        from features.combat.handler import CombatHandler
        self.room1.msg_contents = lambda m, **kw: None
        handler = self.room1.scripts.add(CombatHandler)
        handler.db.modo_duelo = True
        handler.iniciar([self.char1, self.char2])
        self.cap1.msgs.clear()
        cmd = _make_cmd(CmdRendirse, self.char1, "")
        cmd.func()
        # char2 gana → duelos_ganados = 1
        self.assertEqual(self.char2.db.duelos_ganados, 1)
        self.assertEqual(self.char1.db.duelos_perdidos, 1)

    def test_rendirse_en_duelo_libera_combate(self):
        from features.combat.handler import CombatHandler
        self.room1.msg_contents = lambda m, **kw: None
        handler = self.room1.scripts.add(CombatHandler)
        handler.db.modo_duelo = True
        handler.iniciar([self.char1, self.char2])
        cmd = _make_cmd(CmdRendirse, self.char1, "")
        cmd.func()
        self.assertFalse(self.char1.db.en_combate)
        self.assertFalse(self.char2.db.en_combate)


if __name__ == "__main__":
    import unittest
    unittest.main()
