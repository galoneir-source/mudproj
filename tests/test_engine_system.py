"""
tests/test_engine_system.py

Tests unitarios para systems/combat/engine.py.
No dependen de Evennia ni de Django — se ejecutan con unittest estándar.
"""
import unittest
from unittest.mock import patch

from systems.combat.engine import (
    STAT_DEFAULTS,
    XP_POR_NIVEL,
    calcular_dano_base,
    calcular_esquiva,
    calcular_critico,
    reduccion_por_defensa,
    resolver_ataque,
    _aplicar_habilidad,
    calcular_xp_recompensa,
    xp_para_siguiente_nivel,
    procesar_subida_de_nivel,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _stats(**kwargs):
    """Devuelve stats por defecto con overrides opcionales."""
    s = dict(STAT_DEFAULTS)
    s.update(kwargs)
    return s


# --------------------------------------------------------------------------- #
#  calcular_dano_base
# --------------------------------------------------------------------------- #

class TestCalcularDanoBase(unittest.TestCase):

    def test_minimo_siempre_uno(self):
        # Con fuerza muy baja y nivel 1 el resultado debe ser >= 1
        for _ in range(50):
            self.assertGreaterEqual(calcular_dano_base(fuerza=1, nivel=1), 1)

    def test_fuerza_alta_aumenta_dano(self):
        # Promediar sobre muchas tiradas para comparar tendencias
        n = 200
        bajo = sum(calcular_dano_base(10, 1) for _ in range(n)) / n
        alto = sum(calcular_dano_base(20, 1) for _ in range(n)) / n
        self.assertGreater(alto, bajo)

    def test_nivel_alto_aumenta_dano(self):
        n = 200
        bajo = sum(calcular_dano_base(10, 1) for _ in range(n)) / n
        alto = sum(calcular_dano_base(10, 10) for _ in range(n)) / n
        self.assertGreater(alto, bajo)

    def test_dado_dentro_de_rango(self):
        # Con fuerza y nivel base el valor crudo debe estar en 1-8 + bonuses
        for _ in range(100):
            d = calcular_dano_base(10, 1)
            self.assertGreaterEqual(d, 1)
            self.assertLessEqual(d, 20)  # dado 8 + bonus fuerza 0 + bonus nivel 0 max = 8


# --------------------------------------------------------------------------- #
#  calcular_esquiva
# --------------------------------------------------------------------------- #

class TestCalcularEsquiva(unittest.TestCase):

    def test_probabilidad_baja_destreza_baja(self):
        n = 1000
        esquivas = sum(1 for _ in range(n) if calcular_esquiva(1))
        # Con destreza 1 la prob está por el suelo (mínimo 2 %)
        self.assertLess(esquivas / n, 0.10)

    def test_probabilidad_alta_destreza_alta(self):
        n = 1000
        esquivas = sum(1 for _ in range(n) if calcular_esquiva(30))
        # Con destreza 30 la prob es alta (cap 40 %)
        self.assertGreater(esquivas / n, 0.20)

    def test_cap_maximo(self):
        # Destreza 200 no debe superar 40%
        n = 1000
        esquivas = sum(1 for _ in range(n) if calcular_esquiva(200))
        self.assertLessEqual(esquivas / n, 0.55)  # margen estadístico

    def test_devuelve_bool(self):
        self.assertIsInstance(calcular_esquiva(10), bool)


# --------------------------------------------------------------------------- #
#  calcular_critico
# --------------------------------------------------------------------------- #

class TestCalcularCritico(unittest.TestCase):

    def test_probabilidad_razonable_destreza_normal(self):
        n = 1000
        criticos = sum(1 for _ in range(n) if calcular_critico(10))
        # Prob base 10 %, margen estadístico amplio
        self.assertGreater(criticos / n, 0.03)
        self.assertLess(criticos / n, 0.20)

    def test_destreza_alta_mas_criticos(self):
        n = 1000
        bajos = sum(1 for _ in range(n) if calcular_critico(10))
        altos = sum(1 for _ in range(n) if calcular_critico(30))
        self.assertGreater(altos, bajos)

    def test_devuelve_bool(self):
        self.assertIsInstance(calcular_critico(10), bool)


# --------------------------------------------------------------------------- #
#  reduccion_por_defensa
# --------------------------------------------------------------------------- #

class TestReduccionPorDefensa(unittest.TestCase):

    def test_minimo_siempre_uno(self):
        self.assertEqual(reduccion_por_defensa(1, 100), 1)

    def test_sin_defensa(self):
        self.assertEqual(reduccion_por_defensa(10, 0), 10)

    def test_reduccion_parcial(self):
        # defensa 6 → reduccion 2 → daño 8 - 2 = 6
        self.assertEqual(reduccion_por_defensa(8, 6), 6)

    def test_defensa_alta(self):
        # defensa 30 → reduccion 10 → daño 5 - 10 = max(1,1)
        self.assertEqual(reduccion_por_defensa(5, 30), 1)


# --------------------------------------------------------------------------- #
#  resolver_ataque
# --------------------------------------------------------------------------- #

class TestResolverAtaque(unittest.TestCase):

    def _ataque_forzado(self, exito_esquiva=False, exito_critico=False, dado=4):
        """Llama resolver_ataque con random controlado."""
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=50, hp_max=50, destreza=10)
        with patch("systems.combat.engine.random") as mock_rng:
            # calcular_esquiva usa random.random()
            mock_rng.random.side_effect = [
                0.01 if exito_esquiva else 0.99,  # esquiva
                0.01 if exito_critico else 0.99,  # critico
            ]
            mock_rng.randint.return_value = dado
            return resolver_ataque(at, df, "Jugador", "Goblin")

    def test_esquiva_devuelve_exito_falso(self):
        resultado = self._ataque_forzado(exito_esquiva=True)
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.dano, 0)
        self.assertFalse(resultado.muerto)

    def test_golpe_normal_reduce_hp(self):
        resultado = self._ataque_forzado(exito_esquiva=False, exito_critico=False, dado=4)
        self.assertTrue(resultado.exito)
        self.assertGreater(resultado.dano, 0)
        self.assertEqual(resultado.hp_restante, 50 - resultado.dano)

    def test_golpe_critico_duplica_dano(self):
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=10)
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.01]  # no esquiva, sí crítico
            mock_rng.randint.return_value = 4
            resultado = resolver_ataque(at, df, "J", "G")
        self.assertTrue(resultado.critico)
        # daño base 4, reduccion 0, crítico x2 = 8
        self.assertEqual(resultado.dano, 8)

    def test_muerto_cuando_hp_llega_a_cero(self):
        at = _stats(fuerza=20, destreza=10, nivel=10)
        df = _stats(defensa=0, hp=1, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.99]  # no esquiva, no critico
            mock_rng.randint.return_value = 8  # dado 8 → dano 8+5+5=18 > 1 HP
            resultado = resolver_ataque(at, df, "J", "G")
        self.assertTrue(resultado.muerto)
        self.assertEqual(resultado.hp_restante, 0)

    def test_mensajes_no_vacios(self):
        resultado = self._ataque_forzado()
        self.assertTrue(resultado.mensaje_atacante)
        self.assertTrue(resultado.mensaje_defensor)
        self.assertTrue(resultado.mensaje_sala)

    def test_habilidad_modifica_dano(self):
        at = _stats(fuerza=10, destreza=10, nivel=1)
        df = _stats(defensa=0, hp=100, hp_max=100, destreza=1)
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.99]
            mock_rng.randint.return_value = 4
            resultado_base = resolver_ataque(at, df, "J", "G")
        with patch("systems.combat.engine.random") as mock_rng:
            mock_rng.random.side_effect = [0.99, 0.99]
            mock_rng.randint.return_value = 4
            resultado_hab = resolver_ataque(at, df, "J", "G", habilidad="golpe fuerte")
        # "golpe fuerte" x1.5 → más daño
        self.assertGreater(resultado_hab.dano, resultado_base.dano)


