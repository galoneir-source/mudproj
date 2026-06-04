"""
tests/test_time_system.py

Tests unitarios puros para systems/time/clock.py y la integración
con systems/perception/perception_manager.py. Sin Django ni Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && python -m pytest tests/test_time_system.py -v
"""
from systems.time.clock import (
    periodo_del_dia,
    penalizacion_percepcion,
    texto_ambiente,
    hora_a_texto,
    TEXTOS_AMBIENTE,
    MENSAJES_TRANSICION,
    PERIODOS,
)
from systems.perception.perception_manager import PerceptionManager


# --------------------------------------------------------------------------- #
#  periodo_del_dia
# --------------------------------------------------------------------------- #

class TestPeriodoDelDia:
    def test_noche_medianoche(self):
        pid, _, _ = periodo_del_dia(0)
        assert pid == "noche"

    def test_noche_madrugada(self):
        pid, _, _ = periodo_del_dia(3)
        assert pid == "noche"

    def test_amanecer_inicio(self):
        pid, _, _ = periodo_del_dia(5)
        assert pid == "amanecer"

    def test_amanecer_medio(self):
        pid, _, _ = periodo_del_dia(6)
        assert pid == "amanecer"

    def test_manana_inicio(self):
        pid, _, _ = periodo_del_dia(7)
        assert pid == "manana"

    def test_manana_medio(self):
        pid, _, _ = periodo_del_dia(10)
        assert pid == "manana"

    def test_mediodia_inicio(self):
        pid, _, _ = periodo_del_dia(12)
        assert pid == "mediodia"

    def test_tarde_inicio(self):
        pid, _, _ = periodo_del_dia(14)
        assert pid == "tarde"

    def test_tarde_medio(self):
        pid, _, _ = periodo_del_dia(17)
        assert pid == "tarde"

    def test_anochecer_inicio(self):
        pid, _, _ = periodo_del_dia(19)
        assert pid == "anochecer"

    def test_noche_tarde(self):
        pid, _, _ = periodo_del_dia(21)
        assert pid == "noche"

    def test_noche_fin(self):
        pid, _, _ = periodo_del_dia(23)
        assert pid == "noche"

    def test_devuelve_nombre_y_color(self):
        pid, nombre, color = periodo_del_dia(12)
        assert nombre == "Mediodía"
        assert color.startswith("|")

    def test_modulo_24(self):
        pid_0, _, _ = periodo_del_dia(0)
        pid_24, _, _ = periodo_del_dia(24)
        assert pid_0 == pid_24


# --------------------------------------------------------------------------- #
#  penalizacion_percepcion
# --------------------------------------------------------------------------- #

class TestPenalizacionPercepcion:
    def test_noche_penaliza_tres(self):
        assert penalizacion_percepcion(22) == -3

    def test_anochecer_penaliza_uno(self):
        assert penalizacion_percepcion(20) == -1

    def test_amanecer_penaliza_uno(self):
        assert penalizacion_percepcion(6) == -1

    def test_manana_sin_penalizacion(self):
        assert penalizacion_percepcion(9) == 0

    def test_mediodia_sin_penalizacion(self):
        assert penalizacion_percepcion(12) == 0

    def test_tarde_sin_penalizacion(self):
        assert penalizacion_percepcion(16) == 0


# --------------------------------------------------------------------------- #
#  texto_ambiente
# --------------------------------------------------------------------------- #

class TestTextoAmbiente:
    def test_devuelve_texto_no_vacio_para_todos_los_periodos(self):
        for hora in [6, 9, 13, 16, 20, 22]:
            assert texto_ambiente(hora, "exterior_natural") != ""
            assert texto_ambiente(hora, "exterior_urbano") != ""

    def test_tipo_inexistente_devuelve_vacio(self):
        assert texto_ambiente(12, "inexistente") == ""

    def test_distintos_tipos_distintos_textos(self):
        natural = texto_ambiente(9, "exterior_natural")
        urbano = texto_ambiente(9, "exterior_urbano")
        assert natural != urbano

    def test_noche_tiene_texto(self):
        assert len(texto_ambiente(23, "exterior_natural")) > 0


# --------------------------------------------------------------------------- #
#  hora_a_texto
# --------------------------------------------------------------------------- #

class TestHoraATexto:
    def test_formato_doble_digito(self):
        assert hora_a_texto(8) == "08:00"

    def test_mediodia(self):
        assert hora_a_texto(12) == "12:00"

    def test_medianoche(self):
        assert hora_a_texto(0) == "00:00"

    def test_modulo_24(self):
        assert hora_a_texto(24) == "00:00"


# --------------------------------------------------------------------------- #
#  Cobertura de datos
# --------------------------------------------------------------------------- #

class TestCoberturaData:
    def test_todos_los_periodos_tienen_mensajes_transicion(self):
        periodos_ids = {"amanecer", "manana", "mediodia", "tarde", "anochecer", "noche"}
        for pid in periodos_ids:
            assert pid in MENSAJES_TRANSICION, f"Falta transición para {pid}"

    def test_todos_los_periodos_tienen_textos_ambiente(self):
        periodos_ids = {"amanecer", "manana", "mediodia", "tarde", "anochecer", "noche"}
        for pid in periodos_ids:
            assert pid in TEXTOS_AMBIENTE
            assert "exterior_natural" in TEXTOS_AMBIENTE[pid]
            assert "exterior_urbano" in TEXTOS_AMBIENTE[pid]


# --------------------------------------------------------------------------- #
#  Integración con PerceptionManager
# --------------------------------------------------------------------------- #

class _MockObserver:
    class db:
        inteligencia = 10
        nivel = 1


class TestPercepcionConHora:
    def test_sin_hora_no_penaliza(self):
        pm = PerceptionManager()
        obs = _MockObserver()
        nivel_base = pm.nivel_percepcion(obs, hora=None)
        nivel_noche = pm.nivel_percepcion(obs, hora=22)
        assert nivel_noche < nivel_base

    def test_dia_sin_penalizacion(self):
        pm = PerceptionManager()
        obs = _MockObserver()
        nivel_base = pm.nivel_percepcion(obs, hora=None)
        nivel_dia = pm.nivel_percepcion(obs, hora=10)
        assert nivel_dia == nivel_base

    def test_noche_penaliza_tres_puntos(self):
        pm = PerceptionManager()
        obs = _MockObserver()
        nivel_base = pm.nivel_percepcion(obs, hora=None)
        nivel_noche = pm.nivel_percepcion(obs, hora=22)
        assert nivel_base - nivel_noche == 3

    def test_nivel_minimo_uno(self):
        pm = PerceptionManager()

        class ObserverDebil:
            class db:
                inteligencia = 1
                nivel = 1

        nivel = pm.nivel_percepcion(ObserverDebil(), hora=22)
        assert nivel >= 1
