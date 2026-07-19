"""Tests puros para systems/loot/rarity.py (sin dependencias de Evennia)."""

import pytest

from systems.loot.rarity import (
    RAREZAS,
    tirar_rareza,
    aplicar_rareza_bonuses,
    nombre_con_rareza,
    color_rareza,
    es_notable,
    formatear_drop,
    _TOTAL,
)


# ---------------------------------------------------------------------------
# Fixture: rng determinista
# ---------------------------------------------------------------------------

class FakeRng:
    """Objeto que simula random.randint con un valor fijo."""
    def __init__(self, value):
        self.value = value

    def randint(self, a, b):
        return self.value


# Umbrales de rareza según los pesos (comun=70, raro=25, epico=5):
#   comun: 1–70   → FakeRng(1), FakeRng(70)
#   raro:  71–95  → FakeRng(71), FakeRng(95)
#   épico: 96–100 → FakeRng(96), FakeRng(100)


# ---------------------------------------------------------------------------
# tirar_rareza
# ---------------------------------------------------------------------------

class TestTirarRareza:
    def test_total_es_100(self):
        assert _TOTAL == 100

    def test_comun_limite_bajo(self):
        assert tirar_rareza(FakeRng(1)) == "comun"

    def test_comun_limite_alto(self):
        assert tirar_rareza(FakeRng(70)) == "comun"

    def test_raro_limite_bajo(self):
        assert tirar_rareza(FakeRng(71)) == "raro"

    def test_raro_limite_alto(self):
        assert tirar_rareza(FakeRng(95)) == "raro"

    def test_epico_limite_bajo(self):
        assert tirar_rareza(FakeRng(96)) == "epico"

    def test_epico_limite_alto(self):
        assert tirar_rareza(FakeRng(100)) == "epico"

    def test_sin_rng_devuelve_rareza_valida(self):
        resultado = tirar_rareza()
        assert resultado in RAREZAS

    def test_distribucion_aproximada(self):
        """Lanza 10.000 veces y verifica que las frecuencias son razonables."""
        conteos = {"comun": 0, "raro": 0, "epico": 0}
        for _ in range(10_000):
            conteos[tirar_rareza()] += 1
        # comun ≈ 70% ± 3%
        assert 6700 < conteos["comun"] < 7300
        # raro ≈ 25% ± 3%
        assert 2200 < conteos["raro"] < 2800
        # epico ≈ 5% ± 2%
        assert 300 < conteos["epico"] < 700


# ---------------------------------------------------------------------------
# aplicar_rareza_bonuses
# ---------------------------------------------------------------------------

class TestAplicarRarezaBonuses:
    def test_comun_no_cambia(self):
        b = {"fuerza": 3, "destreza": 2}
        assert aplicar_rareza_bonuses(b, "comun") == {"fuerza": 3, "destreza": 2}

    def test_comun_no_modifica_original(self):
        b = {"fuerza": 5}
        resultado = aplicar_rareza_bonuses(b, "comun")
        assert resultado is not b

    def test_raro_multiplica_1_2(self):
        b = {"fuerza": 10}
        r = aplicar_rareza_bonuses(b, "raro")
        assert r["fuerza"] == 12   # round(10 * 1.2) = 12

    def test_epico_multiplica_1_5(self):
        b = {"inteligencia": 8}
        r = aplicar_rareza_bonuses(b, "epico")
        assert r["inteligencia"] == 12  # round(8 * 1.5) = 12

    def test_bonus_negativo_no_escala(self):
        b = {"defensa": -1}
        r = aplicar_rareza_bonuses(b, "epico")
        assert r["defensa"] == -1

    def test_resultado_minimo_1_para_positivos(self):
        # Un bonus de 1 con mult 1.2 → round(1.2) = 1, max(1, 1) = 1
        b = {"fuerza": 1}
        r = aplicar_rareza_bonuses(b, "raro")
        assert r["fuerza"] >= 1

    def test_dict_vacio(self):
        assert aplicar_rareza_bonuses({}, "epico") == {}

    def test_rareza_desconocida_trata_como_comun(self):
        b = {"fuerza": 5}
        assert aplicar_rareza_bonuses(b, "legendario") == {"fuerza": 5}

    def test_multiples_stats(self):
        b = {"fuerza": 4, "destreza": 4, "inteligencia": 4}
        r = aplicar_rareza_bonuses(b, "raro")
        # round(4 * 1.2) = round(4.8) = 5
        assert all(v == 5 for v in r.values())


# ---------------------------------------------------------------------------
# nombre_con_rareza
# ---------------------------------------------------------------------------

class TestNombreConRareza:
    def test_comun_sin_sufijo(self):
        assert nombre_con_rareza("espada de hierro", "comun") == "espada de hierro"

    def test_raro_sufijo(self):
        assert nombre_con_rareza("espada de hierro", "raro") == "espada de hierro (Raro)"

    def test_epico_sufijo(self):
        assert nombre_con_rareza("espada de hierro", "epico") == "espada de hierro (Épico)"


# ---------------------------------------------------------------------------
# color_rareza
# ---------------------------------------------------------------------------

class TestColorRareza:
    def test_comun_amarillo(self):
        assert color_rareza("comun") == "|y"

    def test_raro_cian(self):
        assert color_rareza("raro") == "|c"

    def test_epico_magenta(self):
        assert color_rareza("epico") == "|m"

    def test_desconocido_usa_comun(self):
        assert color_rareza("??") == "|y"


# ---------------------------------------------------------------------------
# es_notable
# ---------------------------------------------------------------------------

class TestEsNotable:
    def test_comun_no_notable(self):
        assert es_notable("comun") is False

    def test_raro_notable(self):
        assert es_notable("raro") is True

    def test_epico_notable(self):
        assert es_notable("epico") is True

    def test_desconocido_no_notable(self):
        assert es_notable("legendario") is False


# ---------------------------------------------------------------------------
# formatear_drop
# ---------------------------------------------------------------------------

class TestFormatearDrop:
    def test_comun_color_amarillo(self):
        txt = formatear_drop("daga de bronce", "comun")
        assert txt.startswith("|y")
        assert "daga de bronce" in txt
        assert "(Raro)" not in txt

    def test_raro_color_cian_y_sufijo(self):
        txt = formatear_drop("espada de hierro", "raro")
        assert txt.startswith("|c")
        assert "espada de hierro (Raro)" in txt

    def test_epico_color_magenta_y_sufijo(self):
        txt = formatear_drop("hacha de guerra", "epico")
        assert txt.startswith("|m")
        assert "hacha de guerra (Épico)" in txt
