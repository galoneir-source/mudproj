"""
tests/test_gremios_system.py

Tests de integración Evennia para el sistema de gremios (v0.22.0).
Cubre: crear, invitar, aceptar/rechazar, salir, expulsar, promover,
degradar, banco del gremio y disolución.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_gremios_system
"""
import time

from evennia import create_script
from evennia.utils.test_resources import EvenniaTest

from features.guilds.commands import (
    CmdAceptarGremio,
    CmdBancoGremio,
    CmdCrearGremio,
    CmdDegrading,
    CmdDisolver,
    CmdExpulsar,
    CmdGremio,
    CmdInvitar,
    CmdPromover,
    CmdRechazarGremio,
    CmdSalirGremio,
)
from features.guilds.guild_script import GuildScript, obtener_gremio_de
from systems.guilds.guilds import (
    COSTE_CREAR_GREMIO,
    RANGO_LIDER,
    RANGO_MIEMBRO,
    RANGO_OFICIAL,
    normalizar_nombre,
)


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


def _init_char(char, monedas=1000):
    char.db.monedas = monedas
    char.db.nivel = 5
    char.db.gremio = None
    char.db.invitacion_gremio = None


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        # Evennia llama a receiver.msg(text=..., **kwargs) desde msg_contents(),
        # así que el parámetro debe llamarse "text" para capturarlo también ahí.
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def all(self):
        return "\n".join(self.msgs)


def _crear_guild(nombre, lider):
    """Helper: crea un GuildScript con el personaje dado como Líder."""
    guild = create_script(
        GuildScript,
        key=f"guild_{normalizar_nombre(nombre)}",
        persistent=True,
    )
    guild.db.nombre  = nombre
    guild.db.fundado = time.time()
    guild.añadir_miembro(lider, RANGO_LIDER)
    return guild


# ---------------------------------------------------------------------------
# GuildScript: pruebas de la capa de datos
# ---------------------------------------------------------------------------

class TestGuildScriptData(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.guild = _crear_guild("Prueba", self.char1)

    def tearDown(self):
        try:
            self.guild.delete()
        except Exception:
            pass
        super().tearDown()

    def test_get_rango_lider(self):
        self.assertEqual(self.guild.get_rango(self.char1), RANGO_LIDER)

    def test_get_rango_no_miembro(self):
        self.assertIsNone(self.guild.get_rango(self.char2))

    def test_añadir_miembro(self):
        self.guild.añadir_miembro(self.char2)
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)
        self.assertEqual(self.char2.db.gremio, "Prueba")

    def test_eliminar_miembro(self):
        self.guild.añadir_miembro(self.char2)
        self.guild.eliminar_miembro(self.char2)
        self.assertIsNone(self.guild.get_rango(self.char2))
        self.assertIsNone(self.char2.db.gremio)

    def test_cambiar_rango(self):
        self.guild.añadir_miembro(self.char2)
        self.guild.cambiar_rango(self.char2, RANGO_OFICIAL)
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_OFICIAL)

    def test_contar_miembros(self):
        self.assertEqual(self.guild.contar_miembros(), 1)
        self.guild.añadir_miembro(self.char2)
        self.assertEqual(self.guild.contar_miembros(), 2)

    def test_depositar_deduce_monedas(self):
        self.guild.añadir_miembro(self.char2)
        self.char2.db.monedas = 100
        ok = self.guild.depositar(self.char2, 30)
        self.assertTrue(ok)
        self.assertEqual(self.char2.db.monedas, 70)
        self.assertEqual(self.guild.db.banco, 30)

    def test_depositar_insuficiente(self):
        self.char2.db.monedas = 10
        ok = self.guild.depositar(self.char2, 50)
        self.assertFalse(ok)

    def test_retirar_aumenta_monedas(self):
        self.guild.db.banco = 100
        ok = self.guild.retirar(self.char1, 40)
        self.assertTrue(ok)
        self.assertEqual(self.guild.db.banco, 60)
        self.assertEqual(self.char1.db.monedas, 1040)

    def test_retirar_insuficiente(self):
        self.guild.db.banco = 10
        ok = self.guild.retirar(self.char1, 50)
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# CmdCrearGremio
# ---------------------------------------------------------------------------

