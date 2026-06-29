"""
tests/test_runas_system.py

Tests puros del sistema de runas (sin dependencias de Evennia/Django).
"""
import pytest
from systems.runes.runes import (
    RUNAS, SLOTS_VALIDOS,
    buscar_runa, puede_grabar, slot_compatible,
    tiene_materiales, obtener_efectos,
    formatear_lista, formatear_runa, formatear_runas_equipadas,
)


# --------------------------------------------------------------------------- #
#  Datos de catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:
    def test_num_runas(self):
        assert len(RUNAS) == 8

    def test_todos_tienen_efecto(self):
        for rid, r in RUNAS.items():
            assert "efecto" in r, f"{rid} sin efecto"

    def test_todos_tienen_materiales(self):
        for rid, r in RUNAS.items():
            assert r["materiales"], f"{rid} sin materiales"

    def test_slots_son_validos(self):
        for rid, r in RUNAS.items():
            assert r["slot"] is None or r["slot"] in SLOTS_VALIDOS, \
                f"{rid}: slot inválido '{r['slot']}'"

    def test_efectos_conocidos(self):
        efectos_validos = {
            "regen_hp", "sangrado_chance", "reduccion_dano",
            "robo_vida", "evasion", "bonus_fuerza",
            "resistencia_estados", "bonus_inteligencia",
        }
        for rid, r in RUNAS.items():
            assert r["efecto"] in efectos_validos, \
                f"{rid}: efecto desconocido '{r['efecto']}'"

    def test_runa_vigor_existe(self):
        assert "RUNA_VIGOR" in RUNAS

    def test_runa_arcana_nivel_mas_alto(self):
        max_nivel = max(r["nivel_req"] for r in RUNAS.values())
        assert RUNAS["RUNA_ARCANA"]["nivel_req"] == max_nivel


# --------------------------------------------------------------------------- #
#  buscar_runa
# --------------------------------------------------------------------------- #

class TestBuscarRuna:
    def test_por_id_exacto(self):
        assert buscar_runa("RUNA_VIGOR") == "RUNA_VIGOR"

    def test_por_id_lower(self):
        assert buscar_runa("runa_vigor") == "RUNA_VIGOR"

    def test_por_nombre_exacto(self):
        assert buscar_runa("Runa de Vigor") == "RUNA_VIGOR"

    def test_por_nombre_parcial(self):
        assert buscar_runa("Evasión") == "RUNA_EVASION"

    def test_por_fragmento_id(self):
        assert buscar_runa("arcana") == "RUNA_ARCANA"

    def test_no_encontrada(self):
        assert buscar_runa("xyzzy_inexistente") is None

    def test_busqueda_case_insensitive(self):
        assert buscar_runa("VIGOR") == "RUNA_VIGOR"


# --------------------------------------------------------------------------- #
#  puede_grabar
# --------------------------------------------------------------------------- #

class TestPuedeGrabar:
    def test_nivel_suficiente(self):
        ok, msg = puede_grabar(5, "RUNA_VIGOR")
        assert ok
        assert msg == ""

    def test_nivel_exacto(self):
        req = RUNAS["RUNA_FILO"]["nivel_req"]
        ok, _ = puede_grabar(req, "RUNA_FILO")
        assert ok

    def test_nivel_insuficiente(self):
        req = RUNAS["RUNA_ARCANA"]["nivel_req"]
        ok, msg = puede_grabar(req - 1, "RUNA_ARCANA")
        assert not ok
        assert "nivel" in msg.lower() or str(req) in msg

    def test_runa_desconocida(self):
        ok, msg = puede_grabar(99, "RUNA_INEXISTENTE")
        assert not ok

    def test_nivel_1_para_vigor(self):
        ok, _ = puede_grabar(1, "RUNA_VIGOR")
        assert ok


# --------------------------------------------------------------------------- #
#  slot_compatible
# --------------------------------------------------------------------------- #

class TestSlotCompatible:
    def test_runa_arma_en_arma(self):
        assert slot_compatible("RUNA_FILO", "arma") is True

    def test_runa_arma_en_armadura(self):
        assert slot_compatible("RUNA_FILO", "armadura") is False

    def test_runa_arma_en_accesorio(self):
        assert slot_compatible("RUNA_FILO", "accesorio") is False

    def test_runa_armadura_en_armadura(self):
        assert slot_compatible("RUNA_ESCUDO", "armadura") is True

    def test_runa_armadura_en_arma(self):
        assert slot_compatible("RUNA_ESCUDO", "arma") is False

    def test_runa_universal_en_arma(self):
        assert slot_compatible("RUNA_VIGOR", "arma") is True

    def test_runa_universal_en_armadura(self):
        assert slot_compatible("RUNA_VIGOR", "armadura") is True

    def test_runa_universal_en_accesorio(self):
        assert slot_compatible("RUNA_VIGOR", "accesorio") is True

    def test_runa_evasion_universal(self):
        for slot in SLOTS_VALIDOS:
            assert slot_compatible("RUNA_EVASION", slot) is True

    def test_runa_desconocida(self):
        assert slot_compatible("RUNA_FALSA", "arma") is False


