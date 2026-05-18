"""
tests/test_skills_trees.py

Tests unitarios puros para systems/skills/trees.py y systems/skills/engine.py.
No dependen de Evennia ni Django.
"""
import unittest

from systems.skills.trees import HABILIDADES, RAMAS, HABILIDADES_INICIALES
from systems.skills.engine import (
    puntos_gastados,
    puntos_disponibles,
    puede_aprender,
    aprender,
    buscar_habilidad,
    habilidades_por_rama,
)


# --------------------------------------------------------------------------- #
#  Estructura del catálogo
# --------------------------------------------------------------------------- #

class TestEstructuraHabilidades(unittest.TestCase):

    def test_no_vacio(self):
        self.assertGreater(len(HABILIDADES), 0)

    def test_tres_ramas(self):
        self.assertEqual(len(RAMAS), 3)
        self.assertIn("guerrero", RAMAS)
        self.assertIn("explorador", RAMAS)
        self.assertIn("mago", RAMAS)

    def test_campos_obligatorios(self):
        campos = {"nombre", "rama", "nivel_req", "coste", "requisitos", "tipo", "descripcion"}
        for hid, info in HABILIDADES.items():
            for campo in campos:
                self.assertIn(campo, info, f"'{hid}' falta campo '{campo}'")

    def test_tipos_validos(self):
        for hid, info in HABILIDADES.items():
            self.assertIn(info["tipo"], ("activa", "pasiva"), f"'{hid}' tipo inválido")

    def test_coste_positivo(self):
        for hid, info in HABILIDADES.items():
            self.assertGreater(info["coste"], 0, f"'{hid}' coste <= 0")

    def test_nivel_req_positivo(self):
        for hid, info in HABILIDADES.items():
            self.assertGreaterEqual(info["nivel_req"], 1, f"'{hid}' nivel_req < 1")

    def test_requisitos_existen(self):
        for hid, info in HABILIDADES.items():
            for req in info["requisitos"]:
                self.assertIn(req, HABILIDADES, f"'{hid}' req '{req}' no existe")

    def test_cada_rama_tiene_cuatro_habilidades(self):
        for rama in RAMAS:
            habs = [hid for hid, info in HABILIDADES.items() if info["rama"] == rama]
            self.assertEqual(len(habs), 4, f"Rama '{rama}' no tiene 4 habilidades")

    def test_iniciales_en_catalogo(self):
        for hid in HABILIDADES_INICIALES:
            self.assertIn(hid, HABILIDADES)

    def test_pasivas_tienen_efecto_pasivo(self):
        for hid, info in HABILIDADES.items():
            if info["tipo"] == "pasiva":
                self.assertIn("efecto_pasivo", info, f"'{hid}' pasiva sin efecto_pasivo")
                self.assertIsInstance(info["efecto_pasivo"], dict)


# --------------------------------------------------------------------------- #
#  puntos_gastados / puntos_disponibles
# --------------------------------------------------------------------------- #

class TestPuntos(unittest.TestCase):

    def test_solo_iniciales_gastados_cero(self):
        self.assertEqual(puntos_gastados(set(HABILIDADES_INICIALES)), 0)

    def test_iniciales_mas_embestida(self):
        habs = set(HABILIDADES_INICIALES) | {"embestida"}
        self.assertEqual(puntos_gastados(habs), 1)

    def test_disponibles_nivel1_cero(self):
        self.assertEqual(puntos_disponibles(1, 0), 0)

    def test_disponibles_nivel2_uno(self):
        self.assertEqual(puntos_disponibles(2, 0), 1)

    def test_disponibles_nivel5_gastado1(self):
        self.assertEqual(puntos_disponibles(5, 1), 3)

    def test_no_negativos(self):
        self.assertEqual(puntos_disponibles(1, 5), 0)


# --------------------------------------------------------------------------- #
#  puede_aprender
# --------------------------------------------------------------------------- #