# --------------------------------------------------------------------------- #
#  _aplicar_habilidad
# --------------------------------------------------------------------------- #

class TestAplicarHabilidad(unittest.TestCase):

    def _hab(self, nombre, dano_base=10):
        return _aplicar_habilidad(dano_base, nombre, _stats())

    def test_golpe_fuerte(self):
        self.assertEqual(self._hab("golpe fuerte", 10), 15)

    def test_golpe_rapido(self):
        self.assertEqual(self._hab("golpe rapido", 10), 8)

    def test_embestida(self):
        self.assertEqual(self._hab("embestida", 10), 15)

    def test_corte(self):
        self.assertEqual(self._hab("corte", 10), 13)

    def test_veneno_rango(self):
        for _ in range(50):
            d = self._hab("veneno", 10)
            self.assertGreaterEqual(d, 11)
            self.assertLessEqual(d, 14)

    def test_habilidad_desconocida_no_modifica(self):
        self.assertEqual(self._hab("invisibilidad", 10), 10)

    def test_case_insensitive(self):
        self.assertEqual(self._hab("GOLPE FUERTE", 10), self._hab("golpe fuerte", 10))

    # ── dardo_magico / nova_arcana: usan Inteligencia EN LUGAR DE Fuerza ──────
    # Ambas prometen (en su descripción de systems/skills/trees.py) sustituir
    # el bonus de Fuerza por el de Inteligencia, no sumarlo encima.

    def test_dardo_magico_ignora_fuerza(self):
        # dano_base ya incorpora el bonus de la fuerza de quien ataca (como en
        # el flujo real de resolver_ataque); tras aplicar dardo mágico, ese
        # bonus debe quedar sustituido por el de inteligencia y desaparecer
        # la diferencia entre tener mucha o poca fuerza.
        with patch("random.randint", return_value=4):
            d_fuerza_baja = calcular_dano_base(fuerza=6, nivel=1)
            d_fuerza_alta = calcular_dano_base(fuerza=20, nivel=1)
        resultado_fuerza_baja = _aplicar_habilidad(
            d_fuerza_baja, "dardo magico", _stats(fuerza=6, inteligencia=10)
        )
        resultado_fuerza_alta = _aplicar_habilidad(
            d_fuerza_alta, "dardo magico", _stats(fuerza=20, inteligencia=10)
        )
        self.assertEqual(resultado_fuerza_baja, resultado_fuerza_alta)

    def test_dardo_magico_escala_con_inteligencia(self):
        base_int_baja = _aplicar_habilidad(10, "dardo magico", _stats(fuerza=10, inteligencia=10))
        base_int_alta = _aplicar_habilidad(10, "dardo magico", _stats(fuerza=10, inteligencia=20))
        self.assertGreater(base_int_alta, base_int_baja)

    def test_dardo_magico_stats_por_defecto_no_modifica(self):
        # fuerza=10 e inteligencia=10 (STAT_DEFAULTS) -> ambos bonus son 0
        self.assertEqual(self._hab("dardo magico", 10), 10)

    def test_nova_arcana_ignora_fuerza(self):
        with patch("random.randint", return_value=4):
            d_fuerza_baja = calcular_dano_base(fuerza=6, nivel=1)
            d_fuerza_alta = calcular_dano_base(fuerza=20, nivel=1)
        resultado_fuerza_baja = _aplicar_habilidad(
            d_fuerza_baja, "nova arcana", _stats(fuerza=6, inteligencia=10)
        )
        resultado_fuerza_alta = _aplicar_habilidad(
            d_fuerza_alta, "nova arcana", _stats(fuerza=20, inteligencia=10)
        )
        self.assertEqual(resultado_fuerza_baja, resultado_fuerza_alta)

    def test_nova_arcana_escala_con_inteligencia(self):
        base_int_baja = _aplicar_habilidad(10, "nova arcana", _stats(fuerza=10, inteligencia=10))
        base_int_alta = _aplicar_habilidad(10, "nova arcana", _stats(fuerza=10, inteligencia=20))
        self.assertGreater(base_int_alta, base_int_baja)

    def test_nova_arcana_multiplicador_2_5(self):
        self.assertEqual(self._hab("nova arcana", 10), 25)


