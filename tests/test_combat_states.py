"""
tests/test_combat_states.py

Tests de integración para estados de combate.
Ejecutar con:
  evennia test --settings settings.py tests.test_combat_states
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from typeclasses.npc import NPC
from typeclasses.objects import Consumible
from systems.combat.engine import resolver_ataque, STAT_DEFAULTS
from systems.combat.states import aplicar_estado, tick_estados
from features.combat.handler import CombatHandler, _get_stats
from features.combat.states_script import EstadosScript, programar_estados_script


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _stats(**kwargs):
    s = dict(STAT_DEFAULTS)
    s.update(kwargs)
    return s


def _set_stats(obj, **overrides):
    for k, v in STAT_DEFAULTS.items():
        setattr(obj.db, k, overrides.get(k, v))
    obj.db.estados = overrides.get("estados", {})


# --------------------------------------------------------------------------- #
#  estado_aplicado en ResultadoAtaque
# --------------------------------------------------------------------------- #

class TestResultadoAtaqueEstado(EvenniaTest):

    def test_veneno_skill_marca_estado(self):
        from unittest.mock import patch
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as rng:
            rng.random.side_effect = [0.99, 0.99]
            rng.randint.return_value = 4
            resultado = resolver_ataque(at, df, "J", "G", habilidad="veneno")
        self.assertEqual(resultado.estado_aplicado, "veneno")

    def test_corte_skill_marca_sangrado(self):
        from unittest.mock import patch
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as rng:
            rng.random.side_effect = [0.99, 0.99]
            rng.randint.return_value = 4
            resultado = resolver_ataque(at, df, "J", "G", habilidad="corte")
        self.assertEqual(resultado.estado_aplicado, "sangrado")

    def test_golpe_fuerte_no_marca_estado(self):
        from unittest.mock import patch
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as rng:
            rng.random.side_effect = [0.99, 0.99]
            rng.randint.return_value = 4
            resultado = resolver_ataque(at, df, "J", "G", habilidad="golpe fuerte")
        self.assertIsNone(resultado.estado_aplicado)

    def test_ataque_letal_no_aplica_estado(self):
        from unittest.mock import patch
        at = _stats(fuerza=20, destreza=10, nivel=10)
        df = _stats(defensa=0, hp=1, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as rng:
            rng.random.side_effect = [0.99, 0.99]
            rng.randint.return_value = 8
            resultado = resolver_ataque(at, df, "J", "G", habilidad="veneno")
        # Letal → no aplica estado
        self.assertIsNone(resultado.estado_aplicado)

    def test_esquiva_no_aplica_estado(self):
        from unittest.mock import patch
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=10)
        with patch("systems.combat.engine.random") as rng:
            rng.random.side_effect = [0.01]  # esquiva
            resultado = resolver_ataque(at, df, "J", "G", habilidad="veneno")
        self.assertFalse(resultado.exito)
        self.assertIsNone(resultado.estado_aplicado)


# --------------------------------------------------------------------------- #
#  Antídoto limpia estado de veneno
# --------------------------------------------------------------------------- #

class TestAntidotoLimpiaVeneno(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.hp = 80
        self.char1.db.hp_max = 100
        self.char1.db.estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 3}}

    def _crear_antidoto(self):
        poc = create_object(Consumible, key="antídoto", location=self.char1)
        poc.db.efecto = "curar_veneno"
        poc.db.potencia = 0
        poc.db.usos = 1
        return poc

    def test_antidoto_elimina_veneno(self):
        anti = self._crear_antidoto()
        anti.aplicar(self.char1)
        self.assertNotIn("veneno", self.char1.db.estados)

    def test_antidoto_no_elimina_otros_estados(self):
        self.char1.db.estados["sangrado"] = {"dano_por_turno": 3, "turnos_restantes": 2}
        anti = self._crear_antidoto()
        anti.aplicar(self.char1)
        self.assertNotIn("veneno", self.char1.db.estados)
        self.assertIn("sangrado", self.char1.db.estados)

    def test_antidoto_sin_veneno_no_falla(self):
        self.char1.db.estados = {}
        anti = self._crear_antidoto()
        msg = anti.aplicar(self.char1)
        self.assertIsNotNone(msg)


# --------------------------------------------------------------------------- #
#  CombatHandler — aplicar_ticks_estado
# --------------------------------------------------------------------------- #

class TestHandlerTicks(EvenniaTest):

    def _crear_handler(self):
        handler = self.room1.scripts.add(CombatHandler)
        handler.db.participantes = []
        handler.db.turno_actual = 0
        handler.db.acciones = {}
        handler.db.turno_tiempo = 0
        handler.db.activo = True
        return handler

    def setUp(self):
        super().setUp()
        _set_stats(self.char1, hp=50, hp_max=100)
        _set_stats(self.char2, hp=50, hp_max=100)

    def test_tick_reduce_hp_con_veneno(self):
        handler = self._crear_handler()
        self.char1.db.estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 2}}
        murio = handler._aplicar_ticks_estado(self.char1)
        self.assertFalse(murio)
        self.assertEqual(self.char1.db.hp, 45)

    def test_tick_sin_estados_no_cambia_hp(self):
        handler = self._crear_handler()
        self.char1.db.estados = {}
        handler._aplicar_ticks_estado(self.char1)
        self.assertEqual(self.char1.db.hp, 50)

    def test_tick_decrementa_turnos(self):
        handler = self._crear_handler()
        self.char1.db.estados = {"sangrado": {"dano_por_turno": 3, "turnos_restantes": 2}}
        handler._aplicar_ticks_estado(self.char1)
        self.assertEqual(self.char1.db.estados["sangrado"]["turnos_restantes"], 1)

    def test_tick_elimina_estado_expirado(self):
        handler = self._crear_handler()
        self.char1.db.estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 1}}
        handler._aplicar_ticks_estado(self.char1)
        self.assertNotIn("veneno", self.char1.db.estados)


# --------------------------------------------------------------------------- #
#  EstadosScript — no debe aplicar un tick antes de TICK_INTERVAL segundos
# --------------------------------------------------------------------------- #

class TestEstadosScriptStartDelay(EvenniaTest):
    """
    Regresión: sin start_delay=True, Evennia dispara el primer at_repeat()
    de forma inmediata en vez de esperar TICK_INTERVAL segundos. Como
    programar_estados_script() solo se llama con estados ya poblados
    (justo al salir de combate), ese primer tick inmediato aplicaba daño
    de veneno/sangrado (o curación de regeneración) en el instante mismo
    en que el combate termina, no tras el intervalo esperado.
    """

    def test_start_delay_activado(self):
        script = self.char1.scripts.add(EstadosScript)
        self.assertTrue(script.start_delay)
        script.delete()

    def test_programar_no_aplica_tick_inmediato(self):
        self.char1.db.hp = 50
        self.char1.db.hp_max = 100
        self.char1.db.estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 2}}
        programar_estados_script(self.char1)
        # Si el primer at_repeat() se disparase de inmediato (bug), el HP
        # ya habría bajado a 45 aquí, antes de que pase ningún tiempo real.
        self.assertEqual(self.char1.db.hp, 50)
