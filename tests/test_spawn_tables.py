"""
tests/test_spawn_tables.py

Tests unitarios para systems/spawn/tables.py.
No dependen de Evennia ni Django.
"""
import unittest

from systems.spawn.tables import ZONAS, npcs_necesarios, calcular_faltantes


class TestEstructuraZonas(unittest.TestCase):

    def test_zonas_no_vacio(self):
        self.assertGreater(len(ZONAS), 0)

    def test_todas_las_zonas_tienen_entradas(self):
        for zona_id, entradas in ZONAS.items():
            self.assertIsInstance(entradas, list, f"Zona '{zona_id}' debe ser lista")
            self.assertGreater(len(entradas), 0, f"Zona '{zona_id}' no puede estar vacía")

    def test_todas_las_entradas_tienen_prototipo_y_cantidad(self):
        for zona_id, entradas in ZONAS.items():
            for e in entradas:
                self.assertIn("prototipo", e, f"Entrada en '{zona_id}' sin 'prototipo'")
                self.assertIn("cantidad", e, f"Entrada en '{zona_id}' sin 'cantidad'")
                self.assertIsInstance(e["prototipo"], str)
                self.assertGreater(e["cantidad"], 0)

    def test_zonas_mundo_base_presentes(self):
        zonas_base = {
            "plaza_ciudad", "taberna", "mercado",
            "bosque_norte", "claro_bosque",
            "calabozo_entrada", "calabozo_pasillo", "calabozo_celda",
        }
        for z in zonas_base:
            self.assertIn(z, ZONAS, f"Zona '{z}' no está en ZONAS")

    def test_zonas_expansion_presentes(self):
        zonas_exp = {
            "senda_fangosa", "pantano_cenagoso", "guarida_troll",
            "sala_tumbas", "camara_nigromante",
        }
        for z in zonas_exp:
            self.assertIn(z, ZONAS, f"Zona de expansión '{z}' no está en ZONAS")


class TestNpcsNecesarios(unittest.TestCase):

    def test_plaza_ciudad(self):
        resultado = npcs_necesarios("plaza_ciudad")
        self.assertEqual(resultado, {"GUARDIA": 1, "SACERDOTE": 1, "BANQUERO": 1})

    def test_bosque_norte_dos_goblins(self):
        resultado = npcs_necesarios("bosque_norte")
        self.assertEqual(resultado, {"GOBLIN": 2})

    def test_sala_tumbas_dos_esqueletos(self):
        resultado = npcs_necesarios("sala_tumbas")
        self.assertEqual(resultado, {"ESQUELETO": 2})

    def test_pantano_cenagoso_dos_tipos(self):
        resultado = npcs_necesarios("pantano_cenagoso")
        self.assertEqual(resultado, {"SERPIENTE_PANTANO": 1, "HOMBRE_LAGARTO": 1})

    def test_zona_inexistente_devuelve_vacio(self):
        resultado = npcs_necesarios("zona_que_no_existe")
        self.assertEqual(resultado, {})


class TestCalcularFaltantes(unittest.TestCase):

    def test_sin_npcs_presentes_faltan_todos(self):
        faltantes = calcular_faltantes("plaza_ciudad", {})
        self.assertEqual(faltantes, {"GUARDIA": 1, "SACERDOTE": 1, "BANQUERO": 1})

    def test_ya_completo_devuelve_vacio(self):
        faltantes = calcular_faltantes("plaza_ciudad", {"GUARDIA": 1, "SACERDOTE": 1, "BANQUERO": 1})
        self.assertEqual(faltantes, {})

    def test_exceso_no_da_negativo(self):
        faltantes = calcular_faltantes("plaza_ciudad", {"GUARDIA": 3, "SACERDOTE": 2, "BANQUERO": 2})
        self.assertEqual(faltantes, {})

    def test_parcial_bosque_norte(self):
        faltantes = calcular_faltantes("bosque_norte", {"GOBLIN": 1})
        self.assertEqual(faltantes, {"GOBLIN": 1})

    def test_completo_bosque_norte(self):
        faltantes = calcular_faltantes("bosque_norte", {"GOBLIN": 2})
        self.assertEqual(faltantes, {})

    def test_zona_inexistente_devuelve_vacio(self):
        faltantes = calcular_faltantes("zona_inexistente", {})
        self.assertEqual(faltantes, {})

    def test_varios_tipos_faltantes(self):
        faltantes = calcular_faltantes("pantano_cenagoso", {})
        self.assertEqual(faltantes, {"SERPIENTE_PANTANO": 1, "HOMBRE_LAGARTO": 1})

    def test_un_tipo_falta_otro_no(self):
        faltantes = calcular_faltantes("pantano_cenagoso", {"SERPIENTE_PANTANO": 1})
        self.assertEqual(faltantes, {"HOMBRE_LAGARTO": 1})

    def test_sala_tumbas_faltan_parcialmente(self):
        faltantes = calcular_faltantes("sala_tumbas", {"ESQUELETO": 1})
        self.assertEqual(faltantes, {"ESQUELETO": 1})


if __name__ == "__main__":
    unittest.main()
