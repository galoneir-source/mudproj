"""
tests/test_eventos.py

Tests de integración Evennia para el sistema de eventos mundiales (v0.19.0).
Cubre: EventoMundialScript, obtener_evento_activo(), tiempo_restante_evento(),
       CmdEvento, y los efectos en tienda y combate.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_eventos
"""
import time

from evennia.utils.test_resources import EvenniaTest

from features.events.commands import CmdEvento
from features.events.event_script import (
    obtener_evento_activo,
    tiempo_restante_evento,
    obtener_evento_script,
)
from systems.events.events import EVENTOS


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


def _init_char(char):
    char.db.nivel = 5
    char.db.monedas = 500
    char.db.reputacion = {}
    char.db.quests = {}
    char.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido"]
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
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


# ---------------------------------------------------------------------------
# EventoMundialScript — inicialización y estado
# ---------------------------------------------------------------------------

class TestEventoScriptInit(EvenniaTest):

    def _get_or_create_script(self):
        return obtener_evento_script()

    def test_script_creado_correctamente(self):
        script = self._get_or_create_script()
        self.assertIsNotNone(script)

    def test_sin_evento_activo_por_defecto(self):
        script = self._get_or_create_script()
        script.db.evento_activo = None
        self.assertIsNone(obtener_evento_activo())

    def test_set_evento_activo_y_leer(self):
        script = self._get_or_create_script()
        script.db.evento_activo = "feria_mercado"
        self.assertEqual(obtener_evento_activo(), "feria_mercado")
        script.db.evento_activo = None   # limpiar

    def test_idempotente_no_crea_duplicados(self):
        s1 = obtener_evento_script()
        s2 = obtener_evento_script()
        self.assertEqual(s1.id, s2.id)


# ---------------------------------------------------------------------------
# tiempo_restante_evento
# ---------------------------------------------------------------------------

