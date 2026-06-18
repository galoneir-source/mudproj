"""
tests/test_weather_system.py

Tests unitarios puros para systems/weather/weather.py.
No requieren Django ni Evennia. Ejecutar con:
  python -m pytest tests/test_weather_system.py
"""
import pytest

from systems.weather.weather import (
    CLIMAS,
    TRANSICIONES,
    PENALIZACION_PERCEPCION,
    MENSAJES_TRANSICION,
    siguiente_clima,
    penalizacion_percepcion,
    texto_ambiente_clima,
)

# --------------------------------------------------------------------------- #
#  Catálogo de climas
# --------------------------------------------------------------------------- #

def test_climas_tienen_nombre():
    for cid, data in CLIMAS.items():
        assert "nombre" in data, f"'{cid}' no tiene 'nombre'"


def test_climas_tienen_color():
    for cid, data in CLIMAS.items():
        assert "color" in data, f"'{cid}' no tiene 'color'"


def test_climas_tienen_textos_exterior_natural():
    for cid, data in CLIMAS.items():
        textos = data.get("textos", {})
        assert "exterior_natural" in textos, f"'{cid}' no tiene texto 'exterior_natural'"
        assert textos["exterior_natural"], f"'{cid}' tiene texto 'exterior_natural' vacío"


def test_climas_tienen_textos_exterior_urbano():
    for cid, data in CLIMAS.items():
        textos = data.get("textos", {})
        assert "exterior_urbano" in textos, f"'{cid}' no tiene texto 'exterior_urbano'"
        assert textos["exterior_urbano"], f"'{cid}' tiene texto 'exterior_urbano' vacío"


# --------------------------------------------------------------------------- #
#  Transiciones
# --------------------------------------------------------------------------- #

def test_transiciones_cubren_todos_los_climas():
    for cid in CLIMAS:
        assert cid in TRANSICIONES, f"No hay transiciones definidas para '{cid}'"


def test_transiciones_destinos_son_climas_validos():
    for origen, destinos in TRANSICIONES.items():
        for destino in destinos:
            assert destino in CLIMAS, (
                f"Destino inválido '{destino}' desde '{origen}'"
            )


def test_transiciones_pesos_positivos():
    for origen, destinos in TRANSICIONES.items():
        for destino, peso in destinos.items():
            assert peso > 0, f"Peso no positivo en '{origen}' → '{destino}'"


# --------------------------------------------------------------------------- #
#  siguiente_clima
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("clima", list(CLIMAS.keys()))
def test_siguiente_clima_devuelve_clima_valido(clima):
    resultado = siguiente_clima(clima)
    assert resultado in CLIMAS


def test_siguiente_clima_con_entrada_desconocida():
    resultado = siguiente_clima("clima_inexistente")
    assert resultado in CLIMAS


# --------------------------------------------------------------------------- #
#  penalizacion_percepcion
# --------------------------------------------------------------------------- #

def test_penalizacion_niebla_es_negativa():
    assert penalizacion_percepcion("niebla") < 0


def test_penalizacion_tormenta_es_negativa():
    assert penalizacion_percepcion("tormenta") < 0


def test_penalizacion_lluvia_es_negativa():
    assert penalizacion_percepcion("lluvia") < 0


def test_penalizacion_despejado_es_cero():
    assert penalizacion_percepcion("despejado") == 0


def test_penalizacion_nublado_es_cero():
    assert penalizacion_percepcion("nublado") == 0


def test_penalizacion_clima_desconocido_es_cero():
    assert penalizacion_percepcion("xyz") == 0


def test_orden_penalizaciones():
    # niebla penaliza más que tormenta, que lluvia, que nublado/despejado
    assert penalizacion_percepcion("niebla") <= penalizacion_percepcion("tormenta")
    assert penalizacion_percepcion("tormenta") <= penalizacion_percepcion("lluvia")
    assert penalizacion_percepcion("lluvia") <= penalizacion_percepcion("nublado")
    assert penalizacion_percepcion("nublado") <= penalizacion_percepcion("despejado")


# --------------------------------------------------------------------------- #
#  texto_ambiente_clima
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("clima", list(CLIMAS.keys()))
def test_texto_ambiente_natural_no_vacio(clima):
    texto = texto_ambiente_clima(clima, "exterior_natural")
    assert isinstance(texto, str) and len(texto) > 0


@pytest.mark.parametrize("clima", list(CLIMAS.keys()))
def test_texto_ambiente_urbano_no_vacio(clima):
    texto = texto_ambiente_clima(clima, "exterior_urbano")
    assert isinstance(texto, str) and len(texto) > 0


def test_texto_tipo_desconocido_devuelve_vacio():
    assert texto_ambiente_clima("despejado", "interior") == ""


def test_texto_clima_desconocido_devuelve_vacio():
    assert texto_ambiente_clima("xyz", "exterior_natural") == ""


# --------------------------------------------------------------------------- #
#  Mensajes de transición
# --------------------------------------------------------------------------- #

def test_mensajes_transicion_cubren_todos_los_climas():
    for cid in CLIMAS:
        assert cid in MENSAJES_TRANSICION, f"Falta mensaje de transición para '{cid}'"
        assert MENSAJES_TRANSICION[cid], f"Mensaje de transición vacío para '{cid}'"


# --------------------------------------------------------------------------- #
#  Integración con PerceptionManager (pura, sin Evennia)
# --------------------------------------------------------------------------- #

class _MockDb:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

class _MockObserver:
    def __init__(self, inteligencia=10, nivel=1):
        self.db = _MockDb(inteligencia=inteligencia, nivel=nivel)


def test_percepcion_penalizada_con_niebla():
    from systems.perception.perception_manager import PerceptionManager
    pm = PerceptionManager()
    obs = _MockObserver()
    sin_clima = pm.nivel_percepcion(obs)
    con_niebla = pm.nivel_percepcion(obs, clima="niebla")
    assert con_niebla < sin_clima


def test_percepcion_sin_penalizacion_con_despejado():
    from systems.perception.perception_manager import PerceptionManager
    pm = PerceptionManager()
    obs = _MockObserver()
    sin_clima = pm.nivel_percepcion(obs)
    con_despejado = pm.nivel_percepcion(obs, clima="despejado")
    assert con_despejado == sin_clima


def test_percepcion_acumula_hora_y_clima():
    from systems.perception.perception_manager import PerceptionManager
    pm = PerceptionManager()
    obs = _MockObserver()
    base = pm.nivel_percepcion(obs)
    solo_noche = pm.nivel_percepcion(obs, hora=23)       # Noche: -3
    noche_y_niebla = pm.nivel_percepcion(obs, hora=23, clima="niebla")  # -3 + -4
    assert noche_y_niebla < solo_noche < base
