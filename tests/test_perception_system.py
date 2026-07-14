"""
tests/test_perception_system.py

Tests unitarios para systems/perception/perception_manager.py.
No dependen de Evennia — usan objetos mock simples.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && pytest tests/test_perception_system.py
"""
import unittest
from types import SimpleNamespace

from systems.perception.perception_manager import PerceptionManager


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _obj(**attrs):
    """Crea un objeto mock con db.* attrs."""
    db = SimpleNamespace(**attrs)
    return SimpleNamespace(db=db)


def _sala(detalles=None):
    """Crea una sala mock con detalles ocultos opcionales."""
    db = SimpleNamespace(detalles_ocultos=detalles)
    return SimpleNamespace(db=db)


# --------------------------------------------------------------------------- #
#  nivel_percepcion
# --------------------------------------------------------------------------- #

class TestNivelPercepcion(unittest.TestCase):

    def setUp(self):
        self.pm = PerceptionManager()

    def test_formula_base(self):
        # inteligencia 10, nivel 1 → 10 + 0 = 10
        personaje = _obj(inteligencia=10, nivel=1)
        self.assertEqual(self.pm.nivel_percepcion(personaje), 10)

    def test_formula_con_nivel_alto(self):
        # inteligencia 10, nivel 8 → 10 + 4 = 14
        personaje = _obj(inteligencia=10, nivel=8)
        self.assertEqual(self.pm.nivel_percepcion(personaje), 14)

    def test_inteligencia_alta(self):
        # inteligencia 18, nivel 2 → 18 + 1 = 19
        personaje = _obj(inteligencia=18, nivel=2)
        self.assertEqual(self.pm.nivel_percepcion(personaje), 19)

    def test_observer_none_devuelve_diez(self):
        self.assertEqual(self.pm.nivel_percepcion(None), 10)

    def test_inteligencia_none_usa_default(self):
        # Si db.inteligencia es None se usa 10
        personaje = _obj(inteligencia=None, nivel=1)
        self.assertEqual(self.pm.nivel_percepcion(personaje), 10)

    def test_nivel_none_usa_uno(self):
        # Si db.nivel es None, nivel = 1 → nivel//2 = 0
        personaje = _obj(inteligencia=12, nivel=None)
        self.assertEqual(self.pm.nivel_percepcion(personaje), 12)


# --------------------------------------------------------------------------- #
#  revelar_detalles
# --------------------------------------------------------------------------- #

class TestRevelarDetalles(unittest.TestCase):

    def setUp(self):
        self.pm = PerceptionManager()
        self.personaje = _obj(inteligencia=10, nivel=4)  # percepcion = 12

    def test_sin_detalles_devuelve_lista_vacia(self):
        sala = _sala(detalles=None)
        self.assertEqual(self.pm.revelar_detalles(sala, self.personaje), [])

    def test_detalles_vacios(self):
        sala = _sala(detalles=[])
        self.assertEqual(self.pm.revelar_detalles(sala, self.personaje), [])

    def test_detalle_accesible(self):
        # percepcion 12 >= req 10 → se revela
        sala = _sala(detalles=[{"texto": "Una grieta.", "req_percepcion": 10}])
        resultado = self.pm.revelar_detalles(sala, self.personaje)
        self.assertIn("Una grieta.", resultado)

    def test_detalle_inaccesible(self):
        # percepcion 12 < req 15 → no se revela
        sala = _sala(detalles=[{"texto": "Secreto.", "req_percepcion": 15}])
        resultado = self.pm.revelar_detalles(sala, self.personaje)
        self.assertNotIn("Secreto.", resultado)

    def test_mezcla_accesible_e_inaccesible(self):
        sala = _sala(detalles=[
            {"texto": "Pista visible.",  "req_percepcion": 10},
            {"texto": "Pista oculta.",   "req_percepcion": 20},
        ])
        resultado = self.pm.revelar_detalles(sala, self.personaje)
        self.assertIn("Pista visible.", resultado)
        self.assertNotIn("Pista oculta.", resultado)

    def test_req_igual_a_percepcion_es_visible(self):
        # >= en el límite
        personaje = _obj(inteligencia=12, nivel=0)  # percepcion = 12
        sala = _sala(detalles=[{"texto": "Exacto.", "req_percepcion": 12}])
        resultado = self.pm.revelar_detalles(sala, personaje)
        self.assertIn("Exacto.", resultado)

    def test_detalle_sin_req_siempre_visible(self):
        sala = _sala(detalles=[{"texto": "Siempre."}])
        resultado = self.pm.revelar_detalles(sala, self.personaje)
        self.assertIn("Siempre.", resultado)

    def test_entrada_no_dict_se_ignora(self):
        sala = _sala(detalles=["cadena suelta", None, 42])
        resultado = self.pm.revelar_detalles(sala, self.personaje)
        self.assertEqual(resultado, [])


