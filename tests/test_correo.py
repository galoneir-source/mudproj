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

from features.mail.commands import CmdCarta, CmdCorreo, _buscar_obj_inv
from typeclasses.characters import Character
from typeclasses.objects import Equipo, Object


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


class TestBuscarObjInv(TestCorreoBase):
    """
    Regresión: _buscar_obj_inv() hacía coincidencia por substring y
    rechazaba como "ambiguo" en cuanto había 2+ coincidencias parciales,
    sin priorizar una coincidencia exacta — mismo patrón ya corregido en
    banco (609bbea), tienda (98d67ae), grupo (e56b9aa) y equipamiento
    (155cbb3). Un jugador con "daga" y "daga oxidada" en el inventario
    no podía adjuntar la "daga" exacta a una carta.
    """

    def setUp(self):
        super().setUp()
        self.daga = create.create_object(Object, key="daga", location=self.char1)
        self.daga_oxidada = create.create_object(
            Object, key="daga oxidada", location=self.char1
        )

    def test_nombre_exacto_no_es_ambiguo_pese_a_substring_de_otro(self):
        obj, err = _buscar_obj_inv(self.char1, "daga")
        self.assertEqual(obj, self.daga)
        self.assertEqual(err, "")

    def test_nombre_parcial_sin_coincidencia_exacta_sigue_ambiguo(self):
        # Ningún objeto se llama exactamente "daga oxi" — ambigüedad real.
        create.create_object(Object, key="daga oxidada de hierro", location=self.char1)
        obj, err = _buscar_obj_inv(self.char1, "daga oxi")
        self.assertIsNone(obj)
        self.assertIn("ambiguo", err.lower())

    def test_carta_adjuntar_nombre_exacto_funciona_pese_a_ambiguedad_parcial(self):
        """Regresión end-to-end vía el comando real: antes del fix,
        'carta X adjuntar daga = ...' fallaba con 'Nombre ambiguo' pese a
        que 'daga' es exactamente el nombre de un objeto real."""
        _make_cmd(
            CmdCarta, self.char1, f"{self.char2.key} adjuntar daga = hola"
        ).func()

        self.assertIsNone(self.daga.location)
        self.assertEqual(self.daga_oxidada.location, self.char1)
        self.assertEqual(len(self.char2.db.correo), 1)


class TestCmdCorreoLeerYResponder(TestCorreoBase):
    def test_leer_marca_como_leida(self):
        _make_cmd(CmdCarta, self.char1, f"{self.char2.key} = hola").func()
        _make_cmd(CmdCorreo, self.char2, "leer 1").func()

        self.assertTrue(self.char2.db.correo[0]["leida"])

    def test_responder_envia_carta_nueva_al_remitente_original(self):
        _make_cmd(CmdCarta, self.char1, f"{self.char2.key} = hola").func()
        _make_cmd(CmdCorreo, self.char2, "responder 1 = gracias por escribir").func()

        self.assertEqual(len(self.char1.db.correo), 1)
        self.assertIn("gracias por escribir", self.char1.db.correo[0]["mensaje"])


class TestCmdCartaValidaciones(TestCorreoBase):
    def test_no_puede_enviarse_carta_a_si_mismo(self):
        _make_cmd(CmdCarta, self.char1, f"{self.char1.key} = hola").func()

        self.assertEqual(list(self.char1.db.correo or []), [])

    def test_objeto_equipado_no_se_puede_adjuntar(self):
        arma = create.create_object(Equipo, key="espada equipada", location=self.char1)
        arma.db.slot = "arma"
        self.char1.db.equipamiento["arma"] = arma

        _make_cmd(
            CmdCarta, self.char1, f"{self.char2.key} adjuntar espada equipada = toma"
        ).func()

        self.assertEqual(arma.location, self.char1)
        self.assertEqual(list(self.char2.db.correo or []), [])

    def test_monedas_insuficientes_rechaza_el_envio(self):
        self.char1.db.monedas = 10
        _make_cmd(
            CmdCarta, self.char1, f"{self.char2.key} monedas 50 = toma"
        ).func()

        self.assertEqual(self.char1.db.monedas, 10)
        self.assertEqual(list(self.char2.db.correo or []), [])


class TestNotificacionEnLogin(TestCorreoBase):
    def test_at_post_puppet_notifica_correo_no_leido(self):
        """at_post_puppet() envía primero el mensaje base de Evennia
        ("You become Char2.") y luego, si hay correo sin leer, la
        notificación — hay que capturar todos los mensajes, no solo el
        primero."""
        _make_cmd(CmdCarta, self.char1, f"{self.char2.key} = hola").func()

        mensajes = []
        self.char2.msg = lambda text=None, **kw: mensajes.append(text)
        self.char2.at_post_puppet()

        self.assertTrue(any("carta nueva" in str(m).lower() for m in mensajes))
