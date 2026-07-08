"""
tests/test_bounty_system.py

Tests puros del sistema de cazarrecompensas (sin Evennia).
Ejecutar con: pytest tests/test_bounty_system.py
"""
import pytest
import time

from systems.bounty.bounty import (
    MIN_RECOMPENSA, MAX_RECOMPENSA,
    hay_recompensa, bounties_sobre, total_sobre_objetivo, bounties_de_emisor,
    puede_poner, puede_cancelar,
    añadir_bounty, cobrar_bounties, cancelar_bounty,
    formatear_tablon, formatear_mi_estado,
)


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #

def _b(objetivo="#10", emisor="#5", recompensa=200, objetivo_nombre="Valeria",
       emisor_nombre="Ragnar", fecha=None):
    return {
        "objetivo_dbref":  objetivo,
        "objetivo_nombre": objetivo_nombre,
        "emisor_dbref":    emisor,
        "emisor_nombre":   emisor_nombre,
        "recompensa":      recompensa,
        "fecha":           fecha or time.time(),
    }


@pytest.fixture
def bounties_vacias():
    return []


@pytest.fixture
def una_recompensa():
    return [_b()]


@pytest.fixture
def varias_recompensas():
    return [
        _b(objetivo="#10", emisor="#5", recompensa=200),
        _b(objetivo="#10", emisor="#6", recompensa=300, emisor_nombre="Bela"),
        _b(objetivo="#20", emisor="#5", recompensa=100, objetivo_nombre="Kael"),
    ]


# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

def test_min_recompensa():
    assert MIN_RECOMPENSA == 100

def test_max_recompensa():
    assert MAX_RECOMPENSA == 5_000


# --------------------------------------------------------------------------- #
#  Consultas
# --------------------------------------------------------------------------- #

class TestHayRecompensa:
    def test_sin_recompensas(self, bounties_vacias):
        assert not hay_recompensa("#10", bounties_vacias)

    def test_con_recompensa(self, una_recompensa):
        assert hay_recompensa("#10", una_recompensa)

    def test_otro_objetivo(self, una_recompensa):
        assert not hay_recompensa("#99", una_recompensa)

    def test_varias(self, varias_recompensas):
        assert hay_recompensa("#10", varias_recompensas)
        assert hay_recompensa("#20", varias_recompensas)
        assert not hay_recompensa("#30", varias_recompensas)


class TestBountiesSobre:
    def test_vacio(self, bounties_vacias):
        assert bounties_sobre("#10", bounties_vacias) == []

    def test_una(self, una_recompensa):
        res = bounties_sobre("#10", una_recompensa)
        assert len(res) == 1
        assert res[0]["objetivo_dbref"] == "#10"

    def test_varias_sobre_mismo(self, varias_recompensas):
        res = bounties_sobre("#10", varias_recompensas)
        assert len(res) == 2

    def test_otro_objetivo(self, varias_recompensas):
        res = bounties_sobre("#20", varias_recompensas)
        assert len(res) == 1


class TestTotalSobreObjetivo:
    def test_cero_sin_bounties(self, bounties_vacias):
        assert total_sobre_objetivo("#10", bounties_vacias) == 0

    def test_una(self, una_recompensa):
        assert total_sobre_objetivo("#10", una_recompensa) == 200

    def test_suma_varias(self, varias_recompensas):
        assert total_sobre_objetivo("#10", varias_recompensas) == 500

    def test_objetivo_menor(self, varias_recompensas):
        assert total_sobre_objetivo("#20", varias_recompensas) == 100


class TestBountiesDeEmisor:
    def test_vacio(self, bounties_vacias):
        assert bounties_de_emisor("#5", bounties_vacias) == []

    def test_emisor_con_dos(self, varias_recompensas):
        res = bounties_de_emisor("#5", varias_recompensas)
        assert len(res) == 2

    def test_emisor_con_una(self, varias_recompensas):
        res = bounties_de_emisor("#6", varias_recompensas)
        assert len(res) == 1

    def test_emisor_inexistente(self, varias_recompensas):
        assert bounties_de_emisor("#99", varias_recompensas) == []


