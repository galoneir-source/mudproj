"""
tests/test_mascotas.py

Tests de integración Evennia para el sistema de mascotas de combate (v0.26.0).
Cubre: CmdMascota (ver, liberar, alimentar, renombrar), CmdCapturar (bloqueos),
       integración con CombatHandler (pet attack, bond increase, captura).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_mascotas
"""
from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from features.pets.commands import CmdCapturar, CmdMascota
from systems.pets.pets import (
    COSTE_ALIMENTAR,
    VINCULO_SUBE_ALIMENTAR,
    VINCULO_SUBE_VICTORIA,
    calcular_daño_mascota,
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


def _crear_npc(sala, nombre="lobo", hp=40, hp_max=40, ataque=8, defensa=3):
    npc = create_object("typeclasses.objects.Object", key=nombre, location=sala)
    npc.db.hp = hp
    npc.db.hp_max = hp_max
    npc.db.ataque = ataque
    npc.db.defensa = defensa
    npc.db.nivel = 2
    npc.db.en_combate = False
    return npc


def _mascota_base(nombre="Fang", especie="lobo", vinculo=30, hp=40):
    return {
        "nombre": nombre,
        "especie": especie,
        "vinculo": vinculo,
        "hp": hp,
        "hp_max": hp,
        "ataque": 8,
        "defensa": 3,
    }


# --------------------------------------------------------------------------- #
#  CmdMascota — sin mascota
# --------------------------------------------------------------------------- #

class TestCmdMascotaSinMascota(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.mascota = None
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_mascota_sin_arg_informa(self):
        cmd = _make_cmd(CmdMascota, self.char1, "")
        cmd.func()
        self.assertIn("capturar", self.cap.all().lower())

    def test_liberar_sin_mascota_informa(self):
        cmd = _make_cmd(CmdMascota, self.char1, "liberar")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_alimentar_sin_mascota_informa(self):
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_nombre_sin_mascota_informa(self):
        cmd = _make_cmd(CmdMascota, self.char1, "nombre Killer")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdMascota — con mascota
# --------------------------------------------------------------------------- #

class TestCmdMascotaConMascota(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.mascota = _mascota_base()
        self.char1.db.monedas = 100
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_mostrar_stats(self):
        cmd = _make_cmd(CmdMascota, self.char1, "")
        cmd.func()
        texto = self.cap.all()
        self.assertIn("Fang", texto)
        self.assertIn("lobo", texto)

    def test_mostrar_vinculo(self):
        cmd = _make_cmd(CmdMascota, self.char1, "")
        cmd.func()
        self.assertIn("30", self.cap.all())

    def test_liberar_elimina_mascota(self):
        cmd = _make_cmd(CmdMascota, self.char1, "liberar")
        cmd.func()
        self.assertIsNone(self.char1.db.mascota)

    def test_liberar_mensaje(self):
        cmd = _make_cmd(CmdMascota, self.char1, "liberar")
        cmd.func()
        self.assertIn("liberado", self.cap.all().lower())

    def test_alimentar_sube_vinculo(self):
        vinculo_inicial = self.char1.db.mascota["vinculo"]
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertGreater(mascota["vinculo"], vinculo_inicial)

    def test_alimentar_sube_vinculo_correcto(self):
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["vinculo"], 30 + VINCULO_SUBE_ALIMENTAR)

    def test_alimentar_descuenta_monedas(self):
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        self.assertEqual(self.char1.db.monedas, 100 - COSTE_ALIMENTAR)

    def test_alimentar_sin_fondos_falla(self):
        self.char1.db.monedas = 0
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        self.assertIn("monedas", self.cap.all().lower())

    def test_alimentar_sin_fondos_no_cambia_vinculo(self):
        self.char1.db.monedas = 0
        vinculo_antes = self.char1.db.mascota["vinculo"]
        cmd = _make_cmd(CmdMascota, self.char1, "alimentar")
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["vinculo"], vinculo_antes)

    def test_renombrar(self):
        cmd = _make_cmd(CmdMascota, self.char1, "nombre Colmillo")
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["nombre"], "Colmillo")

    def test_renombrar_confirma(self):
        cmd = _make_cmd(CmdMascota, self.char1, "nombre Colmillo")
        cmd.func()
        self.assertIn("Colmillo", self.cap.all())

    def test_renombrar_nombre_vacio_falla(self):
        cmd = _make_cmd(CmdMascota, self.char1, "nombre ")
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["nombre"], "Fang")  # sin cambio

    def test_renombrar_muy_largo_falla(self):
        cmd = _make_cmd(CmdMascota, self.char1, "nombre " + "A" * 25)
        cmd.func()
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["nombre"], "Fang")  # sin cambio


