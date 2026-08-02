"""
tests/test_marriage_system.py

Tests puros (pytest, sin Evennia) de systems/marriage/marriage.py.
"""
from systems.marriage.marriage import (
    TIMEOUT_PROPUESTA_SEGUNDOS,
    propuesta_expirada,
    puede_proponer,
    puede_divorciarse,
    formatear_propuesta_recibida,
    formatear_boda,
    formatear_divorcio,
    formatear_estado_civil,
)


# --------------------------------------------------------------------------- #
#  propuesta_expirada
# --------------------------------------------------------------------------- #

class TestPropuestaExpirada:
    def test_no_expira_de_inmediato(self):
        assert propuesta_expirada(1000.0, 1000.0) is False

    def test_no_expira_justo_antes_del_limite(self):
        assert propuesta_expirada(1000.0, 1000.0 + TIMEOUT_PROPUESTA_SEGUNDOS - 1) is False

    def test_expira_justo_en_el_limite(self):
        assert propuesta_expirada(1000.0, 1000.0 + TIMEOUT_PROPUESTA_SEGUNDOS) is True

    def test_expira_bastante_despues(self):
        assert propuesta_expirada(1000.0, 1000.0 + TIMEOUT_PROPUESTA_SEGUNDOS + 500) is True


# --------------------------------------------------------------------------- #
#  puede_proponer
# --------------------------------------------------------------------------- #

class TestPuedeProponer:
    def test_propuesta_valida(self):
        ok, error = puede_proponer("#1", "#2", None, None, False, False)
        assert ok is True
        assert error == ""

    def test_no_puede_proponerse_a_si_mismo(self):
        ok, error = puede_proponer("#1", "#1", None, None, False, False)
        assert ok is False
        assert "ti mismo" in error

    def test_no_puede_proponer_si_ya_esta_casado(self):
        ok, error = puede_proponer("#1", "#2", "#9", None, False, False)
        assert ok is False
        assert "casado" in error.lower()

    def test_no_puede_proponer_si_objetivo_ya_esta_casado(self):
        ok, error = puede_proponer("#1", "#2", None, "#9", False, False)
        assert ok is False
        assert "casada" in error.lower()

    def test_no_puede_proponer_con_propuesta_saliente_pendiente(self):
        ok, error = puede_proponer("#1", "#2", None, None, True, False)
        assert ok is False
        assert "pendiente" in error.lower()

    def test_no_puede_proponer_si_objetivo_tiene_propuesta_entrante(self):
        ok, error = puede_proponer("#1", "#2", None, None, False, True)
        assert ok is False
        assert "pendiente" in error.lower()


# --------------------------------------------------------------------------- #
#  puede_divorciarse
# --------------------------------------------------------------------------- #

class TestPuedeDivorciarse:
    def test_puede_divorciarse_si_esta_casado(self):
        ok, error = puede_divorciarse("#9")
        assert ok is True
        assert error == ""

    def test_no_puede_divorciarse_si_no_esta_casado(self):
        ok, error = puede_divorciarse(None)
        assert ok is False
        assert "no estás casado" in error.lower()


# --------------------------------------------------------------------------- #
#  formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_formatear_propuesta_recibida_incluye_nombre_y_comandos(self):
        txt = formatear_propuesta_recibida("Gandalf")
        assert "Gandalf" in txt
        assert "aceptar boda" in txt
        assert "rechazar boda" in txt

    def test_formatear_boda_incluye_ambos_nombres(self):
        txt = formatear_boda("Gandalf", "Galadriel")
        assert "Gandalf" in txt
        assert "Galadriel" in txt

    def test_formatear_divorcio_incluye_ambos_nombres(self):
        txt = formatear_divorcio("Gandalf", "Galadriel")
        assert "Gandalf" in txt
        assert "Galadriel" in txt

    def test_formatear_estado_civil_soltero(self):
        txt = formatear_estado_civil(None, None)
        assert "no estás casado" in txt.lower()

    def test_formatear_estado_civil_casado_con_fecha(self):
        txt = formatear_estado_civil("Galadriel", "2026-08-02")
        assert "Galadriel" in txt
        assert "2026-08-02" in txt

    def test_formatear_estado_civil_casado_sin_fecha(self):
        txt = formatear_estado_civil("Galadriel", None)
        assert "Galadriel" in txt
