"""
tests/test_guilds.py

Tests de integración para features/guilds/commands.py y guild_script.py.
Ejecutar con:
  cd mygame && ../venv/bin/evennia test --settings settings.py tests.test_guilds
"""
import time

from evennia import create_object
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
from features.guilds.guild_script import obtener_gremio_por_nombre
from systems.guilds.guilds import (
    COSTE_CREAR_GREMIO,
    INVITACION_TIMEOUT,
    RANGO_LIDER,
    RANGO_MIEMBRO,
    RANGO_OFICIAL,
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


class GuildTestBase(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.monedas = 1000
        self.char2.db.monedas = 1000

    def _crear_gremio(self, caller=None, nombre="Los Guardianes"):
        caller = caller or self.char1
        _make_cmd(CmdCrearGremio, caller, nombre).func()
        return obtener_gremio_por_nombre(nombre)

    def _invitar_y_aceptar(self, lider, objetivo, gremio_nombre="Los Guardianes"):
        _make_cmd(CmdInvitar, lider, objetivo.key).func()
        _make_cmd(CmdAceptarGremio, objetivo).func()


# --------------------------------------------------------------------------- #
#  CmdCrearGremio
# --------------------------------------------------------------------------- #

class TestCmdCrearGremio(GuildTestBase):

    def test_crear_gremio_deduce_coste(self):
        self._crear_gremio()
        self.assertEqual(self.char1.db.monedas, 1000 - COSTE_CREAR_GREMIO)

    def test_crear_gremio_asigna_lider(self):
        guild = self._crear_gremio()
        self.assertEqual(guild.get_rango(self.char1), RANGO_LIDER)

    def test_crear_gremio_sin_monedas_falla(self):
        self.char1.db.monedas = 10
        self._crear_gremio()
        self.assertIsNone(obtener_gremio_por_nombre("Los Guardianes"))
        self.assertEqual(self.char1.db.monedas, 10)

    def test_crear_gremio_nombre_invalido_no_cobra(self):
        self._crear_gremio(nombre="Ab")
        self.assertEqual(self.char1.db.monedas, 1000)

    def test_crear_gremio_ya_en_gremio_falla(self):
        self._crear_gremio()
        self.char1.db.monedas = 1000
        self._crear_gremio(nombre="Otro Gremio")
        self.assertIsNone(obtener_gremio_por_nombre("Otro Gremio"))

    def test_crear_gremio_nombre_duplicado_falla(self):
        self._crear_gremio()
        self.char2.db.monedas = 1000
        self._crear_gremio(caller=self.char2, nombre="Los Guardianes")
        # char2 no debe haber sido cobrado ni asignado al gremio existente
        self.assertEqual(self.char2.db.monedas, 1000)
        self.assertIsNone(self.char2.db.gremio)

    def test_crear_gremio_incrementa_contador_fundados(self):
        self._crear_gremio()
        self.assertEqual(self.char1.db.gremios_fundados, 1)


# --------------------------------------------------------------------------- #
#  CmdInvitar / CmdAceptarGremio / CmdRechazarGremio
# --------------------------------------------------------------------------- #

class TestInvitacionesGremio(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()

    def test_invitar_crea_invitacion_pendiente(self):
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        self.assertIsNotNone(self.char2.db.invitacion_gremio)

    def test_miembro_normal_no_puede_invitar(self):
        self._invitar_y_aceptar(self.char1, self.char2)
        objetivo = create_object(
            "typeclasses.characters.Character", key="Tercero", location=self.room1
        )
        objetivo.db.monedas = 0
        # char2 es Miembro (rango base), no puede invitar
        _make_cmd(CmdInvitar, self.char2, objetivo.key).func()
        self.assertIsNone(objetivo.db.invitacion_gremio)

    def test_aceptar_invitacion_une_al_gremio(self):
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        _make_cmd(CmdAceptarGremio, self.char2).func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)

    def test_rechazar_invitacion_no_une(self):
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        _make_cmd(CmdRechazarGremio, self.char2).func()
        self.assertFalse(self.guild.es_miembro(self.char2))
        self.assertIsNone(self.char2.db.invitacion_gremio)

    def test_invitacion_expirada_no_se_puede_aceptar(self):
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        inv = self.char2.db.invitacion_gremio
        inv["timestamp"] = time.time() - INVITACION_TIMEOUT - 1
        self.char2.db.invitacion_gremio = inv
        _make_cmd(CmdAceptarGremio, self.char2).func()
        self.assertFalse(self.guild.es_miembro(self.char2))

    def test_invitacion_duplicada_bloqueada_mientras_vigente(self):
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        primera = dict(self.char2.db.invitacion_gremio)
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        # La invitación no debe haberse reemplazado: sigue vigente
        self.assertEqual(self.char2.db.invitacion_gremio["timestamp"], primera["timestamp"])

    def test_invitacion_caducada_permite_nueva_invitacion(self):
        """
        Regresión: antes del fix, cualquier invitación pendiente (aunque
        llevara horas caducada sin ser aceptada ni rechazada) bloqueaba
        para siempre nuevas invitaciones a ese jugador, ya que el check
        solo miraba si el atributo existía, no si seguía vigente.
        """
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        inv = self.char2.db.invitacion_gremio
        inv["timestamp"] = time.time() - INVITACION_TIMEOUT - 100
        self.char2.db.invitacion_gremio = inv

        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()

        nueva = self.char2.db.invitacion_gremio
        self.assertGreater(nueva["timestamp"], time.time() - 5)

    def test_ya_miembro_no_puede_ser_invitado(self):
        self._invitar_y_aceptar(self.char1, self.char2)
        objetivo = self.char2
        _make_cmd(CmdInvitar, self.char1, objetivo.key).func()
        # Sigue siendo miembro y no genera invitación
        self.assertIsNone(objetivo.db.invitacion_gremio)

    def test_gremio_lleno_no_permite_invitar(self):
        from systems.guilds.guilds import MAX_MIEMBROS
        for i in range(MAX_MIEMBROS - 1):
            npc = create_object("typeclasses.characters.Character", key=f"Jugador{i}")
            self.guild.añadir_miembro(npc)
        _make_cmd(CmdInvitar, self.char1, self.char2.key).func()
        self.assertIsNone(self.char2.db.invitacion_gremio)


# --------------------------------------------------------------------------- #
#  CmdSalirGremio
# --------------------------------------------------------------------------- #

class TestCmdSalirGremio(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()

    def test_lider_unico_al_salir_disuelve_gremio(self):
        _make_cmd(CmdSalirGremio, self.char1).func()
        self.assertIsNone(obtener_gremio_por_nombre("Los Guardianes"))
        self.assertIsNone(self.char1.db.gremio)

    def test_lider_con_otros_miembros_no_puede_salir_directo(self):
        self._invitar_y_aceptar(self.char1, self.char2)
        _make_cmd(CmdSalirGremio, self.char1).func()
        self.assertTrue(self.guild.es_miembro(self.char1))

    def test_miembro_puede_salir_libremente(self):
        self._invitar_y_aceptar(self.char1, self.char2)
        _make_cmd(CmdSalirGremio, self.char2).func()
        self.assertFalse(self.guild.es_miembro(self.char2))
        self.assertIsNone(self.char2.db.gremio)

    def test_disolver_automatico_devuelve_banco(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar 200").func()
        _make_cmd(CmdSalirGremio, self.char1).func()
        self.assertEqual(self.char1.db.monedas, 1000 - COSTE_CREAR_GREMIO)


# --------------------------------------------------------------------------- #
#  CmdExpulsar
# --------------------------------------------------------------------------- #

class TestCmdExpulsar(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()
        self._invitar_y_aceptar(self.char1, self.char2)

    def test_lider_expulsa_miembro(self):
        _make_cmd(CmdExpulsar, self.char1, self.char2.key).func()
        self.assertFalse(self.guild.es_miembro(self.char2))

    def test_miembro_no_puede_expulsar(self):
        _make_cmd(CmdExpulsar, self.char2, self.char1.key).func()
        self.assertTrue(self.guild.es_miembro(self.char1))

    def test_no_puede_expulsarse_a_si_mismo(self):
        _make_cmd(CmdExpulsar, self.char1, self.char1.key).func()
        self.assertTrue(self.guild.es_miembro(self.char1))

    def test_expulsado_limpia_atributo_gremio(self):
        _make_cmd(CmdExpulsar, self.char1, self.char2.key).func()
        self.assertIsNone(self.char2.db.gremio)


# --------------------------------------------------------------------------- #
#  CmdPromover / CmdDegrading
# --------------------------------------------------------------------------- #

class TestPromoverDegradar(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()
        self._invitar_y_aceptar(self.char1, self.char2)

    def test_promover_miembro_a_oficial(self):
        _make_cmd(CmdPromover, self.char1, self.char2.key).func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_OFICIAL)

    def test_promover_oficial_transfiere_liderazgo(self):
        _make_cmd(CmdPromover, self.char1, self.char2.key).func()  # -> Oficial
        _make_cmd(CmdPromover, self.char1, self.char2.key).func()  # -> Líder
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_LIDER)
        self.assertEqual(self.guild.get_rango(self.char1), RANGO_OFICIAL)

    def test_no_lider_no_puede_promover(self):
        _make_cmd(CmdPromover, self.char2, self.char1.key).func()
        self.assertEqual(self.guild.get_rango(self.char1), RANGO_LIDER)

    def test_degradar_oficial_a_miembro(self):
        _make_cmd(CmdPromover, self.char1, self.char2.key).func()
        _make_cmd(CmdDegrading, self.char1, self.char2.key).func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)

    def test_degradar_sin_args_usa_mensaje_del_comando_correcto(self):
        """
        Regresión: el mensaje de uso decía "degrading" (inglés) en vez
        de "degradar", el nombre real del comando en español.
        """
        msgs = []
        self.char1.msg = lambda text=None, **kw: msgs.append(text)
        _make_cmd(CmdDegrading, self.char1, "").func()
        salida = "\n".join(str(m) for m in msgs)
        self.assertIn("degradar", salida)
        self.assertNotIn("degrading", salida)

    def test_no_puede_degradar_a_un_miembro_normal(self):
        _make_cmd(CmdDegrading, self.char1, self.char2.key).func()
        self.assertEqual(self.guild.get_rango(self.char2), RANGO_MIEMBRO)


# --------------------------------------------------------------------------- #
#  CmdBancoGremio
# --------------------------------------------------------------------------- #

class TestCmdBancoGremio(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()
        self._invitar_y_aceptar(self.char1, self.char2)

    def test_depositar_reduce_monedas_del_jugador(self):
        antes = self.char1.db.monedas
        _make_cmd(CmdBancoGremio, self.char1, "depositar 100").func()
        self.assertEqual(self.char1.db.monedas, antes - 100)
        self.assertEqual(self.guild.db.banco, 100)

    def test_miembro_puede_depositar(self):
        _make_cmd(CmdBancoGremio, self.char2, "depositar 50").func()
        self.assertEqual(self.guild.db.banco, 50)

    def test_miembro_no_puede_retirar(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar 100").func()
        _make_cmd(CmdBancoGremio, self.char2, "retirar 50").func()
        self.assertEqual(self.guild.db.banco, 100)

    def test_lider_puede_retirar(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar 100").func()
        _make_cmd(CmdBancoGremio, self.char1, "retirar 40").func()
        self.assertEqual(self.guild.db.banco, 60)

    def test_depositar_cantidad_negativa_rechazada(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar -5").func()
        self.assertEqual(self.guild.db.banco, 0)

    def test_retirar_mas_de_lo_disponible_falla(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar 10").func()
        _make_cmd(CmdBancoGremio, self.char1, "retirar 999").func()
        self.assertEqual(self.guild.db.banco, 10)

    def test_depositar_mas_de_lo_que_tiene_falla(self):
        self.char2.db.monedas = 10
        _make_cmd(CmdBancoGremio, self.char2, "depositar 999").func()
        self.assertEqual(self.guild.db.banco, 0)
        self.assertEqual(self.char2.db.monedas, 10)


# --------------------------------------------------------------------------- #
#  CmdDisolver
# --------------------------------------------------------------------------- #

class TestCmdDisolver(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()
        self._invitar_y_aceptar(self.char1, self.char2)

    def test_no_lider_no_puede_disolver(self):
        _make_cmd(CmdDisolver, self.char2).func()
        self.assertIsNotNone(obtener_gremio_por_nombre("Los Guardianes"))

    def test_lider_disuelve_y_recupera_banco(self):
        _make_cmd(CmdBancoGremio, self.char1, "depositar 300").func()
        antes = self.char1.db.monedas
        _make_cmd(CmdDisolver, self.char1).func()
        self.assertIsNone(obtener_gremio_por_nombre("Los Guardianes"))
        self.assertEqual(self.char1.db.monedas, antes + 300)

    def test_disolver_limpia_gremio_de_todos_los_miembros(self):
        _make_cmd(CmdDisolver, self.char1).func()
        self.assertIsNone(self.char1.db.gremio)
        self.assertIsNone(self.char2.db.gremio)


# --------------------------------------------------------------------------- #
#  CmdGremio
# --------------------------------------------------------------------------- #

class TestCmdGremio(GuildTestBase):

    def setUp(self):
        super().setUp()
        self.guild = self._crear_gremio()

    def test_gremio_sin_pertenecer_avisa(self):
        _make_cmd(CmdGremio, self.char2).func()

    def test_lider_cambia_descripcion(self):
        _make_cmd(CmdGremio, self.char1, "descripcion Los mejores de la ciudad").func()
        self.assertEqual(self.guild.db.descripcion, "Los mejores de la ciudad")

    def test_miembro_no_puede_cambiar_descripcion(self):
        self._invitar_y_aceptar(self.char1, self.char2)
        _make_cmd(CmdGremio, self.char2, "descripcion Intento no autorizado").func()
        self.assertEqual(self.guild.db.descripcion, "")

    def test_gremio_muestra_info_no_explota(self):
        _make_cmd(CmdGremio, self.char1).func()
