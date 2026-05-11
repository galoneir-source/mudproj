"""
tests/test_states.py

Tests unitarios para systems/combat/states.py.
No dependen de Evennia ni Django — se ejecutan con unittest estándar.
"""
import unittest

from systems.combat.states import (
    ESTADO_DEFAULTS,
    aplicar_estado,
    tick_estados,
    limpiar_estado,
    limpiar_todos,
    estado_de_habilidad,
)


# --------------------------------------------------------------------------- #
#  estado_de_habilidad
# --------------------------------------------------------------------------- #

class TestEstadoDeHabilidad(unittest.TestCase):

    def test_veneno_aplica_veneno(self):
        self.assertEqual(estado_de_habilidad("veneno"), "veneno")

    def test_corte_aplica_sangrado(self):
        self.assertEqual(estado_de_habilidad("corte"), "sangrado")

    def test_golpe_fuerte_no_aplica(self):
        self.assertIsNone(estado_de_habilidad("golpe fuerte"))

    def test_embestida_no_aplica(self):
        self.assertIsNone(estado_de_habilidad("embestida"))

    def test_case_insensitive(self):
        self.assertEqual(estado_de_habilidad("VENENO"), "veneno")
        self.assertEqual(estado_de_habilidad("Corte"), "sangrado")

    def test_habilidad_inexistente(self):
        self.assertIsNone(estado_de_habilidad("habilidad_rara"))


# --------------------------------------------------------------------------- #
#  aplicar_estado
# --------------------------------------------------------------------------- #

class TestAplicarEstado(unittest.TestCase):

    def test_nuevo_estado_usa_defaults(self):
        estados = aplicar_estado({}, "veneno")
        self.assertIn("veneno", estados)
        self.assertEqual(estados["veneno"]["turnos_restantes"], ESTADO_DEFAULTS["veneno"]["turnos_restantes"])
        self.assertEqual(estados["veneno"]["dano_por_turno"], ESTADO_DEFAULTS["veneno"]["dano_por_turno"])

    def test_renovar_estado_existente_no_acumula(self):
        estados = aplicar_estado({}, "veneno")
        estados["veneno"]["turnos_restantes"] = 1
        estados = aplicar_estado(estados, "veneno")
        # Debe renovar los turnos, no sumarlos
        self.assertEqual(estados["veneno"]["turnos_restantes"], ESTADO_DEFAULTS["veneno"]["turnos_restantes"])
        # Solo un estado veneno, sin duplicados
        self.assertEqual(len(estados), 1)

    def test_multiples_estados_coexisten(self):
        estados = aplicar_estado({}, "veneno")
        estados = aplicar_estado(estados, "sangrado")
        self.assertIn("veneno", estados)
        self.assertIn("sangrado", estados)

    def test_kwargs_sobreescriben_defaults(self):
        estados = aplicar_estado({}, "veneno", dano_por_turno=10, turnos_restantes=5)
        self.assertEqual(estados["veneno"]["dano_por_turno"], 10)
        self.assertEqual(estados["veneno"]["turnos_restantes"], 5)

    def test_no_muta_dict_original(self):
        original = {}
        aplicar_estado(original, "veneno")
        self.assertEqual(original, {})


# --------------------------------------------------------------------------- #
#  tick_estados
# --------------------------------------------------------------------------- #

class TestTickEstados(unittest.TestCase):

    def _tick(self, estados, hp=100, hp_max=100):
        return tick_estados(estados, hp, hp_max)

    def test_veneno_reduce_hp(self):
        estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 3}}
        nuevos, nuevo_hp, _ = self._tick(estados, hp=100)
        self.assertEqual(nuevo_hp, 95)

    def test_sangrado_reduce_hp(self):
        estados = {"sangrado": {"dano_por_turno": 3, "turnos_restantes": 2}}
        nuevos, nuevo_hp, _ = self._tick(estados, hp=100)
        self.assertEqual(nuevo_hp, 97)

    def test_regeneracion_aumenta_hp(self):
        estados = {"regeneracion": {"hp_por_turno": 8, "turnos_restantes": 4}}
        nuevos, nuevo_hp, _ = self._tick(estados, hp=50, hp_max=100)
        self.assertEqual(nuevo_hp, 58)

    def test_regeneracion_no_supera_maximo(self):
        estados = {"regeneracion": {"hp_por_turno": 20, "turnos_restantes": 2}}
        nuevos, nuevo_hp, _ = self._tick(estados, hp=95, hp_max=100)
        self.assertEqual(nuevo_hp, 100)

    def test_veneno_no_baja_de_cero(self):
        estados = {"veneno": {"dano_por_turno": 50, "turnos_restantes": 1}}
        nuevos, nuevo_hp, _ = self._tick(estados, hp=10)
        self.assertEqual(nuevo_hp, 0)

    def test_estado_expira_al_llegar_a_cero_turnos(self):
        estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 1}}
        nuevos, _, mensajes = self._tick(estados)
        self.assertNotIn("veneno", nuevos)
        self.assertTrue(any("expirado" in m for m in mensajes))

    def test_estado_decrementa_turnos(self):
        estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 3}}
        nuevos, _, _ = self._tick(estados)
        self.assertEqual(nuevos["veneno"]["turnos_restantes"], 2)

    def test_mensajes_no_vacios(self):
        estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 2}}
        _, _, mensajes = self._tick(estados)
        self.assertTrue(len(mensajes) > 0)

    def test_sin_estados_devuelve_hp_intacto(self):
        nuevos, nuevo_hp, mensajes = self._tick({}, hp=75)
        self.assertEqual(nuevo_hp, 75)
        self.assertEqual(nuevos, {})
        self.assertEqual(mensajes, [])

    def test_veneno_y_sangrado_acumulan(self):
        estados = {
            "veneno":   {"dano_por_turno": 5, "turnos_restantes": 2},
            "sangrado": {"dano_por_turno": 3, "turnos_restantes": 2},
        }
        _, nuevo_hp, _ = self._tick(estados, hp=100)
        self.assertEqual(nuevo_hp, 92)

    def test_no_muta_dict_original(self):
        original = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 3}}
        tick_estados(original, 100, 100)
        self.assertEqual(original["veneno"]["turnos_restantes"], 3)


# --------------------------------------------------------------------------- #
#  limpiar_estado / limpiar_todos
# --------------------------------------------------------------------------- #

class TestLimpiarEstado(unittest.TestCase):

    def test_elimina_estado_existente(self):
        estados = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 2}}
        estados = limpiar_estado(estados, "veneno")
        self.assertNotIn("veneno", estados)

    def test_no_falla_si_no_existe(self):
        estados = limpiar_estado({}, "veneno")
        self.assertEqual(estados, {})

    def test_no_elimina_otros_estados(self):
        estados = {
            "veneno":   {"dano_por_turno": 5, "turnos_restantes": 2},
            "sangrado": {"dano_por_turno": 3, "turnos_restantes": 1},
        }
        estados = limpiar_estado(estados, "veneno")
        self.assertIn("sangrado", estados)

    def test_limpiar_todos(self):
        estados = {"veneno": {}, "sangrado": {}, "regeneracion": {}}
        self.assertEqual(limpiar_todos(estados), {})

    def test_no_muta_original(self):
        original = {"veneno": {"dano_por_turno": 5, "turnos_restantes": 2}}
        limpiar_estado(original, "veneno")
        self.assertIn("veneno", original)


if __name__ == "__main__":
    unittest.main()
