"""
tests/test_expeditions.py

Tests de integración Evennia para el sistema de expediciones grupales (v0.51.0).
Cubre: CmdExpedicion._iniciar y la recolección real del grupo (party).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_expeditions
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

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
