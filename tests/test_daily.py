"""
tests/test_daily.py

Tests de integración para el sistema de Desafíos Diarios: DesafiosDiariosScript,
notificar_progreso() (la función que llaman combate/profesiones/apuestas/
alquimia/expediciones) y CmdDesafios.

Antes de este archivo no existía NINGÚN test de integración para este sistema
(solo tests/test_daily_system.py, puro sobre el catálogo) — el mismo hueco de
cobertura que dejó pasar bugs similares en mazmorras/expediciones/vivienda, y
que aquí escondía el bug de previsualización de racha (ver test_daily_system.py
y systems/daily/daily.py::racha_si_completa_hoy).

Los 5 desafíos del día se fijan vía mock (uno de cada tipo: kill_faccion,
recolectar, apostar_ganar, alquimia, expedicion) para que los tests sean
deterministas sin depender de la fecha real en la que se ejecutan.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_daily
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from features.daily.commands import CmdDesafios
from features.daily.daily_script import (
    obtener_desafios_script,
    notificar_progreso,
)
from systems.daily.daily import POOL_DESAFIOS


def _hoy_utc():
    # Misma fuente de verdad que features/daily/{daily_script,commands}.py
    # tras el fix de zona horaria (date.today() usaba la hora LOCAL del
    # servidor, no la UTC que promete la ayuda de `desafios`).
    return datetime.now(timezone.utc).date()


def _pool_por_id(*ids):
    por_id = {d["id"]: d for d in POOL_DESAFIOS}
    return [por_id[i] for i in ids]


# Uno de cada tipo, en orden fijo: kill_faccion, recolectar, apostar_ganar,
# alquimia, expedicion.
_DESAFIOS_FIJOS = _pool_por_id(
    "kill_bandidos", "rec_mineria", "apostar_ganar", "alquimia", "expedicion"
)


def _desafios_fijos(_hoy_str):
    return [dict(d) for d in _DESAFIOS_FIJOS]


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


def _preparar_char(char):
    char.db.fecha_desafios = None
    char.db.progreso_desafios = [0, 0, 0, 0, 0]
    char.db.desafios_completados_hoy = []
    char.db.racha_desafios = 0
    char.db.ultimo_dia_desafios = None
    char.db.total_desafios_completados = 0
    char.db.monedas = 0
    char.db.experiencia = 0


def _completar_los_5(char):
    """Dispara notificar_progreso las veces necesarias para completar
    los 5 desafíos fijos de _DESAFIOS_FIJOS (uno de cada tipo)."""
    for _ in range(5):
        notificar_progreso(char, "kill_faccion", faccion="horda_salvaje")
    for _ in range(5):
        notificar_progreso(char, "recolectar", profesion="mineria")
    for _ in range(3):
        notificar_progreso(char, "apostar_ganar")
    for _ in range(2):
        notificar_progreso(char, "alquimia")
    notificar_progreso(char, "expedicion")


class TestObtenerDesafiosScript(EvenniaTest):
    def test_crea_script_si_no_existe(self):
        script = obtener_desafios_script()
        self.assertIsNotNone(script)
        self.assertEqual(script.key, "desafios_diarios_script")

    def test_singleton_devuelve_mismo_script(self):
        s1 = obtener_desafios_script()
        s2 = obtener_desafios_script()
        self.assertEqual(s1.id, s2.id)


class TestFechaUsaUTCNoLocal(EvenniaTest):
    """
    Regresión: _hoy()/_ayer() usaban date.today(), que devuelve la fecha de
    la zona horaria LOCAL del sistema operativo — Django TIME_ZONE=UTC no
    afecta en absoluto al datetime/date de la librería estándar, solo a
    django.utils.timezone.now() y a los campos de fecha del ORM. La ayuda de
    `desafios` promete explícitamente "medianoche (UTC)"; con un servidor en
    cualquier zona horaria distinta de UTC, el reinicio diario ocurría 1-2h
    antes o después de lo prometido. Si el código volviera a usar
    date.today() (zona horaria local, no controlable de forma portable en un
    test), este test comprueba en su lugar que _hoy()/_ayer() derivan de
    datetime.now(timezone.utc): se parchea ese `datetime.now` con un instante
    fijo y se verifica que la fecha calculada corresponde exactamente a ese
    instante en UTC.
    """

    def test_daily_script_hoy_usa_datetime_now_utc(self):
        from features.daily import daily_script
        instante = datetime(2026, 8, 8, 0, 30, tzinfo=timezone.utc)
        with patch.object(daily_script, "datetime") as mock_dt:
            mock_dt.now.return_value = instante
            self.assertEqual(daily_script._hoy(), "2026-08-08")
            mock_dt.now.assert_called_with(timezone.utc)

    def test_daily_script_ayer_usa_datetime_now_utc(self):
        from features.daily import daily_script
        instante = datetime(2026, 8, 8, 0, 30, tzinfo=timezone.utc)
        with patch.object(daily_script, "datetime") as mock_dt:
            mock_dt.now.return_value = instante
            self.assertEqual(daily_script._ayer(), "2026-08-07")

    def test_commands_hoy_usa_datetime_now_utc(self):
        from features.daily import commands as daily_commands
        instante = datetime(2026, 8, 8, 0, 30, tzinfo=timezone.utc)
        with patch.object(daily_commands, "datetime") as mock_dt:
            mock_dt.now.return_value = instante
            self.assertEqual(daily_commands._hoy(), "2026-08-08")
            mock_dt.now.assert_called_with(timezone.utc)

    def test_hoy_coincide_con_datetime_now_utc(self):
        from features.daily import daily_script
        from features.daily import commands as daily_commands
        esperado = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(daily_script._hoy(), esperado)
        self.assertEqual(daily_commands._hoy(), esperado)


@patch("features.daily.daily_script.generar_desafios_del_dia", side_effect=_desafios_fijos)
class TestNotificarProgreso(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def test_sin_cuenta_no_avanza(self, _mock):
        _preparar_char(self.char2)
        notificar_progreso(self.char2, "apostar_ganar")
        self.assertEqual(list(self.char2.db.progreso_desafios), [0, 0, 0, 0, 0])

    def test_kill_faccion_correcta_avanza(self, _mock):
        notificar_progreso(self.char1, "kill_faccion", faccion="horda_salvaje")
        self.assertEqual(self.char1.db.progreso_desafios[0], 1)

    def test_kill_faccion_incorrecta_no_avanza(self, _mock):
        notificar_progreso(self.char1, "kill_faccion", faccion="legion_oscura")
        self.assertEqual(self.char1.db.progreso_desafios[0], 0)

    def test_recolectar_correcto_avanza(self, _mock):
        notificar_progreso(self.char1, "recolectar", profesion="mineria")
        self.assertEqual(self.char1.db.progreso_desafios[1], 1)

    def test_completar_un_desafio_da_recompensa(self, _mock):
        for _ in range(3):
            notificar_progreso(self.char1, "apostar_ganar")
        self.assertEqual(self.char1.db.experiencia, 100)
        self.assertEqual(self.char1.db.monedas, 250)
        self.assertIn(2, list(self.char1.db.desafios_completados_hoy))
        self.assertIn("DESAFÍO COMPLETADO", self.cap.all())

    def test_completar_los_5_primera_vez_racha_1_sin_bonus(self, _mock):
        _completar_los_5(self.char1)

        self.assertEqual(len(list(self.char1.db.desafios_completados_hoy)), 5)
        self.assertEqual(self.char1.db.racha_desafios, 1)
        xp_total = sum(d["recompensa_xp"] for d in _DESAFIOS_FIJOS)
        mon_total = sum(d["recompensa_monedas"] for d in _DESAFIOS_FIJOS)
        # racha 1 → bonus_racha_xp/monedas(1) == 0: el total debe ser
        # exactamente la suma de las recompensas individuales, sin extra.
        self.assertEqual(self.char1.db.experiencia, xp_total)
        self.assertEqual(self.char1.db.monedas, mon_total)

    def test_racha_continua_si_ultimo_dia_fue_ayer(self, _mock):
        hoy = _hoy_utc().isoformat()
        ayer = (_hoy_utc() - timedelta(days=1)).isoformat()
        self.char1.db.ultimo_dia_desafios = ayer
        self.char1.db.racha_desafios = 2

        _completar_los_5(self.char1)

        self.assertEqual(self.char1.db.racha_desafios, 3)
        self.assertEqual(self.char1.db.ultimo_dia_desafios, hoy)
        # bonus_racha_xp(3)=200, bonus_racha_monedas(3)=100, además de la
        # suma de recompensas individuales de los 5 desafíos.
        xp_total = sum(d["recompensa_xp"] for d in _DESAFIOS_FIJOS) + 200
        mon_total = sum(d["recompensa_monedas"] for d in _DESAFIOS_FIJOS) + 100
        self.assertEqual(self.char1.db.experiencia, xp_total)
        self.assertEqual(self.char1.db.monedas, mon_total)

    def test_racha_se_reinicia_si_ultimo_dia_no_fue_ayer(self, _mock):
        """
        Regresión directa: racha_desafios no se resetea a 0 cuando la
        racha se rompe (solo se sobrescribe la próxima vez que se
        completan los 5) — con un ultimo_dia_desafios antiguo, completar
        hoy debe dar racha 1, no racha_desafios_guardada + 1.
        """
        self.char1.db.ultimo_dia_desafios = "2020-01-01"
        self.char1.db.racha_desafios = 7

        _completar_los_5(self.char1)

        self.assertEqual(self.char1.db.racha_desafios, 1)

    def test_reset_progreso_en_nuevo_dia(self, _mock):
        self.char1.db.fecha_desafios = "2000-01-01"
        self.char1.db.progreso_desafios = [5, 5, 5, 5, 5]
        self.char1.db.desafios_completados_hoy = [0, 1, 2, 3, 4]

        notificar_progreso(self.char1, "kill_faccion", faccion="horda_salvaje")

        self.assertEqual(list(self.char1.db.progreso_desafios), [1, 0, 0, 0, 0])
        self.assertEqual(list(self.char1.db.desafios_completados_hoy), [])


@patch("features.daily.daily_script.generar_desafios_del_dia", side_effect=_desafios_fijos)
@patch("features.daily.commands.generar_desafios_del_dia", side_effect=_desafios_fijos)
class TestCmdDesafios(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.cap = _MsgCapture(self.char1)

    def _desafios(self, args=""):
        cmd = _make_cmd(CmdDesafios, self.char1, args)
        cmd.func()

    def test_muestra_los_5_desafios(self, _m1, _m2):
        self._desafios()
        texto = self.cap.all()
        self.assertIn("[1]", texto)
        self.assertIn("[5]", texto)

    def test_subcomando_racha(self, _m1, _m2):
        self.char1.db.racha_desafios = 3
        self._desafios("racha")
        self.assertIn("3", self.cap.all())

    def test_preview_bonus_no_aparece_con_racha_rota(self, _m1, _m2):
        """
        Regresión end-to-end del bug de previsualización (ver
        systems/daily/daily.py::racha_si_completa_hoy): racha_desafios
        alta pero ultimo_dia_desafios NO es ayer → la racha ya está
        rota, completar hoy daría racha 1 (bonus 0) — el comando no debe
        prometer un bonus que _completar_todos() nunca otorgaría.
        """
        self.char1.db.racha_desafios = 5
        self.char1.db.ultimo_dia_desafios = "2020-01-01"
        self._desafios()
        self.assertNotIn("Bonus", self.cap.all())

    def test_preview_bonus_aparece_con_racha_viva(self, _m1, _m2):
        ayer = (_hoy_utc() - timedelta(days=1)).isoformat()
        self.char1.db.racha_desafios = 2
        self.char1.db.ultimo_dia_desafios = ayer
        self._desafios()
        self.assertIn("Bonus", self.cap.all())


class TestDespachoRealCmdDesafios(EvenniaTest):
    def setUp(self):
        super().setUp()
        _preparar_char(self.char1)
        self.char1.location = self.room1
        self.cap = _MsgCapture(self.char1)

    def test_comando_desafios_real_responde(self):
        self.char1.execute_cmd("desafios")
        self.assertIn("Desafíos del Día", self.cap.all())


if __name__ == "__main__":
    import unittest
    unittest.main()
