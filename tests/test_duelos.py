"""
tests/test_duelos.py

Tests de integración Evennia para el sistema de duelos entre jugadores (v0.21.0).
Cubre: CmdRetar, CmdAceptarDuelo, CmdRechazarDuelo, CmdRendirse, _fin_duelo.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_duelos
"""
import time

from evennia.utils.test_resources import EvenniaTest

from features.duels.commands import (
    CmdAceptarDuelo,
    CmdRechazarDuelo,
    CmdRetar,
    CmdRendirse,
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
        import evennia
        otro = evennia.create_object(
            "typeclasses.characters.Character", key="Otro", location=self.room1
        )
        _init_char(otro)
        otro.db.duelo_pendiente = {
            "retado_dbref": self.char2.dbref,
            "apuesta": 0,
            "timestamp": time.time(),
        }
        self.char2.db.duelo_retador_dbref = otro.dbref
        self._retar(self.char2.key)
        self.assertIn("pendiente", self.cap1.all().lower())
        otro.delete()

    def test_retar_sin_args_muestra_uso(self):
        cmd = _make_cmd(CmdRetar, self.char1, "")
        cmd.func()
        self.assertIn("Uso", self.cap1.all())

    def test_retar_reto_saliente_caducado_permite_nuevo_reto(self):
        """
        Regresión: CmdRetar solo comprobaba si caller.db.duelo_pendiente
        existía, sin mirar si ya había caducado (DUEL_TIMEOUT). Un
        jugador que retaba y nunca era respondido (el otro ignoraba
        aceptar/rechazar) quedaba bloqueado para retar a cualquiera,
        para siempre.
        """
        self._retar(self.char2.key)
        pendiente = dict(self.char1.db.duelo_pendiente)
        pendiente["timestamp"] = time.time() - DUEL_TIMEOUT - 10
        self.char1.db.duelo_pendiente = pendiente

        self.cap1.msgs.clear()
        import evennia
        tercero = evennia.create_object(
            "typeclasses.characters.Character", key="Tercero", location=self.room1
        )
        _init_char(tercero)
        tercero.account = self.account2

        cmd = _make_cmd(CmdRetar, self.char1, tercero.key)
        cmd.func()
        nuevo = self.char1.db.duelo_pendiente
        self.assertIsNotNone(nuevo)
        self.assertEqual(nuevo.get("retado_dbref"), tercero.dbref)
        tercero.delete()

    def test_retar_reto_entrante_caducado_permite_nuevo_reto(self):
        """
        Regresión: el mismo defecto, pero visto desde el retado. Si
        alguien te retó y nunca respondiste ni el reto llegó a
        aceptarse/rechazarse, cualquier otro jugador quedaba bloqueado
        para retarte a ti para siempre, aunque el reto original ya
        hubiera caducado hace tiempo.
        """
        import evennia
        tercero = evennia.create_object(
            "typeclasses.characters.Character", key="Tercero", location=self.room1
        )
        _init_char(tercero)
        tercero.account = self.account2

        self._retar(self.char2.key)  # char1 reta a char2
        pendiente = dict(self.char1.db.duelo_pendiente)
        pendiente["timestamp"] = time.time() - DUEL_TIMEOUT - 10
        self.char1.db.duelo_pendiente = pendiente

        cmd = _make_cmd(CmdRetar, tercero, self.char2.key)
        cmd.func()
        self.assertEqual(self.char2.db.duelo_retador_dbref, tercero.dbref)
        tercero.delete()


# ---------------------------------------------------------------------------
# Reto saliente y entrante son independientes
#
# Un jugador puede tener a la vez un reto que él mismo lanzó (slot
# saliente, db.duelo_pendiente) y uno que recibió de otra persona (slot
# entrante, db.duelo_retador_dbref/db.duelo_apuesta_pendiente): son
# atributos distintos y nada en CmdRetar impide que coexistan. Resolver
# uno (aceptar/rechazar) no debe tocar el otro.
# ---------------------------------------------------------------------------

class TestRetoSalienteEntranteIndependientes(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        import evennia
        self.char3 = evennia.create_object(
            "typeclasses.characters.Character", key="Tercero", location=self.room1
        )
        _init_char(self.char3)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.room1.msg_contents = lambda m, **kw: None
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)
        self.cap3 = _MsgCapture(self.char3)

    def tearDown(self):
        self.char3.delete()
        super().tearDown()

    def _retar(self, caller, args):
        cmd = _make_cmd(CmdRetar, caller, args)
        cmd.func()

    def _preparar_saliente_y_entrante(self):
        self._retar(self.char1, self.char2.key)  # char1 -> char2 (saliente de char1)
        self._retar(self.char3, self.char1.key)  # char3 -> char1 (entrante de char1)
        self.assertIsNotNone(self.char1.db.duelo_pendiente)
        self.assertEqual(self.char1.db.duelo_retador_dbref, self.char3.dbref)

    def test_rechazar_entrante_no_cancela_saliente(self):
        self._preparar_saliente_y_entrante()

        cmd = _make_cmd(CmdRechazarDuelo, self.char1, "")
        cmd.func()

        # El reto saliente de char1 hacia char2 sigue intacto.
        self.assertIsNotNone(self.char1.db.duelo_pendiente)
        self.assertEqual(self.char1.db.duelo_pendiente["retado_dbref"], self.char2.dbref)
        self.assertEqual(self.char2.db.duelo_retador_dbref, self.char1.dbref)

        # y char2 todavía puede aceptarlo con normalidad.
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        cmd.func()
        handler = None
        for script in self.room1.scripts.all():
            if script.key == "combat_handler":
                handler = script
                break
        self.assertIsNotNone(handler, "Handler de combate no creado")

    def test_aceptar_entrante_no_borra_saliente_a_ciegas(self):
        self._preparar_saliente_y_entrante()

        # char1 acepta el reto de char3: entran en duelo.
        cmd = _make_cmd(CmdAceptarDuelo, self.char1, "")
        cmd.func()
        self.assertTrue(self.char1.db.en_combate)

        # char2 intenta aceptar su reto (ya obsoleto) de char1: debe
        # fallar por el motivo real -- char1 ya está en combate -- y no
        # con el mensaje engañoso de "expirado" que daba el bug (el reto
        # saliente de char1 se borraba a ciegas al resolver el entrante).
        self.cap2.msgs.clear()
        cmd = _make_cmd(CmdAceptarDuelo, self.char2, "")
        cmd.func()
        self.assertIn("ya está en combate", self.cap2.all())
        self.assertNotIn("expirado", self.cap2.all().lower())


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
# Apuesta "fantasma" tras huir de un duelo (eliminar_participante)
# ---------------------------------------------------------------------------

class TestApuestaTrasHuidaDeDuelo(EvenniaTest):
    """
    _terminar_combate() solo limpia apuesta_duelo de quien queda en
    self.db.participantes — quien huyó ya no está en esa lista y antes se
    quedaba con la apuesta activa, que se cobraba de verdad en su próximo
    duelo sin apuesta explícita (caza de recompensa, torneo de arena).
    """

    def setUp(self):
        super().setUp()
        _init_char(self.char1, monedas=100)
        _init_char(self.char2, monedas=100)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.room1.msg_contents = lambda m, **kw: None

        from features.combat.handler import CombatHandler
        self.handler = self.room1.scripts.add(CombatHandler)
        self.handler.db.modo_duelo = True
        self.handler.iniciar([self.char1, self.char2])
        self.char1.db.apuesta_duelo = 40
        self.char2.db.apuesta_duelo = 40

    def test_huir_de_duelo_limpia_la_apuesta_del_que_huye(self):
        from unittest.mock import patch
        with patch("random.random", return_value=0.1), \
             patch("random.choice", side_effect=lambda seq: seq[0]):
            self.handler._intentar_huida(self.char1)
        self.assertEqual(self.char1.db.apuesta_duelo, 0)

    def test_apuesta_fantasma_no_se_cobra_en_caza_de_recompensa_posterior(self):
        from unittest.mock import patch
        with patch("random.random", return_value=0.1), \
             patch("random.choice", side_effect=lambda seq: seq[0]):
            self.handler._intentar_huida(self.char1)

        # Simula una caza de recompensa posterior: nueva duelo sin apuesta
        # explícita (como hace CmdCazar, que nunca toca apuesta_duelo).
        from features.combat.handler import CombatHandler
        handler2 = self.room1.scripts.add(CombatHandler)
        handler2.db.modo_duelo = True
        handler2.iniciar([self.char1, self.char2])
        handler2._fin_duelo(ganador=self.char1, perdedor=self.char2)

        self.assertEqual(self.char1.db.monedas, 100)
        self.assertEqual(self.char2.db.monedas, 100)


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