# --------------------------------------------------------------------------- #
#  puede_detectar
# --------------------------------------------------------------------------- #

class TestPuedeDetectar(unittest.TestCase):

    def setUp(self):
        self.pm = PerceptionManager()
        self.personaje = _obj(inteligencia=13, nivel=2)  # percepcion = 14

    def test_objeto_visible_siempre_detectable(self):
        obj = _obj(oculto=False, nivel_sigilo=20)
        self.assertTrue(self.pm.puede_detectar(self.personaje, obj))

    def test_objeto_oculto_con_percepcion_suficiente(self):
        obj = _obj(oculto=True, nivel_sigilo=14)
        self.assertTrue(self.pm.puede_detectar(self.personaje, obj))

    def test_objeto_oculto_sin_percepcion_suficiente(self):
        obj = _obj(oculto=True, nivel_sigilo=15)
        self.assertFalse(self.pm.puede_detectar(self.personaje, obj))

    def test_oculto_sin_nivel_sigilo_usa_15(self):
        # nivel_sigilo None → default 15; personaje percepcion 14 → no detecta
        obj = _obj(oculto=True, nivel_sigilo=None)
        self.assertFalse(self.pm.puede_detectar(self.personaje, obj))

    def test_oculto_false_none_es_visible(self):
        obj = _obj(oculto=None, nivel_sigilo=100)
        self.assertTrue(self.pm.puede_detectar(self.personaje, obj))


# --------------------------------------------------------------------------- #
#  filtrar_visibles
# --------------------------------------------------------------------------- #

class TestFiltrarVisibles(unittest.TestCase):

    def setUp(self):
        self.pm = PerceptionManager()
        self.personaje = _obj(inteligencia=10, nivel=2)  # percepcion = 11

    def test_lista_vacia(self):
        self.assertEqual(self.pm.filtrar_visibles(self.personaje, []), [])

    def test_todos_visibles(self):
        objs = [_obj(oculto=False) for _ in range(3)]
        resultado = self.pm.filtrar_visibles(self.personaje, objs)
        self.assertEqual(len(resultado), 3)

    def test_filtra_ocultos(self):
        visible = _obj(oculto=False)
        oculto = _obj(oculto=True, nivel_sigilo=20)
        resultado = self.pm.filtrar_visibles(self.personaje, [visible, oculto])
        self.assertIn(visible, resultado)
        self.assertNotIn(oculto, resultado)

    def test_detecta_con_percepcion_alta(self):
        personaje_agudo = _obj(inteligencia=20, nivel=2)  # percepcion = 21
        oculto = _obj(oculto=True, nivel_sigilo=18)
        resultado = self.pm.filtrar_visibles(personaje_agudo, [oculto])
        self.assertIn(oculto, resultado)


# --------------------------------------------------------------------------- #
#  process (pipeline de texto)
# --------------------------------------------------------------------------- #

class TestProcess(unittest.TestCase):

    def setUp(self):
        self.pm = PerceptionManager()

    def test_texto_sin_modificar(self):
        self.assertEqual(self.pm.process("Hola mundo"), "Hola mundo")

    def test_cadena_vacia(self):
        self.assertEqual(self.pm.process(""), "")


if __name__ == "__main__":
    unittest.main()
