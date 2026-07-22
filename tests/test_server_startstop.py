"""
tests/test_server_startstop.py

Tests de integración Evennia para server/conf/at_server_startstop.py.
Cubre: at_server_start() arranca los 9 scripts globales persistentes, y un
fallo en uno de ellos no impide que los demás arranquen (cada uno está
envuelto en su propio try/except).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_server_startstop
"""
from unittest.mock import patch

from evennia.scripts.models import ScriptDB
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
