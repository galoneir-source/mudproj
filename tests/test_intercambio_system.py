"""
tests/test_intercambio_system.py

Tests unitarios del sistema de intercambio (lógica pura).
No requieren Evennia; se ejecutan con pytest directamente.
"""
import pytest
from systems.trade.trade import (
    nuevo_lado,
    agregar_objeto,
    retirar_objeto,
    establecer_monedas,
    confirmar,
    desconfirmar_ambos,
    ambos_confirmados,
    validar_monedas,
    formatear_intercambio,
    formatear_oferta_simple,
    tiene_oferta,
)


# --------------------------------------------------------------------------- #
#  nuevo_lado
# --------------------------------------------------------------------------- #

class TestNuevoLado:
    def test_lado_vacio(self):
        lado = nuevo_lado()
        assert lado["objetos"] == []
        assert lado["monedas"] == 0
        assert lado["confirmado"] is False

    def test_dos_lados_independientes(self):
        a = nuevo_lado()
        b = nuevo_lado()
        a["objetos"].append({"id": "x", "nombre": "espada"})
        assert b["objetos"] == []


# --------------------------------------------------------------------------- #
#  agregar_objeto
# --------------------------------------------------------------------------- #

class TestAgregarObjeto:
    def test_agrega_correctamente(self):
        lado = nuevo_lado()
        ok, err = agregar_objeto(lado, "#1", "espada de hierro")
        assert ok is True
        assert err == ""
        assert len(lado["objetos"]) == 1
        assert lado["objetos"][0]["nombre"] == "espada de hierro"

    def test_desconfirma_al_agregar(self):
        lado = nuevo_lado()
        lado["confirmado"] = True
        agregar_objeto(lado, "#1", "espada")
        assert lado["confirmado"] is False

    def test_duplicado_falla(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        ok, err = agregar_objeto(lado, "#1", "espada")
        assert ok is False
        assert "Ya estás ofreciendo" in err

    def test_ids_distintos_ok(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        ok, _ = agregar_objeto(lado, "#2", "daga")
        assert ok is True
        assert len(lado["objetos"]) == 2


# --------------------------------------------------------------------------- #
#  retirar_objeto
# --------------------------------------------------------------------------- #

class TestRetirarObjeto:
    def test_retira_correctamente(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        ok, err = retirar_objeto(lado, "#1")
        assert ok is True
        assert lado["objetos"] == []

    def test_retirar_inexistente_falla(self):
        lado = nuevo_lado()
        ok, err = retirar_objeto(lado, "#99")
        assert ok is False

    def test_desconfirma_al_retirar(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        lado["confirmado"] = True
        retirar_objeto(lado, "#1")
        assert lado["confirmado"] is False

    def test_retira_solo_el_correcto(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        agregar_objeto(lado, "#2", "daga")
        retirar_objeto(lado, "#1")
        assert len(lado["objetos"]) == 1
        assert lado["objetos"][0]["id"] == "#2"


# --------------------------------------------------------------------------- #
#  establecer_monedas
# --------------------------------------------------------------------------- #

class TestEstablecerMonedas:
    def test_establece_correctamente(self):
        lado = nuevo_lado()
        ok, err = establecer_monedas(lado, 50)
        assert ok is True
        assert lado["monedas"] == 50

    def test_negativo_falla(self):
        lado = nuevo_lado()
        ok, err = establecer_monedas(lado, -1)
        assert ok is False

    def test_cero_permitido(self):
        lado = nuevo_lado()
        ok, _ = establecer_monedas(lado, 0)
        assert ok is True
        assert lado["monedas"] == 0

    def test_desconfirma_al_cambiar(self):
        lado = nuevo_lado()
        lado["confirmado"] = True
        establecer_monedas(lado, 10)
        assert lado["confirmado"] is False

    def test_sobrescribe_monedas_anteriores(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 30)
        establecer_monedas(lado, 70)
        assert lado["monedas"] == 70


# --------------------------------------------------------------------------- #
#  confirmar / desconfirmar_ambos
# --------------------------------------------------------------------------- #

class TestConfirmar:
    def test_confirmar_lado(self):
        lado = nuevo_lado()
        confirmar(lado)
        assert lado["confirmado"] is True

    def test_desconfirmar_ambos(self):
        a = nuevo_lado()
        b = nuevo_lado()
        a["confirmado"] = True
        b["confirmado"] = True
        desconfirmar_ambos(a, b)
        assert a["confirmado"] is False
        assert b["confirmado"] is False

    def test_ambos_confirmados_false_si_ninguno(self):
        a = nuevo_lado()
        b = nuevo_lado()
        assert ambos_confirmados(a, b) is False

    def test_ambos_confirmados_false_si_solo_uno(self):
        a = nuevo_lado()
        b = nuevo_lado()
        confirmar(a)
        assert ambos_confirmados(a, b) is False

    def test_ambos_confirmados_true(self):
        a = nuevo_lado()
        b = nuevo_lado()
        confirmar(a)
        confirmar(b)
        assert ambos_confirmados(a, b) is True


# --------------------------------------------------------------------------- #
#  validar_monedas
# --------------------------------------------------------------------------- #

class TestValidarMonedas:
    def test_sin_monedas_siempre_ok(self):
        lado = nuevo_lado()
        ok, _ = validar_monedas(lado, 0)
        assert ok is True

    def test_monedas_suficientes(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 50)
        ok, _ = validar_monedas(lado, 100)
        assert ok is True

    def test_monedas_exactas(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 50)
        ok, _ = validar_monedas(lado, 50)
        assert ok is True

    def test_monedas_insuficientes(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 100)
        ok, err = validar_monedas(lado, 50)
        assert ok is False
        assert "100" in err


# --------------------------------------------------------------------------- #
#  tiene_oferta
# --------------------------------------------------------------------------- #

class TestTieneOferta:
    def test_lado_vacio_no_tiene(self):
        assert tiene_oferta(nuevo_lado()) is False

    def test_con_objeto_tiene(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "espada")
        assert tiene_oferta(lado) is True

    def test_con_monedas_tiene(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 10)
        assert tiene_oferta(lado) is True

    def test_monedas_cero_no_tiene(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 0)
        assert tiene_oferta(lado) is False


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_formato_contiene_nombres(self):
        a = nuevo_lado()
        b = nuevo_lado()
        texto = formatear_intercambio("Alice", a, "Bob", b)
        assert "Alice" in texto
        assert "Bob" in texto

    def test_formato_muestra_confirmado(self):
        a = nuevo_lado()
        b = nuevo_lado()
        confirmar(a)
        texto = formatear_intercambio("Alice", a, "Bob", b)
        assert "Confirmado" in texto

    def test_formato_muestra_objeto(self):
        a = nuevo_lado()
        b = nuevo_lado()
        agregar_objeto(a, "#1", "espada mágica")
        texto = formatear_intercambio("Alice", a, "Bob", b)
        assert "espada mágica" in texto

    def test_formato_muestra_monedas(self):
        a = nuevo_lado()
        b = nuevo_lado()
        establecer_monedas(b, 75)
        texto = formatear_intercambio("Alice", a, "Bob", b)
        assert "75" in texto

    def test_oferta_simple_vacia(self):
        lado = nuevo_lado()
        resultado = formatear_oferta_simple(lado)
        assert resultado == "(nada)"

    def test_oferta_simple_con_objeto(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "daga")
        resultado = formatear_oferta_simple(lado)
        assert "daga" in resultado

    def test_oferta_simple_con_monedas(self):
        lado = nuevo_lado()
        establecer_monedas(lado, 30)
        resultado = formatear_oferta_simple(lado)
        assert "30" in resultado

    def test_oferta_simple_combinada(self):
        lado = nuevo_lado()
        agregar_objeto(lado, "#1", "daga")
        establecer_monedas(lado, 20)
        resultado = formatear_oferta_simple(lado)
        assert "daga" in resultado
        assert "20" in resultado