class TestTiempoRestante(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = obtener_evento_script()
        self.script.db.evento_activo = None

    def tearDown(self):
        self.script.db.evento_activo = None
        super().tearDown()

    def test_sin_evento_devuelve_cero(self):
        self.assertEqual(tiempo_restante_evento(), 0)

    def test_evento_recien_iniciado_tiene_duracion_completa(self):
        self.script.db.evento_activo = "tormenta_magica"
        self.script.db.evento_inicio = time.time()
        restante = tiempo_restante_evento()
        duracion = EVENTOS["tormenta_magica"]["duracion"]
        self.assertGreater(restante, duracion - 5)
        self.assertLessEqual(restante, duracion)

    def test_evento_a_mitad_de_duracion(self):
        duracion = EVENTOS["invasion_no_muertos"]["duracion"]
        self.script.db.evento_activo = "invasion_no_muertos"
        self.script.db.evento_inicio = time.time() - duracion / 2
        restante = tiempo_restante_evento()
        self.assertGreater(restante, duracion / 2 - 5)
        self.assertLessEqual(restante, duracion / 2 + 5)

    def test_evento_expirado_devuelve_cero(self):
        self.script.db.evento_activo = "tormenta_magica"
        self.script.db.evento_inicio = time.time() - 9999
        self.assertEqual(tiempo_restante_evento(), 0)


# ---------------------------------------------------------------------------
# CmdEvento
# ---------------------------------------------------------------------------

class TestCmdEvento(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.script = obtener_evento_script()
        self.script.db.evento_activo = None
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        self.script.db.evento_activo = None
        super().tearDown()

    def _run(self, args=""):
        cmd = _make_cmd(CmdEvento, self.char1, args)
        cmd.func()

    def test_sin_evento_muestra_mensaje_vacio(self):
        self._run()
        self.assertIn("No hay ningún evento", self.cap.all())

    def test_con_evento_muestra_nombre(self):
        self.script.db.evento_activo = "feria_mercado"
        self.script.db.evento_inicio = time.time()
        self._run()
        self.assertIn("Feria del Mercado", self.cap.all())

    def test_con_evento_muestra_descripcion(self):
        self.script.db.evento_activo = "feria_mercado"
        self.script.db.evento_inicio = time.time()
        self._run()
        self.assertIn("20%", self.cap.all())

    def test_con_evento_muestra_tiempo_restante(self):
        self.script.db.evento_activo = "tormenta_magica"
        self.script.db.evento_inicio = time.time()
        self._run()
        texto = self.cap.all()
        self.assertIn("Tiempo restante", texto)

    def test_invasion_muestra_xp_factor(self):
        self.script.db.evento_activo = "invasion_no_muertos"
        self.script.db.evento_inicio = time.time()
        self._run()
        self.assertIn("2.0", self.cap.all())

    def test_tormenta_muestra_bonus_int(self):
        self.script.db.evento_activo = "tormenta_magica"
        self.script.db.evento_inicio = time.time()
        self._run()
        self.assertIn("+3", self.cap.all())


# ---------------------------------------------------------------------------
# Efecto tormenta: _get_stats aplica +INT a jugadores
# ---------------------------------------------------------------------------

class TestTormentaEnCombate(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.script = obtener_evento_script()
        self.script.db.evento_activo = None

    def tearDown(self):
        self.script.db.evento_activo = None
        super().tearDown()

    def test_sin_evento_int_normal(self):
        from features.combat.handler import _get_stats
        self.char1.db.inteligencia = 10
        stats = _get_stats(self.char1)
        self.assertEqual(stats["inteligencia"], 10)

    def test_tormenta_suma_bonus_int(self):
        from features.combat.handler import _get_stats
        self.script.db.evento_activo = "tormenta_magica"
        self.script.db.evento_inicio = time.time()
        self.char1.db.inteligencia = 10
        stats = _get_stats(self.char1)
        self.assertEqual(stats["inteligencia"], 13)  # 10 + 3

    def test_tormenta_solo_aplica_con_evento_activo(self):
        from features.combat.handler import _get_stats
        # Sin evento activo, INT base
        self.script.db.evento_activo = None
        self.char1.db.inteligencia = 10
        stats = _get_stats(self.char1)
        self.assertEqual(stats["inteligencia"], 10)


# ---------------------------------------------------------------------------
# Efecto invasión: XP multiplicado en handler
# ---------------------------------------------------------------------------

class TestInvasionXP(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = obtener_evento_script()
        self.script.db.evento_activo = None

    def tearDown(self):
        self.script.db.evento_activo = None
        super().tearDown()

    def test_sin_evento_xp_factor_no_presente(self):
        from features.events.event_script import obtener_evento_activo
        from systems.events.events import EVENTOS
        ev_id = obtener_evento_activo()
        if ev_id:
            xp_factor = EVENTOS.get(ev_id, {}).get("efectos", {}).get("xp_factor", 1.0)
        else:
            xp_factor = 1.0
        self.assertEqual(xp_factor, 1.0)

    def test_invasion_tiene_xp_factor_2(self):
        self.script.db.evento_activo = "invasion_no_muertos"
        self.script.db.evento_inicio = time.time()
        from features.events.event_script import obtener_evento_activo
        from systems.events.events import EVENTOS
        ev_id = obtener_evento_activo()
        factor = EVENTOS[ev_id]["efectos"]["xp_factor"]
        self.assertEqual(factor, 2.0)

    def test_invasion_afecta_solo_legion_oscura(self):
        self.script.db.evento_activo = "invasion_no_muertos"
        facciones = EVENTOS["invasion_no_muertos"]["efectos"]["facciones_afectadas"]
        self.assertIn("legion_oscura", facciones)
        self.assertNotIn("ciudadanos", facciones)


# ---------------------------------------------------------------------------
# Efecto feria: factor de precio en tienda
# ---------------------------------------------------------------------------

class TestFeriaEnTienda(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.script = obtener_evento_script()
        self.script.db.evento_activo = None

    def tearDown(self):
        self.script.db.evento_activo = None
        super().tearDown()

    def test_sin_evento_factor_base_1(self):
        from features.events.event_script import obtener_evento_activo
        from systems.events.events import EVENTOS
        ev_id = obtener_evento_activo()
        factor = 1.0
        if ev_id:
            descuento = EVENTOS.get(ev_id, {}).get("efectos", {}).get("descuento_tienda", 0)
            factor = factor * (1 - descuento)
        self.assertEqual(factor, 1.0)

    def test_feria_reduce_factor_20pct(self):
        self.script.db.evento_activo = "feria_mercado"
        self.script.db.evento_inicio = time.time()
        from features.events.event_script import obtener_evento_activo
        from systems.events.events import EVENTOS
        ev_id = obtener_evento_activo()
        factor = 1.0
        descuento = EVENTOS.get(ev_id, {}).get("efectos", {}).get("descuento_tienda", 0)
        factor = factor * (1 - descuento)
        self.assertAlmostEqual(factor, 0.80)

    def test_feria_sobre_factor_rep_positivo(self):
        # rep factor 0.90 (10% desc rep) + feria 20% → 0.90 * 0.80 = 0.72
        factor_rep = 0.90
        descuento_feria = EVENTOS["feria_mercado"]["efectos"]["descuento_tienda"]
        factor_final = factor_rep * (1 - descuento_feria)
        self.assertAlmostEqual(factor_final, 0.72)


if __name__ == "__main__":
    import unittest
    unittest.main()
