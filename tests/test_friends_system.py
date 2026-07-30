"""
tests/test_friends_system.py

Tests puros del sistema de lista de amigos (sin dependencias de Evennia/Django).
"""
import pytest
from systems.friends.friends import (
    MAX_AMIGOS,
    es_amigo,
    puede_agregar,
    agregar_amigo,
    quitar_amigo,
    formatear_lista_amigos,
)


# --------------------------------------------------------------------------- #
#  es_amigo
# --------------------------------------------------------------------------- #

class TestEsAmigo:

    def test_presente(self):
        assert es_amigo(["#5", "#7"], "#7") is True

    def test_ausente(self):
        assert es_amigo(["#5", "#7"], "#9") is False

    def test_lista_vacia(self):
        assert es_amigo([], "#9") is False


# --------------------------------------------------------------------------- #
#  puede_agregar
# --------------------------------------------------------------------------- #

class TestPuedeAgregar:

    def test_ok(self):
        ok, error = puede_agregar([], "#7", "#1")
        assert ok is True
        assert error == ""

    def test_no_a_si_mismo(self):
        ok, error = puede_agregar([], "#1", "#1")
        assert ok is False
        assert "a ti mismo" in error

    def test_ya_es_amigo(self):
        ok, error = puede_agregar(["#7"], "#7", "#1")
        assert ok is False
        assert "ya tienes" in error.lower()

    def test_lista_llena(self):
        amigos = [f"#{i}" for i in range(MAX_AMIGOS)]
        ok, error = puede_agregar(amigos, "#999", "#1")
        assert ok is False
        assert "llena" in error.lower()

    def test_lista_a_un_lugar_del_limite_permite(self):
        amigos = [f"#{i}" for i in range(MAX_AMIGOS - 1)]
        ok, error = puede_agregar(amigos, "#999", "#1")
        assert ok is True


# --------------------------------------------------------------------------- #
#  agregar_amigo / quitar_amigo
# --------------------------------------------------------------------------- #

class TestAgregarAmigo:

    def test_agrega(self):
        resultado = agregar_amigo(["#5"], "#7")
        assert resultado == ["#5", "#7"]

    def test_no_duplica(self):
        resultado = agregar_amigo(["#5", "#7"], "#7")
        assert resultado == ["#5", "#7"]

    def test_no_muta_la_lista_original(self):
        original = ["#5"]
        agregar_amigo(original, "#7")
        assert original == ["#5"]


class TestQuitarAmigo:

    def test_quita(self):
        resultado = quitar_amigo(["#5", "#7"], "#7")
        assert resultado == ["#5"]

    def test_no_presente_no_falla(self):
        resultado = quitar_amigo(["#5"], "#999")
        assert resultado == ["#5"]

    def test_no_muta_la_lista_original(self):
        original = ["#5", "#7"]
        quitar_amigo(original, "#7")
        assert original == ["#5", "#7"]


# --------------------------------------------------------------------------- #
#  formatear_lista_amigos
# --------------------------------------------------------------------------- #

class TestFormatearListaAmigos:

    def test_lista_vacia(self):
        texto = formatear_lista_amigos([])
        assert "no tienes amigos" in texto.lower()

    def test_incluye_nombres(self):
        texto = formatear_lista_amigos([("Ana", True), ("Beto", False)])
        assert "Ana" in texto
        assert "Beto" in texto

    def test_en_linea_primero(self):
        texto = formatear_lista_amigos([("Zeta", True), ("Alfa", False)])
        assert texto.index("Zeta") < texto.index("Alfa")

    def test_orden_alfabetico_dentro_del_mismo_estado(self):
        texto = formatear_lista_amigos([("Zeta", True), ("Alfa", True)])
        assert texto.index("Alfa") < texto.index("Zeta")
