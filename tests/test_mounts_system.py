"""
tests/test_mounts_system.py

Tests puros del sistema de monturas (sin dependencias de Evennia/Django).
"""
import pytest
from systems.mounts.mounts import (
    MONTURAS,
    puede_comprar,
    puede_invocar,
    puede_desmontar,
    bonus_montura,
    monturas_poseidas_count,
    formatear_estado,
    formatear_catalogo,
    _bonus_texto,
)


# Helpers
def _sin_nada():
    return {"monedas": 0, "nivel": 1, "rep": {}, "poseidas": [], "jefes": {}}

def _rico_max():
    return {
        "monedas": 9999, "nivel": 10,
        "rep": {"ciudadanos": 5000},
        "poseidas": [],
        "jefes": {"DRAGON_CENIZA": 1},
    }


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:

    def test_monturas_no_vacio(self):
        assert len(MONTURAS) > 0

    def test_todas_tienen_campos_obligatorios(self):
        campos = ("nombre", "descripcion", "tipo", "coste", "nivel_min",
                  "faccion", "rep_min", "requisito_jefe", "bonus", "raro")
        for mid, m in MONTURAS.items():
            for c in campos:
                assert c in m, f"{mid} falta campo '{c}'"

    def test_poni_viejo_nv1_sin_req(self):
        m = MONTURAS["poni_viejo"]
        assert m["nivel_min"] == 1
        assert m["faccion"] is None
        assert m["coste"] > 0

    def test_dragon_ceniza_gratis_con_req_jefe(self):
        m = MONTURAS["dragon_ceniza"]
        assert m["coste"] == 0
        assert m["requisito_jefe"] == "DRAGON_CENIZA"

    def test_grifo_real_nv10(self):
        assert MONTURAS["grifo_real"]["nivel_min"] == 10

    def test_bonus_no_vacio(self):
        for mid, m in MONTURAS.items():
            assert m["bonus"], f"{mid} no tiene bonus"

    def test_hipogrifo_requiere_rep_ciudadanos(self):
        m = MONTURAS["hipogrifo"]
        assert m["faccion"] == "ciudadanos"
        assert m["rep_min"] > 0


# --------------------------------------------------------------------------- #
#  puede_comprar
# --------------------------------------------------------------------------- #

class TestPuedeComprar:

    def test_ok_poni_viejo_nv1(self):
        ok, _ = puede_comprar("poni_viejo", 200, 1, {}, [], {})
        assert ok is True

    def test_sin_monedas(self):
        ok, msg = puede_comprar("poni_viejo", 0, 1, {}, [], {})
        assert ok is False
        assert "monedas" in msg.lower() or "suficiente" in msg.lower()

    def test_nivel_insuficiente(self):
        ok, msg = puede_comprar("corcel_guerra", 9999, 1, {}, [], {})
        assert ok is False
        assert "nivel" in msg.lower()

    def test_ya_poseida(self):
        ok, msg = puede_comprar("poni_viejo", 9999, 10, {}, ["poni_viejo"], {})
        assert ok is False
        assert "posees" in msg.lower() or "ya" in msg.lower()

    def test_montura_desconocida(self):
        ok, _ = puede_comprar("unicornio_invisible", 9999, 10, {}, [], {})
        assert ok is False

    def test_hipogrifo_sin_rep(self):
        ok, msg = puede_comprar("hipogrifo", 9999, 10, {}, [], {})
        assert ok is False
        assert "honrado" in msg.lower() or "reputación" in msg.lower()

    def test_hipogrifo_con_rep_suficiente(self):
        ok, _ = puede_comprar("hipogrifo", 9999, 10, {"ciudadanos": 5000}, [], {})
        assert ok is True

    def test_dragon_sin_jefe(self):
        ok, msg = puede_comprar("dragon_ceniza", 0, 1, {}, [], {})
        assert ok is False
        assert "derrotar" in msg.lower() or "jefe" in msg.lower()

    def test_dragon_con_jefe_derrotado(self):
        ok, _ = puede_comprar("dragon_ceniza", 0, 1, {}, [], {"DRAGON_CENIZA": 1})
        assert ok is True

    def test_grifo_real_max_todo(self):
        d = _rico_max()
        ok, _ = puede_comprar("grifo_real", d["monedas"], d["nivel"], d["rep"], d["poseidas"], d["jefes"])
        assert ok is True

    def test_no_modifica_lista_original(self):
        original = ["poni_viejo"]
        puede_comprar("corcel_guerra", 9999, 10, {}, original, {})
        assert original == ["poni_viejo"]


# --------------------------------------------------------------------------- #
#  puede_invocar
# --------------------------------------------------------------------------- #

