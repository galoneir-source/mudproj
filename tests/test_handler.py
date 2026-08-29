"""
tests/test_handler.py

Tests de integración para features/combat/handler.py.
Usan el framework de tests de Evennia (EvenniaTest) que arranca Django y la BD de prueba.

Ejecutar con:
  cd /opt/evennia/mudproj && venv/bin/evennia test mygame.tests.test_handler
"""
from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.combat.handler import CombatHandler, _get_stats, _generar_loot, _runas_activas
from systems.combat.engine import STAT_DEFAULTS
from typeclasses.characters import Character


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

    def test_dano_a_jefe_mundo_se_registra_en_db_no_en_ndb(self):
        """
        Regresión: el tracking de daño contra un jefe de mundo se guardaba
        en objetivo.ndb.dano_por_jugador -- memoria del proceso que Evennia
        NO conserva a través de un `evennia reload` (operación rutinaria,
        publicitada como segura para los jugadores: "recargar sin perder
        conexiones"). Un jefe de mundo tiene mucho HP y la pelea puede durar
        más que el intervalo entre reloads, así que uno ocurriendo a mitad
        de combate borraba todo el progreso de daño acumulado hasta ese
        momento -- quien más había golpeado podía quedarse sin recompensa
        si no volvía a golpear después del reload. Debe guardarse en db.
        """
        self.npc.db.es_jefe_mundo = True
        self.npc.db.dano_por_jugador = {}
        handler = self._crear_handler()
        handler.db.turno_actual = 0  # jugador ataca primero
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.99]  # no esquiva, no critico
            mock_rng.randint.return_value = 4
            handler.registrar_accion(self.jugador, "atacar", objetivo=self.npc)

        self.assertIsNone(getattr(self.npc.ndb, "dano_por_jugador", None))
        tracker = dict(getattr(self.npc.db, "dano_por_jugador", None) or {})
        self.assertIn(self.jugador.dbref, tracker)
        self.assertGreater(tracker[self.jugador.dbref], 0)

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

    def test_terminar_combate_sin_sala_no_falla(self):
        """
        Regresión: _terminar_combate() hacía sala.msg_contents(...) sin
        comprobar antes si self.obj (la sala) seguía existiendo. Si la sala
        fue borrada (p. ej. limpieza del mundo mientras el combate quedó
        huérfano tras un reinicio del servidor, ver
        _limpiar_actividad_huerfana en server/conf/at_server_startstop.py),
        esa llamada lanzaba AttributeError sobre None DESPUÉS de haber
        limpiado ya el estado de los participantes pero ANTES de borrarse a
        sí mismo — dejando el script zombie para siempre y abortando, si se
        llama desde un bucle sin try/except por elemento, la limpieza de
        cualquier otro combate huérfano restante.
        """
        handler = self._crear_handler()
        with patch.object(type(handler), "obj", new_callable=PropertyMock, return_value=None):
            handler._terminar_combate()  # no debe lanzar excepción
        self.assertFalse(self.jugador.db.en_combate)


class JugadorFalsoTurno(Character):
    """Simula un segundo jugador sin sesión real (mismo truco que test_guild_wars.py)."""
    @property
    def has_account(self):
        return True


