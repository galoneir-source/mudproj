"""
tests/test_correo_system.py

Tests unitarios del sistema de correo (lógica pura).
No requieren Evennia; se ejecutan con pytest directamente.
"""
import pytest
from unittest.mock import patch
from systems.mail.mail import (
    MAX_CARTAS,
    nueva_carta,
    puede_recibir,
    formatear_bandeja,
    formatear_carta,
    formatear_notificacion,
    contar_no_leidas,
    adjunto_pendiente,
    tiene_adjunto,
)


# --------------------------------------------------------------------------- #
#  nueva_carta
# --------------------------------------------------------------------------- #

class TestNuevaCarta:
    def test_campos_basicos(self):
        carta = nueva_carta("Alice", "#1", "Hola")
        assert carta["remitente"] == "Alice"
        assert carta["remitente_dbref"] == "#1"
        assert carta["mensaje"] == "Hola"
        assert carta["monedas"] == 0
        assert carta["objetos"] == []
        assert carta["leida"] is False
        assert carta["reclamado"] is False

    def test_con_monedas(self):
        carta = nueva_carta("Alice", "#1", "Toma", monedas=50)
        assert carta["monedas"] == 50

    def test_con_objetos(self):
        objetos = [{"dbref": "#5", "nombre": "espada"}]
        carta = nueva_carta("Alice", "#1", "Toma esto", objetos=objetos)
        assert len(carta["objetos"]) == 1
        assert carta["objetos"][0]["nombre"] == "espada"

    def test_monedas_negativas_se_normalizan(self):
        carta = nueva_carta("Alice", "#1", "msg", monedas=-10)
        assert carta["monedas"] == 0

    def test_mensaje_se_hace_strip(self):
        carta = nueva_carta("Alice", "#1", "  Hola  ")
        assert carta["mensaje"] == "Hola"

    def test_id_unico(self):
        c1 = nueva_carta("Alice", "#1", "msg")
        c2 = nueva_carta("Alice", "#2", "msg")
        assert c1["id"] != c2["id"]

    def test_fecha_no_vacia(self):
        carta = nueva_carta("Alice", "#1", "msg")
        assert len(carta["fecha"]) > 0


# --------------------------------------------------------------------------- #
#  puede_recibir
# --------------------------------------------------------------------------- #

class TestPuedeRecibir:
    def test_bandeja_vacia(self):
        ok, _ = puede_recibir([])
        assert ok is True

    def test_bandeja_al_limite(self):
        bandeja = [nueva_carta("A", "#1", "msg")] * MAX_CARTAS
        ok, err = puede_recibir(bandeja)
        assert ok is False
        assert str(MAX_CARTAS) in err

    def test_bandeja_casi_llena(self):
        bandeja = [nueva_carta("A", "#1", "msg")] * (MAX_CARTAS - 1)
        ok, _ = puede_recibir(bandeja)
        assert ok is True


# --------------------------------------------------------------------------- #
#  tiene_adjunto / adjunto_pendiente
# --------------------------------------------------------------------------- #

class TestAdjunto:
    def test_sin_adjunto(self):
        carta = nueva_carta("A", "#1", "msg")
        assert tiene_adjunto(carta) is False

    def test_con_monedas(self):
        carta = nueva_carta("A", "#1", "msg", monedas=10)
        assert tiene_adjunto(carta) is True

    def test_con_objetos(self):
        carta = nueva_carta("A", "#1", "msg", objetos=[{"dbref": "#1", "nombre": "x"}])
        assert tiene_adjunto(carta) is True

    def test_pendiente_si_no_reclamado(self):
        carta = nueva_carta("A", "#1", "msg", monedas=5)
        assert adjunto_pendiente(carta) is True

    def test_no_pendiente_si_reclamado(self):
        carta = nueva_carta("A", "#1", "msg", monedas=5)
        carta["reclamado"] = True
        assert adjunto_pendiente(carta) is False

    def test_no_pendiente_sin_adjunto(self):
        carta = nueva_carta("A", "#1", "msg")
        assert adjunto_pendiente(carta) is False


# --------------------------------------------------------------------------- #
#  contar_no_leidas
# --------------------------------------------------------------------------- #

class TestContarNoLeidas:
    def test_todas_nuevas(self):
        bandeja = [nueva_carta("A", "#1", "msg") for _ in range(3)]
        assert contar_no_leidas(bandeja) == 3

    def test_todas_leidas(self):
        bandeja = [nueva_carta("A", "#1", "msg") for _ in range(3)]
        for c in bandeja:
            c["leida"] = True
        assert contar_no_leidas(bandeja) == 0

    def test_mixtas(self):
        bandeja = [nueva_carta("A", "#1", "msg") for _ in range(4)]
        bandeja[0]["leida"] = True
        bandeja[2]["leida"] = True
        assert contar_no_leidas(bandeja) == 2

    def test_bandeja_vacia(self):
        assert contar_no_leidas([]) == 0


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_bandeja_vacia(self):
        resultado = formatear_bandeja([])
        assert "vacío" in resultado.lower()

    def test_bandeja_contiene_remitente(self):
        bandeja = [nueva_carta("Bob", "#2", "Hola")]
        resultado = formatear_bandeja(bandeja)
        assert "Bob" in resultado

    def test_bandeja_indica_adj(self):
        carta = nueva_carta("Bob", "#2", "Hola", monedas=10)
        resultado = formatear_bandeja([carta])
        assert "ADJ" in resultado

    def test_bandeja_sin_adj(self):
        carta = nueva_carta("Bob", "#2", "Hola")
        resultado = formatear_bandeja([carta])
        assert "ADJ" not in resultado

    def test_bandeja_muestra_total(self):
        bandeja = [nueva_carta("A", "#1", "msg") for _ in range(3)]
        resultado = formatear_bandeja(bandeja)
        assert "3" in resultado

    def test_carta_muestra_remitente(self):
        carta = nueva_carta("Alice", "#1", "Mensaje de prueba")
        resultado = formatear_carta(carta, 1)
        assert "Alice" in resultado

    def test_carta_muestra_mensaje(self):
        carta = nueva_carta("Alice", "#1", "Contenido especial")
        resultado = formatear_carta(carta, 1)
        assert "Contenido especial" in resultado

    def test_carta_muestra_adjunto_monedas(self):
        carta = nueva_carta("Alice", "#1", "msg", monedas=75)
        resultado = formatear_carta(carta, 2)
        assert "75" in resultado

    def test_carta_nueva_indica_nuevo(self):
        carta = nueva_carta("Alice", "#1", "msg")
        resultado = formatear_carta(carta, 1)
        assert "NUEVA" in resultado

    def test_carta_leida_no_indica_nuevo(self):
        carta = nueva_carta("Alice", "#1", "msg")
        carta["leida"] = True
        resultado = formatear_carta(carta, 1)
        assert "NUEVA" not in resultado

    def test_carta_adj_reclamado(self):
        carta = nueva_carta("Alice", "#1", "msg", monedas=10)
        carta["reclamado"] = True
        resultado = formatear_carta(carta, 1)
        assert "reclamado" in resultado.lower()

    def test_notificacion_singular(self):
        resultado = formatear_notificacion(1)
        assert "1 carta" in resultado

    def test_notificacion_plural(self):
        resultado = formatear_notificacion(5)
        assert "5 cartas" in resultado
