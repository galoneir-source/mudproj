"""
tests/test_fast_travel_system.py

Tests puros (pytest, sin Django) para systems/fast_travel/fast_travel.py.
"""
from systems.fast_travel.fast_travel import (
    COSTE_VIAJE,
    COOLDOWN_SEGUNDOS,
    destinos_disponibles,
    buscar_destino,
    puede_pagar,
    cooldown_restante,
    formatear_destinos,
)

ZONAS_INFO = [
    ("plaza_ciudad", "Plaza de la Ciudad", "Ciudad"),
    ("taberna", "Taberna El Jabalí Borracho", "Ciudad"),
    ("bosque_norte", "Bosque del Norte", "Bosque"),
]

ZONAS_A_DBREF = {
    "plaza_ciudad": "#10",
    "taberna": "#11",
    "bosque_norte": "#12",
}


# --------------------------------------------------------------------------- #
#  destinos_disponibles
# --------------------------------------------------------------------------- #

def test_destinos_disponibles_filtra_por_exploradas():
    destinos = destinos_disponibles(["#10", "#12"], ZONAS_A_DBREF, ZONAS_INFO)
    zona_ids = [d[0] for d in destinos]
    assert zona_ids == ["plaza_ciudad", "bosque_norte"]


def test_destinos_disponibles_vacio_sin_exploracion():
    assert destinos_disponibles([], ZONAS_A_DBREF, ZONAS_INFO) == []


def test_destinos_disponibles_ignora_zonas_no_construidas():
    destinos = destinos_disponibles(["#10"], {}, ZONAS_INFO)
    assert destinos == []


# --------------------------------------------------------------------------- #
#  buscar_destino
# --------------------------------------------------------------------------- #

def test_buscar_destino_exacto():
    destinos = destinos_disponibles(["#10", "#11"], ZONAS_A_DBREF, ZONAS_INFO)
    resultado = buscar_destino("Taberna El Jabalí Borracho", destinos)
    assert resultado[0] == "taberna"


def test_buscar_destino_parcial_unico():
    destinos = destinos_disponibles(["#10", "#11"], ZONAS_A_DBREF, ZONAS_INFO)
    resultado = buscar_destino("taberna", destinos)
    assert resultado[0] == "taberna"


def test_buscar_destino_ambiguo_devuelve_none():
    destinos = destinos_disponibles(["#10", "#11", "#12"], ZONAS_A_DBREF, ZONAS_INFO)
    resultado = buscar_destino("a", destinos)  # coincide con varias
    assert resultado is None


def test_buscar_destino_no_encontrado():
    destinos = destinos_disponibles(["#10"], ZONAS_A_DBREF, ZONAS_INFO)
    assert buscar_destino("Catacumbas", destinos) is None


def test_buscar_destino_vacio():
    destinos = destinos_disponibles(["#10"], ZONAS_A_DBREF, ZONAS_INFO)
    assert buscar_destino("", destinos) is None


# --------------------------------------------------------------------------- #
#  puede_pagar
# --------------------------------------------------------------------------- #

def test_puede_pagar_suficientes_monedas():
    ok, _ = puede_pagar(COSTE_VIAJE)
    assert ok

def test_puede_pagar_insuficientes_monedas():
    ok, msg = puede_pagar(COSTE_VIAJE - 1)
    assert not ok
    assert "monedas" in msg.lower()

def test_puede_pagar_exacto():
    ok, _ = puede_pagar(COSTE_VIAJE, coste=COSTE_VIAJE)
    assert ok


# --------------------------------------------------------------------------- #
#  cooldown_restante
# --------------------------------------------------------------------------- #

def test_cooldown_restante_sin_viaje_previo():
    assert cooldown_restante(0, 1000) == 0


def test_cooldown_restante_recien_viajado():
    restante = cooldown_restante(100, 105)
    assert restante == COOLDOWN_SEGUNDOS - 5


def test_cooldown_restante_ya_paso():
    assert cooldown_restante(100, 100 + COOLDOWN_SEGUNDOS) == 0


def test_cooldown_restante_justo_en_el_limite():
    assert cooldown_restante(100, 100 + COOLDOWN_SEGUNDOS - 1) == 1


# --------------------------------------------------------------------------- #
#  formatear_destinos
# --------------------------------------------------------------------------- #

def test_formatear_destinos_vacio():
    texto = formatear_destinos([])
    assert "no tienes ningún destino" in texto.lower()


def test_formatear_destinos_agrupa_por_area():
    destinos = destinos_disponibles(["#10", "#11", "#12"], ZONAS_A_DBREF, ZONAS_INFO)
    texto = formatear_destinos(destinos)
    assert "Ciudad" in texto
    assert "Bosque" in texto
    assert "Plaza de la Ciudad" in texto
    assert "Bosque del Norte" in texto
