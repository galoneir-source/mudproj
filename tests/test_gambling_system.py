"""
tests/test_gambling_system.py

Tests puros del sistema de apuestas (sin dependencias de Evennia/Django).
La aleatoriedad se inyecta con callables deterministas.
"""
import pytest
from systems.gambling.gambling import (
    MIN_APUESTA, MAX_APUESTA,
    puede_apostar,
    validar_eleccion_moneda,
    validar_numero_ruleta,
    jugar_moneda,
    jugar_dados,
    jugar_cartas,
    jugar_ruleta,
    formatear_reglas,
)


# --------------------------------------------------------------------------- #
#  Helpers de inyección
# --------------------------------------------------------------------------- #

def rng_float(*vals):
    """Devuelve un callable que itera sobre vals (floats para moneda)."""
    it = iter(vals)
    return lambda: next(it)


def rng_int(*vals):
    """Devuelve un callable que itera sobre vals (ints para dados/cartas/ruleta)."""
    it = iter(vals)
    return lambda: next(it)


# --------------------------------------------------------------------------- #
#  puede_apostar
# --------------------------------------------------------------------------- #

class TestPuedeApostar:

    def test_ok_en_rango(self):
        ok, _ = puede_apostar(500, 100)
        assert ok is True

    def test_apuesta_minima_exacta(self):
        ok, _ = puede_apostar(500, MIN_APUESTA)
        assert ok is True

    def test_apuesta_maxima_exacta(self):
        ok, _ = puede_apostar(MAX_APUESTA, MAX_APUESTA)
        assert ok is True

    def test_menos_del_minimo(self):
        ok, msg = puede_apostar(500, MIN_APUESTA - 1)
        assert ok is False
        assert "mínima" in msg.lower()

    def test_mas_del_maximo(self):
        ok, msg = puede_apostar(9999, MAX_APUESTA + 1)
        assert ok is False
        assert "máxima" in msg.lower()

    def test_sin_monedas(self):
        ok, msg = puede_apostar(0, MIN_APUESTA)
        assert ok is False
        assert "suficiente" in msg.lower() or "monedas" in msg.lower()

    def test_apuesta_mayor_que_saldo(self):
        ok, msg = puede_apostar(50, 100)
        assert ok is False
        assert "suficiente" in msg.lower() or "tienes" in msg.lower()


# --------------------------------------------------------------------------- #
#  Validaciones auxiliares
# --------------------------------------------------------------------------- #

class TestValidaciones:

    def test_moneda_cara_ok(self):
        ok, _ = validar_eleccion_moneda("cara")
        assert ok is True

    def test_moneda_cruz_ok(self):
        ok, _ = validar_eleccion_moneda("cruz")
        assert ok is True

    def test_moneda_invalida(self):
        ok, msg = validar_eleccion_moneda("sello")
        assert ok is False
        assert "cara" in msg.lower() or "cruz" in msg.lower()

    def test_ruleta_1_ok(self):
        ok, _ = validar_numero_ruleta(1)
        assert ok is True

    def test_ruleta_6_ok(self):
        ok, _ = validar_numero_ruleta(6)
        assert ok is True

    def test_ruleta_0_invalido(self):
        ok, msg = validar_numero_ruleta(0)
        assert ok is False
        assert "1" in msg and "6" in msg

    def test_ruleta_7_invalido(self):
        ok, _ = validar_numero_ruleta(7)
        assert ok is False


# --------------------------------------------------------------------------- #
#  jugar_moneda
# --------------------------------------------------------------------------- #

class TestJugarMoneda:

    def test_gana_cara(self):
        r = jugar_moneda(100, "cara", _rng=rng_float(0.1))  # 0.1 < 0.5 → cara
        assert r["gano"] is True
        assert r["ganancia_neta"] == 100
        assert r["resultado"] == "cara"

    def test_pierde_cara(self):
        r = jugar_moneda(100, "cara", _rng=rng_float(0.9))  # 0.9 ≥ 0.5 → cruz
        assert r["gano"] is False
        assert r["ganancia_neta"] == -100
        assert r["resultado"] == "cruz"

    def test_gana_cruz(self):
        r = jugar_moneda(50, "cruz", _rng=rng_float(0.8))
        assert r["gano"] is True
        assert r["ganancia_neta"] == 50

    def test_pierde_cruz(self):
        r = jugar_moneda(50, "cruz", _rng=rng_float(0.2))
        assert r["gano"] is False
        assert r["ganancia_neta"] == -50

    def test_juego_en_resultado(self):
        r = jugar_moneda(10, "cara", _rng=rng_float(0.1))
        assert r["juego"] == "moneda"

    def test_descripcion_no_vacia(self):
        r = jugar_moneda(10, "cara", _rng=rng_float(0.1))
        assert r["descripcion"]

    def test_limite_gana_exacto_0_5_es_cruz(self):
        # 0.5 NO es < 0.5, por tanto → cruz
        r = jugar_moneda(10, "cara", _rng=rng_float(0.5))
        assert r["resultado"] == "cruz"


# --------------------------------------------------------------------------- #
#  jugar_dados
# --------------------------------------------------------------------------- #