class TestCmdCrearGremio(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, monedas=1000)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        guild = obtener_gremio_de(self.char1)
        if guild:
            try:
                guild.delete()
            except Exception:
                pass
        super().tearDown()

    def _crear(self, args):
        cmd = _make_cmd(CmdCrearGremio, self.char1, args)
        cmd.func()

    def test_crear_gremio_valido(self):
        self._crear("Los Guardianes")
        self.assertEqual(self.char1.db.gremio, "Los Guardianes")

    def test_crear_deduce_monedas(self):
        self._crear("Los Guardianes")
        self.assertEqual(self.char1.db.monedas, 1000 - COSTE_CREAR_GREMIO)

    def test_crear_asigna_rango_lider(self):
        self._crear("Los Guardianes")
        guild = obtener_gremio_de(self.char1)
        self.assertEqual(guild.get_rango(self.char1), RANGO_LIDER)

    def test_crear_sin_fondos_falla(self):
        self.char1.db.monedas = 100
        self._crear("Los Guardianes")
        self.assertIsNone(self.char1.db.gremio)
        self.assertIn("monedas", self.cap.all().lower())

    def test_crear_ya_en_gremio_falla(self):
        self._crear("Los Guardianes")
        self.cap.msgs.clear()
        self._crear("Otro Gremio")
        self.assertIn("perteneces", self.cap.all().lower())

    def test_crear_nombre_duplicado_falla(self):
        self._crear("Los Guardianes")
        # Resetear para simular otro personaje intentando el mismo nombre
        # (simplificado: usamos el mismo char)
        guild = obtener_gremio_de(self.char1)
        guild.eliminar_miembro(self.char1)
        self.cap.msgs.clear()
        self._crear("Los Guardianes")
        self.assertIn("existe", self.cap.all().lower())
        guild.delete()


# ---------------------------------------------------------------------------
# CmdGremio (info)
# ---------------------------------------------------------------------------