# --------------------------------------------------------------------------- #
#  calcular_xp_recompensa
# --------------------------------------------------------------------------- #

class TestCalcularXpRecompensa(unittest.TestCase):

    def test_minimo_cinco(self):
        for nivel in range(1, 11):
            for _ in range(20):
                self.assertGreaterEqual(calcular_xp_recompensa(nivel), 5)

    def test_nivel_alto_mas_xp(self):
        bajo = sum(calcular_xp_recompensa(1) for _ in range(100)) / 100
        alto = sum(calcular_xp_recompensa(10) for _ in range(100)) / 100
        self.assertGreater(alto, bajo)

    def test_nivel_uno_rango_razonable(self):
        for _ in range(50):
            xp = calcular_xp_recompensa(1)
            self.assertGreaterEqual(xp, 5)
            self.assertLessEqual(xp, 100)


# --------------------------------------------------------------------------- #
#  xp_para_siguiente_nivel
# --------------------------------------------------------------------------- #

class TestXpParaSiguienteNivel(unittest.TestCase):

    def test_nivel_uno(self):
        self.assertEqual(xp_para_siguiente_nivel(1), XP_POR_NIVEL[1])

    def test_nivel_maximo_devuelve_infinito(self):
        self.assertEqual(xp_para_siguiente_nivel(10), 999999)

    def test_nivel_sobre_maximo(self):
        self.assertEqual(xp_para_siguiente_nivel(99), 999999)

    def test_progresion_creciente(self):
        for i in range(1, len(XP_POR_NIVEL) - 2):
            self.assertLessEqual(
                xp_para_siguiente_nivel(i),
                xp_para_siguiente_nivel(i + 1),
            )


