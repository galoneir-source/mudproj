"""
tests/test_guild_wars_system.py

Tests puros (pytest, sin Django) para systems/guild_wars/guild_wars.py.
"""
from systems.guild_wars.guild_wars import (
    TIMEOUT_RETO_SEGUNDOS,
    DURACION_GUERRA_SEGUNDOS,
    reto_expirado,
    guerra_expirada,
    rival_de,
    registrar_kill,
    determinar_ganador,
    tiempo_restante_txt,
    formatear_estado,
    formatear_resultado,
)


def _guerra(kills_a=0, kills_b=0, inicio=1000.0):
    return {
        "gremio_a": "Los Lobos",
        "gremio_b": "Cuervos Negros",
        "kills_a": kills_a,
        "kills_b": kills_b,
        "timestamp_inicio": inicio,
    }


# --------------------------------------------------------------------------- #
#  reto_expirado
# --------------------------------------------------------------------------- #

def test_reto_no_expirado():
    assert not reto_expirado(1000.0, 1000.0 + TIMEOUT_RETO_SEGUNDOS - 1)

def test_reto_expirado_en_el_limite():
    assert reto_expirado(1000.0, 1000.0 + TIMEOUT_RETO_SEGUNDOS)


# --------------------------------------------------------------------------- #
#  guerra_expirada
# --------------------------------------------------------------------------- #

def test_guerra_no_expirada():
    assert not guerra_expirada(1000.0, 1000.0 + DURACION_GUERRA_SEGUNDOS - 1)

def test_guerra_expirada_en_el_limite():
    assert guerra_expirada(1000.0, 1000.0 + DURACION_GUERRA_SEGUNDOS)


# --------------------------------------------------------------------------- #
#  rival_de
# --------------------------------------------------------------------------- #

def test_rival_de_gremio_a():
    entry = _guerra()
    assert rival_de(entry, "Los Lobos") == "Cuervos Negros"

def test_rival_de_gremio_b():
    entry = _guerra()
    assert rival_de(entry, "Cuervos Negros") == "Los Lobos"

def test_rival_de_gremio_ajeno():
    entry = _guerra()
    assert rival_de(entry, "Gremio Ajeno") is None


# --------------------------------------------------------------------------- #
#  registrar_kill
# --------------------------------------------------------------------------- #

def test_registrar_kill_incrementa_gremio_a():
    entry = _guerra()
    nuevo = registrar_kill(entry, "Los Lobos")
    assert nuevo["kills_a"] == 1
    assert nuevo["kills_b"] == 0

def test_registrar_kill_incrementa_gremio_b():
    entry = _guerra()
    nuevo = registrar_kill(entry, "Cuervos Negros")
    assert nuevo["kills_b"] == 1
    assert nuevo["kills_a"] == 0

def test_registrar_kill_no_muta_original():
    entry = _guerra()
    registrar_kill(entry, "Los Lobos")
    assert entry["kills_a"] == 0

def test_registrar_kill_gremio_ajeno_no_incrementa_nada():
    entry = _guerra()
    nuevo = registrar_kill(entry, "Gremio Ajeno")
    assert nuevo["kills_a"] == 0
    assert nuevo["kills_b"] == 0


# --------------------------------------------------------------------------- #
#  determinar_ganador
# --------------------------------------------------------------------------- #

def test_determinar_ganador_gremio_a():
    assert determinar_ganador(_guerra(kills_a=5, kills_b=2)) == "Los Lobos"

def test_determinar_ganador_gremio_b():
    assert determinar_ganador(_guerra(kills_a=1, kills_b=3)) == "Cuervos Negros"

def test_determinar_ganador_empate():
    assert determinar_ganador(_guerra(kills_a=2, kills_b=2)) is None

def test_determinar_ganador_sin_bajas_es_empate():
    assert determinar_ganador(_guerra()) is None


# --------------------------------------------------------------------------- #
#  tiempo_restante_txt
# --------------------------------------------------------------------------- #

def test_tiempo_restante_recien_iniciada():
    assert tiempo_restante_txt(1000.0, 1000.0) == "60m 00s"

def test_tiempo_restante_nunca_negativo():
    txt = tiempo_restante_txt(1000.0, 1000.0 + DURACION_GUERRA_SEGUNDOS + 500)
    assert txt == "0m 00s"


# --------------------------------------------------------------------------- #
#  formateo
# --------------------------------------------------------------------------- #

def test_formatear_estado_incluye_nombres_y_bajas():
    texto = formatear_estado(_guerra(kills_a=3, kills_b=1), 1000.0)
    assert "Los Lobos" in texto
    assert "Cuervos Negros" in texto
    assert "3" in texto
    assert "1" in texto

def test_formatear_resultado_con_ganador():
    texto = formatear_resultado(_guerra(kills_a=5, kills_b=2))
    assert "Los Lobos" in texto
    assert "vencedor" in texto.lower()

def test_formatear_resultado_empate():
    texto = formatear_resultado(_guerra(kills_a=2, kills_b=2))
    assert "empate" in texto.lower()
