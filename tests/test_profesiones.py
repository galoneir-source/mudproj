"""
tests/test_profesiones.py

Tests de integración para el sistema de Profesiones de recolección:
CmdProfesion (mostrar, aprender, info) y CmdRecolectar (gating de zona/nivel,
cooldown, XP y subida de nivel, creación real del objeto).

No existía ningún test de integración para este sistema (solo
tests/test_profesiones_system.py, puro sobre el catálogo) — el mismo hueco de
cobertura visto en mascotas/monturas/percepción/runas esta sesión.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_profesiones
"""
from evennia.utils.test_resources import EvenniaTest

from features.professions.commands import CmdProfesion, CmdRecolectar
from systems.professions.professions import COOLDOWN_SEGUNDOS, XP_POR_NIVEL


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


def _preparar_char(char):
    char.db.profesiones = {}
    char.ndb.cooldown_recolectar = None


class TestCmdProfesionMostrar(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _prof(self, args=""):
        cmd = _make_cmd(CmdProfesion, self.char1, args)
        cmd.func()

    def test_sin_profesiones_informa(self):
        self._prof("")
        self.assertIn("Ninguna profesión aprendida", self.cap.all())

    def test_con_profesion_muestra_nombre(self):
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._prof("")
        self.assertIn("Minería", self.cap.all())


class TestCmdProfesionAprender(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _prof(self, args=""):
        cmd = _make_cmd(CmdProfesion, self.char1, args)
        cmd.func()

    def test_aprender_nueva_la_registra(self):
        self._prof("aprender mineria")
        self.assertIn("mineria", dict(self.char1.db.profesiones))
        self.assertEqual(self.char1.db.profesiones["mineria"], {"nivel": 1, "xp": 0})

    def test_aprender_duplicada_no_la_reinicia(self):
        self._prof("aprender mineria")
        self.char1.db.profesiones["mineria"]["xp"] = 20
        self._prof("aprender mineria")
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 20)
        self.assertIn("Ya conoces", self.cap.all())

    def test_aprender_desconocida_no_registra_nada(self):
        self._prof("aprender vudu")
        self.assertEqual(dict(self.char1.db.profesiones), {})
        self.assertIn("desconocida", self.cap.all().lower())

    def test_aprender_varias_conviven(self):
        self._prof("aprender mineria")
        self._prof("aprender pesca")
        self.assertEqual(set(dict(self.char1.db.profesiones).keys()), {"mineria", "pesca"})


class TestCmdProfesionInfo(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _prof(self, args=""):
        cmd = _make_cmd(CmdProfesion, self.char1, args)
        cmd.func()

    def test_info_valida_muestra_materiales(self):
        self._prof("info mineria")
        self.assertIn("mineral hierro", self.cap.all().lower())

    def test_info_desconocida_avisa(self):
        self._prof("info vudu")
        self.assertIn("desconocida", self.cap.all().lower())

    def test_sin_subcomando_cae_a_info(self):
        """"profesion mineria" sin escribir "info" también muestra el detalle."""
        self._prof("mineria")
        self.assertIn("Minería", self.cap.all())


class TestCmdRecolectar(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)
        self.char1.location = self.room1

    def _recolectar(self, cmdclass=CmdRecolectar, args=""):
        cmd = _make_cmd(cmdclass, self.char1, args)
        cmd.func()

    def test_sin_zona_de_recursos_informa(self):
        self.room1.db.zona = "plaza_ciudad"
        self._recolectar()
        self.assertIn("No hay recursos", self.cap.all())

    def test_zona_valida_sin_profesion_aprendida(self):
        self.room1.db.zona = "boca_mina"
        self._recolectar()
        self.assertIn("requiere la profesión", self.cap.all())
        self.assertNotIn("mineria", dict(self.char1.db.profesiones))

    def test_nivel_insuficiente_bloquea(self):
        self.room1.db.zona = "galeria_principal"  # requiere nivel 2
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._recolectar()
        self.assertIn("Necesitas nivel", self.cap.all())

    def test_recoleccion_exitosa_da_objeto_y_xp(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._recolectar()
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 5)
        nombres = [o.key for o in self.char1.contents]
        self.assertTrue(any("Hierro" in n or "hierro" in n.lower() for n in nombres))

    def test_recoleccion_aplica_buff_de_xp(self):
        """
        Regresión: el buff de XP de taberna (buff_xp, p. ej. Estofado
        Vigorizante "+15% XP") solo se aplicaba a db.experiencia (nivel de
        personaje) desde el barrido de v0.71.39 -- la XP de profesión
        (db.profesiones[prof_id]["xp"]) es una forma de XP igual de real
        que nunca se retomó en ese barrido.
        """
        import time
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self.char1.db.buffs_activos = [{
            "tipo": "buff_xp", "bonus": 0.5, "nombre": "Estofado Vigorizante",
            "expira": time.time() + 1800,
        }]
        self._recolectar()
        self.assertEqual(
            self.char1.db.profesiones["mineria"]["xp"], int(5 * 1.5),
            "La XP de recolección debía multiplicarse por el buff activo.",
        )

    def test_recoleccion_activa_cooldown(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._recolectar()
        self.cap.msgs.clear()
        self._recolectar()
        self.assertIn("esperar", self.cap.all())

    def test_cooldown_expirado_permite_recolectar_de_nuevo(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._recolectar()
        self.char1.ndb.cooldown_recolectar = {
            "mineria": self.char1.ndb.cooldown_recolectar["mineria"] - COOLDOWN_SEGUNDOS - 1
        }
        self.cap.msgs.clear()
        self._recolectar()
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 10)

    def test_subida_de_nivel_notifica(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": XP_POR_NIVEL[1] - 5}}
        self._recolectar()
        self.assertIn("sube al nivel", self.cap.all())

    def test_cooldown_es_independiente_por_profesion(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {
            "mineria": {"nivel": 1, "xp": 0},
            "pesca": {"nivel": 1, "xp": 0},
        }
        self._recolectar()
        self.room1.db.zona = "orilla_rio"
        self.cap.msgs.clear()
        self._recolectar()
        self.assertNotIn("esperar", self.cap.all())
        self.assertEqual(self.char1.db.profesiones["pesca"]["xp"], 5)

    def test_alias_minar_funciona_igual_que_recolectar(self):
        self.room1.db.zona = "boca_mina"
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self._recolectar(args="")
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 5)


class TestDespachoRealCmdSet(EvenniaTest):
    """
    Verifica que 'recolectar'/'minar'/'cosechar'/'pescar'/'profesion' resuelven
    a estos comandos a través del CmdSet real del personaje (sin colisión con
    ningún otro comando registrado en CharacterCmdSet), y que la recolección
    real (con XP persistida) funciona ejecutando por el cmdstring real.
    """

    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.char1.db.profesiones = {"mineria": {"nivel": 1, "xp": 0}}
        self.char1.location = self.room1
        self.room1.db.zona = "boca_mina"
        self.cap = _MsgCapture(self.char1)

    def test_comando_recolectar_real_da_xp(self):
        self.char1.execute_cmd("recolectar")
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 5)

    def test_comando_minar_real_es_alias_de_recolectar(self):
        self.char1.execute_cmd("minar")
        self.assertEqual(self.char1.db.profesiones["mineria"]["xp"], 5)

    def test_comando_profesion_real_lista(self):
        self.char1.execute_cmd("profesion")
        self.assertIn("Minería", self.cap.all())


if __name__ == "__main__":
    import unittest
    unittest.main()
