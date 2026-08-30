"""
tests/test_cartography_system.py

Tests puros del sistema de cartografía (sin dependencias de Evennia/Django).
"""
import pytest
from systems.cartography.cartography import (
    ZONAS_INFO, ZONAS_VALIDAS, TOTAL_SALAS,
    registrar_sala,
    total_exploradas,
    es_zona_explorable,
    formatear_mapa,
    _barra,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:

    def test_zonas_info_no_vacio(self):
        assert len(ZONAS_INFO) > 0

    def test_zonas_validas_coincide_con_info(self):
        ids_info = {z[0] for z in ZONAS_INFO}
        assert ids_info == ZONAS_VALIDAS

    def test_total_salas_coincide_con_len(self):
        assert TOTAL_SALAS == len(ZONAS_INFO)

    def test_cada_entrada_tiene_tres_campos(self):
        for entrada in ZONAS_INFO:
            assert len(entrada) == 3, f"Entrada malformada: {entrada}"

    def test_zonas_conocidas_presentes(self):
        ids = {z[0] for z in ZONAS_INFO}
        for esperada in ("plaza_ciudad", "bosque_norte", "altar_liche", "orilla_rio"):
            assert esperada in ids

    def test_ids_unicos(self):
        ids = [z[0] for z in ZONAS_INFO]
        assert len(ids) == len(set(ids))

    def test_areas_no_vacias(self):
        for _, _, area in ZONAS_INFO:
            assert area.strip()


# --------------------------------------------------------------------------- #
#  registrar_sala
# --------------------------------------------------------------------------- #

class TestRegistrarSala:

    def test_primera_visita(self):
        nueva, es_nueva = registrar_sala([], "#10")
        assert "#10" in nueva
        assert es_nueva is True

    def test_visita_repetida(self):
        base, _ = registrar_sala([], "#10")
        resultado, es_nueva = registrar_sala(base, "#10")
        assert es_nueva is False
        assert resultado.count("#10") == 1

    def test_no_modifica_original(self):
        original = ["#5"]
        registrar_sala(original, "#10")
        assert original == ["#5"]

    def test_multiples_salas_independientes(self):
        e, _ = registrar_sala([], "#1")
        e, _ = registrar_sala(e, "#2")
        e, _ = registrar_sala(e, "#3")
        assert len(e) == 3

    def test_devuelve_lista_nueva(self):
        original = ["#5"]
        nueva, _ = registrar_sala(original, "#6")
        assert nueva is not original


# --------------------------------------------------------------------------- #
#  total_exploradas
# --------------------------------------------------------------------------- #

class TestTotalExploradas:

    def test_vacio(self):
        assert total_exploradas([]) == 0

    def test_una_sala(self):
        assert total_exploradas(["#1"]) == 1

    def test_varias_salas(self):
        assert total_exploradas(["#1", "#2", "#3"]) == 3

    def test_deduplicacion(self):
        assert total_exploradas(["#1", "#1", "#2"]) == 2


# --------------------------------------------------------------------------- #
#  es_zona_explorable
# --------------------------------------------------------------------------- #

class TestEsZonaExplorable:

    def test_zona_valida(self):
        assert es_zona_explorable("plaza_ciudad") is True

    def test_zona_invalida(self):
        assert es_zona_explorable("zona_inventada") is False

    def test_none(self):
        assert es_zona_explorable(None) is False

    def test_string_vacio(self):
        assert es_zona_explorable("") is False

    def test_zona_de_mazmorra_no_en_catalogo(self):
        # Las mazmorras no deben estar en ZONAS_VALIDAS
        assert es_zona_explorable("cripta_ceniza") is False


# --------------------------------------------------------------------------- #
#  _barra
# --------------------------------------------------------------------------- #

class TestBarra:

    def test_longitud_correcta(self):
        b = _barra(5, 10, ancho=10)
        # Contar solo los caracteres visibles (sin códigos de color)
        visible = b.replace("|g", "").replace("|x", "").replace("|n", "")
        assert len(visible) == 10

    def test_vacio_todo_oscuro(self):
        b = _barra(0, 10, ancho=8)
        assert "█" not in b.replace("|g", "").replace("|x", "").replace("|n", "")

    def test_completo_todo_lleno(self):
        b = _barra(10, 10, ancho=8)
        visible = b.replace("|g", "").replace("|x", "").replace("|n", "")
        assert "░" not in visible

    def test_total_cero_no_falla(self):
        b = _barra(0, 0)
        assert b  # no lanza excepción


# --------------------------------------------------------------------------- #
#  formatear_mapa
# --------------------------------------------------------------------------- #

class TestFormatearMapa:

    def _zonas_mock(self):
        """Devuelve un dict minimal de zonas para tests."""
        return {
            "plaza_ciudad":   "#1",
            "bosque_norte":   "#2",
            "altar_liche":    "#3",
        }

    def test_sin_explorar(self):
        txt = formatear_mapa(set(), self._zonas_mock())
        assert "0/3" in txt
        assert "✗" in txt

    def test_con_una_explorada(self):
        txt = formatear_mapa({"#1"}, self._zonas_mock())
        assert "1/3" in txt
        assert "✔" in txt

    def test_completo(self):
        txt = formatear_mapa({"#1", "#2", "#3"}, self._zonas_mock())
        assert "3/3" in txt
        assert "100%" in txt

    def test_sala_no_en_zonas_ignorada(self):
        # dbref explorado que no pertenece a ninguna zona del mock
        txt = formatear_mapa({"#99"}, self._zonas_mock())
        assert "0/3" in txt

    def test_zonas_vacias_no_fallan(self):
        txt = formatear_mapa(set(), {})
        assert txt  # no lanza excepción

    def test_muestra_areas(self):
        txt = formatear_mapa(set(), self._zonas_mock())
        assert "Ciudad" in txt
        assert "Ciudadela" in txt

    def test_muestra_nombres_de_sala(self):
        txt = formatear_mapa(set(), self._zonas_mock())
        assert "Plaza de la Ciudad" in txt
        assert "Bosque del Norte" in txt

    def test_zona_no_construida_omitida(self):
        # Si una zona del ZONAS_INFO no aparece en zonas_a_dbref, se omite
        zonas = {"plaza_ciudad": "#1"}  # solo 1 de las 29 zonas
        txt = formatear_mapa(set(), zonas)
        assert "1" in txt
        # Las zonas no construidas no aparecen
        assert "Catacumbas" not in txt

    def test_pie_no_recomienda_un_comando_explorar_inexistente(self):
        """
        Regresión: desde el primer commit de este sistema (v0.46.0,
        "registrado automáticamente en Room.at_object_receive"), el
        registro de exploración siempre ha sido automático al entrar en
        la sala -- nunca ha existido ningún comando "explorar" en el
        proyecto. Pero el pie del mapa llevaba diciendo desde el
        principio "Usa 'explorar' al llegar a una sala para
        registrarla", indicando a los jugadores un comando que no existe
        para algo que ya sucede solo.
        """
        txt = formatear_mapa(set(), self._zonas_mock())
        assert "explorar" not in txt.lower()
