"""
tests/test_records_system.py

Tests unitarios puros para el sistema de récords globales (v0.23.0).
Sin dependencias de Evennia.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && /opt/evennia/mudproj/venv/bin/pytest tests/test_records_system.py
"""
import unittest

from systems.records.records import (
    CATEGORIAS,
    CAT_IDS,
    TOP_N,
    extraer_stat,
    extraer_stat_crafteo,
    extraer_stat_duelos,
    extraer_stat_jefes,
    extraer_stat_kills,
    extraer_stat_misiones,
    formatear_numero,
    formatear_posicion,
    tiempo_desde,
    top_n,
)


# ---------------------------------------------------------------------------
# Catálogo de categorías
# ---------------------------------------------------------------------------

class TestCategorias(unittest.TestCase):

    def test_existen_cinco_categorias(self):
        self.assertEqual(len(CATEGORIAS), 5)

    def test_cat_ids_contiene_kills(self):
        self.assertIn("kills", CAT_IDS)

    def test_cat_ids_contiene_misiones(self):
        self.assertIn("misiones", CAT_IDS)

    def test_cat_ids_contiene_jefes(self):
        self.assertIn("jefes", CAT_IDS)

    def test_cat_ids_contiene_duelos(self):
        self.assertIn("duelos", CAT_IDS)

    def test_cat_ids_contiene_crafteo(self):
        self.assertIn("crafteo", CAT_IDS)

    def test_todas_tienen_titulo(self):
        for cat_id, cat in CATEGORIAS.items():
            self.assertIn("titulo", cat, cat_id)
            self.assertTrue(cat["titulo"])

    def test_todas_tienen_icono(self):
        for cat_id, cat in CATEGORIAS.items():
            self.assertIn("icono", cat, cat_id)
            self.assertTrue(cat["icono"])

    def test_todas_tienen_descripcion(self):
        for cat_id, cat in CATEGORIAS.items():
            self.assertIn("descripcion", cat, cat_id)

    def test_top_n_es_positivo(self):
        self.assertGreater(TOP_N, 0)


# ---------------------------------------------------------------------------
# Extracción de stats
# ---------------------------------------------------------------------------

class TestExtraerStats(unittest.TestCase):

    # kills
    def test_kills_cero_cuando_none(self):
        self.assertEqual(extraer_stat_kills(None), 0)

    def test_kills_cero_cuando_cero(self):
        self.assertEqual(extraer_stat_kills(0), 0)

    def test_kills_valor_positivo(self):
        self.assertEqual(extraer_stat_kills(42), 42)

    # misiones
    def test_misiones_cero_dict_vacio(self):
        self.assertEqual(extraer_stat_misiones({}), 0)

    def test_misiones_cero_cuando_none(self):
        self.assertEqual(extraer_stat_misiones(None), 0)

    def test_misiones_cuenta_solo_entregadas(self):
        quests = {
            "a": {"estado": "entregada"},
            "b": {"estado": "activa"},
            "c": {"estado": "completada"},
            "d": {"estado": "entregada"},
        }
        self.assertEqual(extraer_stat_misiones(quests), 2)

    def test_misiones_filtra_activas(self):
        quests = {"a": {"estado": "activa"}}
        self.assertEqual(extraer_stat_misiones(quests), 0)

    def test_misiones_filtra_completadas(self):
        quests = {"a": {"estado": "completada"}}
        self.assertEqual(extraer_stat_misiones(quests), 0)

    def test_misiones_todas_entregadas(self):
        quests = {f"q{i}": {"estado": "entregada"} for i in range(5)}
        self.assertEqual(extraer_stat_misiones(quests), 5)

    # jefes
    def test_jefes_cero_lista_vacia(self):
        self.assertEqual(extraer_stat_jefes([]), 0)

    def test_jefes_cero_cuando_none(self):
        self.assertEqual(extraer_stat_jefes(None), 0)

    def test_jefes_cuenta_elementos(self):
        self.assertEqual(extraer_stat_jefes(["BOSS_A", "BOSS_B", "BOSS_C"]), 3)

    # duelos
    def test_duelos_cero_cuando_none(self):
        self.assertEqual(extraer_stat_duelos(None), 0)

    def test_duelos_valor(self):
        self.assertEqual(extraer_stat_duelos(7), 7)

    # crafteo
    def test_crafteo_cero_cuando_none(self):
        self.assertEqual(extraer_stat_crafteo(None), 0)

    def test_crafteo_valor(self):
        self.assertEqual(extraer_stat_crafteo(15), 15)