class TestCmdGremio(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.guild = _crear_guild("Guardianes del Alba", self.char1)
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.guild.delete()
        except Exception:
            pass
        super().tearDown()

    def test_info_muestra_nombre_gremio(self):
        cmd = _make_cmd(CmdGremio, self.char1, "")
        cmd.func()
        self.assertIn("Guardianes del Alba", self.cap.all())

    def test_info_sin_gremio(self):
        self.guild.eliminar_miembro(self.char1)
        cmd = _make_cmd(CmdGremio, self.char1, "")
        cmd.func()
        self.assertIn("ningún gremio", self.cap.all())

    def test_info_muestra_rango_lider(self):
        cmd = _make_cmd(CmdGremio, self.char1, "")
        cmd.func()
        self.assertIn("Líder", self.cap.all())

    def test_lider_puede_cambiar_descripcion(self):
        cmd = _make_cmd(CmdGremio, self.char1, "descripcion Defensores del amanecer")
        cmd.func()
        self.assertEqual(self.guild.db.descripcion, "Defensores del amanecer")


# ---------------------------------------------------------------------------
# Invitar, aceptar y rechazar
# ---------------------------------------------------------------------------

class TestInvitaciones(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.char1.move_to(self.room1, quiet=True)
        self.char2.move_to(self.room1, quiet=True)
        self.guild = _crear_guild("Los Adalides", self.char1)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.guild.delete()
        except Exception:
            pass
        super().tearDown()

    def test_invitar_crea_invitacion(self):
        cmd = _make_cmd(CmdInvitar, self.char1, self.char2.key)
        cmd.func()
        inv = self.char2.db.invitacion_gremio
        self.assertIsNotNone(inv)
        self.assertEqual(inv.get("gremio"), "Los Adalides")

    def test_invitar_notifica_objetivo(self):
        cmd = _make_cmd(CmdInvitar, self.char1, self.char2.key)
        cmd.func()
        self.assertIn("invita", self.cap2.all().lower())

    def test_miembro_no_puede_invitar(self):
        self.guild.añadir_miembro(self.char2, RANGO_MIEMBRO)
        # Reabrir cap para char2
        self.cap2 = _MsgCapture(self.char2)
        # Crear char3 (Object sin cuenta como objetivo de prueba)
        import evennia
        char3 = evennia.create_object(
            "typeclasses.characters.Character", key="Aventurero",
            location=self.room1
        )
        _init_char(char3)
        char3.account = self.account2  # darle cuenta para que pase el check
        cmd = _make_cmd(CmdInvitar, self.char2, "Aventurero")
        cmd.func()
        self.assertIn("oficial", self.cap2.all().lower())
        char3.delete()

    def test_aceptar_invitacion_une_al_gremio(self):
        self.char2.db.invitacion_gremio = {
            "gremio": "Los Adalides",
            "invitador_dbref": self.char1.dbref,
            "timestamp": time.time(),
        }
        cmd = _make_cmd(CmdAceptarGremio, self.char2, "")
        cmd.func()
        self.assertEqual(self.char2.db.gremio, "Los Adalides")
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)

    def test_aceptar_sin_invitacion_falla(self):
        cmd = _make_cmd(CmdAceptarGremio, self.char2, "")
        cmd.func()
        self.assertIn("pendiente", self.cap2.all().lower())

    def test_aceptar_invitacion_expirada_falla(self):
        self.char2.db.invitacion_gremio = {
            "gremio": "Los Adalides",
            "invitador_dbref": self.char1.dbref,
            "timestamp": 0.0,  # muy viejo
        }
        cmd = _make_cmd(CmdAceptarGremio, self.char2, "")
        cmd.func()
        self.assertIn("expirado", self.cap2.all().lower())
        self.assertIsNone(self.char2.db.gremio)

    def test_rechazar_limpia_invitacion(self):
        self.char2.db.invitacion_gremio = {
            "gremio": "Los Adalides",
            "invitador_dbref": self.char1.dbref,
            "timestamp": time.time(),
        }
        cmd = _make_cmd(CmdRechazarGremio, self.char2, "")
        cmd.func()
        self.assertIsNone(self.char2.db.invitacion_gremio)
        self.assertIsNone(self.char2.db.gremio)


# ---------------------------------------------------------------------------
# Salir, expulsar, promover, degradar
# ---------------------------------------------------------------------------

class TestGestionRoster(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        _init_char(self.char2)
        self.guild = _crear_guild("Compañía del Crepúsculo", self.char1)
        self.guild.añadir_miembro(self.char2, RANGO_MIEMBRO)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.guild.delete()
        except Exception:
            pass
        super().tearDown()

    def test_miembro_puede_salir(self):
        cmd = _make_cmd(CmdSalirGremio, self.char2, "")
        cmd.func()
        self.assertIsNone(self.char2.db.gremio)
        self.assertIsNone(self.guild.get_rango(self.char2))

    def test_lider_no_puede_salir_con_miembros(self):
        cmd = _make_cmd(CmdSalirGremio, self.char1, "")
        cmd.func()
        self.assertEqual(self.char1.db.gremio, "Compañía del Crepúsculo")
        self.assertIn("liderazgo", self.cap1.all().lower())

    def test_lider_disuelve_al_salir_solo(self):
        self.guild.eliminar_miembro(self.char2)
        cmd = _make_cmd(CmdSalirGremio, self.char1, "")
        cmd.func()
        self.assertIsNone(self.char1.db.gremio)

    def test_expulsar_miembro(self):
        cmd = _make_cmd(CmdExpulsar, self.char1, self.char2.key)
        cmd.func()
        self.assertIsNone(self.char2.db.gremio)

    def test_expulsar_notifica_expulsado(self):
        cmd = _make_cmd(CmdExpulsar, self.char1, self.char2.key)
        cmd.func()
        self.assertIn("expulsado", self.cap2.all().lower())

    def test_miembro_no_puede_expulsar(self):
        # char2 (Miembro) intenta expulsar a char1 (Líder)
        cmd = _make_cmd(CmdExpulsar, self.char2, self.char1.key)
        cmd.func()
        # char1 sigue en el gremio
        self.assertEqual(self.guild.get_rango(self.char1), RANGO_LIDER)

    def test_promover_miembro_a_oficial(self):
        cmd = _make_cmd(CmdPromover, self.char1, self.char2.key)
        cmd.func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_OFICIAL)

    def test_promover_oficial_transfiere_liderazgo(self):
        self.guild.cambiar_rango(self.char2, RANGO_OFICIAL)
        cmd = _make_cmd(CmdPromover, self.char1, self.char2.key)
        cmd.func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_LIDER)
        self.assertEqual(self.guild.get_rango(self.char1), RANGO_OFICIAL)

    def test_degradar_oficial_a_miembro(self):
        self.guild.cambiar_rango(self.char2, RANGO_OFICIAL)
        cmd = _make_cmd(CmdDegrading, self.char1, self.char2.key)
        cmd.func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)