class TestPuedeAprender(unittest.TestCase):

    def setUp(self):
        self.iniciales = set(HABILIDADES_INICIALES)

    def test_habilidad_inexistente(self):
        puede, _ = puede_aprender("xyz_inventada", self.iniciales, 10)
        self.assertFalse(puede)

    def test_ya_conocida(self):
        puede, _ = puede_aprender("golpe_fuerte", self.iniciales, 5)
        self.assertFalse(puede)

    def test_nivel_insuficiente(self):
        puede, _ = puede_aprender("embestida", self.iniciales, 1)
        self.assertFalse(puede)

    def test_requisito_faltante(self):
        habs = {"golpe_rapido"}
        puede, _ = puede_aprender("embestida", habs, 5)
        self.assertFalse(puede)

    def test_sin_puntos(self):
        # nivel 2 = 1 punto, pero ya gastamos 1 en embestida
        habs = set(HABILIDADES_INICIALES) | {"embestida"}
        puede, _ = puede_aprender("corte", habs, 2)
        self.assertFalse(puede)

    def test_puede_aprender_embestida(self):
        puede, err = puede_aprender("embestida", self.iniciales, 3)
        self.assertTrue(puede, err)

    def test_puede_aprender_corte(self):
        puede, err = puede_aprender("corte", self.iniciales, 3)
        self.assertTrue(puede, err)

    def test_cadena_guerrero_completa(self):
        habs = set(HABILIDADES_INICIALES)
        for hid in ("embestida", "escudo_fe"):
            exito, habs, _ = aprender(hid, habs, 10)
            self.assertTrue(exito)
        puede, err = puede_aprender("golpe_maestro", habs, 10)
        self.assertTrue(puede, err)

    def test_cadena_explorador_completa(self):
        habs = set(HABILIDADES_INICIALES)
        for hid in ("corte", "veneno"):
            exito, habs, _ = aprender(hid, habs, 10)
            self.assertTrue(exito)
        puede, err = puede_aprender("ejecutar", habs, 10)
        self.assertTrue(puede, err)

    def test_cadena_mago_completa(self):
        habs = set(HABILIDADES_INICIALES)
        for hid in ("dardo_magico", "escudo_arcano"):
            exito, habs, _ = aprender(hid, habs, 10)
            self.assertTrue(exito)
        puede, err = puede_aprender("bola_fuego", habs, 10)
        self.assertTrue(puede, err)


# --------------------------------------------------------------------------- #
#  aprender
# --------------------------------------------------------------------------- #

class TestAprender(unittest.TestCase):

    def test_aprende_embestida(self):
        habs = set(HABILIDADES_INICIALES)
        exito, nuevas, err = aprender("embestida", habs, 3)
        self.assertTrue(exito)
        self.assertIn("embestida", nuevas)
        self.assertEqual(err, "")

    def test_falla_sin_nivel(self):
        habs = set(HABILIDADES_INICIALES)
        exito, nuevas, _ = aprender("embestida", habs, 1)
        self.assertFalse(exito)
        self.assertNotIn("embestida", nuevas)

    def test_resultado_inmutable(self):
        habs = set(HABILIDADES_INICIALES)
        _, nuevas, _ = aprender("embestida", habs, 3)
        self.assertNotEqual(id(habs), id(nuevas))
        self.assertNotIn("embestida", habs)


# --------------------------------------------------------------------------- #
#  buscar_habilidad
# --------------------------------------------------------------------------- #

class TestBuscarHabilidad(unittest.TestCase):

    def test_por_id_exacto(self):
        hid, info = buscar_habilidad("embestida")
        self.assertEqual(hid, "embestida")

    def test_por_id_con_guion_bajo(self):
        hid, info = buscar_habilidad("golpe_fuerte")
        self.assertEqual(hid, "golpe_fuerte")

    def test_por_nombre_con_espacio(self):
        hid, info = buscar_habilidad("golpe fuerte")
        self.assertEqual(hid, "golpe_fuerte")

    def test_nombre_exacto_display(self):
        hid, info = buscar_habilidad("Golpe Fuerte")
        self.assertEqual(hid, "golpe_fuerte")

    def test_parcial_unico(self):
        hid, info = buscar_habilidad("embestida")
        self.assertIsNotNone(hid)

    def test_inexistente_devuelve_none(self):
        hid, info = buscar_habilidad("xyz_inventada_zzz")
        self.assertIsNone(hid)
        self.assertIsNone(info)

    def test_busca_drenar(self):
        hid, info = buscar_habilidad("drenar vida")
        self.assertEqual(hid, "drenar_vida")

    def test_busca_bola_fuego(self):
        hid, info = buscar_habilidad("bola fuego")
        self.assertEqual(hid, "bola_fuego")

    def test_busca_escudo_fe(self):
        hid, info = buscar_habilidad("escudo de fe")
        self.assertEqual(hid, "escudo_fe")


# --------------------------------------------------------------------------- #
#  habilidades_por_rama
# --------------------------------------------------------------------------- #

class TestHabilidadesPorRama(unittest.TestCase):

    def test_guerrero_ordenado(self):
        habs = habilidades_por_rama("guerrero")
        niveles = [info["nivel_req"] for _, info in habs]
        self.assertEqual(niveles, sorted(niveles))

    def test_explorador_cuatro(self):
        self.assertEqual(len(habilidades_por_rama("explorador")), 4)

    def test_mago_cuatro(self):
        self.assertEqual(len(habilidades_por_rama("mago")), 4)

    def test_rama_invalida_vacia(self):
        self.assertEqual(habilidades_por_rama("xxxx"), [])


if __name__ == "__main__":
    unittest.main()
