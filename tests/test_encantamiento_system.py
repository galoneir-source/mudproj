"""
tests/test_encantamiento_system.py

Tests unitarios para el sistema de encantamiento (v0.16.0).
Sin dependencias de Evennia.
"""
import unittest

from systems.enchantment.enchantment import (
    MAX_ENCANTAMIENTO,
    COSTES_ENCANTAMIENTO,
    stat_primario,
    delta_encantamiento,
    coste_encantamiento,
    puede_encantar,
    verificar_ingredientes_encantamiento,
    texto_coste,
)


class TestStatPrimario(unittest.TestCase):

    def test_stat_primario_basico(self):
        self.assertEqual(stat_primario({"fuerza": 5, "destreza": 1}), "fuerza")

    def test_stat_primario_empate_mayor_primero(self):
        bonuses = {"inteligencia": 8, "defensa": 1}
        self.assertEqual(stat_primario(bonuses), "inteligencia")

    def test_stat_primario_ignora_negativos(self):
        bonuses = {"fuerza": 6, "defensa": -1}
        self.assertEqual(stat_primario(bonuses), "fuerza")

    def test_stat_primario_solo_negativos_devuelve_none(self):
        self.assertIsNone(stat_primario({"defensa": -1}))

    def test_stat_primario_bonuses_vacios_devuelve_none(self):
        self.assertIsNone(stat_primario({}))

    def test_stat_primario_inteligencia(self):
        bonuses = {"inteligencia": 8, "defensa": 1}
        self.assertEqual(stat_primario(bonuses), "inteligencia")

    def test_stat_primario_destreza(self):
        bonuses = {"destreza": 3, "fuerza": 1}
        self.assertEqual(stat_primario(bonuses), "destreza")


class TestDeltaEncantamiento(unittest.TestCase):

    def test_delta_arma_fuerza(self):
        delta = delta_encantamiento("arma", {"fuerza": 5, "constitucion": 1})
        self.assertEqual(delta, {"fuerza": 2})

    def test_delta_arma_inteligencia(self):
        delta = delta_encantamiento("arma", {"inteligencia": 8, "defensa": 1})
        self.assertEqual(delta, {"inteligencia": 2})

    def test_delta_arma_sin_stats_positivos(self):
        delta = delta_encantamiento("arma", {"defensa": -1})
        self.assertEqual(delta, {})

    def test_delta_armadura_fijo(self):
        delta = delta_encantamiento("armadura", {"defensa": 4, "hp_max": 10})
        self.assertEqual(delta, {"defensa": 2, "hp_max": 5})

    def test_delta_armadura_ignora_bonuses(self):
        self.assertEqual(
            delta_encantamiento("armadura", {}),
            {"defensa": 2, "hp_max": 5},
        )

    def test_delta_accesorio_todos_stats_positivos(self):
        delta = delta_encantamiento("accesorio", {"constitucion": 4, "hp_max": 15})
        self.assertEqual(delta, {"constitucion": 1, "hp_max": 1})

    def test_delta_accesorio_ignora_negativos(self):
        bonuses = {"inteligencia": 5, "defensa": 2, "hp_max": -10}
        delta = delta_encantamiento("accesorio", bonuses)
        self.assertIn("inteligencia", delta)
        self.assertIn("defensa", delta)
        self.assertNotIn("hp_max", delta)

    def test_delta_accesorio_vacio_da_dict_vacio(self):
        self.assertEqual(delta_encantamiento("accesorio", {}), {})

    def test_delta_slot_invalido(self):
        self.assertEqual(delta_encantamiento("slot_raro", {"fuerza": 3}), {})


class TestCosteEncantamiento(unittest.TestCase):

    def test_arma_nivel_1(self):
        self.assertEqual(coste_encantamiento("arma", 1), {"mineral de hierro": 2})

    def test_arma_nivel_2(self):
        coste = coste_encantamiento("arma", 2)
        self.assertIn("mineral de hierro", coste)
        self.assertIn("núcleo de piedra", coste)

    def test_arma_nivel_3(self):
        coste = coste_encantamiento("arma", 3)
        self.assertIn("núcleo de piedra", coste)
        self.assertIn("núcleo arcano", coste)

    def test_armadura_nivel_1(self):
        self.assertEqual(coste_encantamiento("armadura", 1), {"escama de lagarto": 2})

    def test_armadura_nivel_2(self):
        coste = coste_encantamiento("armadura", 2)
        self.assertIn("escama de lagarto", coste)
        self.assertIn("fragmento de alma", coste)

    def test_armadura_nivel_3(self):
        coste = coste_encantamiento("armadura", 3)
        self.assertIn("fragmento de alma", coste)
        self.assertIn("cenizas arcanas", coste)

    def test_accesorio_nivel_1(self):
        self.assertEqual(coste_encantamiento("accesorio", 1), {"gema en bruto": 1})

    def test_accesorio_nivel_2(self):
        coste = coste_encantamiento("accesorio", 2)
        self.assertIn("gema en bruto", coste)
        self.assertIn("cristal sagrado", coste)

    def test_accesorio_nivel_3(self):
        coste = coste_encantamiento("accesorio", 3)
        self.assertIn("cristal sagrado", coste)
        self.assertIn("núcleo arcano", coste)

    def test_nivel_invalido_devuelve_vacio(self):
        self.assertEqual(coste_encantamiento("arma", 4), {})

    def test_slot_invalido_devuelve_vacio(self):
        self.assertEqual(coste_encantamiento("gorro", 1), {})