# ---------------------------------------------------------------------------
# Banco del gremio
# ---------------------------------------------------------------------------

class TestBancoGremio(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, monedas=200)
        _init_char(self.char2, monedas=200)
        self.guild = _crear_guild("Bóveda de Hierro", self.char1)
        self.guild.añadir_miembro(self.char2, RANGO_MIEMBRO)
        self.cap1 = _MsgCapture(self.char1)
        self.cap2 = _MsgCapture(self.char2)

    def tearDown(self):
        try:
            self.guild.delete()
        except Exception:
            pass
        super().tearDown()

    def test_depositar_funciona(self):
        cmd = _make_cmd(CmdBancoGremio, self.char2, "depositar 50")
        cmd.func()
        self.assertEqual(self.guild.db.banco, 50)
        self.assertEqual(self.char2.db.monedas, 150)

    def test_depositar_sin_fondos_falla(self):
        self.char2.db.monedas = 10
        cmd = _make_cmd(CmdBancoGremio, self.char2, "depositar 50")
        cmd.func()
        self.assertEqual(self.guild.db.banco, 0)
        self.assertIn("suficientes", self.cap2.all().lower())

    def test_lider_puede_retirar(self):
        self.guild.db.banco = 100
        cmd = _make_cmd(CmdBancoGremio, self.char1, "retirar 40")
        cmd.func()
        self.assertEqual(self.guild.db.banco, 60)
        self.assertEqual(self.char1.db.monedas, 240)

    def test_miembro_no_puede_retirar(self):
        self.guild.db.banco = 100
        cmd = _make_cmd(CmdBancoGremio, self.char2, "retirar 40")
        cmd.func()
        self.assertEqual(self.guild.db.banco, 100)
        self.assertIn("oficial", self.cap2.all().lower())

    def test_ver_saldo(self):
        self.guild.db.banco = 75
        cmd = _make_cmd(CmdBancoGremio, self.char1, "")
        cmd.func()
        self.assertIn("75", self.cap1.all())


# ---------------------------------------------------------------------------
# Disolver
# ---------------------------------------------------------------------------

class TestDisolver(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1, monedas=0)
        _init_char(self.char2)
        self.guild = _crear_guild("Efímeros", self.char1)
        self.guild.añadir_miembro(self.char2, RANGO_MIEMBRO)
        self.cap1 = _MsgCapture(self.char1)

    def test_lider_puede_disolver(self):
        cmd = _make_cmd(CmdDisolver, self.char1, "")
        cmd.func()
        self.assertIsNone(self.char1.db.gremio)
        self.assertIsNone(self.char2.db.gremio)

    def test_disolver_devuelve_banco_al_lider(self):
        self.guild.db.banco = 200
        cmd = _make_cmd(CmdDisolver, self.char1, "")
        cmd.func()
        self.assertEqual(self.char1.db.monedas, 200)

    def test_miembro_no_puede_disolver(self):
        cap2 = _MsgCapture(self.char2)
        cmd = _make_cmd(CmdDisolver, self.char2, "")
        cmd.func()
        # Gremio sigue existiendo
        self.assertIsNotNone(self.char1.db.gremio)
        self.assertIn("líder", cap2.all().lower())
        self.guild.delete()


if __name__ == "__main__":
    import unittest
    unittest.main()
