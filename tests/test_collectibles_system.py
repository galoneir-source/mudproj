"""
tests/test_collectibles_system.py

Tests puros del sistema de coleccionables (sin dependencias de Evennia/Django).
"""
import pytest
from systems.collectibles.collectibles import (
    TESOROS,
    ZONA_A_TESORO,
    tesoro_de_zona,
    ya_encontrado,
    puede_buscar,
    total_tesoros,
    tesoros_encontrados_count,
    coleccion_completa,
    formatear_coleccion,
    formatear_pistas,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:

    def test_no_vacio(self):
        assert len(TESOROS) > 0

    def test_total_es_15(self):
        assert total_tesoros() == 15

    def test_todos_tienen_campos_obligatorios(self):
        campos = ("nombre", "descripcion", "pista", "zona",
                  "nivel_min", "requiere_kill", "recompensa")
        for tid, t in TESOROS.items():
            for c in campos:
                assert c in t, f"{tid} falta campo '{c}'"

    def test_recompensa_tiene_monedas(self):
        for tid, t in TESOROS.items():
            assert "monedas" in t["recompensa"], f"{tid} sin monedas en recompensa"
            assert t["recompensa"]["monedas"] > 0

    def test_zonas_unicas(self):
        zonas = [t["zona"] for t in TESOROS.values()]
        assert len(zonas) == len(set(zonas)), "Dos tesoros en la misma zona"

    def test_zona_a_tesoro_coincide(self):
        for tid, t in TESOROS.items():
            assert ZONA_A_TESORO[t["zona"]] == tid

    def test_tesoros_con_kill_conocidos(self):
        kills = {t["requiere_kill"] for t in TESOROS.values() if t["requiere_kill"]}
        assert len(kills) >= 3

    def test_nivel_minimo_rango_valido(self):
        for tid, t in TESOROS.items():
            assert 1 <= t["nivel_min"] <= 10, f"{tid} nivel_min fuera de rango"

    def test_tesoro_nivel_1_existe(self):
        assert any(t["nivel_min"] == 1 for t in TESOROS.values())

    def test_tesoro_nivel_10_existe(self):
        assert any(t["nivel_min"] == 10 for t in TESOROS.values())


# --------------------------------------------------------------------------- #
#  tesoro_de_zona
# --------------------------------------------------------------------------- #

class TestTesoroDEZona:

    def test_zona_con_tesoro(self):
        assert tesoro_de_zona("plaza_ciudad") == "moneda_antigua"

    def test_zona_sin_tesoro(self):
        assert tesoro_de_zona("vestibulo_portal") is None

    def test_none(self):
        assert tesoro_de_zona(None) is None

    def test_zona_inventada(self):
        assert tesoro_de_zona("zona_imaginaria") is None

    def test_altar_liche_devuelve_ceniza(self):
        assert tesoro_de_zona("altar_liche") == "ceniza_liche"


# --------------------------------------------------------------------------- #
#  ya_encontrado
# --------------------------------------------------------------------------- #

class TestYaEncontrado:

    def test_vacio(self):
        assert ya_encontrado("moneda_antigua", []) is False

    def test_encontrado(self):
        assert ya_encontrado("moneda_antigua", ["moneda_antigua"]) is True

    def test_otro_tesoro(self):
        assert ya_encontrado("moneda_antigua", ["pergamino_taberna"]) is False

    def test_lista_con_varios(self):
        assert ya_encontrado("corona_lodo", ["moneda_antigua", "corona_lodo"]) is True


# --------------------------------------------------------------------------- #
#  puede_buscar
# --------------------------------------------------------------------------- #

class TestPuedeBuscar:

    def _bestiary_con(self, *proto_keys):
        return {k: {"kills": 1, "primera_vez": 0} for k in proto_keys}

    def test_ok_sin_requisitos(self):
        ok, _ = puede_buscar("moneda_antigua", 1, {}, [])
        assert ok is True

    def test_ya_encontrado(self):
        ok, msg = puede_buscar("moneda_antigua", 10, {}, ["moneda_antigua"])
        assert ok is False
        assert "encontraste" in msg.lower() or "ya" in msg.lower()

    def test_nivel_insuficiente(self):
        ok, msg = puede_buscar("ceniza_liche", 5, {}, [])
        assert ok is False
        assert "nivel" in msg.lower()

    def test_nivel_exacto_ok(self):
        ok, _ = puede_buscar("ceniza_liche", 10, self._bestiary_con("LICHE_INMORTAL"), [])
        assert ok is True

    def test_requiere_kill_sin_bestiary(self):
        ok, msg = puede_buscar("corona_lodo", 10, {}, [])
        assert ok is False
        assert "derrotar" in msg.lower() or "troll" in msg.lower()

    def test_requiere_kill_con_bestiary(self):
        ok, _ = puede_buscar("corona_lodo", 10, self._bestiary_con("TROLL"), [])
        assert ok is True

    def test_requiere_kill_kills_cero(self):
        bestiary = {"TROLL": {"kills": 0, "primera_vez": 0}}
        ok, _ = puede_buscar("corona_lodo", 10, bestiary, [])
        assert ok is False

    def test_sello_baron_requiere_caballero(self):
        ok, _ = puede_buscar("sello_baron", 10, self._bestiary_con("CABALLERO_OSCURO"), [])
        assert ok is True

    def test_desconocido_falla(self):
        ok, _ = puede_buscar("tesoro_inventado", 10, {}, [])
        assert ok is False

    def test_no_modifica_lista_original(self):
        original = ["moneda_antigua"]
        puede_buscar("pergamino_taberna", 1, {}, original)
        assert original == ["moneda_antigua"]


# --------------------------------------------------------------------------- #
#  tesoros_encontrados_count
# --------------------------------------------------------------------------- #

class TestTesorosEncontradosCount:

    def test_vacio(self):
        assert tesoros_encontrados_count([]) == 0

    def test_uno(self):
        assert tesoros_encontrados_count(["moneda_antigua"]) == 1

    def test_varios(self):
        assert tesoros_encontrados_count(["moneda_antigua", "pergamino_taberna"]) == 2

    def test_deduplicacion(self):
        assert tesoros_encontrados_count(["moneda_antigua", "moneda_antigua"]) == 1


# --------------------------------------------------------------------------- #
#  coleccion_completa
# --------------------------------------------------------------------------- #

class TestColeccionCompleta:

    def test_vacio(self):
        assert coleccion_completa([]) is False

    def test_parcial(self):
        assert coleccion_completa(["moneda_antigua"]) is False

    def test_completa(self):
        assert coleccion_completa(list(TESOROS.keys())) is True

    def test_falta_uno(self):
        casi_todos = [tid for tid in TESOROS if tid != "ceniza_liche"]
        assert coleccion_completa(casi_todos) is False


# --------------------------------------------------------------------------- #
#  formatear_coleccion
# --------------------------------------------------------------------------- #

class TestFormatearColeccion:

    def test_sin_nada(self):
        txt = formatear_coleccion([])
        assert "0/15" in txt
        assert "0%" in txt

    def test_con_uno(self):
        txt = formatear_coleccion(["moneda_antigua"])
        assert "1/15" in txt
        assert "Moneda Antigua" in txt

    def test_completa(self):
        txt = formatear_coleccion(list(TESOROS.keys()))
        assert "15/15" in txt
        assert "100%" in txt

    def test_muestra_todos_los_nombres(self):
        txt = formatear_coleccion([])
        for t in TESOROS.values():
            assert t["nombre"] in txt

    def test_hallado_con_checkmark(self):
        txt = formatear_coleccion(["moneda_antigua"])
        assert "✔" in txt

    def test_no_hallado_con_x(self):
        txt = formatear_coleccion([])
        assert "✗" in txt


# --------------------------------------------------------------------------- #
#  formatear_pistas
# --------------------------------------------------------------------------- #

class TestFormatearPistas:

    def test_sin_nada_muestra_todas(self):
        txt = formatear_pistas([])
        assert "15" in txt

    def test_completa_da_felicitacion(self):
        txt = formatear_pistas(list(TESOROS.keys()))
        assert "todos" in txt.lower() or "hallado" in txt.lower()

    def test_muestra_texto_de_pista(self):
        txt = formatear_pistas([])
        # Al menos una pista debe aparecer
        pistas = [t["pista"][:20] for t in TESOROS.values()]
        assert any(p in txt for p in pistas)

    def test_con_uno_encontrado_reduce_lista(self):
        txt_0 = formatear_pistas([])
        txt_1 = formatear_pistas(["moneda_antigua"])
        assert len(txt_1) < len(txt_0)
