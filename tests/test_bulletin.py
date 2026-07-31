"""
tests/test_bulletin.py

Tests de integración Evennia para la cartelera de anuncios global:
BulletinScript (publicar, retirar, expiración) y CmdCartelera.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_bulletin
"""
from evennia import create_script
from evennia.utils.test_resources import EvenniaTest

from features.bulletin.commands import CmdCartelera
from features.bulletin.bulletin_script import BulletinScript
from systems.bulletin.bulletin import MAX_ANUNCIOS, MAX_LONGITUD_TEXTO


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
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def all(self):
        return "\n".join(self.msgs)


def _crear_script():
    return create_script(BulletinScript, key="cartelera_global", persistent=True)


# --------------------------------------------------------------------------- #
#  BulletinScript — publicar
# --------------------------------------------------------------------------- #

class TestBulletinScriptPublicar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_publicar_devuelve_true(self):
        ok, _ = self.script.publicar(self.char1, "Se vende espada")
        self.assertTrue(ok)

    def test_anuncio_aparece_en_obtener(self):
        self.script.publicar(self.char1, "Se vende espada")
        anuncios = self.script.obtener_anuncios()
        self.assertEqual(len(anuncios), 1)
        self.assertEqual(anuncios[0]["texto"], "Se vende espada")

    def test_anuncio_guarda_autor(self):
        self.script.publicar(self.char1, "Hola")
        anuncios = self.script.obtener_anuncios()
        self.assertEqual(anuncios[0]["autor"], self.char1.key)
        self.assertEqual(anuncios[0]["autor_dbref"], self.char1.dbref)

    def test_texto_vacio_falla(self):
        ok, msg = self.script.publicar(self.char1, "   ")
        self.assertFalse(ok)
        self.assertIn("vacío", msg.lower())

    def test_texto_demasiado_largo_falla(self):
        ok, msg = self.script.publicar(self.char1, "x" * (MAX_LONGITUD_TEXTO + 1))
        self.assertFalse(ok)
        self.assertIn("largo", msg.lower())

    def test_tablon_lleno_bloquea_publicacion(self):
        for i in range(MAX_ANUNCIOS):
            self.script.publicar(self.char1, f"Anuncio {i}")
        ok, msg = self.script.publicar(self.char1, "Uno de más")
        self.assertFalse(ok)
        self.assertIn("llena", msg.lower())


# --------------------------------------------------------------------------- #
#  BulletinScript — retirar
# --------------------------------------------------------------------------- #

class TestBulletinScriptRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.script.publicar(self.char1, "Anuncio de char1")
        self.anuncio_id = self.script.obtener_anuncios()[0]["id"]

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_autor_puede_retirar(self):
        ok, _ = self.script.retirar(self.anuncio_id, self.char1)
        self.assertTrue(ok)
        self.assertEqual(self.script.obtener_anuncios(), [])

    def test_otro_jugador_no_puede_retirar(self):
        ok, msg = self.script.retirar(self.anuncio_id, self.char2)
        self.assertFalse(ok)
        self.assertIn("autor", msg.lower())
        self.assertEqual(len(self.script.obtener_anuncios()), 1)

    def test_id_inexistente_falla(self):
        ok, msg = self.script.retirar("id_que_no_existe", self.char1)
        self.assertFalse(ok)
        self.assertTrue(msg)


# --------------------------------------------------------------------------- #
#  BulletinScript — expiración
# --------------------------------------------------------------------------- #

class TestBulletinScriptExpiracion(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_anuncio_expirado_no_aparece(self):
        from systems.bulletin.bulletin import DURACION_SEGUNDOS
        self.script.publicar(self.char1, "Viejo anuncio")
        anuncios_crudos = list(self.script.db.anuncios)
        anuncios_crudos[0]["timestamp"] -= DURACION_SEGUNDOS + 10
        self.script.db.anuncios = anuncios_crudos

        self.assertEqual(self.script.obtener_anuncios(), [])

    def test_anuncio_expirado_libera_espacio(self):
        from systems.bulletin.bulletin import DURACION_SEGUNDOS
        for i in range(MAX_ANUNCIOS):
            self.script.publicar(self.char1, f"Anuncio {i}")
        anuncios_crudos = list(self.script.db.anuncios)
        anuncios_crudos[0]["timestamp"] -= DURACION_SEGUNDOS + 10
        self.script.db.anuncios = anuncios_crudos

        ok, _ = self.script.publicar(self.char1, "Ahora sí cabe")
        self.assertTrue(ok)


# --------------------------------------------------------------------------- #
#  CmdCartelera — sin argumentos (listar)
# --------------------------------------------------------------------------- #

class TestCmdCarteleraListar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_cartelera_vacia_muestra_mensaje(self):
        _make_cmd(CmdCartelera, self.char1, "").func()
        self.assertIn("no hay anuncios", self.cap.all().lower())

    def test_cartelera_con_anuncio_muestra_texto_y_autor(self):
        self.script.publicar(self.char1, "Se busca herrero")
        _make_cmd(CmdCartelera, self.char1, "").func()
        texto = self.cap.all()
        self.assertIn("Se busca herrero", texto)
        self.assertIn(self.char1.key, texto)


# --------------------------------------------------------------------------- #
#  CmdCartelera — publicar
# --------------------------------------------------------------------------- #

class TestCmdCarteleraPublicar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_publicar_exitoso(self):
        _make_cmd(CmdCartelera, self.char1, "publicar Se vende armadura").func()
        self.assertIn("publicado", self.cap.all().lower())
        self.assertEqual(len(self.script.obtener_anuncios()), 1)

    def test_publicar_sin_texto_muestra_uso(self):
        _make_cmd(CmdCartelera, self.char1, "publicar").func()
        self.assertIn("uso", self.cap.all().lower())

    def test_publicar_demasiado_largo_falla(self):
        _make_cmd(CmdCartelera, self.char1, "publicar " + "x" * (MAX_LONGITUD_TEXTO + 1)).func()
        self.assertIn("largo", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdCartelera — retirar
# --------------------------------------------------------------------------- #

class TestCmdCarteleraRetirar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script()
        self.script.publicar(self.char1, "Anuncio de char1")
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_retirar_exitoso(self):
        _make_cmd(CmdCartelera, self.char1, "retirar 1").func()
        self.assertIn("retirado", self.cap1.all().lower())
        self.assertEqual(self.script.obtener_anuncios(), [])

    def test_otro_jugador_no_puede_retirar(self):
        _make_cmd(CmdCartelera, self.char2, "retirar 1").func()
        self.assertIn("autor", self.cap2.all().lower())
        self.assertEqual(len(self.script.obtener_anuncios()), 1)

    def test_indice_fuera_de_rango_muestra_uso(self):
        _make_cmd(CmdCartelera, self.char1, "retirar 99").func()
        self.assertIn("uso", self.cap1.all().lower())

    def test_indice_no_numerico_muestra_uso(self):
        _make_cmd(CmdCartelera, self.char1, "retirar abc").func()
        self.assertIn("uso", self.cap1.all().lower())
