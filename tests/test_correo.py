"""
tests/test_correo.py

Tests de integración Evennia para el sistema de correo entre jugadores
(v0.40.0). Cubre: envío con adjuntos, lectura, reclamar, doble reclamo,
borrar sin reclamar (devolución al remitente), buzón lleno.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_correo
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from features.mail.commands import CmdCarta, CmdCorreo
from typeclasses.characters import Character
from typeclasses.objects import Object


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


class TestCorreoBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char1.db.monedas = 100
        self.char2.db.monedas = 0
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None
        self.espada = create.create_object(Object, key="espada de prueba", location=self.char1)


class TestEnviarYReclamar(TestCorreoBase):
    def test_enviar_con_adjunto_no_crashea_y_transfiere(self):
        """
        Regresión: _buscar_destinatario() llamaba a search_object(nombre,
        typeclass=..., quiet=True) — 'quiet' no es un kwarg válido de
        ObjectDBManager.search_object() -> TypeError sin capturar en cada
        intento de enviar una carta. El sistema de correo no ha podido
        enviar ni una sola carta desde que se escribió.
        """
        _make_cmd(
            CmdCarta, self.char1,
            f"{self.char2.key} adjuntar espada de prueba monedas 30 = hola",
        ).func()

        self.assertIsNone(self.espada.location)
        self.assertEqual(self.char1.db.monedas, 70)
        self.assertEqual(len(self.char2.db.correo), 1)

    def test_reclamar_transfiere_adjunto_al_destinatario(self):
        _make_cmd(
            CmdCarta, self.char1,
            f"{self.char2.key} adjuntar espada de prueba monedas 30 = hola",
        ).func()
        _make_cmd(CmdCorreo, self.char2, "reclamar 1").func()

        self.assertEqual(self.espada.location, self.char2)
        self.assertEqual(self.char2.db.monedas, 30)

    def test_no_se_puede_reclamar_dos_veces(self):
        _make_cmd(
            CmdCarta, self.char1,
            f"{self.char2.key} adjuntar espada de prueba monedas 30 = hola",
        ).func()
        _make_cmd(CmdCorreo, self.char2, "reclamar 1").func()
        _make_cmd(CmdCorreo, self.char2, "reclamar 1").func()

        self.assertEqual(self.char2.db.monedas, 30)


class TestBorrarSinReclamar(TestCorreoBase):
    def test_borrar_sin_reclamar_devuelve_al_remitente(self):
        _make_cmd(
            CmdCarta, self.char1,
            f"{self.char2.key} adjuntar espada de prueba monedas 30 = hola",
        ).func()
        _make_cmd(CmdCorreo, self.char2, "borrar 1").func()

        self.assertEqual(self.espada.location, self.char1)
        self.assertEqual(self.char1.db.monedas, 100)

    def test_borrar_tras_reclamar_no_duplica(self):
        _make_cmd(
            CmdCarta, self.char1,
            f"{self.char2.key} adjuntar espada de prueba monedas 30 = hola",
        ).func()
        _make_cmd(CmdCorreo, self.char2, "reclamar 1").func()
        _make_cmd(CmdCorreo, self.char2, "borrar 1").func()

        self.assertEqual(self.espada.location, self.char2)
        self.assertEqual(self.char1.db.monedas, 70)
        self.assertEqual(self.char2.db.monedas, 30)


class TestBuzonLleno(TestCorreoBase):
    def test_buzon_lleno_rechaza_nuevas_cartas(self):
        for i in range(20):
            _make_cmd(CmdCarta, self.char1, f"{self.char2.key} = msg {i}").func()
        _make_cmd(CmdCarta, self.char1, f"{self.char2.key} = una carta de más").func()

        self.assertEqual(len(self.char2.db.correo), 20)