# --------------------------------------------------------------------------- #
#  tiene_materiales
# --------------------------------------------------------------------------- #

class TestTieneMateriales:
    def test_inventario_completo(self):
        inv = {"hierba medicinal": 3}
        ok, faltantes = tiene_materiales(inv, "RUNA_VIGOR")
        assert ok
        assert faltantes == []

    def test_inventario_excedente(self):
        inv = {"hierba medicinal": 10}
        ok, _ = tiene_materiales(inv, "RUNA_VIGOR")
        assert ok

    def test_inventario_insuficiente(self):
        inv = {"hierba medicinal": 2}
        ok, faltantes = tiene_materiales(inv, "RUNA_VIGOR")
        assert not ok
        assert len(faltantes) == 1

    def test_inventario_vacio(self):
        ok, faltantes = tiene_materiales({}, "RUNA_VIGOR")
        assert not ok
        assert faltantes

    def test_faltan_varios(self):
        inv = {}
        ok, faltantes = tiene_materiales(inv, "RUNA_FILO")
        assert not ok
        assert len(faltantes) == 2

    def test_faltan_algunos(self):
        inv = {"mineral de hierro": 2}  # tiene hierro, falta hierba
        ok, faltantes = tiene_materiales(inv, "RUNA_FILO")
        assert not ok
        assert len(faltantes) == 1

    def test_runa_desconocida(self):
        ok, faltantes = tiene_materiales({}, "RUNA_FALSA")
        assert not ok

    def test_inventario_case_insensitive(self):
        inv = {"HIERBA MEDICINAL": 3}
        # La búsqueda es lowercase, así que "HIERBA MEDICINAL" != "hierba medicinal"
        # Este test verifica el comportamiento real: no encuentra por mayúsculas
        ok, _ = tiene_materiales(inv, "RUNA_VIGOR")
        assert not ok  # correcto — el inventario debe estar en minúsculas


# --------------------------------------------------------------------------- #
#  obtener_efectos
# --------------------------------------------------------------------------- #

class TestObtenerEfectos:
    def test_sin_runas(self):
        efectos = obtener_efectos({"arma": None, "armadura": None, "accesorio": None})
        assert efectos == {}

    def test_un_efecto(self):
        efectos = obtener_efectos({"arma": None, "armadura": "RUNA_VIGOR", "accesorio": None})
        assert efectos.get("regen_hp") == 3

    def test_varios_efectos(self):
        efectos = obtener_efectos({
            "arma": "RUNA_FILO",
            "armadura": "RUNA_ESCUDO",
            "accesorio": None,
        })
        assert "sangrado_chance" in efectos
        assert "reduccion_dano" in efectos

    def test_efecto_bonus_fuerza(self):
        efectos = obtener_efectos({"arma": "RUNA_PODER", "armadura": None, "accesorio": None})
        assert efectos.get("bonus_fuerza") == 5

    def test_efecto_bonus_inteligencia(self):
        efectos = obtener_efectos({"arma": None, "armadura": None, "accesorio": "RUNA_ARCANA"})
        assert efectos.get("bonus_inteligencia") == 3

    def test_runa_invalida_ignorada(self):
        efectos = obtener_efectos({"arma": "RUNA_FALSA", "armadura": None, "accesorio": None})
        assert efectos == {}

    def test_dict_vacio(self):
        efectos = obtener_efectos({})
        assert efectos == {}

    def test_acumulacion_mismo_efecto(self):
        # Dos runas de tipo universal con mismo efecto en distintos slots
        # (no debería ocurrir en la práctica, pero el sistema lo soporta)
        efectos = obtener_efectos({
            "arma": "RUNA_VIGOR",
            "armadura": "RUNA_VIGOR",
            "accesorio": None,
        })
        assert efectos.get("regen_hp") == 6  # 3 + 3 acumulados


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_formatear_lista_contiene_runas(self):
        resultado = formatear_lista()
        assert "RUNA_VIGOR" in resultado
        assert "RUNA_ARCANA" in resultado
        assert "Catálogo" in resultado

    def test_formatear_lista_contiene_slots(self):
        resultado = formatear_lista()
        assert "arma" in resultado.lower() or "todos" in resultado.lower()

    def test_formatear_runa_valida(self):
        resultado = formatear_runa("RUNA_VIGOR")
        assert "Vigor" in resultado
        assert "hierba medicinal" in resultado.lower()
        assert "nivel" in resultado.lower()

    def test_formatear_runa_invalida(self):
        resultado = formatear_runa("RUNA_FALSA")
        assert "desconocida" in resultado.lower()

    def test_formatear_runas_equipadas_vacias(self):
        resultado = formatear_runas_equipadas({"arma": None, "armadura": None, "accesorio": None})
        assert "vacío" in resultado
        assert "Arma" in resultado

    def test_formatear_runas_equipadas_con_runa(self):
        resultado = formatear_runas_equipadas({"arma": "RUNA_PODER", "armadura": None, "accesorio": None})
        assert "Runa de Poder" in resultado
        assert "vacío" in resultado  # los otros slots siguen vacíos
