"""
tests/test_records.py

Tests de integración Evennia para el sistema de récords globales (v0.23.0).
Cubre: RecordsScript (caché y actualización), CmdRecords (global, personal, categoría).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_records
"""
from evennia import create_script
from evennia.utils.test_resources import EvenniaTest

from features.records.commands import CmdRecords
from features.records.records_script import RecordsScript
from systems.records.records import CAT_IDS, CATEGORIAS


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


def _init_char(char, kills=0, quests=None, jefes=None, duelos=0, crafteo=0, nivel=5):
    char.db.nivel = nivel
    char.db.kills_totales = kills
    char.db.quests = quests if quests is not None else {}
    char.db.jefes_derrotados = jefes if jefes is not None else []
    char.db.duelos_ganados = duelos
    char.db.objetos_crafteados = crafteo
    char.db.gremio = None
    char.db.titulo_activo = None


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def all(self):
        return "\n".join(self.msgs)


def _crear_script():
    return create_script(RecordsScript, key="records_global", persistent=True)


# ---------------------------------------------------------------------------
# RecordsScript: caché y actualización
# ---------------------------------------------------------------------------

class TestRecordsScript(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, kills=100, duelos=5)
        _init_char(self.char2, kills=50, duelos=10)
        self.script = _crear_script()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_script_se_crea_con_clave(self):
        self.assertEqual(self.script.key, "records_global")

    def test_cache_se_inicializa_como_dict(self):
        cache = dict(self.script.db.cache or {})
        self.assertIsInstance(cache, dict)

    def test_actualizar_rellena_cache(self):
        self.script.actualizar()
        cache = dict(self.script.db.cache or {})
        self.assertIn("kills", cache)

    def test_actualizar_incluye_char_con_kills(self):
        self.script.actualizar()
        top = self.script.get_top("kills")
        nombres = [n for n, _ in top]
        self.assertIn(self.char1.key, nombres)

    def test_top_kills_ordenado_desc(self):
        self.script.actualizar()
        top = self.script.get_top("kills")
        if len(top) >= 2:
            self.assertGreaterEqual(top[0][1], top[1][1])

    def test_get_top_cat_desconocida_vacia(self):
        self.script.actualizar()
        top = self.script.get_top("xyz")
        self.assertEqual(top, [])

    def test_ultimo_actualizado_se_registra(self):
        self.script.actualizar()
        ts = self.script.db.ultimo_actualizado or 0
        self.assertGreater(ts, 0)

    def test_actualizar_cuenta_misiones_entregadas(self):
        self.char1.db.quests = {
            "q1": {"estado": "entregada"},
            "q2": {"estado": "activa"},
            "q3": {"estado": "entregada"},
        }
        self.script.actualizar()
        top = self.script.get_top("misiones")
        # char1 debe tener 2 misiones entregadas
        entry = next((v for n, v in top if n == self.char1.key), None)
        self.assertEqual(entry, 2)

    def test_actualizar_cuenta_jefes(self):
        self.char2.db.jefes_derrotados = ["JEFE_A", "JEFE_B"]
        self.script.actualizar()
        top = self.script.get_top("jefes")
        entry = next((v for n, v in top if n == self.char2.key), None)
        self.assertEqual(entry, 2)


# ---------------------------------------------------------------------------
# CmdRecords — vista global
# ---------------------------------------------------------------------------

class TestCmdRecordsGlobal(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, kills=200)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        self.script = _crear_script()
        self.script.actualizar()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_records_sin_args_muestra_todas_categorias(self):
        cmd = _make_cmd(CmdRecords, self.char1, "")
        cmd.func()
        texto = self.cap.all()
        for cat_id in CAT_IDS:
            cat = CATEGORIAS[cat_id]
            self.assertIn(cat["titulo"], texto, f"Falta categoría: {cat_id}")

    def test_records_muestra_jugador_con_kills(self):
        cmd = _make_cmd(CmdRecords, self.char1, "")
        cmd.func()
        self.assertIn(self.char1.key, self.cap.all())

    def test_records_sin_script_no_falla(self):
        self.script.delete()
        cmd = _make_cmd(CmdRecords, self.char1, "")
        # No debe lanzar excepción
        try:
            cmd.func()
        except Exception as e:
            self.fail(f"CmdRecords lanzó excepción sin script: {e}")
        self.script = None  # ya borrado


# ---------------------------------------------------------------------------
# CmdRecords — vista personal
# ---------------------------------------------------------------------------

class TestCmdRecordsPersonal(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(
            self.char1,
            kills=42,
            quests={"q1": {"estado": "entregada"}, "q2": {"estado": "activa"}},
            jefes=["J1", "J2"],
            duelos=7,
            crafteo=13,
            nivel=8,
        )
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _personal(self):
        cmd = _make_cmd(CmdRecords, self.char1, "personal")
        cmd.func()

    def test_muestra_nombre_personaje(self):
        self._personal()
        self.assertIn(self.char1.key.upper(), self.cap.all())

    def test_muestra_kills(self):
        self._personal()
        self.assertIn("42", self.cap.all())

    def test_muestra_misiones_entregadas(self):
        self._personal()
        self.assertIn("1", self.cap.all())  # solo 1 entregada

    def test_muestra_jefes(self):
        self._personal()
        self.assertIn("2", self.cap.all())

    def test_muestra_duelos(self):
        self._personal()
        self.assertIn("7", self.cap.all())

    def test_muestra_crafteo(self):
        self._personal()
        self.assertIn("13", self.cap.all())

    def test_muestra_nivel(self):
        self._personal()
        self.assertIn("8", self.cap.all())

    def test_muestra_gremio_si_existe(self):
        self.char1.db.gremio = "Guardianes"
        self._personal()
        self.assertIn("Guardianes", self.cap.all())


# ---------------------------------------------------------------------------
# CmdRecords — vista por categoría
# ---------------------------------------------------------------------------

class TestCmdRecordsCategoria(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, kills=999)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        self.script = _crear_script()
        self.script.actualizar()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_records_categoria_kills(self):
        cmd = _make_cmd(CmdRecords, self.char1, "kills")
        cmd.func()
        texto = self.cap.all()
        self.assertIn("Guerrero", texto)
        self.assertIn(self.char1.key, texto)

    def test_records_categoria_duelos(self):
        cmd = _make_cmd(CmdRecords, self.char1, "duelos")
        cmd.func()
        self.assertIn("Duelista", self.cap.all())

    def test_records_categoria_invalida(self):
        cmd = _make_cmd(CmdRecords, self.char1, "magia")
        cmd.func()
        self.assertIn("no reconocida", self.cap.all().lower())


if __name__ == "__main__":
    import unittest
    unittest.main()