# --------------------------------------------------------------------------- #
#  procesar_subida_de_nivel
# --------------------------------------------------------------------------- #

class TestProcesarSubidaDeNivel(unittest.TestCase):

    def test_sin_xp_suficiente_no_sube(self):
        stats = _stats(nivel=1, experiencia=50)  # necesita 100
        subio, nuevos = procesar_subida_de_nivel(stats)
        self.assertFalse(subio)
        self.assertEqual(nuevos["nivel"], 1)

    def test_sube_nivel_con_xp_exacta(self):
        umbral = XP_POR_NIVEL[1]  # 100
        stats = _stats(nivel=1, experiencia=umbral)
        subio, nuevos = procesar_subida_de_nivel(stats)
        self.assertTrue(subio)
        self.assertEqual(nuevos["nivel"], 2)

    def test_stats_aumentan_al_subir(self):
        stats = _stats(nivel=1, experiencia=XP_POR_NIVEL[1])
        _, nuevos = procesar_subida_de_nivel(stats)
        self.assertEqual(nuevos["fuerza"], stats["fuerza"] + 1)
        self.assertEqual(nuevos["constitucion"], stats["constitucion"] + 1)
        self.assertEqual(nuevos["defensa"], stats["defensa"] + 1)
        self.assertEqual(nuevos["hp_max"], stats["hp_max"] + 10)

    def test_hp_se_restaura_al_subir(self):
        stats = _stats(nivel=1, experiencia=XP_POR_NIVEL[1], hp=1)
        _, nuevos = procesar_subida_de_nivel(stats)
        self.assertEqual(nuevos["hp"], nuevos["hp_max"])

    def test_xp_sobrante_se_conserva(self):
        umbral = XP_POR_NIVEL[1]
        stats = _stats(nivel=1, experiencia=umbral + 30)
        _, nuevos = procesar_subida_de_nivel(stats)
        self.assertEqual(nuevos["experiencia"], 30)

    def test_doble_subida_de_nivel(self):
        # Suficiente XP para saltar dos niveles
        xp_total = XP_POR_NIVEL[1] + XP_POR_NIVEL[2]  # 100 + 250 = 350
        stats = _stats(nivel=1, experiencia=xp_total)
        subio, nuevos = procesar_subida_de_nivel(stats)
        self.assertTrue(subio)
        self.assertEqual(nuevos["nivel"], 3)

    def test_stats_originales_no_se_mutan(self):
        # La función debe trabajar sobre copia
        stats = _stats(nivel=1, experiencia=XP_POR_NIVEL[1])
        fuerza_original = stats["fuerza"]
        procesar_subida_de_nivel(stats)
        self.assertEqual(stats["fuerza"], fuerza_original)

    def test_nivel_maximo_no_sube_mas(self):
        # En nivel 10 con mucha XP no debe subir
        stats = _stats(nivel=10, experiencia=999999)
        subio, _ = procesar_subida_de_nivel(stats)
        self.assertFalse(subio)


if __name__ == "__main__":
    unittest.main()