class TestPuedeInvocar:

    def test_ok_montura_poseida(self):
        ok, _ = puede_invocar("poni_viejo", ["poni_viejo"])
        assert ok is True

    def test_no_poseida(self):
        ok, msg = puede_invocar("poni_viejo", [])
        assert ok is False
        assert "posees" in msg.lower() or "no" in msg.lower()

    def test_desconocida(self):
        ok, _ = puede_invocar("id_falsa", ["id_falsa"])
        # no está en MONTURAS, debe fallar
        assert ok is False

    def test_varias_poseidas_elige_correcta(self):
        ok, _ = puede_invocar("corcel_guerra", ["poni_viejo", "corcel_guerra"])
        assert ok is True


# --------------------------------------------------------------------------- #
#  puede_desmontar
# --------------------------------------------------------------------------- #

class TestPuedeDesmontar:

    def test_ok_si_activa(self):
        ok, _ = puede_desmontar("poni_viejo")
        assert ok is True

    def test_falla_si_ninguna(self):
        ok, msg = puede_desmontar(None)
        assert ok is False
        assert "montado" in msg.lower()


# --------------------------------------------------------------------------- #
#  bonus_montura
# --------------------------------------------------------------------------- #

class TestBonusMontura:

    def test_sin_montura(self):
        assert bonus_montura(None) == {}

    def test_desconocida(self):
        assert bonus_montura("montura_fantasma") == {}

    def test_poni_viejo(self):
        b = bonus_montura("poni_viejo")
        assert b.get("defensa") == 1

    def test_corcel_guerra_dos_stats(self):
        b = bonus_montura("corcel_guerra")
        assert b.get("defensa") == 2
        assert b.get("fuerza") == 1

    def test_lobo_cazador_destreza(self):
        b = bonus_montura("lobo_cazador")
        assert b.get("destreza") == 3

    def test_no_modifica_catalogo(self):
        b1 = bonus_montura("corcel_guerra")
        b1["defensa"] = 999
        b2 = bonus_montura("corcel_guerra")
        assert b2["defensa"] == 2


# --------------------------------------------------------------------------- #
#  monturas_poseidas_count
# --------------------------------------------------------------------------- #

class TestMonturasPoseidasCount:

    def test_vacio(self):
        assert monturas_poseidas_count([]) == 0

    def test_una(self):
        assert monturas_poseidas_count(["poni_viejo"]) == 1

    def test_varias(self):
        assert monturas_poseidas_count(["poni_viejo", "lobo_cazador"]) == 2

    def test_deduplicacion(self):
        assert monturas_poseidas_count(["poni_viejo", "poni_viejo"]) == 1


# --------------------------------------------------------------------------- #
#  formatear_estado
# --------------------------------------------------------------------------- #

class TestFormatearEstado:

    def test_sin_monturas(self):
        txt = formatear_estado(None, [])
        assert "No estás montado" in txt
        assert "No posees" in txt

    def test_montado_muestra_nombre(self):
        txt = formatear_estado("poni_viejo", ["poni_viejo"])
        assert "Poni Viejo" in txt
        assert "ACTIVA" in txt

    def test_lista_monturas_poseidas(self):
        txt = formatear_estado(None, ["poni_viejo", "lobo_cazador"])
        assert "Poni Viejo" in txt
        assert "Lobo Cazador" in txt

    def test_montada_muestra_bonus(self):
        txt = formatear_estado("corcel_guerra", ["corcel_guerra"])
        assert "DEF" in txt or "defensa" in txt.lower()


# --------------------------------------------------------------------------- #
#  formatear_catalogo
# --------------------------------------------------------------------------- #

class TestFormatearCatalogo:

    def test_sin_nada_muestra_todas(self):
        txt = formatear_catalogo([], 1, {}, 0, {})
        assert "Poni Viejo" in txt
        assert "Grifo Real" in txt

    def test_poseida_marcada(self):
        txt = formatear_catalogo(["poni_viejo"], 10, {}, 9999, {"DRAGON_CENIZA": 1})
        assert "Poseída" in txt

    def test_requisito_nivel_mostrado(self):
        txt = formatear_catalogo([], 1, {}, 9999, {})
        assert "Nv." in txt

    def test_dragon_gratis_indicado(self):
        txt = formatear_catalogo([], 1, {}, 0, {})
        assert "Gratis" in txt or "0 monedas" in txt

    def test_grifo_real_nv10_mencionado(self):
        txt = formatear_catalogo([], 1, {}, 9999, {})
        assert "10" in txt


# --------------------------------------------------------------------------- #
#  _bonus_texto
# --------------------------------------------------------------------------- #

class TestBonusTexto:

    def test_una_stat(self):
        assert "+1 DEF" in _bonus_texto({"defensa": 1})

    def test_varias_stats(self):
        txt = _bonus_texto({"fuerza": 2, "defensa": 3})
        assert "+2 FUE" in txt
        assert "+3 DEF" in txt

    def test_vacio(self):
        assert _bonus_texto({}) == "sin bonus"