# --------------------------------------------------------------------------- #
#  Validaciones — puede_poner
# --------------------------------------------------------------------------- #

class TestPuedePoner:
    def test_ok(self, bounties_vacias):
        ok, msg = puede_poner("#5", "#10", 500, 200, bounties_vacias)
        assert ok
        assert msg == ""

    def test_sobre_si_mismo(self, bounties_vacias):
        ok, msg = puede_poner("#5", "#5", 500, 200, bounties_vacias)
        assert not ok
        assert "ti mismo" in msg

    def test_cantidad_minima(self, bounties_vacias):
        ok, msg = puede_poner("#5", "#10", 500, 50, bounties_vacias)
        assert not ok
        assert str(MIN_RECOMPENSA) in msg

    def test_cantidad_maxima(self, bounties_vacias):
        ok, msg = puede_poner("#5", "#10", 10_000, 6_000, bounties_vacias)
        assert not ok
        assert str(MAX_RECOMPENSA) in msg

    def test_monedas_insuficientes(self, bounties_vacias):
        ok, msg = puede_poner("#5", "#10", 50, 200, bounties_vacias)
        assert not ok
        assert "suficientes" in msg

    def test_ya_existe(self, una_recompensa):
        ok, msg = puede_poner("#5", "#10", 500, 200, una_recompensa)
        assert not ok
        assert "activa" in msg

    def test_puede_si_es_otro_emisor(self, una_recompensa):
        ok, _ = puede_poner("#7", "#10", 500, 200, una_recompensa)
        assert ok

    def test_exactamente_minimo(self, bounties_vacias):
        ok, _ = puede_poner("#5", "#10", 500, MIN_RECOMPENSA, bounties_vacias)
        assert ok

    def test_exactamente_maximo(self, bounties_vacias):
        ok, _ = puede_poner("#5", "#10", 5_000, MAX_RECOMPENSA, bounties_vacias)
        assert ok


# --------------------------------------------------------------------------- #
#  Validaciones — puede_cancelar
# --------------------------------------------------------------------------- #

class TestPuedeCancelar:
    def test_ok(self, una_recompensa):
        ok, msg = puede_cancelar("#5", "#10", una_recompensa)
        assert ok
        assert msg == ""

    def test_no_existe(self, bounties_vacias):
        ok, msg = puede_cancelar("#5", "#10", bounties_vacias)
        assert not ok
        assert "activa" in msg

    def test_otro_emisor(self, una_recompensa):
        ok, msg = puede_cancelar("#99", "#10", una_recompensa)
        assert not ok

    def test_objetivo_incorrecto(self, una_recompensa):
        ok, msg = puede_cancelar("#5", "#99", una_recompensa)
        assert not ok


# --------------------------------------------------------------------------- #
#  Mutaciones
# --------------------------------------------------------------------------- #

class TestAñadirBounty:
    def test_añade_uno(self, bounties_vacias):
        nueva = _b()
        res = añadir_bounty(bounties_vacias, nueva)
        assert len(res) == 1
        assert res[0]["recompensa"] == 200

    def test_no_modifica_original(self, bounties_vacias):
        añadir_bounty(bounties_vacias, _b())
        assert len(bounties_vacias) == 0

    def test_añade_multiples(self, una_recompensa):
        nueva = _b(emisor="#7", recompensa=500)
        res = añadir_bounty(una_recompensa, nueva)
        assert len(res) == 2


