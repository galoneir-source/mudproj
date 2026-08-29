"""
tests/test_expeditions_system.py

Tests puros del sistema de expediciones grupales (sin Evennia).
Ejecutar con: pytest tests/test_expeditions_system.py
"""
import pytest

from systems.expeditions.expeditions import (
    EXPEDICIONES, OLEADAS, TIPOS_VALIDOS,
    tipos_validos, oleadas_de, total_oleadas, es_oleada_jefe,
    puede_iniciar, calcular_recompensa_oleada, calcular_recompensa_total,
    calcular_bonus_completar,
    formatear_catalogo, formatear_info, formatear_progreso,
)


# --------------------------------------------------------------------------- #
#  Constantes y catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:
    def test_hay_tres_expediciones(self):
        assert len(EXPEDICIONES) == 3

    def test_tipos_validos_coinciden_con_expediciones(self):
        assert tipos_validos() == frozenset(EXPEDICIONES)

    def test_todas_tienen_campos_obligatorios(self):
        campos = {"nombre", "descripcion", "nivel_min", "miembros_min", "miembros_max", "zona_nombre"}
        for tid, exp in EXPEDICIONES.items():
            for campo in campos:
                assert campo in exp, f"{tid} falta '{campo}'"

    def test_oleadas_definidas_para_todos(self):
        for tid in EXPEDICIONES:
            assert tid in OLEADAS, f"{tid} no tiene OLEADAS"
            assert len(OLEADAS[tid]) >= 3

    def test_nivel_min_creciente(self):
        niveles = [exp["nivel_min"] for exp in EXPEDICIONES.values()]
        assert niveles == sorted(niveles)

    def test_miembros_min_validos(self):
        for exp in EXPEDICIONES.values():
            assert exp["miembros_min"] >= 2
            assert exp["miembros_min"] <= exp["miembros_max"]

    def test_bosque_profundo_nivel_min(self):
        assert EXPEDICIONES["bosque_profundo"]["nivel_min"] == 3

    def test_catacumbas_nivel_min(self):
        assert EXPEDICIONES["catacumbas_perdidas"]["nivel_min"] == 5

    def test_fortaleza_nivel_min(self):
        assert EXPEDICIONES["fortaleza_caida"]["nivel_min"] == 7


# --------------------------------------------------------------------------- #
#  Oleadas
# --------------------------------------------------------------------------- #

class TestOleadas:
    def test_oleadas_de_bosque(self):
        oleadas = oleadas_de("bosque_profundo")
        assert len(oleadas) == 3

    def test_oleadas_de_catacumbas(self):
        assert len(oleadas_de("catacumbas_perdidas")) == 4

    def test_oleadas_de_fortaleza(self):
        assert len(oleadas_de("fortaleza_caida")) == 5

    def test_oleadas_de_inexistente(self):
        assert oleadas_de("no_existe") == []

    def test_total_oleadas_bosque(self):
        assert total_oleadas("bosque_profundo") == 3

    def test_total_oleadas_fortaleza(self):
        assert total_oleadas("fortaleza_caida") == 5

    def test_total_oleadas_inexistente(self):
        assert total_oleadas("no_existe") == 0

    def test_ultima_oleada_es_jefe(self):
        for tid in EXPEDICIONES:
            n = total_oleadas(tid)
            assert es_oleada_jefe(tid, n - 1), f"{tid}: última oleada no marcada como jefe"

    def test_primera_oleada_no_es_jefe(self):
        for tid in EXPEDICIONES:
            assert not es_oleada_jefe(tid, 0)

    def test_oleadas_tienen_npcs(self):
        for tid, oleadas in OLEADAS.items():
            for i, oleada in enumerate(oleadas):
                assert len(oleada) >= 1, f"{tid} oleada {i} está vacía"
                for proto_key, cantidad in oleada:
                    assert isinstance(proto_key, str)
                    assert cantidad >= 1

    def test_jefe_bosque_es_goblin(self):
        oleadas = oleadas_de("bosque_profundo")
        ultima = oleadas[-1]
        proto_keys = [p for p, _ in ultima]
        assert "GOBLIN_JEFE" in proto_keys

    def test_jefe_catacumbas(self):
        oleadas = oleadas_de("catacumbas_perdidas")
        ultima = oleadas[-1]
        proto_keys = [p for p, _ in ultima]
        assert "CABALLERO_OSCURO" in proto_keys

    def test_jefe_fortaleza(self):
        oleadas = oleadas_de("fortaleza_caida")
        ultima = oleadas[-1]
        proto_keys = [p for p, _ in ultima]
        assert "BANDIDO_CAPITAN" in proto_keys


