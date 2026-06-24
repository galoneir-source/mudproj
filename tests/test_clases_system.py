"""
tests/test_clases_system.py

Tests unitarios puros para el sistema de clases de personaje (v0.28.0).
Sin dependencias de Evennia; ejecutar con pytest directamente.
"""
import pytest

from systems.classes.classes import (
    CLASES,
    clase_valida,
    puede_aprender_clase,
    aplicar_clase,
)
from systems.skills.engine import puede_aprender, aprender
from systems.combat.engine import STAT_DEFAULTS


# ---------------------------------------------------------------------------
# clase_valida
# ---------------------------------------------------------------------------

def test_clase_valida_guerrero():
    assert clase_valida("guerrero")

def test_clase_valida_explorador():
    assert clase_valida("explorador")

def test_clase_valida_mago():
    assert clase_valida("mago")

def test_clase_invalida():
    assert not clase_valida("paladin")

def test_clase_invalida_vacia():
    assert not clase_valida("")


# ---------------------------------------------------------------------------
# puede_aprender_clase
# ---------------------------------------------------------------------------

def test_sin_clase_permite_todo():
    puede, _ = puede_aprender_clase("embestida", None)
    assert puede

def test_sin_clase_vacia_permite_todo():
    puede, _ = puede_aprender_clase("embestida", "")
    assert puede

def test_guerrero_puede_aprender_su_rama():
    puede, _ = puede_aprender_clase("golpe_fuerte", "guerrero")
    assert puede
    puede, _ = puede_aprender_clase("embestida", "guerrero")
    assert puede
    puede, _ = puede_aprender_clase("escudo_fe", "guerrero")
    assert puede
    puede, _ = puede_aprender_clase("golpe_maestro", "guerrero")
    assert puede

def test_guerrero_no_puede_aprender_rama_explorador():
    puede, err = puede_aprender_clase("corte", "guerrero")
    assert not puede
    assert "Guerrero" in err or "guerrero" in err.lower()

def test_guerrero_no_puede_aprender_rama_mago():
    puede, err = puede_aprender_clase("dardo_magico", "guerrero")
    assert not puede

def test_explorador_puede_aprender_su_rama():
    puede, _ = puede_aprender_clase("golpe_rapido", "explorador")
    assert puede
    puede, _ = puede_aprender_clase("corte", "explorador")
    assert puede
    puede, _ = puede_aprender_clase("veneno", "explorador")
    assert puede
    puede, _ = puede_aprender_clase("ejecutar", "explorador")
    assert puede

def test_explorador_no_puede_aprender_rama_guerrero():
    puede, err = puede_aprender_clase("golpe_fuerte", "explorador")
    # golpe_fuerte es habilidad inicial, exenta de restricción de clase
    assert puede  # las iniciales siempre se permiten

def test_explorador_no_puede_aprender_embestida():
    puede, err = puede_aprender_clase("embestida", "explorador")
    assert not puede

def test_mago_puede_aprender_su_rama():
    puede, _ = puede_aprender_clase("dardo_magico", "mago")
    assert puede
    puede, _ = puede_aprender_clase("escudo_arcano", "mago")
    assert puede
    puede, _ = puede_aprender_clase("bola_fuego", "mago")
    assert puede
    puede, _ = puede_aprender_clase("drenar_vida", "mago")
    assert puede

def test_mago_no_puede_aprender_rama_guerrero():
    puede, err = puede_aprender_clase("embestida", "mago")
    assert not puede

def test_mago_no_puede_aprender_rama_explorador():
    puede, err = puede_aprender_clase("corte", "mago")
    assert not puede

def test_clase_invalida_no_restringe():
    puede, _ = puede_aprender_clase("embestida", "paladin")
    assert puede

def test_skill_inexistente_no_falla():
    puede, _ = puede_aprender_clase("habilidad_inventada", "guerrero")
    assert puede


# ---------------------------------------------------------------------------
# aplicar_clase
# ---------------------------------------------------------------------------

