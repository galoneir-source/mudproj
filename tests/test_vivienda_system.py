"""
tests/test_vivienda_system.py

Tests puros del sistema de vivienda (sin dependencias de Evennia/Django).
"""
import pytest
from systems.housing.housing import (
    PRECIO_VIVIENDA, MAX_INVITADOS, MAX_DESC_LEN,
    puede_comprar,
    puede_invitar,
    puede_quitar_acceso,
    puede_entrar,
    validar_descripcion,
    formatear_estado,
    formatear_sin_vivienda,
)


# --------------------------------------------------------------------------- #
#  puede_comprar
# --------------------------------------------------------------------------- #

class TestPuedeComprar:

    def test_ok(self):
        ok, msg = puede_comprar(PRECIO_VIVIENDA, False)
        assert ok
        assert msg == ""

    def test_ok_con_saldo_extra(self):
        ok, _ = puede_comprar(PRECIO_VIVIENDA + 200, False)
        assert ok

    def test_falla_ya_tiene(self):
        ok, msg = puede_comprar(9999, True)
        assert not ok
        assert "Ya tienes" in msg

    def test_falla_sin_monedas(self):
        ok, msg = puede_comprar(PRECIO_VIVIENDA - 1, False)
        assert not ok
        assert str(PRECIO_VIVIENDA) in msg

    def test_falla_sin_monedas_exacto_cero(self):
        ok, _ = puede_comprar(0, False)
        assert not ok

    def test_ya_tiene_prioridad_sobre_monedas(self):
        ok, msg = puede_comprar(0, True)
        assert not ok
        assert "Ya tienes" in msg


# --------------------------------------------------------------------------- #
#  puede_invitar
# --------------------------------------------------------------------------- #

class TestPuedeInvitar:

    def test_ok(self):
        ok, _ = puede_invitar([], "#5")
        assert ok

    def test_falla_ya_invitado(self):
        ok, msg = puede_invitar(["#5"], "#5")
        assert not ok
        assert "ya tiene acceso" in msg

    def test_falla_max_invitados(self):
        invitados = [f"#{i}" for i in range(MAX_INVITADOS)]
        ok, msg = puede_invitar(invitados, "#99")
        assert not ok
        assert str(MAX_INVITADOS) in msg

    def test_ok_justo_antes_de_limite(self):
        invitados = [f"#{i}" for i in range(MAX_INVITADOS - 1)]
        ok, _ = puede_invitar(invitados, "#99")
        assert ok


# --------------------------------------------------------------------------- #
#  puede_quitar_acceso
# --------------------------------------------------------------------------- #

class TestPuedeQuitarAcceso:

    def test_ok(self):
        ok, _ = puede_quitar_acceso(["#5"], "#5")
        assert ok

    def test_falla_no_en_lista(self):
        ok, msg = puede_quitar_acceso([], "#5")
        assert not ok
        assert "no tiene acceso" in msg

    def test_falla_otro_dbref(self):
        ok, _ = puede_quitar_acceso(["#5"], "#6")
        assert not ok


# --------------------------------------------------------------------------- #
#  puede_entrar
# --------------------------------------------------------------------------- #

class TestPuedeEntrar:

    def test_propietario_siempre_puede(self):
        assert puede_entrar("#1", [], "#1")

    def test_invitado_puede(self):
        assert puede_entrar("#1", ["#2", "#3"], "#2")

    def test_extraño_no_puede(self):
        assert not puede_entrar("#1", ["#2"], "#3")

    def test_lista_vacía(self):
        assert not puede_entrar("#1", [], "#2")


# --------------------------------------------------------------------------- #
#  validar_descripcion
# --------------------------------------------------------------------------- #

class TestValidarDescripcion:

    def test_ok(self):
        ok, texto = validar_descripcion("Una habitación acogedora.")
        assert ok
        assert texto == "Una habitación acogedora."

    def test_strip_espacios(self):
        ok, texto = validar_descripcion("  Texto con espacios  ")
        assert ok
        assert texto == "Texto con espacios"

    def test_falla_vacio(self):
        ok, msg = validar_descripcion("")
        assert not ok
        assert "vacía" in msg

    def test_falla_solo_espacios(self):
        ok, _ = validar_descripcion("   ")
        assert not ok

    def test_falla_demasiado_largo(self):
        ok, msg = validar_descripcion("x" * (MAX_DESC_LEN + 1))
        assert not ok
        assert str(MAX_DESC_LEN) in msg

    def test_ok_exactamente_limite(self):
        ok, _ = validar_descripcion("x" * MAX_DESC_LEN)
        assert ok


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:

    def test_formatear_estado_sin_invitados_sin_desc(self):
        txt = formatear_estado("Aldric", [], None, "Casa de Aldric")
        assert "Aldric" in txt
        assert "sin decorar" in txt
        assert "nadie invitado" in txt

    def test_formatear_estado_con_invitados(self):
        txt = formatear_estado("Aldric", ["Mira", "Torben"], "Una sala cálida.", "Casa de Aldric")
        assert "Mira" in txt
        assert "Torben" in txt
        assert "Una sala cálida." in txt

    def test_formatear_sin_vivienda(self):
        txt = formatear_sin_vivienda()
        assert str(PRECIO_VIVIENDA) in txt
        assert "vivienda comprar" in txt

    def test_formatear_estado_muestra_comandos(self):
        txt = formatear_estado("X", [], None, "Casa de X")
        assert "casa" in txt
        assert "decorar" in txt