class TestCobrarBounties:
    def test_cobra_todas(self, varias_recompensas):
        nueva, total = cobrar_bounties(varias_recompensas, "#10")
        assert total == 500
        assert not any(b["objetivo_dbref"] == "#10" for b in nueva)

    def test_deja_otros_objetivos(self, varias_recompensas):
        nueva, _ = cobrar_bounties(varias_recompensas, "#10")
        assert any(b["objetivo_dbref"] == "#20" for b in nueva)

    def test_sin_recompensa(self, bounties_vacias):
        nueva, total = cobrar_bounties(bounties_vacias, "#10")
        assert total == 0
        assert nueva == []

    def test_objetivo_inexistente(self, una_recompensa):
        nueva, total = cobrar_bounties(una_recompensa, "#99")
        assert total == 0
        assert len(nueva) == 1

    def test_no_modifica_original(self, varias_recompensas):
        original_len = len(varias_recompensas)
        cobrar_bounties(varias_recompensas, "#10")
        assert len(varias_recompensas) == original_len


class TestCancelarBounty:
    def test_cancela_y_reembolsa(self, una_recompensa):
        nueva, reembolso = cancelar_bounty(una_recompensa, "#5", "#10")
        assert reembolso == 200
        assert len(nueva) == 0

    def test_deja_otras(self, varias_recompensas):
        nueva, reembolso = cancelar_bounty(varias_recompensas, "#5", "#10")
        assert reembolso == 200
        # debe quedar la de emisor #6 sobre #10 y la de #5 sobre #20
        assert len(nueva) == 2

    def test_inexistente(self, bounties_vacias):
        nueva, reembolso = cancelar_bounty(bounties_vacias, "#5", "#10")
        assert reembolso == 0
        assert nueva == []

    def test_no_modifica_original(self, varias_recompensas):
        original_len = len(varias_recompensas)
        cancelar_bounty(varias_recompensas, "#5", "#10")
        assert len(varias_recompensas) == original_len


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormatearTablon:
    def test_vacio(self, bounties_vacias):
        txt = formatear_tablon(bounties_vacias)
        assert "Sin recompensas" in txt

    def test_muestra_objetivo(self, una_recompensa):
        txt = formatear_tablon(una_recompensa)
        assert "Valeria" in txt
        assert "200" in txt

    def test_muestra_emisor(self, una_recompensa):
        txt = formatear_tablon(una_recompensa)
        assert "Ragnar" in txt

    def test_ordena_por_total(self, varias_recompensas):
        txt = formatear_tablon(varias_recompensas)
        pos_valeria = txt.find("Valeria")
        pos_kael = txt.find("Kael")
        assert pos_valeria < pos_kael  # Valeria (500m) antes que Kael (100m)

    def test_varios_emisores(self, varias_recompensas):
        txt = formatear_tablon(varias_recompensas)
        # Debe mencionar múltiples emisores de Valeria
        assert "Ragnar" in txt or "Bela" in txt

    def test_menciona_comando_cazar(self, una_recompensa):
        txt = formatear_tablon(una_recompensa)
        assert "cazar" in txt.lower()


class TestFormatearMiEstado:
    def test_sin_nada(self, bounties_vacias):
        txt = formatear_mi_estado(bounties_vacias, "#5", "Ragnar")
        assert "Nadie" in txt
        assert "ninguna recompensa" in txt.lower()

    def test_tiene_precio(self, una_recompensa):
        txt = formatear_mi_estado(una_recompensa, "#10", "Valeria")
        assert "precio en tu cabeza" in txt.lower()
        assert "200" in txt

    def test_puestas_por_mi(self, una_recompensa):
        txt = formatear_mi_estado(una_recompensa, "#5", "Ragnar")
        assert "Valeria" in txt
        assert "200" in txt

    def test_nombre_jugador(self, bounties_vacias):
        txt = formatear_mi_estado(bounties_vacias, "#5", "Ragnar")
        assert "Ragnar" in txt

    def test_muestra_instrucciones(self, bounties_vacias):
        txt = formatear_mi_estado(bounties_vacias, "#5", "Ragnar")
        assert "recompensa poner" in txt.lower()
        assert "recompensa cancelar" in txt.lower()
