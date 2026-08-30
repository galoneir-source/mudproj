"""
tests/test_expeditions.py

Tests de integración Evennia para el sistema de expediciones grupales (v0.51.0).
Cubre: CmdExpedicion._iniciar y la recolección real del grupo (party).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_expeditions
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from features.combat.handler import CombatHandler
from features.expeditions.commands import CmdExpedicion, _obtener_script_expedicion
from features.party.commands import _añadir_miembro, _crear_partido
from typeclasses.characters import Character


class PersonajeConectado(Character):
    """
    has_account cuenta sesiones conectadas reales; para simular un segundo
    jugador realmente presente (además de self.char1, que ya trae sesión
    real por defecto en esta versión de Evennia) sin montar una sesión
    real, se sobreescribe la propiedad -- mismo truco que test_guild_wars.py.
    """
    @property
    def has_account(self):
        return True


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


# --------------------------------------------------------------------------- #
#  Recompensas al completar la expedición entera
# --------------------------------------------------------------------------- #

class TestExpedicionRecompensaTotal(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.companera = create_object(PersonajeConectado, key="Compañera")
        _init_char(self.companera)
        self.char1.db.experiencia = 0
        self.char1.db.monedas = 0
        self.companera.db.experiencia = 0
        self.companera.db.monedas = 0
        self.companera.move_to(self.char1.location, quiet=True)
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.companera)

    def tearDown(self):
        script = _obtener_script_expedicion(self.char1)
        if script:
            try:
                script.delete()
            except Exception:
                pass
        super().tearDown()

    def _matar_npcs_de_la_sala(self, sala):
        for obj in list(sala.contents):
            if type(obj).__name__ == "NPC":
                obj.delete()

    def _jugar_expedicion_completa(self, tipo_id="bosque_profundo"):
        from systems.expeditions.expeditions import total_oleadas

        _make_cmd(CmdExpedicion, self.char1, f"iniciar {tipo_id}").func()
        script = _obtener_script_expedicion(self.char1)
        sala = self.char1.location

        n = total_oleadas(tipo_id)
        for _ in range(n):
            self._matar_npcs_de_la_sala(sala)
            script.at_repeat()
            if script.db.ticks_pausa:
                script.at_repeat()
        return script

    def test_recompensar_oleada_aplica_buff_de_xp(self):
        """
        Regresión: factor_xp() (buffs_activos, p.ej. Estofado Vigorizante)
        solo se aplicaba en _dar_xp_a_grupo() (kills de combate normal)
        desde que se introdujo este buff en v0.34.0 -- expediciones nunca
        retomó esta integración en _recompensar_oleada(), así que el mismo
        buff que promete "+N% XP" sin excepción de alcance no tenía ningún
        efecto al superar una oleada.
        """
        import time
        from systems.expeditions.expeditions import calcular_recompensa_oleada

        self.char1.db.buffs_activos = [{
            "tipo": "buff_xp", "bonus": 0.5, "nombre": "Estofado Vigorizante",
            "expira": time.time() + 1800,
        }]

        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()
        script = _obtener_script_expedicion(self.char1)
        script._recompensar_oleada(0)

        rec = calcular_recompensa_oleada("bosque_profundo", 2)
        self.assertEqual(self.char1.db.experiencia, int(rec["xp"] * 1.5))

    def test_completar_bonus_aplica_buff_de_xp(self):
        """
        Mismo bug que test_recompensar_oleada_aplica_buff_de_xp, pero en
        el bonus adicional de _completar() -- llamado en aislamiento
        (sin pasar por las oleadas) para no depender del bug preexistente
        y no relacionado de doble recompensa en la última oleada. Se
        parchea notificar_progreso() del sistema de desafíos diarios (que
        _completar() dispara como efecto secundario) para que su propia
        recompensa de XP -si "expedicion" resulta ser el desafío del
        día- no se mezcle con la aserción de este test.
        """
        import time
        from unittest.mock import patch
        from systems.expeditions.expeditions import calcular_bonus_completar

        self.char1.db.buffs_activos = [{
            "tipo": "buff_xp", "bonus": 0.5, "nombre": "Estofado Vigorizante",
            "expira": time.time() + 1800,
        }]

        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()
        script = _obtener_script_expedicion(self.char1)
        with patch("features.daily.daily_script.notificar_progreso"):
            script._completar()

        bonus = calcular_bonus_completar("bosque_profundo", 2)
        self.assertEqual(self.char1.db.experiencia, int(bonus["xp"] * 1.5))

    def test_completar_expedicion_no_crashea_al_subir_de_nivel(self):
        """
        Regresión: _recompensar_oleada()/_completar() llamaban a
        procesar_subida_de_nivel(nivel, experiencia) -- dos argumentos
        posicionales y un resultado tratado como dict con claves
        "subio"/"nuevo_nivel"/"nuevo_hp_max". La función real solo acepta
        UN argumento (un dict de stats) y devuelve una tupla (bool, dict)
        con clave "nivel" (sin el prefijo "nuevo_"), como ya hacen
        correctamente combat/handler.py, quests y contratos. El resultado
        era un TypeError sin capturar en cuanto se despejaba la primera
        oleada de CUALQUIER expedición -- at_repeat() nunca llegaba a
        avanzar de oleada ni a completar nada; la expedición quedaba
        atascada para siempre hasta expirar por timeout sin recompensa.
        Nunca se detectó porque ningún test anterior hacía avanzar el
        script más allá de iniciar().
        """
        self._jugar_expedicion_completa()  # no debe lanzar TypeError

    def test_completar_expedicion_no_duplica_la_recompensa_de_la_ultima_oleada(self):
        """
        Regresión: at_repeat() llama incondicionalmente a
        _recompensar_oleada(oleada_idx) para cualquier oleada que se
        despeja -- incluida la última (el jefe) -- y justo después, si era
        la última, llama también a _completar(). _completar() usaba
        calcular_recompensa_total(), que por definición (y su propio test,
        "El total = por_oleada × num_oleadas + bonus_completar") ya es la
        suma de TODAS las oleadas más el bonus -- no solo el bonus. El
        resultado era que la recompensa de cada oleada (incluida la del
        jefe) se pagaba dos veces: una vez oleada a oleada y otra vez de
        golpe al completar, en todas las expediciones, siempre.
        """
        from systems.expeditions.expeditions import calcular_recompensa_total

        self._jugar_expedicion_completa()

        esperado = calcular_recompensa_total("bosque_profundo", 2)
        self.assertEqual(self.char1.db.experiencia, esperado["xp"])
        self.assertEqual(self.char1.db.monedas, esperado["monedas"])


class TestExpedicionLimpiezaConCombateActivo(EvenniaTest):
    """
    Regresión: ExpedicionScript._limpiar() teletransporta a los jugadores y
    borra la sala temporal directamente, sin comprobar antes si hay un
    combate activo dentro -- mismo bug ya corregido en vivienda (v0.71.34)
    y en mazmorras. El timeout global de 30 minutos (at_repeat()) se
    dispara sin esperar a que termine ningún combate en curso contra los
    NPCs de la oleada actual: si el jugador sigue peleando justo cuando
    expira, CombatHandler (script hijo de la sala) se borra en cascada
    junto con ella sin pasar por _terminar_combate(), dejándolo con
    db.en_combate=True para siempre.
    """
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.companera = create_object(PersonajeConectado, key="Compañera")
        _init_char(self.companera)
        self.companera.move_to(self.char1.location, quiet=True)
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.companera)

    def test_timeout_termina_el_combate_activo_en_la_sala(self):
        import time

        _make_cmd(CmdExpedicion, self.char1, "iniciar bosque_profundo").func()
        script = _obtener_script_expedicion(self.char1)
        sala = self.char1.location

        npc = next(o for o in sala.contents if type(o).__name__ == "NPC")
        handler = sala.scripts.add(CombatHandler)
        handler.iniciar([self.char1, npc])

        from features.expeditions.expedition_script import _TIMEOUT_SEGS
        script.db.tiempo_inicio = time.time() - _TIMEOUT_SEGS - 10

        script.at_repeat()

        self.assertFalse(
            getattr(self.char1.db, "en_combate", False),
            "El jugador debía salir del combate al expirar la expedición "
            "con él dentro, no quedarse bloqueado para siempre por la "
            "sala borrada.",
        )
