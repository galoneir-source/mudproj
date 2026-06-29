"""
tests/test_rangos.py

Tests de integración Evennia para el sistema de rangos de aventurero (v0.36.0).
Cubre: puntuación desde atributos db, subida de rango, comando rango, perfil.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_rangos
"""
from evennia.utils.test_resources import EvenniaTest

from features.ranks.commands import CmdRango, verificar_subida_rango
from commands.general_commands import CmdPerfil
from systems.ranks.ranks import calcular_puntuacion, rango_actual


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
        char.msg = lambda m, **kw: self.msgs.append(str(m))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


def _init_char(char):
    char.db.nivel = 1
    char.db.experiencia = 0
    char.db.quests = {}
    char.db.logros = []
    char.db.kills_totales = 0
    char.db.rango = "aprendiz"
    char.db.clase = None
    char.db.titulo_activo = None


# ---------------------------------------------------------------------------
# verificar_subida_rango
# ---------------------------------------------------------------------------

class TestVerificarSubidaRango(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def test_sin_cambio_no_notifica(self):
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        assert cap.msgs == []

    def test_subida_a_novicio(self):
        # 50 kills → 50 pts → Novicio
        self.char1.db.kills_totales = 50
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        assert "Novicio" in cap.all()
        assert self.char1.db.rango == "novicio"

    def test_subida_a_veterano(self):
        # nivel 5 (60) + 10 quests entregadas (100) + 5 logros (100) + 50 kills (50) = 310
        self.char1.db.nivel = 5
        self.char1.db.quests = {f"q{i}": {"estado": "entregada"} for i in range(10)}
        self.char1.db.logros = [f"l{i}" for i in range(5)]
        self.char1.db.kills_totales = 50
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        assert "Veterano" in cap.all()
        assert self.char1.db.rango == "veterano"

    def test_rango_se_persiste(self):
        self.char1.db.kills_totales = 50
        verificar_subida_rango(self.char1)
        assert self.char1.db.rango == "novicio"
        # segunda llamada: no hay nueva notificación
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        assert cap.msgs == []

    def test_rango_no_baja(self):
        self.char1.db.rango = "veterano"
        self.char1.db.kills_totales = 0  # puntuación 0 → Aprendiz calculado
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        # No notifica ni cambia a un rango inferior
        assert self.char1.db.rango == "veterano"
        assert cap.msgs == []

    def test_quests_activas_no_cuentan(self):
        self.char1.db.quests = {
            "q1": {"estado": "activa"},
            "q2": {"estado": "completada"},
            "q3": {"estado": "entregada"},
        }
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        # Solo 1 entregada → 10 pts → sigue Aprendiz
        assert cap.msgs == []
        assert self.char1.db.rango == "aprendiz"

    def test_subida_multiples_rangos_en_un_paso(self):
        # Dar puntuación que supera varios umbrales a la vez
        self.char1.db.nivel = 10
        self.char1.db.kills_totales = 700
        cap = _MsgCapture(self.char1)
        verificar_subida_rango(self.char1)
        # 135 + 700 = 835 → Héroe (700)
        assert "Héroe" in cap.all()
        assert self.char1.db.rango == "heroe"


# ---------------------------------------------------------------------------
# CmdRango
# ---------------------------------------------------------------------------

class TestCmdRango(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def _run(self, args=""):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdRango, self.char1, args)
        cmd.func()
        return cap.all()

    def test_muestra_aprendiz_inicial(self):
        salida = self._run()
        assert "Aprendiz" in salida

    def test_muestra_puntuacion(self):
        salida = self._run()
        assert "Puntuación total" in salida

    def test_muestra_desglose(self):
        salida = self._run()
        assert "Nivel" in salida
        assert "Misiones" in salida
        assert "Logros" in salida
        assert "Combate" in salida

    def test_muestra_siguiente_rango(self):
        salida = self._run()
        assert "Novicio" in salida

    def test_muestra_leyenda_maximo(self):
        self.char1.db.kills_totales = 10000
        self.char1.db.rango = "leyenda"
        salida = self._run()
        assert "máximo" in salida or "Leyenda" in salida

    def test_puntuacion_refleja_nivel(self):
        self.char1.db.nivel = 5
        salida = self._run()
        # nivel 5 → 60 pts
        assert "60" in salida

    def test_puntuacion_refleja_kills(self):
        self.char1.db.kills_totales = 200
        salida = self._run()
        assert "200" in salida

    def test_puntuacion_refleja_quests(self):
        self.char1.db.quests = {f"q{i}": {"estado": "entregada"} for i in range(7)}
        salida = self._run()
        # 7 quests × 10 = 70 pts
        assert "70" in salida

    def test_puntuacion_refleja_logros(self):
        self.char1.db.logros = ["l1", "l2", "l3"]
        salida = self._run()
        # 3 logros × 20 = 60 pts
        assert "60" in salida


# ---------------------------------------------------------------------------
# CmdPerfil muestra el rango
# ---------------------------------------------------------------------------

class TestPerfilMuestraRango(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)

    def test_perfil_muestra_rango_aprendiz(self):
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdPerfil, self.char1)
        cmd.func()
        assert "Rango" in cap.all()
        assert "Aprendiz" in cap.all()

    def test_perfil_muestra_rango_veterano(self):
        self.char1.db.rango = "veterano"
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdPerfil, self.char1)
        cmd.func()
        assert "Veterano" in cap.all()

    def test_perfil_muestra_rango_heroe(self):
        self.char1.db.rango = "heroe"
        cap = _MsgCapture(self.char1)
        cmd = _make_cmd(CmdPerfil, self.char1)
        cmd.func()
        assert "Héroe" in cap.all()
