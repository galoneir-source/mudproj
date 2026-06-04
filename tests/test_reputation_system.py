"""
tests/test_reputation_system.py

Tests unitarios puros para systems/reputation/ (sin Django ni Evennia).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && python -m pytest tests/test_reputation_system.py -v
"""
import pytest
from systems.reputation.factions import FACCIONES, NIVELES_REP, REP_MINIMA, REP_MAXIMA
from systems.reputation.engine import (
    obtener_rep,
    modificar_rep,
    titulo_reputacion,
    proximo_umbral,
    descuento_tienda,
    es_enemigo,
    aplicar_rep_quest,
)


# --------------------------------------------------------------------------- #
#  obtener_rep
# --------------------------------------------------------------------------- #

class TestObtenerRep:
    def test_faccion_inexistente_devuelve_cero(self):
        assert obtener_rep({}, "ciudadanos") == 0

    def test_faccion_presente_devuelve_valor(self):
        assert obtener_rep({"ciudadanos": 1500}, "ciudadanos") == 1500

    def test_no_muta_el_dict(self):
        rep = {"ciudadanos": 100}
        obtener_rep(rep, "ciudadanos")
        assert rep == {"ciudadanos": 100}

    def test_faccion_negativa(self):
        assert obtener_rep({"horda_salvaje": -2000}, "horda_salvaje") == -2000


# --------------------------------------------------------------------------- #
#  modificar_rep
# --------------------------------------------------------------------------- #

class TestModificarRep:
    def test_incremento_basico(self):
        rep = modificar_rep({}, "ciudadanos", 500)
        assert rep["ciudadanos"] == 500

    def test_decremento_basico(self):
        rep = modificar_rep({"ciudadanos": 500}, "ciudadanos", -200)
        assert rep["ciudadanos"] == 300

    def test_no_supera_maximo(self):
        rep = modificar_rep({"ciudadanos": REP_MAXIMA - 100}, "ciudadanos", 500)
        assert rep["ciudadanos"] == REP_MAXIMA

    def test_no_baja_del_minimo(self):
        rep = modificar_rep({"horda_salvaje": REP_MINIMA + 100}, "horda_salvaje", -500)
        assert rep["horda_salvaje"] == REP_MINIMA

    def test_no_muta_dict_original(self):
        original = {"ciudadanos": 100}
        modificar_rep(original, "ciudadanos", 500)
        assert original == {"ciudadanos": 100}

    def test_nueva_faccion_parte_de_cero(self):
        rep = modificar_rep({}, "legion_oscura", -300)
        assert rep["legion_oscura"] == -300


# --------------------------------------------------------------------------- #
#  titulo_reputacion
# --------------------------------------------------------------------------- #

class TestTituloReputacion:
    def test_muy_negativo_es_enemigo(self):
        titulo, _ = titulo_reputacion(-5000)
        assert titulo == "Enemigo"

    def test_limite_inferior_enemigo(self):
        titulo, _ = titulo_reputacion(-3001)
        assert titulo == "Enemigo"

    def test_limite_superior_hostil(self):
        titulo, _ = titulo_reputacion(-3000)
        assert titulo == "Hostil"

    def test_neutral(self):
        titulo, _ = titulo_reputacion(0)
        assert titulo == "Neutral"

    def test_limite_amistoso(self):
        titulo, _ = titulo_reputacion(1000)
        assert titulo == "Amistoso"

    def test_honrado(self):
        titulo, _ = titulo_reputacion(3000)
        assert titulo == "Honrado"

    def test_venerado(self):
        titulo, _ = titulo_reputacion(6000)
        assert titulo == "Venerado"

    def test_exaltado(self):
        titulo, _ = titulo_reputacion(12000)
        assert titulo == "Exaltado"

    def test_devuelve_color(self):
        _, color = titulo_reputacion(0)
        assert color.startswith("|")


# --------------------------------------------------------------------------- #
#  proximo_umbral
# --------------------------------------------------------------------------- #

