"""
tests/test_time.py

Tests de integración para el sistema de ciclo día/noche.
Usan EvenniaTest (Django + BD de prueba).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test --settings settings.py tests.test_time
"""
from unittest.mock import MagicMock, patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from features.time.clock_script import RelojMundial, hora_actual, obtener_reloj
from commands.general_commands import CmdHora
from systems.time.clock import periodo_del_dia


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _run_cmd(caller, cmdclass, args=""):
    cmd = cmdclass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmdclass.key
    cmd.session = MagicMock()
    cmd.func()


def _crear_reloj(hora=8):
    import evennia
    reloj = evennia.create_script("features.time.clock_script.RelojMundial")
    reloj.db.hora = hora
    return reloj


# --------------------------------------------------------------------------- #
#  RelojMundial: creación y avance
# --------------------------------------------------------------------------- #

class TestRelojMundial(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.reloj = _crear_reloj(hora=8)

    def tearDown(self):
        if self.reloj and self.reloj.pk:
            self.reloj.delete()
        super().tearDown()

    def test_hora_inicial_es_ocho(self):
        self.assertEqual(self.reloj.db.hora, 8)

    def test_at_repeat_avanza_una_hora(self):
        self.reloj.db.hora = 10
        self.reloj.at_repeat()
        self.assertEqual(self.reloj.db.hora, 11)

    def test_at_repeat_vuelta_a_medianoche(self):
        self.reloj.db.hora = 23
        self.reloj.at_repeat()
        self.assertEqual(self.reloj.db.hora, 0)

    def test_hora_actual_devuelve_hora_del_reloj(self):
        self.reloj.db.hora = 15
        self.assertEqual(hora_actual(), 15)


# --------------------------------------------------------------------------- #
#  obtener_reloj
# --------------------------------------------------------------------------- #

class TestObtenerReloj(EvenniaTest):
    def test_crea_reloj_si_no_existe(self):
        reloj = obtener_reloj()
        self.assertIsNotNone(reloj)
        reloj.delete()

    def test_no_duplica_reloj_existente(self):
        r1 = _crear_reloj()
        r2 = obtener_reloj()
        # Deben ser el mismo objeto (mismo pk)
        self.assertEqual(r1.pk, r2.pk)
        r1.delete()


# --------------------------------------------------------------------------- #
#  Comando: hora
# --------------------------------------------------------------------------- #

class TestCmdHora(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.reloj = _crear_reloj(hora=14)

    def tearDown(self):
        if self.reloj and self.reloj.pk:
            self.reloj.delete()
        super().tearDown()

    def test_muestra_hora_y_periodo(self):
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdHora)
        output = "\n".join(msgs)
        self.assertIn("14:00", output)
        self.assertIn("Tarde", output)

    def test_muestra_texto_ambiente(self):
        msgs = []
        self.char1.msg = lambda text, **kw: msgs.append(text)
        _run_cmd(self.char1, CmdHora)
        output = "\n".join(msgs)
        # Debe incluir texto de ambiente del período actual
        self.assertTrue(len(output) > 20)


# --------------------------------------------------------------------------- #
#  Sala: texto de ambiente en return_appearance
# --------------------------------------------------------------------------- #

class TestRoomAmbiente(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.reloj = _crear_reloj(hora=9)  # mañana

    def tearDown(self):
        if self.reloj and self.reloj.pk:
            self.reloj.delete()
        super().tearDown()

    def test_sala_exterior_muestra_texto_ambiente(self):
        # room1 es exterior por defecto (exterior=True)
        self.room1.db.exterior = True
        text = self.room1.return_appearance(self.char1)
        # Debe contener algo de texto de ambiente
        self.assertTrue(len(text) > 0)

    def test_sala_interior_no_muestra_texto_ambiente(self):
        self.room1.db.exterior = False
        pid, _, _ = periodo_del_dia(9)
        from systems.time.clock import TEXTOS_AMBIENTE
        texto_esperado = TEXTOS_AMBIENTE[pid]["exterior_natural"]
        text = self.room1.return_appearance(self.char1)
        self.assertNotIn(texto_esperado, text)

    def test_tipo_urbano_usa_texto_urbano(self):
        self.room1.db.exterior = True
        self.room1.db.tipo_ambiente = "exterior_urbano"
        pid, _, _ = periodo_del_dia(9)
        from systems.time.clock import TEXTOS_AMBIENTE
        texto_urbano = TEXTOS_AMBIENTE[pid]["exterior_urbano"]
        text = self.room1.return_appearance(self.char1)
        self.assertIn(texto_urbano, text)


# --------------------------------------------------------------------------- #
#  Percepción nocturna
# --------------------------------------------------------------------------- #

class TestPercepcionNocturna(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.npc.NPC", key="NPC Oculto Test")
        self.npc.move_to(self.room1, quiet=True)
        self.npc.db.oculto = True
        self.npc.db.nivel_sigilo = 13  # difícil de detectar
        self.char1.db.inteligencia = 12
        self.char1.db.nivel = 2

    def test_de_dia_puede_detectar(self):
        # mañana → sin penalización → percepción = 12 + 2//2 = 13 >= 13
        self.reloj = _crear_reloj(hora=10)
        from systems.perception.perception_manager import PerceptionManager
        from features.time.clock_script import hora_actual
        pm = PerceptionManager()
        hora = hora_actual()
        self.assertTrue(pm.puede_detectar(self.char1, self.npc, hora=hora))
        self.reloj.delete()

    def test_de_noche_no_puede_detectar(self):
        # noche → -3 → percepción = 12 + 1 - 3 = 10 < 13
        self.reloj = _crear_reloj(hora=22)
        from systems.perception.perception_manager import PerceptionManager
        from features.time.clock_script import hora_actual
        pm = PerceptionManager()
        hora = hora_actual()
        self.assertFalse(pm.puede_detectar(self.char1, self.npc, hora=hora))
        self.reloj.delete()
