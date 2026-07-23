"""
tests/test_handler.py

Tests de integración para features/combat/handler.py.
Usan el framework de tests de Evennia (EvenniaTest) que arranca Django y la BD de prueba.

Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_handler
"""
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.combat.handler import CombatHandler, _get_stats, _generar_loot, _runas_activas
from systems.combat.engine import STAT_DEFAULTS


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _set_stats(obj, **overrides):
    """Escribe stats de combate en db.* de un objeto Evennia."""
    for k, v in STAT_DEFAULTS.items():
        setattr(obj.db, k, overrides.get(k, v))


# --------------------------------------------------------------------------- #
#  Tests de _get_stats
# --------------------------------------------------------------------------- #

class TestGetStats(EvenniaTest):

    def test_devuelve_defaults_si_db_vacio(self):
        obj = create_object("typeclasses.characters.Character", key="hero")
        # Los personajes inicializan stats en at_object_creation, pero
        # comprobamos que _get_stats nunca devuelve None en ningún campo
        stats = _get_stats(obj)
        for key in STAT_DEFAULTS:
            self.assertIn(key, stats)
            self.assertIsNotNone(stats[key])

    def test_devuelve_valores_seteados(self):
        obj = create_object("typeclasses.characters.Character", key="guerrero")
        obj.db.fuerza = 18
        obj.db.hp = 75
        stats = _get_stats(obj)
        self.assertEqual(stats["fuerza"], 18)
        self.assertEqual(stats["hp"], 75)


# --------------------------------------------------------------------------- #
#  Tests de _runas_activas
# --------------------------------------------------------------------------- #

class TestRunasActivas(EvenniaTest):
    """
    Regresión: las runas se graban por slot (arma/armadura/accesorio), no
    por ítem concreto — desequipar el objeto nunca borraba la entrada de
    db.runas_equipadas, así que el efecto (bonus_fuerza, evasion, etc.)
    seguía activo para siempre en cualquiera de los ~7 puntos de
    handler.py que leían runas_equipadas directamente, contradiciendo
    descripciones como la de RUNA_PODER ("mientras el arma esté
    equipada"). _runas_activas() filtra por slots con equipo puesto.
    """

    def setUp(self):
        super().setUp()
        self.arma = create_object(
            "typeclasses.objects.Equipo", key="espada de runas", location=self.char1
        )
        self.char1.db.equipamiento["arma"] = self.arma
        self.char1.db.runas_equipadas["arma"] = "RUNA_PODER"

    def test_runa_activa_si_slot_equipado(self):
        self.assertEqual(_runas_activas(self.char1), {"arma": "RUNA_PODER"})

    def test_runa_inactiva_si_slot_desequipado(self):
        self.char1.db.equipamiento["arma"] = None
        self.assertEqual(_runas_activas(self.char1), {})

    def test_bonus_fuerza_desaparece_al_desequipar(self):
        stats_equipado = _get_stats(self.char1)
        self.char1.db.equipamiento["arma"] = None
        stats_desequipado = _get_stats(self.char1)
        self.assertEqual(
            stats_desequipado["fuerza"],
            stats_equipado["fuerza"] - 5,  # RUNA_PODER: +5 Fuerza
        )


# --------------------------------------------------------------------------- #
#  Tests de _generar_loot
# --------------------------------------------------------------------------- #

