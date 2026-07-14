"""
tests/test_buffs_system.py

Tests puros para systems/buffs/buffs.py (sin dependencias de Evennia).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && pytest tests/test_buffs_system.py
"""

import time
import pytest

from systems.buffs.buffs import (
    buffs_vigentes,
    aplicar_buff,
    bonus_stat,
    factor_xp,
    hay_buffs,
    formatear_buffs,
)


def _buff(tipo, bonus, expira, nombre="Test", stat=""):
    return {"tipo": tipo, "bonus": bonus, "expira": expira,
            "nombre": nombre, "stat": stat}


def _ahora():
    return time.time()


# ---------------------------------------------------------------------------
# buffs_vigentes
# ---------------------------------------------------------------------------

class TestBuffsVigentes:
    def test_lista_vacia(self):
        assert buffs_vigentes([]) == []

    def test_buff_expirado_excluido(self):
        b = _buff("buff_stat", 3, _ahora() - 10, stat="fuerza")
        assert buffs_vigentes([b]) == []

    def test_buff_activo_incluido(self):
        b = _buff("buff_stat", 3, _ahora() + 100, stat="fuerza")
        assert buffs_vigentes([b]) == [b]

    def test_mezcla_validos_expirados(self):
        activo = _buff("buff_stat", 3, _ahora() + 100, stat="destreza")
        caducado = _buff("buff_xp", 0.15, _ahora() - 1)
        resultado = buffs_vigentes([activo, caducado])
        assert resultado == [activo]


# ---------------------------------------------------------------------------
# aplicar_buff
# ---------------------------------------------------------------------------

class TestAplicarBuff:
    def test_añade_buff_a_lista_vacia(self):
        resultado = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        assert len(resultado) == 1
        assert resultado[0]["tipo"] == "buff_stat"
        assert resultado[0]["stat"] == "fuerza"
        assert resultado[0]["bonus"] == 3

    def test_sobreescribe_mismo_tipo_y_stat(self):
        base = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        nuevo = aplicar_buff(base, "buff_stat", 5, "Cerveza+", 600, "fuerza")
        assert len(nuevo) == 1
        assert nuevo[0]["bonus"] == 5

    def test_no_sobreescribe_stat_diferente(self):
        base = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        nuevo = aplicar_buff(base, "buff_stat", 3, "Vino", 1200, "destreza")
        assert len(nuevo) == 2

    def test_expira_en_el_futuro(self):
        resultado = aplicar_buff([], "buff_xp", 0.15, "Estofado", 1800)
        assert resultado[0]["expira"] > _ahora()

    def test_buff_xp_sin_stat(self):
        resultado = aplicar_buff([], "buff_xp", 0.15, "Estofado", 1800)
        assert resultado[0]["stat"] == ""


# ---------------------------------------------------------------------------
# bonus_stat
# ---------------------------------------------------------------------------

class TestBonusStat:
    def test_sin_buffs(self):
        assert bonus_stat([], "fuerza") == 0

    def test_buff_activo_fuerza(self):
        buffs = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        assert bonus_stat(buffs, "fuerza") == 3

    def test_buff_expirado_no_suma(self):
        b = _buff("buff_stat", 3, _ahora() - 1, stat="fuerza")
        assert bonus_stat([b], "fuerza") == 0

    def test_stat_equivocado_no_suma(self):
        buffs = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        assert bonus_stat(buffs, "destreza") == 0

    def test_acumula_si_stat_diferente(self):
        buffs = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        buffs = aplicar_buff(buffs, "buff_stat", 2, "Otro", 1200, "fuerza")
        # sobreescribe → sólo 1
        assert bonus_stat(buffs, "fuerza") == 2


# ---------------------------------------------------------------------------
# factor_xp
# ---------------------------------------------------------------------------

class TestFactorXp:
    def test_sin_buffs_es_uno(self):
        assert factor_xp([]) == 1.0

    def test_buff_xp_activo(self):
        buffs = aplicar_buff([], "buff_xp", 0.15, "Estofado", 1800)
        assert abs(factor_xp(buffs) - 1.15) < 1e-9

    def test_buff_xp_expirado_no_suma(self):
        b = _buff("buff_xp", 0.15, _ahora() - 1)
        assert factor_xp([b]) == 1.0

    def test_buff_stat_no_afecta_xp(self):
        buffs = aplicar_buff([], "buff_stat", 3, "Cerveza", 1200, "fuerza")
        assert factor_xp(buffs) == 1.0


# ---------------------------------------------------------------------------
# hay_buffs
# ---------------------------------------------------------------------------

class TestHayBuffs:
    def test_lista_vacia(self):
        assert hay_buffs([]) is False

    def test_todos_expirados(self):
        b = _buff("buff_stat", 3, _ahora() - 1, stat="fuerza")
        assert hay_buffs([b]) is False

    def test_uno_activo(self):
        b = _buff("buff_stat", 3, _ahora() + 100, stat="fuerza")
        assert hay_buffs([b]) is True


# ---------------------------------------------------------------------------
# formatear_buffs
# ---------------------------------------------------------------------------

class TestFormatarBuffs:
    def test_sin_buffs_lista_vacia(self):
        assert formatear_buffs([]) == []

    def test_buff_stat_formato(self):
        buffs = aplicar_buff([], "buff_stat", 3, "Cerveza de Combate", 120, "fuerza")
        lineas = formatear_buffs(buffs)
        assert len(lineas) == 1
        assert "Cerveza de Combate" in lineas[0]
        assert "+3 fuerza" in lineas[0]

    def test_buff_xp_formato(self):
        buffs = aplicar_buff([], "buff_xp", 0.15, "Estofado Vigorizante", 120)
        lineas = formatear_buffs(buffs)
        assert len(lineas) == 1
        assert "Estofado Vigorizante" in lineas[0]
        assert "+15% XP" in lineas[0]

    def test_expirados_no_aparecen(self):
        b = _buff("buff_stat", 3, _ahora() - 1, nombre="Viejo", stat="fuerza")
        assert formatear_buffs([b]) == []
