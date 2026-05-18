"""
tests/test_party_system.py

Tests unitarios puros para systems/party/engine.py.
No requieren Evennia.
"""
import unittest
from systems.party.engine import xp_por_miembro, puede_invitar_validar, MAX_MIEMBROS


class TestMaxMiembros(unittest.TestCase):
    def test_max_es_cuatro(self):
        self.assertEqual(MAX_MIEMBROS, 4)


class TestXpPorMiembro(unittest.TestCase):
    def test_solo_sin_cambio(self):
        self.assertEqual(xp_por_miembro(100, 1), 100)

    def test_cero_o_negativo_como_solo(self):
        self.assertEqual(xp_por_miembro(100, 0), 100)

    def test_dos_miembros_con_bonus(self):
        # 100 * 1.2 = 120 // 2 = 60
        self.assertEqual(xp_por_miembro(100, 2), 60)

    def test_tres_miembros(self):
        # 100 * 1.2 = 120 // 3 = 40
        self.assertEqual(xp_por_miembro(100, 3), 40)

    def test_cuatro_miembros(self):
        # 100 * 1.2 = 120 // 4 = 30
        self.assertEqual(xp_por_miembro(100, 4), 30)

    def test_minimo_uno_con_xp_bajo(self):
        self.assertGreaterEqual(xp_por_miembro(1, 4), 1)

    def test_total_grupo_mayor_que_solo(self):
        # El bonus hace que el total distribuido supere el valor individual
        solo = xp_por_miembro(100, 1)        # 100
        por_dos = xp_por_miembro(100, 2)     # 60
        self.assertGreater(por_dos * 2, solo)  # 120 > 100

    def test_xp_cero(self):
        self.assertEqual(xp_por_miembro(0, 1), 0)

    def test_xp_grande(self):
        resultado = xp_por_miembro(1000, 4)
        self.assertEqual(resultado, 300)  # 1000*1.2=1200//4=300


class TestPuedeInvitarValidar(unittest.TestCase):
    def test_caso_feliz(self):
        ok, msg = puede_invitar_validar(False, False, False, True)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_diferente_sala(self):
        ok, msg = puede_invitar_validar(False, False, False, False)
        self.assertFalse(ok)
        self.assertIn("sala", msg.lower())

    def test_objetivo_ya_en_partido(self):
        ok, msg = puede_invitar_validar(False, False, True, True)
        self.assertFalse(ok)
        self.assertIn("grupo", msg.lower())

    def test_invitante_en_partido_sin_ser_lider(self):
        ok, msg = puede_invitar_validar(True, False, False, True)
        self.assertFalse(ok)
        self.assertIn("líder", msg.lower())

    def test_invitante_lider_puede_invitar(self):
        ok, _ = puede_invitar_validar(True, True, False, True)
        self.assertTrue(ok)

    def test_invitante_sin_partido_puede_invitar(self):
        ok, _ = puede_invitar_validar(False, False, False, True)
        self.assertTrue(ok)

    def test_objetivo_en_partido_distinta_sala(self):
        ok, _ = puede_invitar_validar(False, False, True, False)
        self.assertFalse(ok)

    def test_combinacion_todo_malo(self):
        ok, _ = puede_invitar_validar(True, False, True, False)
        self.assertFalse(ok)

    def test_lider_invitante_objetivo_en_partido(self):
        # El objetivo ya tiene grupo → no se puede aunque el invitante sea líder
        ok, _ = puede_invitar_validar(True, True, True, True)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
