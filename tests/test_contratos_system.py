"""
tests/test_contratos_system.py

Tests unitarios puros para el sistema de tablón de contratos (v0.27.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_contratos_system.py
"""
import unittest

from systems.contracts.contracts import (
    NUM_CONTRATOS,
    DIFICULTADES,
    MATERIALES,
    generar_contrato,
    generar_tablón,
    puede_completar_kill,
    puede_completar_entrega,
    formatear_contrato,
    formatear_progreso,
    seed_hora_actual,
)


# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

class TestConstantes(unittest.TestCase):

    def test_num_contratos_positivo(self):
        self.assertGreater(NUM_CONTRATOS, 0)

    def test_num_contratos_es_5(self):
        self.assertEqual(NUM_CONTRATOS, 5)

    def test_dificultades_tiene_tres_niveles(self):
        self.assertEqual(len(DIFICULTADES), 3)

    def test_dificultades_contiene_1_2_3(self):
        self.assertIn(1, DIFICULTADES)
        self.assertIn(2, DIFICULTADES)
        self.assertIn(3, DIFICULTADES)

    def test_materiales_no_vacio(self):
        self.assertGreater(len(MATERIALES), 0)

    def test_dificultad_1_recompensa_menor_que_3(self):
        self.assertLess(
            DIFICULTADES[1]["monedas"][1],
            DIFICULTADES[3]["monedas"][0],
        )


# --------------------------------------------------------------------------- #
#  generar_contrato
# --------------------------------------------------------------------------- #

class TestGenerarContrato(unittest.TestCase):

    def setUp(self):
        self.contrato = generar_contrato(0, seed=12345)

    def test_contrato_es_dict(self):
        self.assertIsInstance(self.contrato, dict)

    def test_tiene_campo_id(self):
        self.assertIn("id", self.contrato)

    def test_tiene_campo_tipo(self):
        self.assertIn("tipo", self.contrato)

    def test_tipo_valido(self):
        self.assertIn(self.contrato["tipo"], ("kill", "entrega"))

    def test_tiene_descripcion(self):
        self.assertIn("descripcion", self.contrato)
        self.assertIsInstance(self.contrato["descripcion"], str)
        self.assertTrue(len(self.contrato["descripcion"]) > 0)

    def test_tiene_objetivo(self):
        self.assertIn("objetivo", self.contrato)

    def test_tiene_cantidad_positiva(self):
        self.assertIn("cantidad", self.contrato)
        self.assertGreater(self.contrato["cantidad"], 0)

    def test_tiene_dificultad(self):
        self.assertIn("dificultad", self.contrato)
        self.assertIn(self.contrato["dificultad"], (1, 2, 3))

    def test_tiene_etiqueta(self):
        self.assertIn("etiqueta", self.contrato)
        self.assertIn("★", self.contrato["etiqueta"])

    def test_tiene_recompensa(self):
        self.assertIn("recompensa", self.contrato)
        r = self.contrato["recompensa"]
        self.assertIn("monedas", r)
        self.assertIn("xp", r)

    def test_recompensa_monedas_positivas(self):
        self.assertGreater(self.contrato["recompensa"]["monedas"], 0)

    def test_recompensa_xp_positivo(self):
        self.assertGreater(self.contrato["recompensa"]["xp"], 0)

    def test_determinista_misma_seed(self):
        c1 = generar_contrato(0, seed=42)
        c2 = generar_contrato(0, seed=42)
        self.assertEqual(c1, c2)

    def test_diferente_indice_diferente_contrato(self):
        c0 = generar_contrato(0, seed=42)
        c1 = generar_contrato(1, seed=42)
        self.assertNotEqual(c0["descripcion"], c1["descripcion"])

    def test_diferente_seed_diferente_contrato(self):
        c1 = generar_contrato(0, seed=100)
        c2 = generar_contrato(0, seed=200)
        self.assertNotEqual(c1, c2)

    def test_kill_descripcion_contiene_numero(self):
        # Generar muchos hasta conseguir un kill
        for i in range(50):
            c = generar_contrato(i, seed=i * 7)
            if c["tipo"] == "kill":
                self.assertIn(str(c["cantidad"]), c["descripcion"])
                break

    def test_entrega_descripcion_contiene_material(self):
        for i in range(50):
            c = generar_contrato(i, seed=i * 11)
            if c["tipo"] == "entrega":
                self.assertIn(c["objetivo"], c["descripcion"])
                break