# --------------------------------------------------------------------------- #
#  CmdCapturar — bloqueos sin combate
# --------------------------------------------------------------------------- #

class TestCmdCapturarSinCombate(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.mascota = None
        self.char1.db.en_combate = False
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_combate_falla(self):
        cmd = _make_cmd(CmdCapturar, self.char1, "")
        cmd.func()
        self.assertIn("combate", self.cap.all().lower())

    def test_con_mascota_ya_existente_falla(self):
        self.char1.db.mascota = _mascota_base()
        self.char1.db.en_combate = True
        cmd = _make_cmd(CmdCapturar, self.char1, "")
        cmd.func()
        self.assertIn("ya tienes", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CombatHandler — ataque de mascota
# --------------------------------------------------------------------------- #

class TestCombatHandlerMascota(EvenniaTest):
    """
    Prueba directamente los helpers del CombatHandler relacionados con mascotas.
    """

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.mascota = _mascota_base(vinculo=50)
        self.char1.db.hp = 100
        self.char1.db.hp_max = 100
        self.char1.db.nivel = 5
        self.npc = _crear_npc(self.room1, hp=50, hp_max=50)
        self.cap = _MsgCapture(self.char1)

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1)
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1, self.npc]
        self.handler.db.turno_actual = 0
        self.handler.db.acciones = {}
        self.handler.db.turno_tiempo = 0
        self.handler.db.modo_duelo = False
        self.char1.db.en_combate = True
        self.npc.db.en_combate = True

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        try:
            self.npc.delete()
        except Exception:
            pass
        super().tearDown()

    def test_pet_ataca_y_reduce_hp(self):
        hp_antes = self.npc.db.hp
        self.handler._aplicar_ataque_mascota(self.char1, self.npc)
        self.assertLess(self.npc.db.hp, hp_antes)

    def test_pet_daño_correcto(self):
        mascota = dict(self.char1.db.mascota)
        daño_esperado = calcular_daño_mascota(mascota["vinculo"], mascota["ataque"])
        hp_antes = int(self.npc.db.hp)
        self.handler._aplicar_ataque_mascota(self.char1, self.npc)
        self.assertEqual(self.npc.db.hp, hp_antes - daño_esperado)

    def test_sin_mascota_no_ataca(self):
        self.char1.db.mascota = None
        hp_antes = int(self.npc.db.hp)
        self.handler._aplicar_ataque_mascota(self.char1, self.npc)
        self.assertEqual(self.npc.db.hp, hp_antes)

    def test_pet_mensaje_en_sala(self):
        mensajes_sala = []
        self.room1.msg_contents = lambda m, **kw: mensajes_sala.append(str(m))
        self.handler._aplicar_ataque_mascota(self.char1, self.npc)
        self.assertTrue(any("Fang" in m or "muerde" in m for m in mensajes_sala))

    def test_pet_ataca_jefe_mundo_registra_dano(self):
        """
        Regresión: el ataque de la mascota reducía el HP del objetivo pero
        nunca actualizaba ndb.dano_por_jugador (a diferencia del golpe
        directo del jugador, que sí lo hace) — el daño de mascota contra un
        jefe de mundo era invisible para distribuir_recompensas_jefe_mundo(),
        infravalorando la contribución real de jugadores con mascota fuerte.
        """
        mascota = dict(self.char1.db.mascota)
        daño_esperado = calcular_daño_mascota(mascota["vinculo"], mascota["ataque"])
        self.npc.db.es_jefe_mundo = True
        self.npc.ndb.dano_por_jugador = {}

        self.handler._aplicar_ataque_mascota(self.char1, self.npc)

        tracker = dict(self.npc.ndb.dano_por_jugador or {})
        self.assertEqual(tracker.get(self.char1.dbref), daño_esperado)

    def test_pet_ataca_npc_normal_no_registra_dano(self):
        """Sin es_jefe_mundo, no debe crearse tracker (solo aplica a jefes)."""
        self.handler._aplicar_ataque_mascota(self.char1, self.npc)
        self.assertIsNone(getattr(self.npc.ndb, "dano_por_jugador", None))