class TestJugarDados:

    def test_jugador_gana(self):
        # p=6+6=12, c=1+1=2 → gana
        r = jugar_dados(100, _rng=rng_int(6, 6, 1, 1))
        assert r["gano"] is True
        assert r["ganancia_neta"] == 100
        assert r["total_jugador"] == 12
        assert r["total_casa"] == 2

    def test_jugador_pierde(self):
        # p=1+1=2, c=6+6=12 → pierde
        r = jugar_dados(100, _rng=rng_int(1, 1, 6, 6))
        assert r["gano"] is False
        assert r["ganancia_neta"] == -100

    def test_empate_gana_casa(self):
        # p=3+3=6, c=4+2=6 → empate → casa gana
        r = jugar_dados(100, _rng=rng_int(3, 3, 4, 2))
        assert r["gano"] is False
        assert r["ganancia_neta"] == -100

    def test_dados_estructura(self):
        r = jugar_dados(50, _rng=rng_int(4, 3, 2, 1))
        assert "dados_jugador" in r
        assert "dados_casa" in r
        assert r["dados_jugador"] == (4, 3)
        assert r["dados_casa"] == (2, 1)

    def test_juego_en_resultado(self):
        r = jugar_dados(10, _rng=rng_int(1, 1, 1, 1))
        assert r["juego"] == "dados"


# --------------------------------------------------------------------------- #
#  jugar_cartas
# --------------------------------------------------------------------------- #

class TestJugarCartas:

    def test_jugador_gana_rey_vs_as(self):
        # Rey(13) > As(1) → gana
        r = jugar_cartas(100, _rng=rng_int(13, 1))
        assert r["gano"] is True
        assert r["ganancia_neta"] == 100
        assert r["nombre_jugador"] == "K"
        assert r["nombre_casa"] == "As"

    def test_jugador_pierde(self):
        r = jugar_cartas(100, _rng=rng_int(1, 13))
        assert r["gano"] is False
        assert r["ganancia_neta"] == -100

    def test_empate_gana_casa(self):
        r = jugar_cartas(100, _rng=rng_int(7, 7))
        assert r["gano"] is False

    def test_naipe_j_q_k(self):
        r = jugar_cartas(10, _rng=rng_int(12, 11))
        assert r["nombre_jugador"] == "Q"
        assert r["nombre_casa"] == "J"

    def test_numero_sin_nombre_especial(self):
        r = jugar_cartas(10, _rng=rng_int(5, 3))
        assert r["nombre_jugador"] == "5"
        assert r["nombre_casa"] == "3"

    def test_juego_en_resultado(self):
        r = jugar_cartas(10, _rng=rng_int(5, 3))
        assert r["juego"] == "cartas"


# --------------------------------------------------------------------------- #
#  jugar_ruleta
# --------------------------------------------------------------------------- #

class TestJugarRuleta:

    def test_acierto_ganancia_x4(self):
        r = jugar_ruleta(100, 3, _rng=rng_int(3))
        assert r["gano"] is True
        assert r["ganancia_neta"] == 400  # 100 * 4

    def test_fallo_pierde_apuesta(self):
        r = jugar_ruleta(100, 3, _rng=rng_int(5))
        assert r["gano"] is False
        assert r["ganancia_neta"] == -100

    def test_resultado_correcto(self):
        r = jugar_ruleta(50, 6, _rng=rng_int(6))
        assert r["resultado"] == 6

    def test_juego_en_resultado(self):
        r = jugar_ruleta(10, 1, _rng=rng_int(1))
        assert r["juego"] == "ruleta"

    def test_ganancia_neta_proporcional(self):
        r = jugar_ruleta(200, 2, _rng=rng_int(2))
        assert r["ganancia_neta"] == 800  # 200 * 4


# --------------------------------------------------------------------------- #
#  formatear_reglas
# --------------------------------------------------------------------------- #

class TestFormatearReglas:

    def test_no_vacio(self):
        assert formatear_reglas()

    def test_menciona_todos_los_juegos(self):
        txt = formatear_reglas()
        for juego in ("moneda", "dados", "cartas", "ruleta"):
            assert juego in txt

    def test_menciona_limites(self):
        txt = formatear_reglas()
        assert str(MIN_APUESTA) in txt
        assert str(MAX_APUESTA) in txt


# --------------------------------------------------------------------------- #
#  Propiedades invariantes
# --------------------------------------------------------------------------- #

class TestInvariantes:

    def test_moneda_gano_implica_ganancia_positiva(self):
        r = jugar_moneda(100, "cara", _rng=rng_float(0.1))
        assert r["gano"] == (r["ganancia_neta"] > 0)

    def test_dados_gano_implica_ganancia_positiva(self):
        r = jugar_dados(100, _rng=rng_int(6, 6, 1, 1))
        assert r["gano"] == (r["ganancia_neta"] > 0)

    def test_cartas_gano_implica_ganancia_positiva(self):
        r = jugar_cartas(100, _rng=rng_int(13, 1))
        assert r["gano"] == (r["ganancia_neta"] > 0)

    def test_ruleta_gano_implica_ganancia_positiva(self):
        r = jugar_ruleta(100, 3, _rng=rng_int(3))
        assert r["gano"] == (r["ganancia_neta"] > 0)

    def test_todos_tienen_campo_gano(self):
        for r in [
            jugar_moneda(10, "cara", _rng=rng_float(0.1)),
            jugar_dados(10, _rng=rng_int(1, 1, 1, 1)),
            jugar_cartas(10, _rng=rng_int(5, 3)),
            jugar_ruleta(10, 1, _rng=rng_int(2)),
        ]:
            assert "gano" in r
            assert "ganancia_neta" in r
            assert "descripcion" in r
            assert "juego" in r