# --------------------------------------------------------------------------- #
#  puede_iniciar
# --------------------------------------------------------------------------- #

class TestPuedeIniciar:
    def test_ok_bosque_dos_jugadores(self):
        ok, msg = puede_iniciar("bosque_profundo", 2, [3, 4])
        assert ok
        assert msg == ""

    def test_ok_catacumbas(self):
        ok, msg = puede_iniciar("catacumbas_perdidas", 3, [5, 6, 7])
        assert ok

    def test_ok_fortaleza_tres(self):
        ok, msg = puede_iniciar("fortaleza_caida", 3, [7, 8, 9])
        assert ok

    def test_ok_fortaleza_cuatro(self):
        ok, msg = puede_iniciar("fortaleza_caida", 4, [7, 7, 7, 7])
        assert ok

    def test_tipo_invalido(self):
        ok, msg = puede_iniciar("no_existe", 2, [5, 5])
        assert not ok
        assert "desconocida" in msg.lower() or "no_existe" in msg

    def test_pocos_miembros_bosque(self):
        ok, msg = puede_iniciar("bosque_profundo", 1, [5])
        assert not ok
        assert "menos" in msg.lower() or "2" in msg

    def test_demasiados_miembros(self):
        ok, msg = puede_iniciar("bosque_profundo", 5, [5, 5, 5, 5, 5])
        assert not ok
        assert "4" in msg or "máximo" in msg.lower()

    def test_nivel_bajo(self):
        ok, msg = puede_iniciar("bosque_profundo", 2, [3, 2])
        assert not ok
        assert "nivel" in msg.lower() or "3" in msg

    def test_nivel_exacto_minimo(self):
        ok, _ = puede_iniciar("bosque_profundo", 2, [3, 3])
        assert ok

    def test_fortaleza_pocos_miembros(self):
        ok, msg = puede_iniciar("fortaleza_caida", 2, [9, 9])
        assert not ok
        assert "3" in msg

    def test_nivel_bajo_un_miembro(self):
        ok, msg = puede_iniciar("catacumbas_perdidas", 2, [5, 4])
        assert not ok


# --------------------------------------------------------------------------- #
#  Recompensas
# --------------------------------------------------------------------------- #

