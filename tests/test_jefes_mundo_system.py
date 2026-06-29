"""
tests/test_jefes_mundo_system.py

Tests unitarios del sistema de jefes de mundo (lógica pura).
No requieren Evennia; se ejecutan con pytest directamente.
"""
import time
import pytest
from systems.world_bosses.world_bosses import (
    JEFES_MUNDO,
    puede_aparecer,
    tiempo_hasta_respawn,
    calcular_recompensas_participante,
    formatear_estado,
    formatear_lista_jefes,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:
    def test_existen_tres_jefes(self):
        assert len(JEFES_MUNDO) == 3

    def test_ids_esperados(self):
        assert "TITAN_PANTANO" in JEFES_MUNDO
        assert "GUARDIAN_FORJA" in JEFES_MUNDO
        assert "DRAGON_CENIZA" in JEFES_MUNDO

    def test_campos_requeridos(self):
        for bid, datos in JEFES_MUNDO.items():
            for campo in ("nombre", "sala_zona", "cooldown", "nivel_req",
                          "xp_total", "monedas_total", "loot_unico"):
                assert campo in datos, f"{bid} falta campo '{campo}'"

    def test_cooldowns_crecientes(self):
        cooldowns = [JEFES_MUNDO[k]["cooldown"] for k in (
            "TITAN_PANTANO", "GUARDIAN_FORJA", "DRAGON_CENIZA"
        )]
        assert cooldowns == sorted(cooldowns)

    def test_xp_creciente(self):
        xps = [JEFES_MUNDO[k]["xp_total"] for k in (
            "TITAN_PANTANO", "GUARDIAN_FORJA", "DRAGON_CENIZA"
        )]
        assert xps == sorted(xps)

    def test_nivel_req_creciente(self):
        niveles = [JEFES_MUNDO[k]["nivel_req"] for k in (
            "TITAN_PANTANO", "GUARDIAN_FORJA", "DRAGON_CENIZA"
        )]
        assert niveles == sorted(niveles)

    def test_loot_unico_diferente(self):
        loots = [d["loot_unico"] for d in JEFES_MUNDO.values()]
        assert len(loots) == len(set(loots))


# --------------------------------------------------------------------------- #
#  puede_aparecer
# --------------------------------------------------------------------------- #

class TestPuedeAparecer:
    def test_nunca_muerto_puede_aparecer(self):
        assert puede_aparecer("TITAN_PANTANO", None) is True

    def test_recien_muerto_no_puede(self):
        assert puede_aparecer("TITAN_PANTANO", time.time()) is False

    def test_cooldown_cumplido_puede(self):
        cooldown = JEFES_MUNDO["TITAN_PANTANO"]["cooldown"]
        antes = time.time() - cooldown - 1
        assert puede_aparecer("TITAN_PANTANO", antes) is True

    def test_cooldown_justo(self):
        cooldown = JEFES_MUNDO["GUARDIAN_FORJA"]["cooldown"]
        antes = time.time() - cooldown
        assert puede_aparecer("GUARDIAN_FORJA", antes) is True

    def test_boss_desconocido_usa_default(self):
        # Boss desconocido: cooldown default 6h, nunca muerto → puede aparecer
        assert puede_aparecer("NO_EXISTE", None) is True


# --------------------------------------------------------------------------- #
#  tiempo_hasta_respawn
# --------------------------------------------------------------------------- #

class TestTiempoHastaRespawn:
    def test_nunca_muerto_es_cero(self):
        assert tiempo_hasta_respawn("TITAN_PANTANO", None) == 0

    def test_recien_muerto_cercano_al_cooldown(self):
        cooldown = JEFES_MUNDO["TITAN_PANTANO"]["cooldown"]
        restante = tiempo_hasta_respawn("TITAN_PANTANO", time.time())
        # Debe ser aprox. cooldown (tolerancia 5s)
        assert abs(restante - cooldown) <= 5

    def test_cooldown_cumplido_es_cero(self):
        cooldown = JEFES_MUNDO["TITAN_PANTANO"]["cooldown"]
        antes = time.time() - cooldown - 1
        assert tiempo_hasta_respawn("TITAN_PANTANO", antes) == 0

    def test_es_entero_no_negativo(self):
        r = tiempo_hasta_respawn("DRAGON_CENIZA", time.time())
        assert isinstance(r, int)
        assert r >= 0


# --------------------------------------------------------------------------- #
#  calcular_recompensas_participante
# --------------------------------------------------------------------------- #

class TestCalcularRecompensas:
    def test_unico_participante_recibe_todo(self):
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        xp, mon = calcular_recompensas_participante("TITAN_PANTANO", 1000, 1000)
        assert xp == datos["xp_total"]
        assert mon == datos["monedas_total"]

    def test_mitad_dano_mitad_reward(self):
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        xp, mon = calcular_recompensas_participante("TITAN_PANTANO", 500, 1000)
        assert xp == datos["xp_total"] // 2
        assert mon == datos["monedas_total"] // 2

    def test_minimo_10_pct(self):
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        # Daño mínimo (1 de 10000) → fracción mínima 10%
        xp, mon = calcular_recompensas_participante("TITAN_PANTANO", 1, 10000)
        assert xp >= int(datos["xp_total"] * 0.10)
        assert mon >= int(datos["monedas_total"] * 0.10)

    def test_dano_total_cero_devuelve_cero(self):
        xp, mon = calcular_recompensas_participante("TITAN_PANTANO", 0, 0)
        assert xp == 0
        assert mon == 0

    def test_boss_desconocido_no_explota(self):
        xp, mon = calcular_recompensas_participante("NO_EXISTE", 100, 100)
        assert isinstance(xp, int)
        assert isinstance(mon, int)

    def test_reward_mayor_para_dragon(self):
        xp_titan, _ = calcular_recompensas_participante("TITAN_PANTANO", 1000, 1000)
        xp_dragon, _ = calcular_recompensas_participante("DRAGON_CENIZA", 1000, 1000)
        assert xp_dragon > xp_titan


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_estado_vivo(self):
        resultado = formatear_estado("TITAN_PANTANO", True, None)
        assert "VIVO" in resultado or "vivo" in resultado.lower()
        assert "Titán del Pantano" in resultado

    def test_estado_listo(self):
        resultado = formatear_estado("GUARDIAN_FORJA", False, None)
        assert "Listo" in resultado or "listo" in resultado.lower()

    def test_estado_con_tiempo(self):
        resultado = formatear_estado("DRAGON_CENIZA", False, time.time())
        assert "h" in resultado  # contiene horas

    def test_lista_contiene_todos(self):
        estados = {bid: False for bid in JEFES_MUNDO}
        ultimos = {bid: None for bid in JEFES_MUNDO}
        resultado = formatear_lista_jefes(estados, ultimos)
        for datos in JEFES_MUNDO.values():
            assert datos["nombre"] in resultado

    def test_lista_muestra_vivo(self):
        estados = {"TITAN_PANTANO": True, "GUARDIAN_FORJA": False, "DRAGON_CENIZA": False}
        ultimos = {bid: None for bid in JEFES_MUNDO}
        resultado = formatear_lista_jefes(estados, ultimos)
        assert "VIVO" in resultado or "vivo" in resultado.lower()