# --------------------------------------------------------------------------- #
#  generar_tablón
# --------------------------------------------------------------------------- #

class TestGenerarTablon(unittest.TestCase):

    def setUp(self):
        self.tablón = generar_tablón(seed=9999)

    def test_devuelve_lista(self):
        self.assertIsInstance(self.tablón, list)

    def test_longitud_correcta(self):
        self.assertEqual(len(self.tablón), NUM_CONTRATOS)

    def test_todos_son_dicts(self):
        for c in self.tablón:
            self.assertIsInstance(c, dict)

    def test_ids_unicos(self):
        ids = [c["id"] for c in self.tablón]
        self.assertEqual(len(ids), len(set(ids)))

    def test_determinista(self):
        t1 = generar_tablón(seed=42)
        t2 = generar_tablón(seed=42)
        self.assertEqual(t1, t2)

    def test_diferente_seed_diferente_tablón(self):
        t1 = generar_tablón(seed=1)
        t2 = generar_tablón(seed=2)
        self.assertNotEqual(t1[0], t2[0])

    def test_n_personalizado(self):
        t = generar_tablón(seed=0, n=3)
        self.assertEqual(len(t), 3)


# --------------------------------------------------------------------------- #
#  seed_hora_actual
# --------------------------------------------------------------------------- #

class TestSeedHoraActual(unittest.TestCase):

    def test_devuelve_entero(self):
        self.assertIsInstance(seed_hora_actual(), int)

    def test_es_positivo(self):
        self.assertGreater(seed_hora_actual(), 0)

    def test_dos_llamadas_consecutivas_igual(self):
        s1 = seed_hora_actual()
        s2 = seed_hora_actual()
        self.assertEqual(s1, s2)


# --------------------------------------------------------------------------- #
#  puede_completar_kill
# --------------------------------------------------------------------------- #

class TestPuedeCompletarKill(unittest.TestCase):

    def _contrato(self, cantidad=5, kills_al_aceptar=0):
        return {
            "tipo":            "kill",
            "cantidad":        cantidad,
            "kills_al_aceptar": kills_al_aceptar,
        }

    def test_kills_exactas_completa(self):
        ok, hechas = puede_completar_kill(self._contrato(5, 10), kills_totales=15)
        self.assertTrue(ok)
        self.assertEqual(hechas, 5)

    def test_kills_de_mas_completa(self):
        ok, _ = puede_completar_kill(self._contrato(5, 0), kills_totales=10)
        self.assertTrue(ok)

    def test_kills_insuficientes_no_completa(self):
        ok, hechas = puede_completar_kill(self._contrato(5, 0), kills_totales=3)
        self.assertFalse(ok)
        self.assertEqual(hechas, 3)

    def test_sin_kills_no_completa(self):
        ok, hechas = puede_completar_kill(self._contrato(5, 0), kills_totales=0)
        self.assertFalse(ok)
        self.assertEqual(hechas, 0)

    def test_kills_al_aceptar_descuentan_correctamente(self):
        # Tenía 100 kills, acepta, necesita 5 más → ahora tiene 104 → faltan 1
        ok, hechas = puede_completar_kill(self._contrato(5, 100), kills_totales=104)
        self.assertFalse(ok)
        self.assertEqual(hechas, 4)

    def test_kills_al_aceptar_no_contaminan(self):
        ok, hechas = puede_completar_kill(self._contrato(5, 50), kills_totales=55)
        self.assertTrue(ok)
        self.assertEqual(hechas, 5)

    def test_hechas_nunca_negativas(self):
        # Si kills_totales < kills_al_aceptar (caso anómalo), hechas = 0
        ok, hechas = puede_completar_kill(self._contrato(5, 100), kills_totales=50)
        self.assertEqual(hechas, 0)
        self.assertFalse(ok)

    def test_sin_campo_kills_al_aceptar_usa_0(self):
        contrato = {"tipo": "kill", "cantidad": 3}
        ok, hechas = puede_completar_kill(contrato, kills_totales=3)
        self.assertTrue(ok)

    def test_devuelve_tuple_dos_elementos(self):
        resultado = puede_completar_kill(self._contrato(5, 0), kills_totales=5)
        self.assertEqual(len(resultado), 2)


