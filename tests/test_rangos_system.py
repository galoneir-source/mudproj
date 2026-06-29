"""
tests/test_rangos_system.py

Tests unitarios puros para el sistema de rangos de aventurero (v0.36.0).
Sin dependencias de Evennia; ejecutar con pytest directamente.
"""
import pytest

from systems.ranks.ranks import (
    RANGOS,
    calcular_puntuacion,
    desglose_puntuacion,
    formatear_rango,
    puntos_para_siguiente,
    rango_actual,
    siguiente_rango,
)


# ---------------------------------------------------------------------------
# calcular_puntuacion
# ---------------------------------------------------------------------------

def test_puntuacion_cero_inicial():
    assert calcular_puntuacion(1, 0, 0, 0) == 0


def test_puntuacion_nivel_aporta_desde_nivel_2():
    # nivel 1 → 0 pts; nivel 2 → 15 pts
    assert calcular_puntuacion(1, 0, 0, 0) == 0
    assert calcular_puntuacion(2, 0, 0, 0) == 15
    assert calcular_puntuacion(10, 0, 0, 0) == 135  # 9 × 15


def test_puntuacion_quests():
    assert calcular_puntuacion(1, 5, 0, 0) == 50   # 5 × 10


def test_puntuacion_logros():
    assert calcular_puntuacion(1, 0, 3, 0) == 60   # 3 × 20


def test_puntuacion_kills():
    assert calcular_puntuacion(1, 0, 0, 100) == 100


def test_puntuacion_combinada():
    # nivel 5 (4×15=60) + 8 quests (80) + 5 logros (100) + 50 kills (50) = 290
    assert calcular_puntuacion(5, 8, 5, 50) == 290


def test_puntuacion_valores_negativos_clampeados():
    assert calcular_puntuacion(-1, -5, -3, -10) == 0


def test_puntuacion_nivel_maximo():
    # nivel 10: 9 × 15 = 135
    assert calcular_puntuacion(10, 0, 0, 0) == 135


# ---------------------------------------------------------------------------
# rango_actual
# ---------------------------------------------------------------------------

def test_rango_aprendiz_en_cero():
    r = rango_actual(0)
    assert r["id"] == "aprendiz"


def test_rango_aprendiz_justo_antes_novicio():
    r = rango_actual(49)
    assert r["id"] == "aprendiz"


def test_rango_novicio_en_umbral():
    r = rango_actual(50)
    assert r["id"] == "novicio"


def test_rango_novicio_entre_umbrales():
    r = rango_actual(200)
    assert r["id"] == "novicio"


def test_rango_veterano():
    r = rango_actual(300)
    assert r["id"] == "veterano"


def test_rango_heroe():
    r = rango_actual(700)
    assert r["id"] == "heroe"


def test_rango_campeon():
    r = rango_actual(1400)
    assert r["id"] == "campeon"


def test_rango_leyenda():
    r = rango_actual(2500)
    assert r["id"] == "leyenda"


def test_rango_leyenda_mas_alla():
    r = rango_actual(9999)
    assert r["id"] == "leyenda"


# ---------------------------------------------------------------------------
# siguiente_rango
# ---------------------------------------------------------------------------

def test_siguiente_desde_aprendiz():
    sig = siguiente_rango(0)
    assert sig is not None
    assert sig["id"] == "novicio"


def test_siguiente_desde_novicio():
    sig = siguiente_rango(50)
    assert sig["id"] == "veterano"


def test_siguiente_desde_veterano():
    sig = siguiente_rango(300)
    assert sig["id"] == "heroe"


def test_siguiente_desde_heroe():
    sig = siguiente_rango(700)
    assert sig["id"] == "campeon"


def test_siguiente_desde_campeon():
    sig = siguiente_rango(1400)
    assert sig["id"] == "leyenda"


def test_siguiente_desde_leyenda_es_none():
    assert siguiente_rango(2500) is None
    assert siguiente_rango(9999) is None


# ---------------------------------------------------------------------------
# puntos_para_siguiente
# ---------------------------------------------------------------------------

def test_puntos_para_siguiente_aprendiz():
    # desde 0 faltan 50 para novicio
    assert puntos_para_siguiente(0) == 50


