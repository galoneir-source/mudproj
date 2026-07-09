"""
tests/test_party.py

Tests de integración para el sistema de grupos (party).
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object
from typeclasses.characters import Character
from features.party.commands import (
    CmdInvitar, CmdUnirse, CmdDeclinar, CmdPartido, CmdAbandonar, CmdExpulsar,
    esta_en_partido,
    es_lider,
    get_lider,
    get_miembros,
    _crear_partido,
    _añadir_miembro,
    _quitar_miembro,
    _disolver_partido,
)


def _cmd(CmdClass, caller, args="", target=None):
    """Instancia y ejecuta un comando directamente, sin pasar por el parser."""
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = " " + args if args else ""
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = []
    cmd.lhs = args
    cmd.rhs = ""
    # Inyectar resultado de búsqueda si se indica
    if target is not None:
        original_search = caller.search
        caller.search = lambda q, **kw: target
        try:
            cmd.func()
        finally:
            caller.search = original_search
    else:
        cmd.func()


# --------------------------------------------------------------------------- #
#  Tests de operaciones internas
# --------------------------------------------------------------------------- #

class TestPartyOps(EvenniaTest):
    character_typeclass = Character

    def test_nuevo_personaje_sin_partido(self):
        self.assertFalse(esta_en_partido(self.char1))
        self.assertFalse(esta_en_partido(self.char2))

    def test_get_miembros_sin_partido(self):
        self.assertEqual(get_miembros(self.char1), [])

    def test_crear_partido(self):
        _crear_partido(self.char1)
        self.assertTrue(esta_en_partido(self.char1))
        self.assertTrue(es_lider(self.char1))
        self.assertEqual(get_lider(self.char1), self.char1)

    def test_lider_es_miembro_del_partido(self):
        _crear_partido(self.char1)
        self.assertIn(self.char1, get_miembros(self.char1))

    def test_añadir_miembro(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        miembros = get_miembros(self.char1)
        self.assertIn(self.char1, miembros)
        self.assertIn(self.char2, miembros)
        self.assertEqual(len(miembros), 2)

    def test_miembro_conoce_a_su_lider(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        self.assertEqual(get_lider(self.char2), self.char1)
        self.assertTrue(esta_en_partido(self.char2))

    def test_miembro_no_es_lider(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        self.assertFalse(es_lider(self.char2))

    def test_quitar_miembro_disuelve_partido_pequeno(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        restantes = _quitar_miembro(self.char2)
        self.assertEqual(restantes, [])
        self.assertFalse(esta_en_partido(self.char1))
        self.assertFalse(esta_en_partido(self.char2))

    def test_quitar_miembro_no_lider_en_partido_grande(self):
        char3 = create_object(Character, key="Char3_test")
        try:
            _crear_partido(self.char1)
            _añadir_miembro(self.char1, self.char2)
            _añadir_miembro(self.char1, char3)
            restantes = _quitar_miembro(self.char2)
            self.assertNotIn(self.char2, restantes)
            self.assertIn(self.char1, restantes)
            self.assertIn(char3, restantes)
            self.assertFalse(esta_en_partido(self.char2))
            self.assertTrue(esta_en_partido(self.char1))
        finally:
            char3.delete()

    def test_quitar_lider_transfiere_liderazgo(self):
        char3 = create_object(Character, key="Char3_lider")
        try:
            _crear_partido(self.char1)
            _añadir_miembro(self.char1, self.char2)
            _añadir_miembro(self.char1, char3)
            _quitar_miembro(self.char1)
            self.assertFalse(esta_en_partido(self.char1))
            self.assertTrue(esta_en_partido(self.char2))
            self.assertTrue(es_lider(self.char2))
            self.assertEqual(get_lider(char3), self.char2)
        finally:
            char3.delete()

    def test_disolver_partido(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _disolver_partido(self.char1)
        self.assertFalse(esta_en_partido(self.char1))
        self.assertFalse(esta_en_partido(self.char2))

    def test_quitar_miembro_sin_partido_no_falla(self):
        self.assertEqual(_quitar_miembro(self.char1), [])

    def test_invitacion_inicializada_en_none(self):
        self.assertIsNone(getattr(self.char1.db, "invitacion_partido", None))

    def test_lider_partido_inicializado_en_none(self):
        self.assertIsNone(getattr(self.char1.db, "lider_partido", None))

    def test_miembros_partido_inicializado_vacio(self):
        self.assertEqual(getattr(self.char1.db, "miembros_partido", []), [])


# --------------------------------------------------------------------------- #
#  Tests de comandos (usando _cmd para evitar el parser de Evennia)
# --------------------------------------------------------------------------- #

class TestPartyCmds(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.char2.move_to(self.char1.location, quiet=True)
        # Silenciar msg para que los tests no dependan de mensajes exactos
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None

    def test_invitar_crea_partido(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        self.assertTrue(esta_en_partido(self.char1))
        self.assertIsNotNone(getattr(self.char2.db, "invitacion_partido", None))

    def test_unirse_añade_al_partido(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdUnirse, self.char2)
        self.assertTrue(esta_en_partido(self.char2))
        self.assertIn(self.char2, get_miembros(self.char1))

    def test_unirse_limpia_invitacion(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdUnirse, self.char2)
        self.assertIsNone(getattr(self.char2.db, "invitacion_partido", None))

    def test_declinar_limpia_invitacion(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdDeclinar, self.char2)
        self.assertIsNone(getattr(self.char2.db, "invitacion_partido", None))

    def test_declinar_no_crea_partido(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdDeclinar, self.char2)
        # char1 creó partido al invitar pero char2 no se unió
        self.assertTrue(esta_en_partido(self.char1))
        self.assertFalse(esta_en_partido(self.char2))

    def test_partido_sin_grupo_no_falla(self):
        _cmd(CmdPartido, self.char1)

    def test_partido_con_grupo(self):
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)
        _cmd(CmdPartido, self.char1)

    def test_abandonar_sin_grupo_no_falla(self):
        _cmd(CmdAbandonar, self.char1)

    def test_abandonar_disuelve_partido_pequeno(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdUnirse, self.char2)
        _cmd(CmdAbandonar, self.char2)
        self.assertFalse(esta_en_partido(self.char1))
        self.assertFalse(esta_en_partido(self.char2))

    def test_abandonar_como_lider_transfiere(self):
        char3 = create_object(Character, key="Char3_cmd")
        char3.msg = lambda text=None, **kw: None
        try:
            # Partido de 3 vía helpers para no depender de has_account en char3
            _crear_partido(self.char1)
            _añadir_miembro(self.char1, self.char2)
            _añadir_miembro(self.char1, char3)
            _cmd(CmdAbandonar, self.char1)
            self.assertFalse(esta_en_partido(self.char1))
            self.assertTrue(es_lider(self.char2))
            self.assertTrue(esta_en_partido(char3))
        finally:
            char3.delete()

    def test_expulsar_sin_ser_lider_falla(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdUnirse, self.char2)
        # char2 intenta expulsar al líder → debe fallar
        _cmd(CmdExpulsar, self.char2, self.char1.key)
        self.assertTrue(esta_en_partido(self.char1))
        self.assertTrue(esta_en_partido(self.char2))

    def test_expulsar_por_lider(self):
        char3 = create_object(Character, key="Char3_exp")
        char3.msg = lambda text=None, **kw: None
        try:
            # Partido de 3 vía helpers para no depender de has_account en char3
            _crear_partido(self.char1)
            _añadir_miembro(self.char1, self.char2)
            _añadir_miembro(self.char1, char3)
            _cmd(CmdExpulsar, self.char1, self.char2.key)
            self.assertFalse(esta_en_partido(self.char2))
            self.assertTrue(esta_en_partido(self.char1))
            self.assertTrue(esta_en_partido(char3))
        finally:
            char3.delete()

    def test_unirse_sin_invitacion_no_falla(self):
        _cmd(CmdUnirse, self.char1)
        self.assertFalse(esta_en_partido(self.char1))

    def test_declinar_sin_invitacion_no_falla(self):
        _cmd(CmdDeclinar, self.char1)

    def test_segundo_invite_al_mismo_no_duplica(self):
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        _cmd(CmdUnirse, self.char2)
        # char2 ya está en el partido → invitarlo de nuevo debe fallar
        _cmd(CmdInvitar, self.char1, self.char2.key, target=self.char2)
        self.assertEqual(len(get_miembros(self.char1)), 2)