class TestGenerarLoot(EvenniaTest):

    def _sala(self):
        return create_object("typeclasses.rooms.Room", key="TestRoom")

    def test_sin_loot_devuelve_lista_vacia(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test")
        npc.db.loot = []
        sala = self._sala()
        result = _generar_loot(npc, sala)
        self.assertEqual(result, [])

    def test_loot_none_devuelve_lista_vacia(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test2")
        npc.db.loot = None
        sala = self._sala()
        result = _generar_loot(npc, sala)
        self.assertEqual(result, [])

    def test_loot_crea_objeto_en_sala(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test3")
        npc.db.loot = [{"key": "moneda", "cantidad": 1, "chance": 1.0}]
        sala = self._sala()
        items = _generar_loot(npc, sala)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].location, sala)

    def test_loot_chance_cero_nunca_crea(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test4")
        npc.db.loot = [{"key": "raro", "cantidad": 1, "chance": 0.0}]
        sala = self._sala()
        items = _generar_loot(npc, sala)
        self.assertEqual(items, [])

    def test_loot_cantidad(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test5")
        npc.db.loot = [{"key": "moneda", "cantidad": 3, "chance": 1.0}]
        sala = self._sala()
        items = _generar_loot(npc, sala)
        self.assertEqual(len(items), 3)

    def test_entrada_no_dict_se_ignora(self):
        npc = create_object("typeclasses.npc.NPC", key="goblin_test6")
        npc.db.loot = ["texto suelto", 42, None]
        sala = self._sala()
        result = _generar_loot(npc, sala)
        self.assertEqual(result, [])


# --------------------------------------------------------------------------- #
#  Tests de CombatHandler
# --------------------------------------------------------------------------- #

class TestCombatHandler(EvenniaTest):

    def setUp(self):
        super().setUp()
        # EvenniaTest provee self.char1 (Character con cuenta) y self.room1
        self.sala = create_object("typeclasses.rooms.Room", key="Arena")
        # Usar char1 que tiene cuenta → has_account=True → muerte de jugador, no de NPC
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        _set_stats(self.jugador, hp=100, hp_max=100, nivel=1)

        self.npc = create_object("typeclasses.npc.NPC", key="Goblin")
        self.npc.move_to(self.sala, quiet=True)
        _set_stats(self.npc, hp=30, hp_max=30, nivel=1)

    def _crear_handler(self):
        handler = self.sala.scripts.add(CombatHandler)
        handler.iniciar([self.jugador, self.npc])
        return handler

    # ------------------------------------------------------------------ #
    #  Creación e inicialización
    # ------------------------------------------------------------------ #

    def test_iniciar_activo(self):
        handler = self._crear_handler()
        self.assertTrue(handler.db.activo)

    def test_iniciar_con_participantes(self):
        handler = self._crear_handler()
        self.assertIn(self.jugador, handler.db.participantes)
        self.assertIn(self.npc, handler.db.participantes)

    def test_turno_inicial_es_cero(self):
        handler = self._crear_handler()
        self.assertEqual(handler.db.turno_actual, 0)

    def test_iniciar_rompe_sigilo_y_cancela_la_tarea_pendiente(self):
        """
        Regresión: iniciar() ya ponía oculto=False al entrar en combate, pero
        no cancelaba la tarea de evennia.utils.delay que Consumible.aplicar()
        (typeclasses/objects.py, efecto "sigilo") programó para restaurarlo —
        la tarea vieja seguía viva y disparaba igualmente a su hora original,
        mandando un "tu sigilo ha expirado" falso después de que el combate
        ya lo hubiera roto.
        """
        self.jugador.db.oculto = True
        self.jugador.db.nivel_sigilo = 25
        tarea = MagicMock()
        self.jugador.ndb.tarea_sigilo = tarea

        self._crear_handler()

        self.assertFalse(self.jugador.db.oculto)
        tarea.cancel.assert_called_once()

    # ------------------------------------------------------------------ #
    #  agregar / eliminar participantes
    # ------------------------------------------------------------------ #

    def test_agregar_participante_nuevo(self):
        handler = self._crear_handler()
        extra = create_object("typeclasses.npc.NPC", key="Troll")
        extra.location = self.sala
        handler.agregar_participante(extra)
        self.assertIn(extra, handler.db.participantes)

    def test_agregar_participante_duplicado(self):
        handler = self._crear_handler()
        handler.agregar_participante(self.jugador)  # ya estaba
        count = handler.db.participantes.count(self.jugador)
        self.assertEqual(count, 1)

    def test_eliminar_participante_termina_combate_si_solo_queda_uno(self):
        handler = self._crear_handler()
        handler.eliminar_participante(self.npc)
        self.assertFalse(handler.db.activo)

    def test_eliminar_participante_ajusta_indice(self):
        npc2 = create_object("typeclasses.npc.NPC", key="Serpiente")
        npc2.location = self.sala
        handler = self.sala.scripts.add(CombatHandler)
        handler.iniciar([self.jugador, self.npc, npc2])
        handler.db.turno_actual = 2  # apunta a npc2
        handler.eliminar_participante(npc2)
        # El índice no debe exceder el nuevo tamaño
        self.assertLess(handler.db.turno_actual, len(handler.db.participantes))

    # ------------------------------------------------------------------ #
    #  registrar_accion
    # ------------------------------------------------------------------ #

    def test_registrar_accion_fuera_de_turno(self):
        handler = self._crear_handler()
        # El jugador es el primero (índice 0); la acción del NPC fuera de turno
        # debe ser rechazada con mensaje
        msgs = []
        self.npc.msg = lambda text=None, **kw: msgs.append(text)
        handler.registrar_accion(self.npc, "atacar", objetivo=self.jugador)
        # El NPC no es el turno actual, debe recibir aviso
        self.assertTrue(any("turno" in m.lower() for m in msgs))

    def test_registrar_accion_pasar(self):
        handler = self._crear_handler()
        handler.db.turno_actual = 0  # turno del jugador
        handler.registrar_accion(self.jugador, "pasar")
        # Debe avanzar al turno del NPC
        self.assertEqual(handler.db.turno_actual, 1)

    def test_registrar_accion_atacar_reduce_hp(self):
        handler = self._crear_handler()
        handler.db.turno_actual = 0  # jugador ataca primero
        hp_antes = self.npc.db.hp
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.99]  # no esquiva, no critico
            mock_rng.randint.return_value = 4
            handler.registrar_accion(self.jugador, "atacar", objetivo=self.npc)
        # El HP del NPC debe haber disminuido o el combate terminado
        hp_despues = self.npc.db.hp if self.npc.pk else 0
        self.assertLessEqual(hp_despues, hp_antes)

    # ------------------------------------------------------------------ #
    #  Timeout de turno (at_repeat)
    # ------------------------------------------------------------------ #

    def test_timeout_avanza_turno(self):
        from features.combat.handler import TURNO_TIMEOUT, INTERVALO_TURNO
        handler = self._crear_handler()
        handler.db.turno_actual = 0
        handler.db.turno_tiempo = TURNO_TIMEOUT - INTERVALO_TURNO
        turno_antes = handler.db.turno_actual
        handler.at_repeat()
        # Debe haber avanzado el turno
        self.assertNotEqual(handler.db.turno_actual, turno_antes)

    def test_no_timeout_si_tiempo_insuficiente(self):
        handler = self._crear_handler()
        handler.db.turno_actual = 0
        handler.db.turno_tiempo = 0
        handler.at_repeat()
        # Sin timeout el turno no cambia
        self.assertEqual(handler.db.turno_actual, 0)

    # ------------------------------------------------------------------ #
    #  _procesar_muerte (NPC)
    # ------------------------------------------------------------------ #

    def test_npc_muerto_otorga_xp(self):
        handler = self._crear_handler()
        xp_antes = self.jugador.db.experiencia or 0
        with patch("features.respawn.respawn.programar_respawn"):
            handler._procesar_muerte(self.npc, asesino=self.jugador)
        xp_despues = self.jugador.db.experiencia or 0
        self.assertGreater(xp_despues, xp_antes)

    def test_jugador_muerto_va_a_home(self):
        handler = self._crear_handler()
        home = create_object("typeclasses.rooms.Room", key="Inicio")
        self.jugador.home = home
        # Verificar estado previo
        self.assertEqual(self.jugador.db.hp, 100)
        self.assertTrue(self.jugador.has_account, "jugador debe tener cuenta para el test")
        handler._procesar_muerte(self.jugador, asesino=self.npc)
        # HP debe quedar en 1 y el jugador debe haber salido del arena
        self.assertEqual(self.jugador.db.hp, 1)
        self.assertNotEqual(self.jugador.location, self.sala,
            "El jugador no debería seguir en la arena tras morir")

    # ------------------------------------------------------------------ #
    #  _terminar_combate
    # ------------------------------------------------------------------ #

    def test_terminar_combate_marca_inactivo(self):
        handler = self._crear_handler()
        handler._terminar_combate()
        # El handler se elimina al terminar; db.activo debe ser False
        self.assertFalse(handler.db.activo)


class TestEventniaCompat(EvenniaTest):
    """
    Tests de compatibilidad con el sistema interno de Evennia.
    Documentan comportamientos no obvios que requieren adaptar el código del juego.
    """

    def test_db_loot_devuelve_saver_dict(self):
        """Los dicts dentro de listas en db.* son _SaverDict, no dict estándar."""
        npc = create_object("typeclasses.npc.NPC", key="npc_compat")
        npc.db.loot = [{"key": "moneda", "cantidad": 1, "chance": 1.0}]
        loot_tabla = npc.db.loot
        self.assertEqual(len(loot_tabla), 1)
        entrada = loot_tabla[0]
        # _SaverDict tiene .get() aunque no sea instancia de dict
        self.assertTrue(hasattr(entrada, "get"))
        self.assertEqual(entrada.get("key"), "moneda")
        self.assertEqual(entrada.get("chance"), 1.0)