def test_puntos_para_siguiente_en_umbral_novicio():
    # desde 50 faltan 250 para veterano
    assert puntos_para_siguiente(50) == 250


def test_puntos_para_siguiente_parcial():
    # desde 100 faltan 200 para veterano (300 - 100)
    assert puntos_para_siguiente(100) == 200


def test_puntos_para_siguiente_en_leyenda():
    assert puntos_para_siguiente(2500) is None
    assert puntos_para_siguiente(5000) is None


# ---------------------------------------------------------------------------
# formatear_rango
# ---------------------------------------------------------------------------

def test_formatear_rango_aprendiz():
    txt = formatear_rango("aprendiz")
    assert "Aprendiz" in txt
    assert "|n" in txt


def test_formatear_rango_leyenda():
    txt = formatear_rango("leyenda")
    assert "Leyenda" in txt


def test_formatear_rango_id_desconocido():
    # Devuelve el id tal cual sin reventar
    resultado = formatear_rango("inexistente")
    assert resultado == "inexistente"


# ---------------------------------------------------------------------------
# desglose_puntuacion
# ---------------------------------------------------------------------------

def test_desglose_cero():
    d = desglose_puntuacion(1, 0, 0, 0)
    assert d == {"nivel": 0, "quests": 0, "logros": 0, "kills": 0}


def test_desglose_suma_igual_a_calcular():
    nivel, quests, logros, kills = 7, 12, 8, 200
    total = calcular_puntuacion(nivel, quests, logros, kills)
    d = desglose_puntuacion(nivel, quests, logros, kills)
    assert sum(d.values()) == total


def test_desglose_nivel():
    d = desglose_puntuacion(5, 0, 0, 0)
    assert d["nivel"] == 60    # 4 × 15
    assert d["quests"] == 0
    assert d["logros"] == 0
    assert d["kills"] == 0


def test_desglose_individual():
    d = desglose_puntuacion(1, 10, 5, 300)
    assert d["quests"] == 100   # 10 × 10
    assert d["logros"] == 100   # 5 × 20
    assert d["kills"] == 300    # 300 × 1


# ---------------------------------------------------------------------------
# Consistencia del catálogo RANGOS
# ---------------------------------------------------------------------------

def test_rangos_ordenados_por_puntos():
    puntos = [r["puntos"] for r in RANGOS]
    assert puntos == sorted(puntos)


def test_primer_rango_empieza_en_cero():
    assert RANGOS[0]["puntos"] == 0


def test_todos_los_rangos_tienen_campos_requeridos():
    for r in RANGOS:
        assert "id" in r
        assert "nombre" in r
        assert "puntos" in r
        assert "color" in r


def test_ids_unicos():
    ids = [r["id"] for r in RANGOS]
    assert len(ids) == len(set(ids))


def test_seis_rangos():
    assert len(RANGOS) == 6


# ---------------------------------------------------------------------------
# Casos de borde
# ---------------------------------------------------------------------------

def test_rango_puntuacion_exactamente_en_cada_umbral():
    for r in RANGOS:
        assert rango_actual(r["puntos"])["id"] == r["id"]


def test_rango_un_punto_antes_de_cada_umbral():
    for r in RANGOS[1:]:  # saltamos aprendiz (umbral 0)
        r_prev = rango_actual(r["puntos"] - 1)
        assert r_prev["id"] != r["id"]


def test_personaje_full_content_alcanza_campeon():
    # nivel 10, 20 quests, 31 logros, sin kills
    puntuacion = calcular_puntuacion(10, 20, 31, 0)
    # 135 + 200 + 620 = 955 → Héroe (700), no llega a Campeón (1400)
    assert rango_actual(puntuacion)["id"] == "heroe"


def test_personaje_con_kills_alcanza_campeon():
    # nivel 10, 20 quests, 31 logros, 450 kills
    puntuacion = calcular_puntuacion(10, 20, 31, 450)
    # 955 + 450 = 1405 → Campeón
    assert rango_actual(puntuacion)["id"] == "campeon"


def test_personaje_con_muchos_kills_alcanza_leyenda():
    puntuacion = calcular_puntuacion(10, 20, 31, 1600)
    # 955 + 1600 = 2555 → Leyenda
    assert rango_actual(puntuacion)["id"] == "leyenda"
