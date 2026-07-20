"""
tests/test_daily_system.py

Tests puros para systems/daily/daily.py (sin Evennia).
Ejecutar con:  /opt/evennia/mudproj/venv/bin/pytest tests/test_daily_system.py
"""
import pytest
from systems.daily.daily import (
    POOL_DESAFIOS,
    _TIPOS_VALIDOS,
    generar_desafios_del_dia,
    progreso_completado,
    actualizar_progreso,
    calcular_multiplicador_racha,
    bonus_racha_monedas,
    bonus_racha_xp,
    racha_si_completa_hoy,
    formatear_desafios,
    formatear_racha,
)


# ─── POOL ───────────────────────────────────────────────────────────────────

class TestPool:
    def test_pool_tiene_al_menos_cinco(self):
        assert len(POOL_DESAFIOS) >= 5

    def test_pool_ids_unicos(self):
        ids = [d["id"] for d in POOL_DESAFIOS]
        assert len(ids) == len(set(ids))

    def test_pool_campos_requeridos(self):
        for d in POOL_DESAFIOS:
            assert "id" in d
            assert "tipo" in d
            assert "objetivo" in d
            assert "recompensa_xp" in d
            assert "recompensa_monedas" in d
            assert "desc" in d

    def test_pool_tipos_validos(self):
        tipos = {"kill_faccion", "recolectar", "apostar_ganar", "alquimia", "expedicion"}
        for d in POOL_DESAFIOS:
            assert d["tipo"] in tipos

    def test_pool_objetivos_positivos(self):
        for d in POOL_DESAFIOS:
            assert d["objetivo"] >= 1

    def test_pool_recompensas_positivas(self):
        for d in POOL_DESAFIOS:
            assert d["recompensa_xp"] > 0
            assert d["recompensa_monedas"] > 0

    def test_pool_kill_tienen_faccion(self):
        for d in POOL_DESAFIOS:
            if d["tipo"] == "kill_faccion":
                assert "faccion" in d and d["faccion"]

    def test_pool_recolectar_tienen_profesion(self):
        for d in POOL_DESAFIOS:
            if d["tipo"] == "recolectar":
                assert "profesion" in d and d["profesion"]

    def test_tipos_validos_set(self):
        assert "kill_faccion" in _TIPOS_VALIDOS
        assert "recolectar" in _TIPOS_VALIDOS
        assert "apostar_ganar" in _TIPOS_VALIDOS
        assert "alquimia" in _TIPOS_VALIDOS
        assert "expedicion" in _TIPOS_VALIDOS

    def test_pool_desc_contiene_objetivo_placeholder(self):
        for d in POOL_DESAFIOS:
            assert "{objetivo}" in d["desc"]


# ─── GENERACIÓN DETERMINISTA ─────────────────────────────────────────────────

class TestGenerar:
    def test_retorna_cinco(self):
        desafios = generar_desafios_del_dia("2026-07-01")
        assert len(desafios) == 5

    def test_determinista_misma_fecha(self):
        a = generar_desafios_del_dia("2026-07-01")
        b = generar_desafios_del_dia("2026-07-01")
        assert [d["id"] for d in a] == [d["id"] for d in b]

    def test_diferente_fecha_diferente_resultado(self):
        a = generar_desafios_del_dia("2026-07-01")
        b = generar_desafios_del_dia("2026-07-02")
        assert [d["id"] for d in a] != [d["id"] for d in b]

    def test_todos_del_pool(self):
        ids_pool = {d["id"] for d in POOL_DESAFIOS}
        desafios = generar_desafios_del_dia("2026-07-01")
        for d in desafios:
            assert d["id"] in ids_pool

    def test_sin_duplicados(self):
        desafios = generar_desafios_del_dia("2026-07-01")
        ids = [d["id"] for d in desafios]
        assert len(ids) == len(set(ids))

    def test_retorna_copias_mutables(self):
        a = generar_desafios_del_dia("2026-07-01")
        a[0]["extra"] = "test"
        b = generar_desafios_del_dia("2026-07-01")
        assert "extra" not in b[0]

    def test_fecha_2026_01_01(self):
        desafios = generar_desafios_del_dia("2026-01-01")
        assert len(desafios) == 5

    def test_varios_dias_consecutivos_distintos(self):
        dias = [f"2026-07-{str(d).zfill(2)}" for d in range(1, 8)]
        resultados = [tuple(d["id"] for d in generar_desafios_del_dia(f)) for f in dias]
        # Al menos dos días distintos deben tener orden diferente
        assert len(set(resultados)) > 1