class TestOrdenDeTurnoTrasEliminarParticipante(EvenniaTest):
    """
    Regresión: eliminar_participante() reindexa turno_actual con un simple
    clamp de desbordamiento (evita que el índice quede fuera de rango), pero
    cada punto de llamada que lo invoca (_procesar_muerte, _intentar_captura)
    volvía a sumar 1 con _siguiente_turno() sin comprobar si ese clamp ya
    había dejado el índice apuntando al participante correcto. Cuando el
    eliminado estaba ANTES del actor en la lista (o era el propio actor,
    p. ej. una muerte por tick de veneno en su propio turno), la suma extra
    saltaba por completo el turno de quien le seguía. _intentar_huida(), por
    su parte, nunca llamaba a _siguiente_turno()/_anunciar_turno() tras una
    huida exitosa, así que el siguiente turno no se anunciaba (ni mensaje al
    jugador, ni IA del NPC programada) hasta que lo rescatara el timeout
    automático de turno. Fix: _avanzar_turno_tras_baja() recalcula siempre a
    partir de la posición real del actor tras el hueco, en vez de sumar un
    paso a ciegas.
    """

    def setUp(self):
        super().setUp()
        self.sala = create_object("typeclasses.rooms.Room", key="Arena")
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        _set_stats(self.jugador, hp=100, hp_max=100, nivel=1)

        self.jugador2 = create_object(JugadorFalsoTurno, key="Compañero")
        self.jugador2.move_to(self.sala, quiet=True)
        _set_stats(self.jugador2, hp=100, hp_max=100, nivel=1)

        self.npc = create_object("typeclasses.npc.NPC", key="Goblin")
        self.npc.move_to(self.sala, quiet=True)
        _set_stats(self.npc, hp=1, hp_max=30, nivel=1)

    def _crear_handler(self, orden):
        handler = self.sala.scripts.add(CombatHandler)
        handler.iniciar(orden)
        return handler

    def test_matar_a_alguien_anterior_en_la_lista_no_salta_el_siguiente_turno(self):
        # Orden: [npc, jugador, jugador2] -> es el turno de jugador (índice 1)
        handler = self._crear_handler([self.npc, self.jugador, self.jugador2])
        handler.db.turno_actual = 1
        with patch("evennia.utils.delay"):
            handler._procesar_muerte(self.npc, asesino=self.jugador)
        siguiente = handler.db.participantes[handler.db.turno_actual]
        self.assertEqual(siguiente, self.jugador2)

    def test_capturar_a_alguien_anterior_en_la_lista_no_salta_el_siguiente_turno(self):
        self.npc.db.hp = 5  # <=20% de 30 -> capturable
        handler = self._crear_handler([self.npc, self.jugador, self.jugador2])
        handler.db.turno_actual = 1
        with patch("evennia.utils.delay"):
            handler._intentar_captura(self.jugador)
        siguiente = handler.db.participantes[handler.db.turno_actual]
        self.assertEqual(siguiente, self.jugador2)

    def test_muerte_en_el_propio_turno_no_salta_el_siguiente(self):
        # El propio jugador muere en su turno (p. ej. tick de veneno, sin
        # asesino) -> el turno debe pasar directo al siguiente, no saltarlo.
        handler = self._crear_handler([self.jugador, self.npc, self.jugador2])
        handler.db.turno_actual = 0
        with patch("evennia.utils.delay"):
            handler._procesar_muerte(self.jugador)
        siguiente = handler.db.participantes[handler.db.turno_actual]
        self.assertEqual(siguiente, self.npc)

    def test_huida_exitosa_anuncia_el_siguiente_turno(self):
        salida = create_object("typeclasses.exits.Exit", key="norte", location=self.sala)
        salida.destination = self.room2
        handler = self._crear_handler([self.jugador, self.npc, self.jugador2])
        handler.db.turno_actual = 0
        handler.db.turno_tiempo = 7  # tiempo ya acumulado antes de huir

        with patch("random.random", return_value=0.01), \
             patch("random.choice", return_value=salida), \
             patch("evennia.utils.delay") as mock_delay:
            handler._intentar_huida(self.jugador)

        self.assertEqual(handler.db.turno_tiempo, 0)
        # El siguiente participante es el NPC -> su turno debe anunciarse
        # (IA programada), no quedar en silencio hasta el timeout.
        self.assertTrue(mock_delay.called)


class TestIaNpcCobardeHuida(EvenniaTest):
    """
    Regresión: _ia_npc() ponía 'enraged'=True a CUALQUIER NPC (sin mirar su
    temperamento) al bajar de 50% HP. Como 'enraged' no se resetea hasta el
    fin del combate y bloquea la rama de huida (HP<25%, gate 'not enraged'),
    un NPC 'cobarde' que pierde HP de forma gradual (el caso normal: cruza
    el 50% antes que el 25%) nunca llegaba a poder huir — pese a que
    world/help_entries.py promete explícitamente "cobarde... puede huir si
    le atacas".
    """

    def setUp(self):
        super().setUp()
        self.sala = create_object("typeclasses.rooms.Room", key="Arena")
        self.jugador = self.char1
        self.jugador.move_to(self.sala, quiet=True)
        _set_stats(self.jugador, hp=100, hp_max=100, nivel=1)

        self.npc = create_object("typeclasses.npc.NPC", key="Goblin cobarde")
        self.npc.db.temperamento = "cobarde"
        self.npc.move_to(self.sala, quiet=True)
        _set_stats(self.npc, hp=40, hp_max=100, nivel=1)

        self.handler = self.sala.scripts.add(CombatHandler)
        self.handler.iniciar([self.jugador, self.npc])

    def test_cobarde_no_se_enfurece_bajo_el_50_por_ciento(self):
        self.handler._ia_npc(self.npc)
        self.assertFalse(self.npc.db.enraged)

    def test_agresivo_si_se_enfurece_bajo_el_50_por_ciento(self):
        # Regresión inversa: el resto de temperamentos deben seguir
        # enfureciéndose igual que antes, sin cambio de comportamiento.
        self.npc.db.temperamento = "agresivo"
        self.handler._ia_npc(self.npc)
        self.assertTrue(self.npc.db.enraged)

    def test_cobarde_puede_huir_tras_perder_mas_de_la_mitad_del_hp(self):
        self.handler._ia_npc(self.npc)  # 40% hp: no se enfurece (ver arriba)
        self.npc.db.hp = 20  # 20% hp: por debajo del umbral crítico de huida
        with patch("random.random", return_value=0.1):
            with patch.object(self.handler, "registrar_accion") as mock_registrar:
                self.handler._ia_npc(self.npc)
        mock_registrar.assert_called_once_with(self.npc, "huir")


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
