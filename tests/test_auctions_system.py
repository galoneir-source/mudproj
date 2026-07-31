"""
tests/test_auctions_system.py

Tests puros (pytest, sin Django) para systems/auctions/auctions.py.
"""
from systems.auctions.auctions import (
    PRECIO_MIN,
    PRECIO_MAX,
    DURACION_SEGUNDOS,
    validar_precio_inicial,
    puja_minima,
    validar_puja,
    subasta_expirada,
    calcular_comision,
    calcular_ganancia,
    tiempo_restante_txt,
    formatear_subasta,
)


# --------------------------------------------------------------------------- #
#  validar_precio_inicial
# --------------------------------------------------------------------------- #

def test_validar_precio_inicial_valido():
    ok, _ = validar_precio_inicial(100)
    assert ok

def test_validar_precio_inicial_no_numerico():
    ok, msg = validar_precio_inicial("abc")
    assert not ok
    assert "número" in msg.lower()

def test_validar_precio_inicial_bajo_minimo():
    ok, msg = validar_precio_inicial(PRECIO_MIN - 1)
    assert not ok
    assert "mínimo" in msg.lower()

def test_validar_precio_inicial_sobre_maximo():
    ok, msg = validar_precio_inicial(PRECIO_MAX + 1)
    assert not ok
    assert "máximo" in msg.lower()

def test_validar_precio_inicial_en_los_limites():
    ok, _ = validar_precio_inicial(PRECIO_MIN)
    assert ok
    ok, _ = validar_precio_inicial(PRECIO_MAX)
    assert ok


# --------------------------------------------------------------------------- #
#  puja_minima
# --------------------------------------------------------------------------- #

def test_puja_minima_es_mayor_que_actual():
    assert puja_minima(100) > 100

def test_puja_minima_al_menos_un_incremento_de_uno():
    assert puja_minima(1) >= 2  # precio bajo: incremento mínimo de 1

def test_puja_minima_redondea_hacia_arriba():
    # 100 * 5% = 5 exacto
    assert puja_minima(100) == 105
    # 101 * 5% = 5.05 -> redondeado hacia arriba a 6
    assert puja_minima(101) == 107


# --------------------------------------------------------------------------- #
#  validar_puja
# --------------------------------------------------------------------------- #

def test_validar_puja_ok():
    minimo = puja_minima(100)
    ok, _ = validar_puja(minimo, 100, monedas_pujador=minimo)
    assert ok

def test_validar_puja_no_numerica():
    ok, msg = validar_puja("abc", 100, monedas_pujador=1000)
    assert not ok
    assert "número" in msg.lower()

def test_validar_puja_bajo_el_minimo():
    ok, msg = validar_puja(puja_minima(100) - 1, 100, monedas_pujador=1000)
    assert not ok
    assert "mínima" in msg.lower()

def test_validar_puja_sin_fondos_suficientes():
    minimo = puja_minima(100)
    ok, msg = validar_puja(minimo, 100, monedas_pujador=minimo - 1)
    assert not ok
    assert "monedas" in msg.lower()


# --------------------------------------------------------------------------- #
#  subasta_expirada
# --------------------------------------------------------------------------- #

def test_subasta_no_expirada():
    assert not subasta_expirada(1000.0, 1000.0 + DURACION_SEGUNDOS - 1)

def test_subasta_expirada_justo_en_el_limite():
    assert subasta_expirada(1000.0, 1000.0 + DURACION_SEGUNDOS)

def test_subasta_expirada_bien_pasado_el_limite():
    assert subasta_expirada(1000.0, 1000.0 + DURACION_SEGUNDOS + 500)


# --------------------------------------------------------------------------- #
#  comisión
# --------------------------------------------------------------------------- #

def test_calcular_comision_redondea_arriba():
    assert calcular_comision(101) == 6  # 5.05 -> 6

def test_calcular_ganancia_descuenta_comision():
    precio = 200
    assert calcular_ganancia(precio) == precio - calcular_comision(precio)


# --------------------------------------------------------------------------- #
#  tiempo_restante_txt
# --------------------------------------------------------------------------- #

def test_tiempo_restante_recien_publicada():
    txt = tiempo_restante_txt(1000.0, 1000.0)
    assert txt == "30m 00s"

def test_tiempo_restante_nunca_negativo():
    txt = tiempo_restante_txt(1000.0, 1000.0 + DURACION_SEGUNDOS + 500)
    assert txt == "0m 00s"


# --------------------------------------------------------------------------- #
#  formatear_subasta
# --------------------------------------------------------------------------- #

def test_formatear_subasta_sin_pujas():
    entry = {
        "item_nombre": "espada de hierro",
        "precio_actual": 100,
        "mejor_pujador_nombre": None,
        "timestamp_inicio": 1000.0,
    }
    texto = formatear_subasta("1", entry, 1000.0)
    assert "espada de hierro" in texto
    assert "sin pujas" in texto

def test_formatear_subasta_con_puja():
    entry = {
        "item_nombre": "daga",
        "precio_actual": 150,
        "mejor_pujador_nombre": "Aldric",
        "timestamp_inicio": 1000.0,
    }
    texto = formatear_subasta("2", entry, 1000.0)
    assert "Aldric" in texto
    assert "150" in texto
