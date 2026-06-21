"""
tests/test_gremios.py

Tests unitarios puros para el sistema de gremios (v0.22.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_gremios.py
"""
import unittest

from systems.guilds.guilds import (
    COSTE_CREAR_GREMIO,
    INVITACION_TIMEOUT,
    MAX_MIEMBROS,
    RANGOS,
    RANGO_LIDER,
    RANGO_MIEMBRO,
    RANGO_OFICIAL,
    indice_rango,
    normalizar_nombre,
    puede_expulsar,
    puede_invitar,
    puede_retirar_banco,
    simbolo_rango,
    validar_nombre_gremio,
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

class TestConstantes(unittest.TestCase):

    def test_rangos_orden_ascendente(self):
        self.assertEqual(RANGOS, ("Miembro", "Oficial", "Líder"))

    def test_max_miembros_positivo(self):
        self.assertGreater(MAX_MIEMBROS, 0)

    def test_coste_crear_positivo(self):
        self.assertGreater(COSTE_CREAR_GREMIO, 0)

    def test_invitacion_timeout_positivo(self):
        self.assertGreater(INVITACION_TIMEOUT, 0)

    def test_rango_lider_es_el_ultimo(self):
        self.assertEqual(RANGOS[-1], RANGO_LIDER)

    def test_rango_miembro_es_el_primero(self):
        self.assertEqual(RANGOS[0], RANGO_MIEMBRO)


# ---------------------------------------------------------------------------
# validar_nombre_gremio
# ---------------------------------------------------------------------------

class TestValidarNombreGremio(unittest.TestCase):

    def test_nombre_valido(self):
        ok, _ = validar_nombre_gremio("Los Guardianes")
        self.assertTrue(ok)

    def test_nombre_exacto_minimo(self):
        ok, _ = validar_nombre_gremio("abc")
        self.assertTrue(ok)

    def test_nombre_demasiado_corto(self):
        ok, _ = validar_nombre_gremio("ab")
        self.assertFalse(ok)

    def test_nombre_exacto_maximo(self):
        ok, _ = validar_nombre_gremio("A" * 24)
        self.assertTrue(ok)

    def test_nombre_demasiado_largo(self):
        ok, _ = validar_nombre_gremio("A" * 25)
        self.assertFalse(ok)

    def test_nombre_con_acento(self):
        ok, _ = validar_nombre_gremio("Ángeles del Norte")
        self.assertTrue(ok)

    def test_nombre_con_apostrofe(self):
        ok, _ = validar_nombre_gremio("D'Artagnan")
        self.assertTrue(ok)

    def test_nombre_con_guion(self):
        ok, _ = validar_nombre_gremio("Anti-Magia")
        self.assertTrue(ok)

    def test_nombre_con_caracter_invalido(self):
        ok, _ = validar_nombre_gremio("Hack<ers>")
        self.assertFalse(ok)

    def test_nombre_con_signos_invalidos(self):
        ok, _ = validar_nombre_gremio("Guild@123!")
        self.assertFalse(ok)

    def test_nombre_vacio_falla(self):
        ok, _ = validar_nombre_gremio("")
        self.assertFalse(ok)

    def test_nombre_solo_espacios_falla(self):
        ok, _ = validar_nombre_gremio("   ")
        self.assertFalse(ok)

    def test_motivo_menciona_longitud_minima(self):
        _, motivo = validar_nombre_gremio("ab")
        self.assertIn("3", motivo)

    def test_motivo_vacio_cuando_valido(self):
        _, motivo = validar_nombre_gremio("Guardianes")
        self.assertEqual(motivo, "")


# ---------------------------------------------------------------------------
# puede_invitar
# ---------------------------------------------------------------------------

class TestPuedeInvitar(unittest.TestCase):

    def test_lider_puede_invitar(self):
        self.assertTrue(puede_invitar(RANGO_LIDER))

    def test_oficial_puede_invitar(self):
        self.assertTrue(puede_invitar(RANGO_OFICIAL))

    def test_miembro_no_puede_invitar(self):
        self.assertFalse(puede_invitar(RANGO_MIEMBRO))

    def test_rango_desconocido_no_puede(self):
        self.assertFalse(puede_invitar("Desconocido"))


# ---------------------------------------------------------------------------
# puede_expulsar
# ---------------------------------------------------------------------------

class TestPuedeExpulsar(unittest.TestCase):

    def test_lider_expulsa_oficial(self):
        self.assertTrue(puede_expulsar(RANGO_LIDER, RANGO_OFICIAL))

    def test_lider_expulsa_miembro(self):
        self.assertTrue(puede_expulsar(RANGO_LIDER, RANGO_MIEMBRO))

    def test_lider_no_expulsa_lider(self):
        # El Líder no puede expulsarse a sí mismo con este mecanismo
        self.assertFalse(puede_expulsar(RANGO_LIDER, RANGO_LIDER))

    def test_oficial_expulsa_miembro(self):
        self.assertTrue(puede_expulsar(RANGO_OFICIAL, RANGO_MIEMBRO))

    def test_oficial_no_expulsa_oficial(self):
        self.assertFalse(puede_expulsar(RANGO_OFICIAL, RANGO_OFICIAL))

    def test_oficial_no_expulsa_lider(self):
        self.assertFalse(puede_expulsar(RANGO_OFICIAL, RANGO_LIDER))

    def test_miembro_no_expulsa_nadie(self):
        self.assertFalse(puede_expulsar(RANGO_MIEMBRO, RANGO_MIEMBRO))

    def test_miembro_no_expulsa_oficial(self):
        self.assertFalse(puede_expulsar(RANGO_MIEMBRO, RANGO_OFICIAL))


# ---------------------------------------------------------------------------
# puede_retirar_banco
# ---------------------------------------------------------------------------

class TestPuedeRetirarBanco(unittest.TestCase):

    def test_lider_puede_retirar(self):
        self.assertTrue(puede_retirar_banco(RANGO_LIDER))

    def test_oficial_puede_retirar(self):
        self.assertTrue(puede_retirar_banco(RANGO_OFICIAL))

    def test_miembro_no_puede_retirar(self):
        self.assertFalse(puede_retirar_banco(RANGO_MIEMBRO))

    def test_rango_desconocido_no_puede(self):
        self.assertFalse(puede_retirar_banco("Invitado"))


# ---------------------------------------------------------------------------
# indice_rango
# ---------------------------------------------------------------------------

class TestIndiceRango(unittest.TestCase):

    def test_miembro_es_0(self):
        self.assertEqual(indice_rango(RANGO_MIEMBRO), 0)

    def test_oficial_es_1(self):
        self.assertEqual(indice_rango(RANGO_OFICIAL), 1)

    def test_lider_es_2(self):
        self.assertEqual(indice_rango(RANGO_LIDER), 2)

    def test_desconocido_es_menos_1(self):
        self.assertEqual(indice_rango("Rex"), -1)

    def test_orden_ascendente(self):
        self.assertLess(indice_rango(RANGO_MIEMBRO), indice_rango(RANGO_OFICIAL))
        self.assertLess(indice_rango(RANGO_OFICIAL), indice_rango(RANGO_LIDER))


# ---------------------------------------------------------------------------
# normalizar_nombre
# ---------------------------------------------------------------------------

class TestNormalizarNombre(unittest.TestCase):

    def test_minusculas(self):
        self.assertEqual(normalizar_nombre("LOS GUARDIANES"), "los_guardianes")

    def test_espacios_a_guiones(self):
        self.assertEqual(normalizar_nombre("Hijos del Caos"), "hijos_del_caos")

    def test_ya_normalizado(self):
        self.assertEqual(normalizar_nombre("abc"), "abc")

    def test_elimina_espacios_borde(self):
        self.assertEqual(normalizar_nombre("  abc  "), "abc")


# ---------------------------------------------------------------------------
# simbolo_rango
# ---------------------------------------------------------------------------

class TestSimboloRango(unittest.TestCase):

    def test_lider_devuelve_diamante(self):
        sim = simbolo_rango(RANGO_LIDER)
        self.assertIn("♦", sim)

    def test_oficial_devuelve_estrella(self):
        sim = simbolo_rango(RANGO_OFICIAL)
        self.assertIn("★", sim)

    def test_miembro_devuelve_punto(self):
        sim = simbolo_rango(RANGO_MIEMBRO)
        self.assertIn("·", sim)

    def test_desconocido_devuelve_punto_simple(self):
        sim = simbolo_rango("Fantasma")
        self.assertIn("·", sim)


if __name__ == "__main__":
    unittest.main()
