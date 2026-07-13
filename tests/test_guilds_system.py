"""
tests/test_guilds_system.py

Tests unitarios puros para systems/guilds/guilds.py.
No requieren Evennia ni Django.
Ejecutar con: python -m pytest tests/test_guilds_system.py
"""
import unittest

from systems.guilds.guilds import (
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


class TestValidarNombreGremio(unittest.TestCase):

    def test_nombre_valido(self):
        ok, motivo = validar_nombre_gremio("Los Guardianes")
        self.assertTrue(ok)
        self.assertEqual(motivo, "")

    def test_nombre_corto_rechazado(self):
        ok, motivo = validar_nombre_gremio("Ab")
        self.assertFalse(ok)
        self.assertIn("al menos", motivo)

    def test_nombre_largo_rechazado(self):
        ok, motivo = validar_nombre_gremio("X" * 25)
        self.assertFalse(ok)
        self.assertIn("superar", motivo)

    def test_nombre_en_limite_minimo_aceptado(self):
        ok, motivo = validar_nombre_gremio("Abc")
        self.assertTrue(ok)

    def test_nombre_en_limite_maximo_aceptado(self):
        ok, motivo = validar_nombre_gremio("X" * 24)
        self.assertTrue(ok)

    def test_nombre_con_caracteres_invalidos_rechazado(self):
        ok, motivo = validar_nombre_gremio("Gremio@Malo!")
        self.assertFalse(ok)
        self.assertIn("no permitidos", motivo)

    def test_nombre_con_acentos_aceptado(self):
        ok, motivo = validar_nombre_gremio("Águilas Doradas")
        self.assertTrue(ok)

    def test_nombre_con_apostrofe_y_guion_aceptado(self):
        ok, motivo = validar_nombre_gremio("D'Artagnan-Team")
        self.assertTrue(ok)

    def test_nombre_se_recorta_antes_de_validar(self):
        ok, motivo = validar_nombre_gremio("   Abc   ")
        self.assertTrue(ok)


class TestPuedeInvitar(unittest.TestCase):

    def test_lider_puede_invitar(self):
        self.assertTrue(puede_invitar(RANGO_LIDER))

    def test_oficial_puede_invitar(self):
        self.assertTrue(puede_invitar(RANGO_OFICIAL))

    def test_miembro_no_puede_invitar(self):
        self.assertFalse(puede_invitar(RANGO_MIEMBRO))

    def test_rango_desconocido_no_puede_invitar(self):
        self.assertFalse(puede_invitar("Novato"))


class TestPuedeExpulsar(unittest.TestCase):

    def test_lider_expulsa_oficial(self):
        self.assertTrue(puede_expulsar(RANGO_LIDER, RANGO_OFICIAL))

    def test_lider_expulsa_miembro(self):
        self.assertTrue(puede_expulsar(RANGO_LIDER, RANGO_MIEMBRO))

    def test_oficial_expulsa_miembro(self):
        self.assertTrue(puede_expulsar(RANGO_OFICIAL, RANGO_MIEMBRO))

    def test_oficial_no_expulsa_oficial(self):
        self.assertFalse(puede_expulsar(RANGO_OFICIAL, RANGO_OFICIAL))

    def test_oficial_no_expulsa_lider(self):
        self.assertFalse(puede_expulsar(RANGO_OFICIAL, RANGO_LIDER))

    def test_miembro_no_expulsa_a_nadie(self):
        self.assertFalse(puede_expulsar(RANGO_MIEMBRO, RANGO_MIEMBRO))

    def test_lider_no_expulsa_lider(self):
        self.assertFalse(puede_expulsar(RANGO_LIDER, RANGO_LIDER))


class TestPuedeRetirarBanco(unittest.TestCase):

    def test_lider_puede_retirar(self):
        self.assertTrue(puede_retirar_banco(RANGO_LIDER))

    def test_oficial_puede_retirar(self):
        self.assertTrue(puede_retirar_banco(RANGO_OFICIAL))

    def test_miembro_no_puede_retirar(self):
        self.assertFalse(puede_retirar_banco(RANGO_MIEMBRO))


class TestIndiceRango(unittest.TestCase):

    def test_miembro_es_cero(self):
        self.assertEqual(indice_rango(RANGO_MIEMBRO), 0)

    def test_oficial_es_uno(self):
        self.assertEqual(indice_rango(RANGO_OFICIAL), 1)

    def test_lider_es_dos(self):
        self.assertEqual(indice_rango(RANGO_LIDER), 2)

    def test_rango_desconocido_es_menos_uno(self):
        self.assertEqual(indice_rango("Emperador"), -1)


class TestNormalizarNombre(unittest.TestCase):

    def test_minusculas_y_guiones_bajos(self):
        self.assertEqual(normalizar_nombre("Los Guardianes"), "los_guardianes")

    def test_recorta_espacios(self):
        self.assertEqual(normalizar_nombre("  Alba  "), "alba")

    def test_nombres_distintos_solo_por_mayusculas_colisionan(self):
        # Dos nombres que solo difieren en mayúsculas deben normalizar
        # igual: así el chequeo de duplicados en obtener_gremio_por_nombre
        # detecta la colisión antes de crear el segundo gremio.
        self.assertEqual(
            normalizar_nombre("LOS GUARDIANES"),
            normalizar_nombre("los guardianes"),
        )


class TestSimboloRango(unittest.TestCase):

    def test_simbolos_de_cada_rango_son_distintos(self):
        simbolos = {simbolo_rango(r) for r in (RANGO_LIDER, RANGO_OFICIAL, RANGO_MIEMBRO)}
        self.assertEqual(len(simbolos), 3)

    def test_rango_desconocido_tiene_fallback(self):
        self.assertEqual(simbolo_rango("Novato"), "·")


if __name__ == "__main__":
    unittest.main()