class TestRecompensas:
    def test_recompensa_oleada_es_positiva(self):
        rec = calcular_recompensa_oleada("bosque_profundo", 2)
        assert rec["xp"] > 0
        assert rec["monedas"] > 0

    def test_recompensa_total_mayor_que_oleada(self):
        total = calcular_recompensa_total("bosque_profundo", 2)
        por_oleada = calcular_recompensa_oleada("bosque_profundo", 2)
        assert total["xp"] > por_oleada["xp"]
        assert total["monedas"] > por_oleada["monedas"]

    def test_mas_miembros_mas_recompensa(self):
        rec2 = calcular_recompensa_oleada("bosque_profundo", 2)
        rec4 = calcular_recompensa_oleada("bosque_profundo", 4)
        assert rec4["xp"] >= rec2["xp"]
        assert rec4["monedas"] >= rec2["monedas"]

    def test_fortaleza_mayor_recompensa_que_bosque(self):
        bosque = calcular_recompensa_total("bosque_profundo", 2)
        fort = calcular_recompensa_total("fortaleza_caida", 3)
        assert fort["xp"] > bosque["xp"]
        assert fort["monedas"] > bosque["monedas"]

    def test_recompensa_oleada_catacumbas_mayor_que_bosque(self):
        bosque = calcular_recompensa_oleada("bosque_profundo", 2)
        cat = calcular_recompensa_oleada("catacumbas_perdidas", 2)
        assert cat["xp"] >= bosque["xp"]

    def test_recompensa_total_incluye_bonus(self):
        # El total = por_oleada × num_oleadas + bonus_completar
        # Verificamos que el total > suma_oleadas
        n = total_oleadas("bosque_profundo")
        por_oleada = calcular_recompensa_oleada("bosque_profundo", 2)
        total = calcular_recompensa_total("bosque_profundo", 2)
        assert total["xp"] > por_oleada["xp"] * n

    def test_recompensa_total_es_oleadas_mas_bonus(self):
        # calcular_recompensa_total() es exactamente la suma de lo pagado
        # oleada a oleada (calcular_recompensa_oleada() × total_oleadas())
        # más el bonus de completar -- no el bonus solo ni el doble.
        n = total_oleadas("fortaleza_caida")
        por_oleada = calcular_recompensa_oleada("fortaleza_caida", 3)
        bonus = calcular_bonus_completar("fortaleza_caida", 3)
        total = calcular_recompensa_total("fortaleza_caida", 3)
        assert total["xp"] == por_oleada["xp"] * n + bonus["xp"]
        assert total["monedas"] == por_oleada["monedas"] * n + bonus["monedas"]

    def test_bonus_completar_no_incluye_oleadas(self):
        bonus = calcular_bonus_completar("bosque_profundo", 2)
        total = calcular_recompensa_total("bosque_profundo", 2)
        assert 0 < bonus["xp"] < total["xp"]
        assert 0 < bonus["monedas"] < total["monedas"]


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormatearCatalogo:
    def test_contiene_todos_los_nombres(self):
        txt = formatear_catalogo()
        for exp in EXPEDICIONES.values():
            assert exp["nombre"] in txt

    def test_contiene_nivel_min(self):
        txt = formatear_catalogo()
        assert "3" in txt   # bosque nivel_min
        assert "5" in txt   # catacumbas
        assert "7" in txt   # fortaleza

    def test_contiene_instrucciones(self):
        txt = formatear_catalogo()
        assert "iniciar" in txt.lower()

    def test_contiene_oleadas(self):
        txt = formatear_catalogo()
        assert "Oleada" in txt or "oleada" in txt


class TestFormatearInfo:
    def test_contiene_nombre(self):
        txt = formatear_info("bosque_profundo")
        assert "Bosque Profundo" in txt

    def test_contiene_descripcion(self):
        txt = formatear_info("bosque_profundo")
        assert "criaturas" in txt.lower() or "bosque" in txt.lower()

    def test_contiene_recompensas(self):
        txt = formatear_info("bosque_profundo")
        assert "XP" in txt or "xp" in txt or "monedas" in txt.lower()

    def test_inexistente(self):
        txt = formatear_info("no_existe")
        assert "no encontrada" in txt.lower() or "error" in txt.lower() or "no_existe" in txt

    def test_catacumbas(self):
        txt = formatear_info("catacumbas_perdidas")
        assert "Catacumbas" in txt


class TestFormatearProgreso:
    def test_muestra_oleada_actual(self):
        txt = formatear_progreso("bosque_profundo", 0)
        assert "1/3" in txt

    def test_muestra_oleada_final(self):
        txt = formatear_progreso("bosque_profundo", 2)
        assert "3/3" in txt

    def test_contiene_nombre_expedicion(self):
        txt = formatear_progreso("bosque_profundo", 0)
        assert "Bosque Profundo" in txt

    def test_contiene_barra(self):
        txt = formatear_progreso("catacumbas_perdidas", 2)
        assert "█" in txt or "░" in txt

    def test_tipo_inexistente_vacio(self):
        txt = formatear_progreso("no_existe", 0)
        assert txt == ""

    def test_muestra_oleada_intermedia_fortaleza(self):
        txt = formatear_progreso("fortaleza_caida", 2)
        assert "3/5" in txt