# --------------------------------------------------------------------------- #
#  CombatHandler — vincuación tras victoria
# --------------------------------------------------------------------------- #

class TestVinculoTrasVictoria(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.mascota = _mascota_base(vinculo=20)
        self.char1.db.hp = 100
        self.char1.db.hp_max = 100
        self.char1.db.nivel = 5
        self.char1.db.kills_totales = 0
        self.char1.db.jefes_derrotados = []
        self.char1.db.quests = {}
        self.npc = _crear_npc(self.room1, hp=1, hp_max=40)

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1)
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1, self.npc]
        self.handler.db.turno_actual = 0
        self.handler.db.acciones = {}
        self.handler.db.turno_tiempo = 0
        self.handler.db.modo_duelo = False
        self.char1.db.en_combate = True
        self.npc.db.en_combate = True

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        super().tearDown()

    def test_vinculo_sube_tras_matar_npc(self):
        vinculo_antes = self.char1.db.mascota["vinculo"]
        self.handler._procesar_muerte(self.npc, asesino=self.char1)
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["vinculo"], vinculo_antes + VINCULO_SUBE_VICTORIA)

    def test_sin_mascota_no_error(self):
        self.char1.db.mascota = None
        # No debe lanzar excepción
        try:
            self.handler._procesar_muerte(self.npc, asesino=self.char1)
        except Exception as e:
            self.fail(f"_procesar_muerte lanzó excepción sin mascota: {e}")


# --------------------------------------------------------------------------- #
#  CombatHandler — intentar captura
# --------------------------------------------------------------------------- #

class TestIntentarCaptura(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.mascota = None
        self.char1.db.hp = 100
        self.char1.db.hp_max = 100
        self.char1.db.nivel = 5

        # NPC debilitado al 10% de HP
        self.npc = _crear_npc(self.room1, hp=4, hp_max=40)  # 10%

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1)
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1, self.npc]
        self.handler.db.turno_actual = 0
        self.handler.db.acciones = {}
        self.handler.db.turno_tiempo = 0
        self.handler.db.modo_duelo = False
        self.char1.db.en_combate = True
        self.npc.db.en_combate = True

        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        super().tearDown()

    def test_captura_exitosa_asigna_mascota(self):
        self.handler._intentar_captura(self.char1)
        self.assertIsNotNone(self.char1.db.mascota)

    def test_mascota_tiene_nombre_del_npc(self):
        self.handler._intentar_captura(self.char1)
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["especie"], "lobo")

    def test_mascota_hp_restaurado(self):
        self.handler._intentar_captura(self.char1)
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["hp"], mascota["hp_max"])

    def test_npc_fuerte_no_puede_capturarse(self):
        self.npc.db.hp = 30  # 75% HP
        self.handler._intentar_captura(self.char1)
        self.assertIsNone(self.char1.db.mascota)
        self.assertIn("%", self.cap.all())  # menciona el porcentaje

    def test_con_mascota_previa_no_captura(self):
        self.char1.db.mascota = _mascota_base()
        self.handler._intentar_captura(self.char1)
        # La mascota original no debe cambiar
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["nombre"], "Fang")


# --------------------------------------------------------------------------- #
#  CombatHandler — intentar captura con más de un NPC en el combate
# --------------------------------------------------------------------------- #