class TestExtraerStatGenerico(unittest.TestCase):
    """Tests de la función unificada extraer_stat(cat_id, db_dict)."""

    def _db(self, **kwargs):
        return {
            "kills_totales": 0,
            "quests": {},
            "jefes_derrotados": [],
            "duelos_ganados": 0,
            "objetos_crafteados": 0,
            **kwargs,
        }

    def test_kills(self):
        self.assertEqual(extraer_stat("kills", self._db(kills_totales=10)), 10)

    def test_misiones(self):
        db = self._db(quests={"q1": {"estado": "entregada"}})
        self.assertEqual(extraer_stat("misiones", db), 1)

    def test_jefes(self):
        db = self._db(jefes_derrotados=["A", "B"])
        self.assertEqual(extraer_stat("jefes", db), 2)

    def test_duelos(self):
        db = self._db(duelos_ganados=5)
        self.assertEqual(extraer_stat("duelos", db), 5)

    def test_crafteo(self):
        db = self._db(objetos_crafteados=3)
        self.assertEqual(extraer_stat("crafteo", db), 3)

    def test_categoria_desconocida(self):
        self.assertEqual(extraer_stat("xyz", self._db()), 0)


# ---------------------------------------------------------------------------
# top_n
# ---------------------------------------------------------------------------

class TestTopN(unittest.TestCase):

    def test_ordena_descendente(self):
        entradas = [("B", 10), ("A", 50), ("C", 30)]
        resultado = top_n(entradas)
        self.assertEqual(resultado[0], ("A", 50))

    def test_devuelve_n_primeros(self):
        entradas = [(str(i), i) for i in range(10)]
        self.assertEqual(len(top_n(entradas, 5)), 5)

    def test_n_mayor_que_lista(self):
        entradas = [("A", 1), ("B", 2)]
        self.assertEqual(len(top_n(entradas, 10)), 2)

    def test_lista_vacia(self):
        self.assertEqual(top_n([], 5), [])

    def test_lista_un_elemento(self):
        self.assertEqual(top_n([("A", 99)]), [("A", 99)])

    def test_usa_top_n_por_defecto(self):
        entradas = [(str(i), i) for i in range(10)]
        self.assertEqual(len(top_n(entradas)), TOP_N)

    def test_empate_preserva_ambos(self):
        entradas = [("A", 10), ("B", 10)]
        resultado = top_n(entradas, 2)
        self.assertEqual(len(resultado), 2)


# ---------------------------------------------------------------------------
# formatear_numero
# ---------------------------------------------------------------------------

class TestFormatearNumero(unittest.TestCase):

    def test_cero(self):
        self.assertEqual(formatear_numero(0), "0")

    def test_menos_de_mil(self):
        self.assertEqual(formatear_numero(999), "999")

    def test_exactamente_mil(self):
        self.assertEqual(formatear_numero(1000), "1.000")

    def test_millón(self):
        self.assertEqual(formatear_numero(1_000_000), "1.000.000")

    def test_usa_punto_como_separador(self):
        # Convención española: puntos como separadores de miles
        self.assertIn(".", formatear_numero(1500))


# ---------------------------------------------------------------------------
# formatear_posicion
# ---------------------------------------------------------------------------

class TestFormatearPosicion(unittest.TestCase):

    def test_devuelve_string(self):
        self.assertIsInstance(formatear_posicion(1, "Aragorn", 100), str)

    def test_contiene_posicion(self):
        linea = formatear_posicion(3, "Aragorn", 100)
        self.assertIn("3.", linea)

    def test_contiene_nombre(self):
        linea = formatear_posicion(1, "Gandalf", 500)
        self.assertIn("Gandalf", linea)

    def test_contiene_valor_formateado(self):
        linea = formatear_posicion(1, "A", 1500)
        self.assertIn("1.500", linea)

    def test_numero_cero(self):
        linea = formatear_posicion(1, "Novato", 0)
        self.assertIn("0", linea)


# ---------------------------------------------------------------------------
# tiempo_desde
# ---------------------------------------------------------------------------

class TestTiempoDesde(unittest.TestCase):

    def test_ts_cero_desconocido(self):
        self.assertIn("desconocido", tiempo_desde(0, 1000))

    def test_segundos(self):
        txt = tiempo_desde(1000, 1030)
        self.assertIn("30s", txt)

    def test_minutos(self):
        txt = tiempo_desde(1000, 1000 + 125)
        self.assertIn("min", txt)

    def test_horas(self):
        txt = tiempo_desde(1000, 1000 + 7200)
        self.assertIn("h", txt)

    def test_menos_de_un_minuto(self):
        txt = tiempo_desde(1000, 1000 + 45)
        self.assertIn("s", txt)


if __name__ == "__main__":
    unittest.main()