# ─── PROGRESO COMPLETADO ─────────────────────────────────────────────────────

class TestProgresoCompletado:
    def test_exacto(self):
        d = {"objetivo": 5}
        assert progreso_completado(d, 5) is True

    def test_superado(self):
        d = {"objetivo": 5}
        assert progreso_completado(d, 10) is True

    def test_incompleto(self):
        d = {"objetivo": 5}
        assert progreso_completado(d, 4) is False

    def test_cero(self):
        d = {"objetivo": 5}
        assert progreso_completado(d, 0) is False

    def test_objetivo_uno(self):
        d = {"objetivo": 1}
        assert progreso_completado(d, 1) is True

    def test_objetivo_uno_incompleto(self):
        d = {"objetivo": 1}
        assert progreso_completado(d, 0) is False


# ─── ACTUALIZAR PROGRESO ──────────────────────────────────────────────────────

def _desafios_de_prueba():
    return [
        {"id": "kill_bandidos", "tipo": "kill_faccion", "faccion": "bandidos", "objetivo": 3},
        {"id": "apostar", "tipo": "apostar_ganar", "objetivo": 2},
        {"id": "rec_herboristeria", "tipo": "recolectar", "profesion": "herboristeria", "objetivo": 4},
        {"id": "alquimia", "tipo": "alquimia", "objetivo": 2},
        {"id": "expedicion", "tipo": "expedicion", "objetivo": 1},
    ]


