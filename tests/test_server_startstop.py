"""
tests/test_server_startstop.py

Tests de integración Evennia para server/conf/at_server_startstop.py.
Cubre: at_server_start() arranca los 9 scripts globales persistentes, un
fallo en uno de ellos no impide que los demás arranquen (cada uno está
envuelto en su propio try/except), y la limpieza de actividad huérfana
(combate/torneo/expedición persistent=False que sobrevive a un reinicio
con el timer muerto).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_server_startstop
"""
from unittest.mock import patch

from evennia.scripts.models import ScriptDB
from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start


class TestAtServerStart(EvenniaTest):
    def test_arranca_los_nueve_scripts_globales(self):
        at_server_start()

        keys_esperadas = {
            "reloj_mundial",
            "clima_mundial",
            "evento_mundial",
            "records_global",
            "mercado_global",
            "tablón_contratos",
            "world_boss_script",
            "gestor_viviendas",
            "recompensas_script",
        }
        keys_reales = set(ScriptDB.objects.filter(
            db_key__in=keys_esperadas
        ).values_list("db_key", flat=True))
        self.assertEqual(keys_reales, keys_esperadas)

        # obtener_desafios_script() no usa una key fija reconocible aquí,
        # pero al menos debe existir un DesafiosDiariosScript tras el arranque.
        from features.daily.daily_script import DesafiosDiariosScript
        self.assertTrue(
            any(isinstance(s, DesafiosDiariosScript) for s in ScriptDB.objects.all())
        )

    def test_fallo_en_un_script_no_bloquea_a_los_demas(self):
        """
        Regresión potencial: cada obtener_*_script() está envuelto en su
        propio try/except Exception, así que un fallo aislado (import roto,
        excepción en at_script_creation, etc.) en uno no debe impedir que
        los demás 8 se arranquen igualmente.
        """
        with patch(
            "features.market.market_script.obtener_mercado_script",
            side_effect=RuntimeError("boom"),
        ):
            at_server_start()

        self.assertEqual(ScriptDB.objects.filter(db_key="reloj_mundial").count(), 1)
        self.assertEqual(ScriptDB.objects.filter(db_key="clima_mundial").count(), 1)
        self.assertEqual(ScriptDB.objects.filter(db_key="mercado_global").count(), 0)


# --------------------------------------------------------------------------- #
#  Limpieza de actividad huérfana (persistent=False superviviente a reinicio)
# --------------------------------------------------------------------------- #

class TestLimpiezaCombateHuerfano(EvenniaTest):
    """
    Regresión: CombatHandler es persistent=False. Evennia para su timer en
    cada arranque (reload o cold start) sin borrar la fila de la base de
    datos, así que sobrevive como un script "zombie" — _get_combat_handler()
    lo sigue devolviendo como activo, pero su temporizador nunca vuelve a
    dispararse. Si ninguno de los participantes vuelve a actuar, el
    combate queda congelado para siempre y db.en_combate se queda en True
    de forma permanente en los personajes implicados (solo se limpia desde
    dentro del propio handler), bloqueando invitar/expulsar de grupo y los
    comandos de duelo indefinidamente.
    """

    def test_en_combate_se_limpia_y_el_handler_zombie_se_borra(self):
        from features.combat.handler import CombatHandler

        handler = self.room1.scripts.add(CombatHandler)
        handler.db.participantes = [self.char1, self.char2]
        self.char1.db.en_combate = True
        self.char2.db.en_combate = True

        at_server_start()

        self.assertFalse(self.char1.db.en_combate)
        self.assertFalse(self.char2.db.en_combate)
        self.assertEqual(ScriptDB.objects.filter(db_key="combat_handler").count(), 0)


class TestLimpiezaTorneoHuerfano(EvenniaTest):
    """
    Regresión: TorneoScript es persistent=False y tiene el mismo problema
    que CombatHandler — un torneo a mitad de un reinicio queda congelado
    (nunca vuelve a expirar por timeout) con las cuotas de inscripción ya
    cobradas y sin forma de recuperarlas (desinscribir() solo funciona en
    estado "inscripcion"). Se resuelve reutilizando _cancelar(), el mismo
    método ya usado para el timeout normal, que reembolsa a todos los
    inscritos.
    """

    def test_torneo_zombie_se_cancela_y_reembolsa(self):
        from features.arena.tournament_script import TorneoScript
        from systems.arena.arena import INSCRIPCION_FEE

        torneo = create_script(TorneoScript, persistent=False, autostart=True)
        self.char1.db.monedas = 0
        torneo.db.inscritos = [self.char1.dbref]
        torneo.db.estado = "activo"

        at_server_start()

        self.assertEqual(self.char1.db.monedas, INSCRIPCION_FEE)
        self.assertEqual(ScriptDB.objects.filter(db_key="torneo_arena").count(), 0)


class TestLimpiezaExpedicionHuerfana(EvenniaTest):
    """
    Regresión: ExpedicionScript es persistent=False. Un grupo a mitad de
    una expedición cuando el servidor reinicia queda con el script zombie
    (timer muerto, nunca vuelve a limpiar/teleportar) — potencialmente
    atrapado en la sala temporal para siempre. Se resuelve llamando a
    _limpiar(exito=False), el mismo método ya usado para el timeout normal.
    """

    def test_expedicion_zombie_se_limpia(self):
        from features.expeditions.commands import CmdExpedicion
        from features.party.commands import _añadir_miembro, _crear_partido

        self.char1.db.nivel = 5
        self.char2.db.nivel = 5
        self.char2.move_to(self.char1.location, quiet=True)
        _crear_partido(self.char1)
        _añadir_miembro(self.char1, self.char2)

        cmd = CmdExpedicion()
        cmd.caller = self.char1
        cmd.args = "iniciar bosque_profundo"
        cmd.cmdstring = cmd.key
        cmd.session = None
        cmd.obj = self.char1
        cmd.raw_string = "expedicion iniciar bosque_profundo"
        cmd.switches = []
        cmd.lhs = cmd.args
        cmd.rhs = ""
        cmd.func()

        sala_expedicion = self.char1.location
        origen = self.room1
        self.assertTrue(getattr(sala_expedicion.db, "es_expedicion", False))

        at_server_start()

        self.assertEqual(ScriptDB.objects.filter(db_key="expedicion_script").count(), 0)
        self.assertEqual(self.char1.location, origen)
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=sala_expedicion.id).exists())