class TestPuedeEncantar(unittest.TestCase):

    def test_nivel_0_puede(self):
        ok, _ = puede_encantar(0)
        self.assertTrue(ok)

    def test_nivel_2_puede(self):
        ok, _ = puede_encantar(2)
        self.assertTrue(ok)

    def test_nivel_max_no_puede(self):
        ok, msg = puede_encantar(MAX_ENCANTAMIENTO)
        self.assertFalse(ok)
        self.assertIn("máximo", msg)

    def test_nivel_sobre_max_no_puede(self):
        ok, _ = puede_encantar(MAX_ENCANTAMIENTO + 1)
        self.assertFalse(ok)

    def test_max_es_tres(self):
        self.assertEqual(MAX_ENCANTAMIENTO, 3)


class TestVerificarIngredientes(unittest.TestCase):

    def test_arma_nivel1_sin_ingredientes_falla(self):
        ok, faltantes = verificar_ingredientes_encantamiento("arma", 1, {})
        self.assertFalse(ok)
        self.assertIn("mineral de hierro", faltantes)

    def test_arma_nivel1_con_un_mineral_insuficiente(self):
        ok, faltantes = verificar_ingredientes_encantamiento(
            "arma", 1, {"mineral de hierro": 1}
        )
        self.assertFalse(ok)
        self.assertEqual(faltantes["mineral de hierro"], 1)

    def test_arma_nivel1_con_dos_minerales_ok(self):
        ok, faltantes = verificar_ingredientes_encantamiento(
            "arma", 1, {"mineral de hierro": 2}
        )
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_arma_nivel1_con_mas_de_los_necesarios_ok(self):
        ok, _ = verificar_ingredientes_encantamiento(
            "arma", 1, {"mineral de hierro": 5}
        )
        self.assertTrue(ok)

    def test_arma_nivel2_falta_nucleo(self):
        inventario = {"mineral de hierro": 2}
        ok, faltantes = verificar_ingredientes_encantamiento("arma", 2, inventario)
        self.assertFalse(ok)
        self.assertIn("núcleo de piedra", faltantes)

    def test_arma_nivel2_completo_ok(self):
        inventario = {"mineral de hierro": 2, "núcleo de piedra": 1}
        ok, faltantes = verificar_ingredientes_encantamiento("arma", 2, inventario)
        self.assertTrue(ok)
        self.assertEqual(faltantes, {})

    def test_armadura_nivel1_ok(self):
        ok, _ = verificar_ingredientes_encantamiento(
            "armadura", 1, {"escama de lagarto": 2}
        )
        self.assertTrue(ok)

    def test_armadura_nivel3_sin_cenizas_falla(self):
        inventario = {"fragmento de alma": 1}
        ok, faltantes = verificar_ingredientes_encantamiento("armadura", 3, inventario)
        self.assertFalse(ok)
        self.assertIn("cenizas arcanas", faltantes)

    def test_accesorio_nivel1_ok(self):
        ok, _ = verificar_ingredientes_encantamiento(
            "accesorio", 1, {"gema en bruto": 1}
        )
        self.assertTrue(ok)

    def test_slot_invalido_nivel_invalido_devuelve_false(self):
        ok, faltantes = verificar_ingredientes_encantamiento("gorro", 1, {"gema en bruto": 99})
        self.assertFalse(ok)
        self.assertEqual(faltantes, {})


class TestTextoCosto(unittest.TestCase):

    def test_texto_arma_nivel1(self):
        txt = texto_coste("arma", 1)
        self.assertIn("mineral de hierro", txt)
        self.assertIn("2", txt)

    def test_texto_armadura_nivel2(self):
        txt = texto_coste("armadura", 2)
        self.assertIn("escama de lagarto", txt)
        self.assertIn("fragmento de alma", txt)

    def test_texto_nivel_invalido(self):
        self.assertEqual(texto_coste("arma", 9), "—")

    def test_texto_slot_invalido(self):
        self.assertEqual(texto_coste("casco", 1), "—")


class TestCostesCompletos(unittest.TestCase):

    def test_todos_los_slots_tienen_tres_niveles(self):
        for slot in ("arma", "armadura", "accesorio"):
            for nivel in (1, 2, 3):
                coste = coste_encantamiento(slot, nivel)
                self.assertTrue(coste, f"Coste vacío para {slot} nivel {nivel}")

    def test_nivel3_siempre_requiere_raro(self):
        # nivel 3 siempre requiere núcleo arcano o cenizas arcanas
        arma3 = coste_encantamiento("arma", 3)
        acc3 = coste_encantamiento("accesorio", 3)
        arm3 = coste_encantamiento("armadura", 3)
        self.assertIn("núcleo arcano", arma3)
        self.assertIn("núcleo arcano", acc3)
        self.assertIn("cenizas arcanas", arm3)

    def test_nivel3_siempre_tiene_mas_tipos_que_nivel1(self):
        for slot in ("arma", "armadura", "accesorio"):
            tipos_1 = len(coste_encantamiento(slot, 1))
            tipos_3 = len(coste_encantamiento(slot, 3))
            self.assertGreaterEqual(tipos_3, tipos_1, f"{slot}: nivel3 debería tener ≥ tipos que nivel1")


if __name__ == "__main__":
    unittest.main()