class TestActualizarProgreso:
    def test_kill_matching_faccion(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, progreso, [], "kill_faccion", {"faccion": "bandidos"}
        )
        assert nuevo[0] == 1
        assert avanzados == [0]
        assert completados == []

    def test_kill_wrong_faccion(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, progreso, [], "kill_faccion", {"faccion": "orcos"}
        )
        assert nuevo == [0, 0, 0, 0, 0]
        assert avanzados == []

    def test_kill_case_insensitive(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, _, avanzados = actualizar_progreso(
            desafios, progreso, [], "kill_faccion", {"faccion": "BANDIDOS"}
        )
        assert avanzados == [0]

    def test_kill_completa_desafio(self):
        desafios = _desafios_de_prueba()
        progreso = [2, 0, 0, 0, 0]
        nuevo, completados, _ = actualizar_progreso(
            desafios, progreso, [], "kill_faccion", {"faccion": "bandidos"}
        )
        assert nuevo[0] == 3
        assert 0 in completados

    def test_kill_ya_completado_no_cuenta(self):
        desafios = _desafios_de_prueba()
        progreso = [3, 0, 0, 0, 0]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, progreso, [0], "kill_faccion", {"faccion": "bandidos"}
        )
        assert nuevo[0] == 3
        assert avanzados == []

    def test_apostar_ganar(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, _, avanzados = actualizar_progreso(
            desafios, progreso, [], "apostar_ganar", {}
        )
        assert nuevo[1] == 1
        assert avanzados == [1]

    def test_apostar_completa(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 1, 0, 0, 0]
        nuevo, completados, _ = actualizar_progreso(
            desafios, progreso, [], "apostar_ganar", {}
        )
        assert 1 in completados

    def test_recolectar_matching_profesion(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, _, avanzados = actualizar_progreso(
            desafios, progreso, [], "recolectar", {"profesion": "herboristeria"}
        )
        assert nuevo[2] == 1
        assert avanzados == [2]

    def test_recolectar_wrong_profesion(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, _, avanzados = actualizar_progreso(
            desafios, progreso, [], "recolectar", {"profesion": "pesca"}
        )
        assert avanzados == []

    def test_alquimia(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, _, avanzados = actualizar_progreso(
            desafios, progreso, [], "alquimia", {}
        )
        assert nuevo[3] == 1
        assert avanzados == [3]

    def test_alquimia_completa(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 1, 0]
        nuevo, completados, _ = actualizar_progreso(
            desafios, progreso, [], "alquimia", {}
        )
        assert 3 in completados

    def test_expedicion(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, progreso, [], "expedicion", {}
        )
        assert nuevo[4] == 1
        assert 4 in completados
        assert avanzados == [4]

    def test_tipo_desconocido_no_avanza(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, progreso, [], "tipo_inexistente", {}
        )
        assert avanzados == []
        assert nuevo == [0, 0, 0, 0, 0]

    def test_progreso_no_muta_original(self):
        desafios = _desafios_de_prueba()
        progreso = [0, 0, 0, 0, 0]
        actualizar_progreso(desafios, progreso, [], "apostar_ganar", {})
        assert progreso == [0, 0, 0, 0, 0]

    def test_progreso_corto_se_rellena(self):
        desafios = _desafios_de_prueba()
        nuevo, _, _ = actualizar_progreso(
            desafios, [0, 0], [], "apostar_ganar", {}
        )
        assert len(nuevo) == 5

    def test_multiples_completados_misma_llamada(self):
        # Dos kill matching (no posible en la práctica con pool sin duplicados,
        # pero el contrato de actualizar_progreso debe manejarlo)
        desafios = [
            {"id": "k1", "tipo": "kill_faccion", "faccion": "bandidos", "objetivo": 1},
            {"id": "k2", "tipo": "kill_faccion", "faccion": "bandidos", "objetivo": 1},
            {"id": "a1", "tipo": "apostar_ganar", "objetivo": 2},
            {"id": "alq", "tipo": "alquimia", "objetivo": 2},
            {"id": "exp", "tipo": "expedicion", "objetivo": 1},
        ]
        nuevo, completados, avanzados = actualizar_progreso(
            desafios, [0, 0, 0, 0, 0], [], "kill_faccion", {"faccion": "bandidos"}
        )
        assert 0 in completados
        assert 1 in completados
        assert nuevo[0] == 1
        assert nuevo[1] == 1


# ─── MULTIPLICADOR DE RACHA ───────────────────────────────────────────────────

class TestMultiplicadorRacha:
    def test_racha_0(self):
        assert calcular_multiplicador_racha(0) == 1.0

    def test_racha_1(self):
        assert calcular_multiplicador_racha(1) == 1.0

    def test_racha_2(self):
        assert calcular_multiplicador_racha(2) == 1.25

    def test_racha_3(self):
        assert calcular_multiplicador_racha(3) == 1.5

    def test_racha_4(self):
        assert calcular_multiplicador_racha(4) == 2.0

    def test_racha_10(self):
        assert calcular_multiplicador_racha(10) == 2.0

    def test_racha_crece_monotonamente(self):
        vals = [calcular_multiplicador_racha(r) for r in range(1, 6)]
        for a, b in zip(vals, vals[1:]):
            assert b >= a


class TestBonusRacha:
    def test_monedas_racha_1(self):
        assert bonus_racha_monedas(1) == 0

    def test_monedas_racha_2(self):
        assert bonus_racha_monedas(2) == 50

    def test_monedas_racha_3(self):
        assert bonus_racha_monedas(3) == 100

    def test_monedas_racha_4(self):
        assert bonus_racha_monedas(4) == 200

    def test_monedas_racha_5_plus(self):
        assert bonus_racha_monedas(5) == 300
        assert bonus_racha_monedas(100) == 300

    def test_xp_racha_1(self):
        assert bonus_racha_xp(1) == 0

    def test_xp_racha_2(self):
        assert bonus_racha_xp(2) == 100

    def test_xp_racha_3(self):
        assert bonus_racha_xp(3) == 200

    def test_xp_racha_4(self):
        assert bonus_racha_xp(4) == 400

    def test_xp_racha_5_plus(self):
        assert bonus_racha_xp(5) == 600
        assert bonus_racha_xp(99) == 600

    def test_bonus_crece_con_racha(self):
        for r in range(1, 6):
            assert bonus_racha_monedas(r) >= bonus_racha_monedas(r - 1)
            assert bonus_racha_xp(r) >= bonus_racha_xp(r - 1)


# ─── FORMATEO ─────────────────────────────────────────────────────────────────

class TestFormatearDesafios:
    def _desafios(self):
        return generar_desafios_del_dia("2026-07-01")

    def test_retorna_string(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [], 1, "2026-07-01")
        assert isinstance(out, str)

    def test_contiene_fecha(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [], 1, "2026-07-01")
        assert "2026-07-01" in out

    def test_sin_progreso_sin_marcas(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [], 1, "2026-07-01")
        assert "✔" not in out

    def test_completado_muestra_marca(self):
        d = self._desafios()
        out = formatear_desafios(d, [d[0]["objetivo"]]+[0]*4, [0], 1, "2026-07-01")
        assert "✔" in out

    def test_muestra_racha(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [], 3, "2026-07-01")
        assert "3" in out

    def test_muestra_conteo_completados(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [0, 1], 1, "2026-07-01")
        assert "2/5" in out

    def test_bonus_racha_aparece_cuando_hay_racha(self):
        d = self._desafios()
        # La racha sigue viva: el último día completado fue ayer (2026-06-30).
        out = formatear_desafios(d, [0]*5, [], 2, "2026-07-01", "2026-06-30")
        assert "Bonus" in out

    def test_cinco_lineas_de_desafio(self):
        d = self._desafios()
        out = formatear_desafios(d, [0]*5, [], 1, "2026-07-01")
        # Cada desafío lleva un [N] — debe haber 5
        assert out.count("[1]") == 1
        assert out.count("[5]") == 1

    def test_bonus_previsualizado_no_asume_racha_viva_por_defecto(self):
        """
        Regresión: antes del fix, el bonus previsualizado se calculaba
        siempre como bonus_racha_xp/monedas(racha + 1), ignorando si la
        racha realmente seguía viva (último día completado == ayer). Un
        jugador con racha_desafios=4 guardada de hace una semana (racha
        ya rota, nunca se resetea a 0 en el atributo) veía prometido el
        bonus de racha 5 aunque _completar_todos() fuera a otorgarle
        racha 1 (bonus 0) al completar hoy. Sin ultimo_dia (o con un
        ultimo_dia que no es ayer), la previsualización debe reflejar el
        reinicio real: sin línea de "Bonus" porque racha 1 no da bonus.
        """
        d = self._desafios()
        out = formatear_desafios(d, [0] * 5, [], 4, "2026-07-01")
        assert "Bonus" not in out

    def test_bonus_previsualizado_se_reinicia_si_no_fue_ayer(self):
        d = self._desafios()
        # ultimo_dia_desafios es de hace varios días, no ayer → racha rota.
        out_roto = formatear_desafios(d, [0] * 5, [], 4, "2026-07-05", "2026-06-30")
        out_vivo = formatear_desafios(d, [0] * 5, [], 4, "2026-07-05", "2026-07-04")
        assert "Bonus" not in out_roto
        assert "Bonus" in out_vivo

    def test_bonus_previsualizado_usa_racha_real_si_ya_completo_hoy(self):
        """Si ya completó los 5 hoy, `racha` YA es el valor real otorgado
        por _completar_todos — no debe previsualizarse racha+1 encima."""
        d = self._desafios()
        out = formatear_desafios(d, [0] * 5, [0, 1, 2, 3, 4], 1, "2026-07-01")
        assert "Bonus" not in out


class TestRachaSiCompletaHoy:
    def test_continua_si_ultimo_dia_fue_ayer(self):
        assert racha_si_completa_hoy(3, "2026-06-30", "2026-07-01") == 4

    def test_reinicia_si_ultimo_dia_no_fue_ayer(self):
        assert racha_si_completa_hoy(3, "2026-06-20", "2026-07-01") == 1

    def test_reinicia_si_nunca_completo(self):
        assert racha_si_completa_hoy(0, None, "2026-07-01") == 1

    def test_reinicia_incluso_con_racha_alta_guardada(self):
        # racha_desafios nunca se resetea a 0 en el atributo — solo se
        # sobrescribe la próxima vez que se completan los 5 de un día.
        assert racha_si_completa_hoy(10, "2026-05-01", "2026-07-01") == 1


class TestFormatearRacha:
    def test_retorna_string(self):
        out = formatear_racha(5, "2026-06-30", 25)
        assert isinstance(out, str)

    def test_muestra_racha(self):
        out = formatear_racha(7, "2026-06-30", 35)
        assert "7" in out

    def test_muestra_ultimo_dia(self):
        out = formatear_racha(3, "2026-06-30", 15)
        assert "2026-06-30" in out

    def test_muestra_total(self):
        out = formatear_racha(2, "2026-06-29", 10)
        assert "10" in out

    def test_nunca(self):
        out = formatear_racha(0, None, 0)
        assert "nunca" in out