class TestProximoUmbral:
    def test_desde_neutral_siguiente_es_amistoso(self):
        faltan, titulo = proximo_umbral(0)
        assert titulo == "Amistoso"
        assert faltan == 1000

    def test_desde_amistoso_siguiente_es_honrado(self):
        faltan, titulo = proximo_umbral(2000)
        assert titulo == "Honrado"
        assert faltan == 1000

    def test_exaltado_no_tiene_siguiente(self):
        faltan, titulo = proximo_umbral(15000)
        assert faltan is None
        assert titulo == ""

    def test_desde_hostil_siguiente_es_neutral(self):
        faltan, titulo = proximo_umbral(-2000)
        assert titulo == "Neutral"
        assert faltan == 1000


# --------------------------------------------------------------------------- #
#  descuento_tienda
# --------------------------------------------------------------------------- #

class TestDescuentoTienda:
    def test_neutral_sin_descuento(self):
        assert descuento_tienda(0) == 1.0

    def test_amistoso_descuento_cinco_porciento(self):
        assert descuento_tienda(1000) == 0.95

    def test_honrado_descuento_diez_porciento(self):
        assert descuento_tienda(3000) == 0.90

    def test_venerado_descuento_quince_porciento(self):
        assert descuento_tienda(6000) == 0.85

    def test_exaltado_descuento_veinte_porciento(self):
        assert descuento_tienda(12000) == 0.80

    def test_hostil_recargo_veinte_porciento(self):
        assert descuento_tienda(-1500) == 1.20

    def test_enemigo_devuelve_none(self):
        assert descuento_tienda(-4000) is None

    def test_limite_hostil(self):
        assert descuento_tienda(-3000) == 1.20

    def test_limite_neutral(self):
        assert descuento_tienda(-1000) == 1.00


# --------------------------------------------------------------------------- #
#  es_enemigo
# --------------------------------------------------------------------------- #

class TestEsEnemigo:
    def test_neutral_no_es_enemigo(self):
        assert not es_enemigo(0)

    def test_muy_negativo_es_enemigo(self):
        assert es_enemigo(-4000)

    def test_limite_exacto_hostil_no_es_enemigo(self):
        assert not es_enemigo(-3000)

    def test_justo_debajo_es_enemigo(self):
        assert es_enemigo(-3001)


# --------------------------------------------------------------------------- #
#  aplicar_rep_quest
# --------------------------------------------------------------------------- #

class TestAplicarRepQuest:
    def test_gana_rep_positiva(self):
        rep, cambios = aplicar_rep_quest({}, {"ciudadanos": 250})
        assert rep["ciudadanos"] == 250
        assert len(cambios) == 1

    def test_pierde_rep_negativa(self):
        rep, cambios = aplicar_rep_quest({}, {"horda_salvaje": -150})
        assert rep["horda_salvaje"] == -150

    def test_multiples_facciones(self):
        rep, cambios = aplicar_rep_quest({}, {"ciudadanos": 250, "horda_salvaje": -150})
        assert rep["ciudadanos"] == 250
        assert rep["horda_salvaje"] == -150
        assert len(cambios) == 2

    def test_faccion_inexistente_ignorada(self):
        rep, cambios = aplicar_rep_quest({}, {"faccion_falsa": 999})
        assert "faccion_falsa" not in rep
        assert len(cambios) == 0

    def test_detecta_cambio_de_titulo(self):
        # De Neutral (0) a Amistoso (1000+) → cambio_titulo=True
        rep, cambios = aplicar_rep_quest({}, {"ciudadanos": 1500})
        _faccion, _delta, _titulo, _color, cambio = cambios[0]
        assert cambio is True

    def test_sin_cambio_de_titulo(self):
        # Sube dentro del mismo rango (Neutral 0→500)
        rep, cambios = aplicar_rep_quest({"ciudadanos": 0}, {"ciudadanos": 500})
        _faccion, _delta, _titulo, _color, cambio = cambios[0]
        assert cambio is False

    def test_no_muta_dict_original(self):
        original = {"ciudadanos": 100}
        aplicar_rep_quest(original, {"ciudadanos": 500})
        assert original == {"ciudadanos": 100}
