"""
tests/test_expeditions.py

Tests de integración Evennia para el sistema de expediciones grupales (v0.51.0).
Cubre: CmdExpedicion._iniciar y la recolección real del grupo (party).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_expeditions
"""
from evennia.utils.test_resources import EvenniaTest

from features.expeditions.commands import CmdExpedicion, _obtener_script_expedicion
from features.party.commands import _añadir_miembro, _crear_partido
from typeclasses.characters import Character


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


def _init_char(char, nivel=5):
    char.db.nivel = nivel
    char.msg = lambda text=None, **kw: None


class TestExpedicionInicioGrupo(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char2.move_to(self.char1.location, quiet=True)

    def tearDown(self):
        script = _obtener_script_expedicion(self.char1)
        if script:
            try:
                script.delete()
            except Exception:
                pass
        super().tearDown()

    def test_lider_real_puede_iniciar_expedicion(self):
        """
        Regresión: db.lider_partido guarda el objeto Character del líder, no
        un dbref. Comparar contra caller.dbref (string) nunca era igual, así
        que el líder legítimo de un grupo real quedaba siempre bloqueado con
        "Solo el líder del grupo puede iniciar una expedición."
        """
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)

        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()

        self.assertTrue(getattr(self.char1.location.db, "es_expedicion", False))
        self.assertEqual(self.char1.location, self.char2.location)

    def test_no_lider_no_puede_iniciar(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)

        _make_cmd(CmdExpedicion, self.char2, "iniciar bosque_profundo").func()

        self.assertFalse(getattr(self.char1.location.db, "es_expedicion", False))
        self.assertFalse(getattr(self.char2.location.db, "es_expedicion", False))

    def test_grupo_por_debajo_del_minimo_no_inicia(self):
        # bosque_profundo requiere miembros_min=2; sin partido, caller va solo.
        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()
        self.assertFalse(getattr(self.char1.location.db, "es_expedicion", False))

    def test_miembro_ausente_es_teletransportado_igualmente(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        self.char2.move_to(self.room1, quiet=True)

        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()

        self.assertEqual(self.char1.location, self.char2.location)
        self.assertTrue(getattr(self.char2.location.db, "es_expedicion", False))

    def test_estado_no_crashea_dentro_de_expedicion(self):
        """
        Regresión: _obtener_script_expedicion() llamaba a
        search_script(dbref, exact=False), kwarg que ScriptDBManager
        no acepta -> TypeError sin capturar. 'expedicion estado' y
        'expedicion abandonar' fallaban siempre para cualquier jugador.
        """
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()

        script = _obtener_script_expedicion(self.char1)
        self.assertIsNotNone(script)

        _make_cmd(CmdExpedicion, self.char1, "estado").func()

    def test_abandonar_no_crashea(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()

        _make_cmd(CmdExpedicion, self.char1, "abandonar").func()
        self.assertFalse(getattr(self.char1.location.db, "es_expedicion", False))