# --------------------------------------------------------------------------- #
#  puede_completar_entrega
# --------------------------------------------------------------------------- #

class TestPuedeCompletarEntrega(unittest.TestCase):

    def _contrato(self, cantidad=3, objetivo="mineral de hierro"):
        return {"tipo": "entrega", "cantidad": cantidad, "objetivo": objetivo}

    def test_cantidad_exacta_completa(self):
        ok, disp = puede_completar_entrega(self._contrato(3), disponible=3)
        self.assertTrue(ok)
        self.assertEqual(disp, 3)

    def test_cantidad_de_mas_completa(self):
        ok, disp = puede_completar_entrega(self._contrato(3), disponible=5)
        self.assertTrue(ok)
        self.assertEqual(disp, 5)

    def test_insuficiente_no_completa(self):
        ok, disp = puede_completar_entrega(self._contrato(3), disponible=2)
        self.assertFalse(ok)
        self.assertEqual(disp, 2)

    def test_sin_materiales_no_completa(self):
        ok, disp = puede_completar_entrega(self._contrato(3), disponible=0)
        self.assertFalse(ok)
        self.assertEqual(disp, 0)

    def test_devuelve_tuple_dos_elementos(self):
        resultado = puede_completar_entrega(self._contrato(3), disponible=3)
        self.assertEqual(len(resultado), 2)


# --------------------------------------------------------------------------- #
#  formatear_contrato
# --------------------------------------------------------------------------- #

class TestFormatearContrato(unittest.TestCase):

    def setUp(self):
        self.contrato = {
            "id":          "42_0",
            "tipo":        "kill",
            "descripcion": "Elimina 5 enemigos.",
            "objetivo":    "enemigo",
            "cantidad":    5,
            "dificultad":  1,
            "etiqueta":    "★☆☆",
            "recompensa":  {"monedas": 50, "xp": 30},
        }

    def test_devuelve_string(self):
        self.assertIsInstance(formatear_contrato(1, self.contrato), str)

    def test_contiene_numero(self):
        self.assertIn("[1]", formatear_contrato(1, self.contrato))

    def test_contiene_descripcion(self):
        self.assertIn("Elimina 5 enemigos", formatear_contrato(1, self.contrato))

    def test_contiene_monedas(self):
        self.assertIn("50", formatear_contrato(1, self.contrato))

    def test_contiene_xp(self):
        self.assertIn("30", formatear_contrato(1, self.contrato))

    def test_contiene_etiqueta(self):
        self.assertIn("★", formatear_contrato(1, self.contrato))


# --------------------------------------------------------------------------- #
#  formatear_progreso
# --------------------------------------------------------------------------- #

class TestFormatearProgreso(unittest.TestCase):

    def setUp(self):
        self.kill = {
            "tipo":            "kill",
            "descripcion":     "Elimina 5 enemigos.",
            "objetivo":        "enemigo",
            "cantidad":        5,
            "kills_al_aceptar": 10,
            "dificultad":      1,
            "etiqueta":        "★☆☆",
            "recompensa":      {"monedas": 50, "xp": 30},
        }
        self.entrega = {
            "tipo":        "entrega",
            "descripcion": "Entrega 3 mineral de hierro.",
            "objetivo":    "mineral de hierro",
            "cantidad":    3,
            "dificultad":  1,
            "etiqueta":    "★☆☆",
            "recompensa":  {"monedas": 50, "xp": 30},
        }

    def test_kill_devuelve_string(self):
        self.assertIsInstance(formatear_progreso(self.kill, kills_totales=12), str)

    def test_kill_muestra_progreso(self):
        texto = formatear_progreso(self.kill, kills_totales=13)
        self.assertIn("3/5", texto)

    def test_kill_progreso_no_excede_cantidad(self):
        texto = formatear_progreso(self.kill, kills_totales=100)
        self.assertIn("5/5", texto)

    def test_entrega_devuelve_string(self):
        self.assertIsInstance(formatear_progreso(self.entrega, disponible=2), str)

    def test_entrega_muestra_disponible(self):
        texto = formatear_progreso(self.entrega, disponible=2)
        self.assertIn("2/3", texto)

    def test_entrega_muestra_nombre_material(self):
        texto = formatear_progreso(self.entrega, disponible=1)
        self.assertIn("mineral de hierro", texto)


if __name__ == "__main__":
    unittest.main()