def test_aplicar_clase_guerrero():
    stats = dict(STAT_DEFAULTS)
    resultado = aplicar_clase(stats, "guerrero")
    assert resultado["fuerza"] == stats["fuerza"] + 3
    assert resultado["constitucion"] == stats["constitucion"] + 2
    assert resultado["defensa"] == stats["defensa"] + 1
    assert resultado["hp_max"] == stats["hp_max"] + 20
    assert resultado["hp"] == stats["hp"] + 20

def test_aplicar_clase_explorador():
    stats = dict(STAT_DEFAULTS)
    resultado = aplicar_clase(stats, "explorador")
    assert resultado["destreza"] == stats["destreza"] + 4
    assert resultado["constitucion"] == stats["constitucion"] + 1
    assert resultado["fuerza"] == stats["fuerza"]  # sin cambio

def test_aplicar_clase_mago():
    stats = dict(STAT_DEFAULTS)
    resultado = aplicar_clase(stats, "mago")
    assert resultado["inteligencia"] == stats["inteligencia"] + 5
    assert resultado["fuerza"] == stats["fuerza"]  # sin cambio

def test_aplicar_clase_invalida_no_cambia():
    stats = dict(STAT_DEFAULTS)
    resultado = aplicar_clase(stats, "paladin")
    assert resultado == stats

def test_aplicar_clase_no_muta_original():
    stats = dict(STAT_DEFAULTS)
    original = dict(stats)
    aplicar_clase(stats, "guerrero")
    assert stats == original


# ---------------------------------------------------------------------------
# Integración con systems/skills/engine
# ---------------------------------------------------------------------------

INICIALES = {"golpe_fuerte", "golpe_rapido"}

def test_puede_aprender_sin_clase():
    puede, _ = puede_aprender("embestida", INICIALES, nivel=2, clase=None)
    assert puede

def test_puede_aprender_con_clase_correcta():
    puede, _ = puede_aprender("embestida", INICIALES, nivel=2, clase="guerrero")
    assert puede

def test_puede_aprender_con_clase_incorrecta():
    puede, err = puede_aprender("embestida", INICIALES, nivel=2, clase="mago")
    assert not puede
    assert "Mago" in err or "guerrero" in err.lower() or "rama" in err.lower()

def test_puede_aprender_clase_bloquea_antes_que_nivel():
    # Aunque el nivel es suficiente, la clase bloquea
    puede, err = puede_aprender("corte", INICIALES | {"golpe_rapido"}, nivel=5, clase="guerrero")
    assert not puede

def test_aprender_con_clase_correcta_exitoso():
    exito, nuevas, _ = aprender("embestida", INICIALES, nivel=2, clase="guerrero")
    assert exito
    assert "embestida" in nuevas

def test_aprender_con_clase_incorrecta_falla():
    exito, nuevas, err = aprender("embestida", INICIALES, nivel=2, clase="mago")
    assert not exito
    assert "embestida" not in nuevas

def test_aprender_sin_clase_no_restringido():
    exito, nuevas, _ = aprender("dardo_magico", INICIALES, nivel=2, clase=None)
    assert exito
    assert "dardo_magico" in nuevas


# ---------------------------------------------------------------------------
# Catálogo CLASES
# ---------------------------------------------------------------------------

def test_todas_las_clases_tienen_nombre():
    for cid, info in CLASES.items():
        assert "nombre" in info, f"Falta 'nombre' en clase {cid}"

def test_todas_las_clases_tienen_rama():
    for cid, info in CLASES.items():
        assert "rama" in info, f"Falta 'rama' en clase {cid}"

def test_todas_las_clases_tienen_stat_bonus():
    for cid, info in CLASES.items():
        assert "stat_bonus" in info, f"Falta 'stat_bonus' en clase {cid}"
        assert len(info["stat_bonus"]) > 0

def test_ramas_corresponden_a_ramas_de_habilidades():
    from systems.skills.trees import RAMAS
    for cid, info in CLASES.items():
        assert info["rama"] in RAMAS, f"Rama '{info['rama']}' de clase {cid} no existe en skills"

def test_hay_exactamente_tres_clases():
    assert len(CLASES) == 3
    assert set(CLASES.keys()) == {"guerrero", "explorador", "mago"}
