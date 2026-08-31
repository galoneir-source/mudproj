"""
tests/test_alchemy_system.py

Tests puros del sistema de alquimia avanzada (sin Evennia).
Ejecutar con: pytest tests/test_alchemy_system.py
"""
import pytest

from systems.alchemy.alchemy import (
    RECETAS, RANGOS, POCIONES_POR_RANGO,
    rango_desde_pociones, pociones_para_siguiente_rango,
    recetas_disponibles, puede_elaborar, buscar_receta,
    formatear_recetas, formatear_info_receta,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:
    def test_hay_9_recetas(self):
        assert len(RECETAS) == 9

    def test_tres_rangos(self):
        assert RANGOS == ["aprendiz", "artesano", "maestro"]

    def test_todas_tienen_campos_obligatorios(self):
        campos = {"nombre", "descripcion", "rango", "ingredientes", "resultado"}
        for rid, rec in RECETAS.items():
            for campo in campos:
                assert campo in rec, f"{rid} falta campo '{campo}'"

    def test_resultado_tiene_campos(self):
        campos_res = {"key", "desc", "efecto", "potencia", "stat_buff", "duracion", "valor"}
        for rid, rec in RECETAS.items():
            for campo in campos_res:
                assert campo in rec["resultado"], f"{rid}.resultado falta '{campo}'"

    def test_rangos_validos(self):
        for rid, rec in RECETAS.items():
            assert rec["rango"] in RANGOS, f"{rid} rango inválido: {rec['rango']}"

    def test_tres_recetas_por_rango(self):
        for rango in RANGOS:
            n = sum(1 for rec in RECETAS.values() if rec["rango"] == rango)
            assert n == 3, f"Rango '{rango}' tiene {n} recetas, se esperaban 3"

    def test_ingredientes_son_dicts_no_vacios(self):
        for rid, rec in RECETAS.items():
            assert isinstance(rec["ingredientes"], dict)
            assert len(rec["ingredientes"]) >= 1

    def test_cantidades_positivas(self):
        for rid, rec in RECETAS.items():
            for nombre, cnt in rec["ingredientes"].items():
                assert cnt >= 1, f"{rid}: ingrediente '{nombre}' cantidad {cnt}"

    def test_pociones_rango_artesano(self):
        assert POCIONES_POR_RANGO["artesano"] == 5

    def test_pociones_rango_maestro(self):
        assert POCIONES_POR_RANGO["maestro"] == 15


# --------------------------------------------------------------------------- #
#  Rangos
# --------------------------------------------------------------------------- #

class TestRangoDesde:
    def test_cero_es_aprendiz(self):
        assert rango_desde_pociones(0) == "aprendiz"

    def test_cuatro_es_aprendiz(self):
        assert rango_desde_pociones(4) == "aprendiz"

    def test_cinco_es_artesano(self):
        assert rango_desde_pociones(5) == "artesano"

    def test_catorce_es_artesano(self):
        assert rango_desde_pociones(14) == "artesano"

    def test_quince_es_maestro(self):
        assert rango_desde_pociones(15) == "maestro"

    def test_cien_es_maestro(self):
        assert rango_desde_pociones(100) == "maestro"


class TestPocionesSiguiente:
    def test_aprendiz_requiere_5(self):
        assert pociones_para_siguiente_rango("aprendiz") == 5

    def test_artesano_requiere_15(self):
        assert pociones_para_siguiente_rango("artesano") == 15

    def test_maestro_devuelve_none(self):
        assert pociones_para_siguiente_rango("maestro") is None


class TestRecetasDisponibles:
    def test_aprendiz_tiene_3(self):
        recs = recetas_disponibles("aprendiz")
        assert len(recs) == 3
        for rec in recs.values():
            assert rec["rango"] == "aprendiz"

    def test_artesano_tiene_6(self):
        recs = recetas_disponibles("artesano")
        assert len(recs) == 6

    def test_maestro_tiene_9(self):
        recs = recetas_disponibles("maestro")
        assert len(recs) == 9


# --------------------------------------------------------------------------- #
#  puede_elaborar
# --------------------------------------------------------------------------- #

class TestPuedeElaborar:
    def _inv(self, **kwargs):
        return {k.lower(): v for k, v in kwargs.items()}

    def test_ok_balsamo(self):
        inv = self._inv(**{"hierba medicinal": 3})
        ok, msg = puede_elaborar("balsamo_regenerador", "aprendiz", inv)
        assert ok
        assert msg == ""

    def test_ok_antidoto(self):
        inv = self._inv(**{"hierba medicinal": 1, "raíz de pantano": 1})
        ok, _ = puede_elaborar("antidoto_reforzado", "aprendiz", inv)
        assert ok

    def test_falta_ingrediente(self):
        inv = self._inv(**{"hierba medicinal": 2})
        ok, msg = puede_elaborar("balsamo_regenerador", "aprendiz", inv)
        assert not ok
        assert "hierba medicinal" in msg.lower()

    def test_falta_un_ingrediente_de_dos(self):
        inv = self._inv(**{"hierba medicinal": 1})
        ok, msg = puede_elaborar("antidoto_reforzado", "aprendiz", inv)
        assert not ok
        assert "raíz de pantano" in msg.lower()

    def test_inventario_vacio(self):
        ok, msg = puede_elaborar("balsamo_regenerador", "aprendiz", {})
        assert not ok

    def test_rango_insuficiente_artesano(self):
        inv = self._inv(**{"flor silvestre": 2})
        ok, msg = puede_elaborar("elixir_reflejos", "aprendiz", inv)
        assert not ok
        assert "artesano" in msg.lower() or "rango" in msg.lower()

    def test_rango_insuficiente_maestro(self):
        inv = self._inv(**{"extracto raro": 2})
        ok, msg = puede_elaborar("esencia_eternidad", "artesano", inv)
        assert not ok
        assert "maestro" in msg.lower()

    def test_artesano_puede_receta_aprendiz(self):
        inv = self._inv(**{"hierba medicinal": 3})
        ok, _ = puede_elaborar("balsamo_regenerador", "artesano", inv)
        assert ok

    def test_maestro_puede_todas(self):
        inv = self._inv(**{"extracto raro": 2})
        ok, _ = puede_elaborar("esencia_eternidad", "maestro", inv)
        assert ok

    def test_receta_invalida(self):
        ok, msg = puede_elaborar("no_existe", "aprendiz", {})
        assert not ok
        assert "desconocida" in msg.lower() or "no_existe" in msg

    def test_cantidad_exacta_ok(self):
        inv = self._inv(**{"raíz de pantano": 2})
        ok, _ = puede_elaborar("pocion_sigilo_menor", "aprendiz", inv)
        assert ok

    def test_cantidad_insuficiente_por_uno(self):
        inv = self._inv(**{"raíz de pantano": 1})
        ok, _ = puede_elaborar("pocion_sigilo_menor", "aprendiz", inv)
        assert not ok


# --------------------------------------------------------------------------- #
#  buscar_receta
# --------------------------------------------------------------------------- #

class TestBuscarReceta:
    def test_id_exacto(self):
        assert buscar_receta("balsamo_regenerador") == "balsamo_regenerador"

    def test_nombre_parcial(self):
        assert buscar_receta("balsamo") == "balsamo_regenerador"

    def test_nombre_parcial_maestro(self):
        assert buscar_receta("esencia") == "esencia_eternidad"

    def test_no_encontrado(self):
        assert buscar_receta("xyzzy_no_existe") is None

    def test_nombre_completo_receta(self):
        assert buscar_receta("Bálsamo Regenerador") == "balsamo_regenerador"

    def test_antidoto(self):
        assert buscar_receta("antidoto") == "antidoto_reforzado"

    def test_nombre_completo_exacto_prioriza_sobre_receta_mas_larga(self):
        # Regresión: "poción de sigilo" es el nombre EXACTO de una receta,
        # pero también es prefijo de "poción de sigilo menor" -- sin
        # priorizar la coincidencia exacta de nombre, ambas entraban como
        # candidatas por startswith y la receta se trataba como ambigua
        # (None) pese a que el jugador escribió un nombre exacto y sin
        # ambigüedad real. Mismo patrón "poción de vida" / "poción de vida
        # mayor" ya corregido en CmdComprar (tienda).
        assert buscar_receta("poción de sigilo") == "pocion_sigilo"
        assert buscar_receta("Poción de Sigilo") == "pocion_sigilo"
        assert buscar_receta("poción de sigilo menor") == "pocion_sigilo_menor"


# --------------------------------------------------------------------------- #
#  Efectos de resultado
# --------------------------------------------------------------------------- #

class TestEfectosResultado:
    def test_balsamo_cura_hp(self):
        assert RECETAS["balsamo_regenerador"]["resultado"]["efecto"] == "curar_hp"
        assert RECETAS["balsamo_regenerador"]["resultado"]["potencia"] == 60

    def test_antidoto_efecto_especial(self):
        assert RECETAS["antidoto_reforzado"]["resultado"]["efecto"] == "curar_veneno_protegido"

    def test_sigilo_menor_efecto(self):
        res = RECETAS["pocion_sigilo_menor"]["resultado"]
        assert res["efecto"] == "sigilo"
        assert res["potencia"] == 120

    def test_sigilo_mayor_duracion(self):
        res = RECETAS["pocion_sigilo"]["resultado"]
        assert res["efecto"] == "sigilo"
        assert res["potencia"] > 120

    def test_elixir_reflejos_destreza(self):
        res = RECETAS["elixir_reflejos"]["resultado"]
        assert res["efecto"] == "buff_stat"
        assert res["stat_buff"] == "destreza"
        assert res["potencia"] >= 5

    def test_pocion_arcana_inteligencia(self):
        res = RECETAS["pocion_arcana"]["resultado"]
        assert res["stat_buff"] == "inteligencia"

    def test_gran_elixir_cura_maximo(self):
        assert RECETAS["gran_elixir_vida"]["resultado"]["efecto"] == "curar_maximo"

    def test_elixir_maestro_fuerza(self):
        res = RECETAS["elixir_maestro"]["resultado"]
        assert res["stat_buff"] == "fuerza"
        assert res["potencia"] >= 8

    def test_esencia_eternidad_buff_xp(self):
        res = RECETAS["esencia_eternidad"]["resultado"]
        assert res["efecto"] == "buff_xp"
        assert res["potencia"] == 0.25


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormatearRecetas:
    def test_contiene_nombre_receta(self):
        txt = formatear_recetas("aprendiz")
        assert "Bálsamo Regenerador" in txt

    def test_aprendiz_ve_solo_aprendiz(self):
        txt = formatear_recetas("aprendiz")
        assert "Elixir de Reflejos" not in txt or "✗" in txt

    def test_maestro_ve_todo(self):
        txt = formatear_recetas("maestro")
        assert "Esencia de la Eternidad" in txt
        assert "Bálsamo Regenerador" in txt

    def test_contiene_instrucciones(self):
        txt = formatear_recetas("aprendiz")
        assert "elaborar" in txt.lower()

    def test_muestra_rango_actual(self):
        txt = formatear_recetas("artesano")
        assert "artesano" in txt.lower() or "Artesano" in txt

    def test_muestra_siguiente_rango_aprendiz(self):
        txt = formatear_recetas("aprendiz")
        assert "5" in txt

    def test_maestro_no_muestra_siguiente(self):
        txt = formatear_recetas("maestro")
        assert "Siguiente rango" not in txt


class TestFormatearInfoReceta:
    def test_contiene_nombre(self):
        txt = formatear_info_receta("balsamo_regenerador")
        assert "Bálsamo Regenerador" in txt

    def test_contiene_ingredientes(self):
        txt = formatear_info_receta("balsamo_regenerador")
        assert "hierba medicinal" in txt.lower()

    def test_contiene_rango(self):
        txt = formatear_info_receta("balsamo_regenerador")
        assert "aprendiz" in txt.lower()

    def test_receta_inexistente(self):
        txt = formatear_info_receta("no_existe")
        assert "no encontrada" in txt.lower() or "no_existe" in txt

    def test_receta_maestro_muestra_rango(self):
        txt = formatear_info_receta("esencia_eternidad")
        assert "maestro" in txt.lower()