class TestIntentarCapturaMultiNpc(EvenniaTest):
    """
    Regresión: _intentar_captura() cogía siempre el primer NPC de
    self.db.participantes sin comprobar su HP. En un combate con más de un
    NPC (grupo, oleada de mazmorra/expedición, o un segundo jugador que se
    une a un combate ya activo atacando a otro NPC), si el primer NPC de la
    lista no estaba debilitado pero SÍ lo estaba otro NPC del mismo
    combate, el jugador recibía "aún tiene X% de HP" sobre el NPC
    equivocado y no podía capturar al que sí cumplía el umbral (≤20% HP).
    """

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.mascota = None
        self.char1.db.hp = 100
        self.char1.db.hp_max = 100
        self.char1.db.nivel = 5

        # Primer NPC de la lista: sano, NO capturable.
        self.npc_sano = _crear_npc(self.room1, nombre="orco", hp=40, hp_max=40)
        # Segundo NPC: debilitado al 10% de HP, sí capturable.
        self.npc_debil = _crear_npc(self.room1, nombre="lobo", hp=4, hp_max=40)

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1)
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1, self.npc_sano, self.npc_debil]
        self.handler.db.turno_actual = 0
        self.handler.db.acciones = {}
        self.handler.db.turno_tiempo = 0
        self.handler.db.modo_duelo = False
        self.char1.db.en_combate = True
        self.npc_sano.db.en_combate = True
        self.npc_debil.db.en_combate = True

        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        super().tearDown()

    def test_captura_al_npc_debilitado_aunque_no_sea_el_primero(self):
        self.handler._intentar_captura(self.char1)
        self.assertIsNotNone(self.char1.db.mascota)
        mascota = dict(self.char1.db.mascota or {})
        self.assertEqual(mascota["especie"], "lobo")

    def test_si_ningun_npc_cumple_el_umbral_reporta_el_primero(self):
        self.npc_debil.db.hp = 40  # ya no está debilitado: ningún NPC captura
        self.handler._intentar_captura(self.char1)
        self.assertIsNone(self.char1.db.mascota)
        self.assertIn("orco", self.cap.all())


# --------------------------------------------------------------------------- #
#  CmdCapturar — despacho real vía CombatHandler (regresión)
# --------------------------------------------------------------------------- #

class TestCapturarDespachoReal(EvenniaTest):
    """
    Regresión: CmdCapturar.func() llama a handler.registrar_accion(caller,
    "capturar"), que a su vez pasa por _resolver_turno(). Ese despacho
    central no tenía ninguna rama para tipo == "capturar" (solo pasar /
    atacar / habilidad / huir), así que el comando real nunca ejecutaba
    _intentar_captura() — caía en silencio a "pasar turno". Los tests
    anteriores de este archivo (TestIntentarCaptura) llaman al método
    privado directamente y no detectaban el problema porque se saltan
    _resolver_turno() por completo.
    """

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.mascota = None
        self.char1.db.hp = 100
        self.char1.db.hp_max = 100
        self.char1.db.nivel = 5
        self.char1.db.en_combate = True

        # NPC debilitado al 10% de HP: apto para captura.
        self.npc = _crear_npc(self.room1, hp=4, hp_max=40)
        self.npc.db.en_combate = True

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1, key="combat_handler")
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1, self.npc]
        self.handler.db.turno_actual = 0
        self.handler.db.acciones = {}
        self.handler.db.turno_tiempo = 0
        self.handler.db.modo_duelo = False

        self.room1.msg_contents = lambda m, **kw: None
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        super().tearDown()

    def test_comando_capturar_real_asigna_mascota(self):
        cmd = _make_cmd(CmdCapturar, self.char1, "")
        cmd.func()
        self.assertIsNotNone(
            self.char1.db.mascota,
            "CmdCapturar no capturó a través del despacho real de _resolver_turno",
        )

    def test_comando_capturar_real_elimina_al_npc(self):
        cmd = _make_cmd(CmdCapturar, self.char1, "")
        cmd.func()
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=self.npc.id).exists())


if __name__ == "__main__":
    import unittest
    unittest.main()
