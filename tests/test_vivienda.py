"""
tests/test_vivienda.py

Tests de integración Evennia para el sistema de vivienda personal (v0.44.0).
Cubre: obtener_gestor_script() (singleton real), CmdVivienda (comprar,
estado, acceso, abandonar), CmdCasa, CmdVisitar, CmdDecorar.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_vivienda
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from features.combat.handler import CombatHandler
from features.housing.commands import CmdCasa, CmdDecorar, CmdVisitar, CmdVivienda
from features.housing.housing_script import obtener_gestor_script
from systems.housing.housing import PRECIO_VIVIENDA
from typeclasses.characters import Character
from typeclasses.rooms import Room


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


class TestGestorViviendasSingleton(EvenniaTest):
    def test_obtener_gestor_script_devuelve_siempre_el_mismo(self):
        """
        Regresión: obtener_gestor_script() llamaba a s.typeclass_instance
        sobre un objeto que YA era la instancia con typeclass (ScriptDB.objects
        devuelve objetos ya typeclasseados) -> AttributeError silenciada por
        un except Exception: pass, así que la función nunca reutilizaba el
        script existente y creaba uno nuevo (con db.viviendas vacío) en cada
        llamada. Efecto en producción: comprar una vivienda no se recordaba
        entre comandos, así que 'vivienda estado'/'casa'/'decorar' siempre
        decían "No tienes vivienda" incluso justo después de comprarla, y
        nada impedía comprar (y pagar) una vivienda nueva una y otra vez.
        """
        g1 = obtener_gestor_script()
        g1.db.viviendas = {"marca": "valor"}

        g2 = obtener_gestor_script()

        self.assertIs(g1, g2)
        self.assertEqual(dict(g2.db.viviendas), {"marca": "valor"})
        self.assertEqual(
            ScriptDB.objects.filter(db_key="gestor_viviendas").count(), 1
        )


class ViviendaTestBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.barrio = self._crear_barrio()
        self.char1.db.monedas = 1000
        self.char2.db.monedas = 1000
        self.char1.msg = lambda text=None, **kw: None
        self.char2.msg = lambda text=None, **kw: None
        self.char1.move_to(self.barrio, quiet=True)
        self.char2.move_to(self.barrio, quiet=True)

    def _crear_barrio(self):
        from evennia import search_object
        existentes = search_object("Barrio Residencial", typeclass="typeclasses.rooms.Room")
        if existentes:
            return existentes[0]
        return create.create_object(Room, key="Barrio Residencial")


class TestCompra(ViviendaTestBase):
    def test_comprar_descuenta_monedas_y_crea_sala(self):
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        self.assertEqual(self.char1.db.monedas, 1000 - PRECIO_VIVIENDA)
        gestor = obtener_gestor_script()
        self.assertTrue(gestor.tiene_vivienda(self.char1))

    def test_comprar_dos_veces_falla_la_segunda(self):
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        monedas_tras_primera = self.char1.db.monedas
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        self.assertEqual(self.char1.db.monedas, monedas_tras_primera)

    def test_estado_refleja_la_compra_inmediatamente(self):
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        gestor = obtener_gestor_script()
        sala = gestor.obtener_sala(self.char1)
        self.assertIsNotNone(sala)


class TestCasaYDecorar(ViviendaTestBase):
    def setUp(self):
        super().setUp()
        _make_cmd(CmdVivienda, self.char1, "comprar").func()

    def test_casa_teletransporta(self):
        _make_cmd(CmdCasa, self.char1).func()
        gestor = obtener_gestor_script()
        self.assertEqual(self.char1.location, gestor.obtener_sala(self.char1))

    def test_decorar_requiere_estar_dentro(self):
        _make_cmd(CmdDecorar, self.char1, "una sala de prueba").func()
        gestor = obtener_gestor_script()
        sala = gestor.obtener_sala(self.char1)
        self.assertIsNone(sala.db.desc_personalizada)

        _make_cmd(CmdCasa, self.char1).func()
        _make_cmd(CmdDecorar, self.char1, "una sala de prueba").func()
        self.assertEqual(sala.db.desc_personalizada, "una sala de prueba")

    def test_casa_bloqueada_en_combate(self):
        """
        Regresión candidata: a diferencia de 'viajar' (que sí comprueba
        en_combate), 'casa' no tenía ninguna restricción -- cualquier
        jugador con vivienda (500 monedas, una sola vez) podía teletransportarse
        a un lugar seguro de forma instantánea y sin coste durante cualquier
        combate, sin pasar por el 50% de fallo real de 'huir' y dejando el
        combate colgado (el hueco se auto-pasa por timeout de turno) en vez
        de resolverse.
        """
        self.char1.db.en_combate = True
        _make_cmd(CmdCasa, self.char1).func()
        gestor = obtener_gestor_script()
        self.assertNotEqual(self.char1.location, gestor.obtener_sala(self.char1))


class TestAccesoYVisitas(ViviendaTestBase):
    def setUp(self):
        super().setUp()
        _make_cmd(CmdVivienda, self.char1, "comprar").func()

    def test_sin_acceso_no_puede_visitar(self):
        _make_cmd(CmdVisitar, self.char2, self.char1.key).func()
        gestor = obtener_gestor_script()
        self.assertNotEqual(self.char2.location, gestor.obtener_sala(self.char1))

    def test_con_acceso_puede_visitar(self):
        _make_cmd(CmdVivienda, self.char1, f"acceso dar {self.char2.key}").func()
        _make_cmd(CmdVisitar, self.char2, self.char1.key).func()
        gestor = obtener_gestor_script()
        self.assertEqual(self.char2.location, gestor.obtener_sala(self.char1))

    def test_quitar_acceso_revoca_la_visita(self):
        _make_cmd(CmdVivienda, self.char1, f"acceso dar {self.char2.key}").func()
        _make_cmd(CmdVivienda, self.char1, f"acceso quitar {self.char2.key}").func()
        _make_cmd(CmdVisitar, self.char2, self.char1.key).func()
        gestor = obtener_gestor_script()
        self.assertNotEqual(self.char2.location, gestor.obtener_sala(self.char1))

    def test_visitar_bloqueado_en_combate(self):
        _make_cmd(CmdVivienda, self.char1, f"acceso dar {self.char2.key}").func()
        self.char2.db.en_combate = True
        _make_cmd(CmdVisitar, self.char2, self.char1.key).func()
        gestor = obtener_gestor_script()
        self.assertNotEqual(self.char2.location, gestor.obtener_sala(self.char1))


class TestAbandonar(ViviendaTestBase):
    def setUp(self):
        super().setUp()
        _make_cmd(CmdVivienda, self.char1, "comprar").func()

    def test_abandonar_requiere_confirmacion(self):
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        gestor = obtener_gestor_script()
        self.assertTrue(gestor.tiene_vivienda(self.char1))

    def test_abandonar_confirmado_libera_la_vivienda(self):
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        gestor = obtener_gestor_script()
        self.assertFalse(gestor.tiene_vivienda(self.char1))
        self.assertIsNone(self.char1.db.vivienda_dbref)

    def test_puede_comprar_de_nuevo_tras_abandonar(self):
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        monedas_antes = self.char1.db.monedas
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        self.assertEqual(self.char1.db.monedas, monedas_antes - PRECIO_VIVIENDA)
        gestor = obtener_gestor_script()
        self.assertTrue(gestor.tiene_vivienda(self.char1))


class TestAbandonarConCombateActivo(ViviendaTestBase):
    """
    Regresión: el PvP es libre en cualquier sala, incluida la vivienda de
    un jugador (no existe ningún concepto de "zona segura" en el motor de
    combate) -- así que dos personajes pueden acabar peleando dentro de
    una vivienda (el propietario y un invitado que la visita). Si el
    propietario la abandona en ese momento, GestorViviendasScript.abandonar()
    movía a los participantes fuera y borraba la sala directamente, sin
    pasar nunca por CombatHandler._terminar_combate(). El script de
    combate es hijo de la sala, así que se borraba en cascada junto con
    ella -- a diferencia de un servidor caído (donde
    _limpiar_actividad_huerfana() encuentra el script "zombie" al
    reiniciar y lo limpia), aquí el script desaparece del todo, así que
    ni siquiera un reinicio del servidor puede arreglarlo después: ambos
    combatientes se quedaban con db.en_combate=True para siempre, bloqueados
    de 'casa', 'visitar', duelos, torneos, viaje rápido y grupos.
    """

    def setUp(self):
        super().setUp()
        _make_cmd(CmdVivienda, self.char1, "comprar").func()
        self.gestor = obtener_gestor_script()
        self.sala = self.gestor.obtener_sala(self.char1)
        self.char1.move_to(self.sala, quiet=True)
        self.char2.move_to(self.sala, quiet=True)
        self.handler = self.sala.scripts.add(CombatHandler)
        self.handler.iniciar([self.char1, self.char2])

    def test_abandonar_termina_el_combate_activo_de_la_sala(self):
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()
        _make_cmd(CmdVivienda, self.char1, "abandonar").func()

        self.assertFalse(
            getattr(self.char1.db, "en_combate", False),
            "El propietario debía salir del combate al abandonar la vivienda.",
        )
        self.assertFalse(
            getattr(self.char2.db, "en_combate", False),
            "El invitado en combate debía salir del combate, no quedarse "
            "bloqueado para siempre por la sala borrada.",
        )
