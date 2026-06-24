"""
tests/test_subclases.py

Tests unitarios puros del sistema de subclases.
No requieren Django ni Evennia.
"""
import unittest

from systems.subclasses.subclasses import (
    SUBCLASES, NIVEL_MIN_SUBCLASE,
    subclase_valida, subclases_de_clase,
    puede_elegir_subclase, aplicar_subclase,
)
from systems.skills.trees import HABILIDADES, RAMAS
from systems.skills.engine import puede_aprender, aprender, puntos_disponibles, puntos_gastados
from systems.combat.engine import _aplicar_habilidad, efecto_postcombat
from systems.combat.states import estado_de_habilidad


# ─── Catálogo SUBCLASES ──────────────────────────────────────────────────────

class TestCatalogo(unittest.TestCase):

    def test_hay_seis_subclases(self):
        self.assertEqual(len(SUBCLASES), 6)

    def test_dos_por_clase(self):
        for clase in ("guerrero", "explorador", "mago"):
            self.assertEqual(len(subclases_de_clase(clase)), 2, clase)

    def test_campos_obligatorios(self):
        campos = ("nombre", "clase_req", "color", "descripcion", "stat_bonus", "habilidades")
        for sid, info in SUBCLASES.items():
            for campo in campos:
                self.assertIn(campo, info, f"{sid} falta {campo}")

    def test_dos_habilidades_por_subclase(self):
        for sid, info in SUBCLASES.items():
            self.assertEqual(len(info["habilidades"]), 2, sid)

    def test_habilidades_existen_en_arbol(self):
        for sid, info in SUBCLASES.items():
            for hid in info["habilidades"]:
                self.assertIn(hid, HABILIDADES, f"{sid}: {hid} no está en HABILIDADES")

    def test_nivel_min_subclase(self):
        self.assertEqual(NIVEL_MIN_SUBCLASE, 5)

    def test_guerrero_subclases(self):
        subs = subclases_de_clase("guerrero")
        self.assertIn("paladin", subs)
        self.assertIn("berserker", subs)

    def test_explorador_subclases(self):
        subs = subclases_de_clase("explorador")
        self.assertIn("asesino", subs)
        self.assertIn("cazador", subs)

    def test_mago_subclases(self):
        subs = subclases_de_clase("mago")
        self.assertIn("hechicero", subs)
        self.assertIn("nigromante", subs)


# ─── subclase_valida ─────────────────────────────────────────────────────────

class TestSubclaseValida(unittest.TestCase):

    def test_valida_existente(self):
        for sid in SUBCLASES:
            self.assertTrue(subclase_valida(sid), sid)

    def test_invalida_inexistente(self):
        self.assertFalse(subclase_valida("druida"))
        self.assertFalse(subclase_valida(""))


# ─── puede_elegir_subclase ───────────────────────────────────────────────────

class TestPuedeElegirSubclase(unittest.TestCase):

    def _ok(self, nivel=5, clase="guerrero", subclase_actual=None, subclase_id="paladin"):
        puede, _ = puede_elegir_subclase(nivel, clase, subclase_actual, subclase_id)
        return puede

    def test_caso_valido(self):
        self.assertTrue(self._ok())

    def test_sin_clase(self):
        puede, err = puede_elegir_subclase(5, None, None, "paladin")
        self.assertFalse(puede)
        self.assertIn("clase", err.lower())

    def test_nivel_insuficiente(self):
        puede, err = puede_elegir_subclase(4, "guerrero", None, "paladin")
        self.assertFalse(puede)
        self.assertIn("nivel", err.lower())

    def test_ya_tiene_subclase(self):
        puede, err = puede_elegir_subclase(5, "guerrero", "paladin", "berserker")
        self.assertFalse(puede)
        self.assertIn("Paladín", err)

    def test_subclase_inexistente(self):
        puede, err = puede_elegir_subclase(5, "guerrero", None, "druida")
        self.assertFalse(puede)

    def test_clase_incorrecta(self):
        # explorador intenta elegir paladin (requiere guerrero)
        puede, err = puede_elegir_subclase(5, "explorador", None, "paladin")
        self.assertFalse(puede)
        self.assertIn("Guerrero", err)

    def test_nivel_exacto(self):
        self.assertTrue(self._ok(nivel=5))

    def test_nivel_superior(self):
        self.assertTrue(self._ok(nivel=10))

    def test_cada_clase_sus_subclases(self):
        casos = [
            ("guerrero", "paladin"), ("guerrero", "berserker"),
            ("explorador", "asesino"), ("explorador", "cazador"),
            ("mago", "hechicero"), ("mago", "nigromante"),
        ]
        for clase, sub in casos:
            puede, _ = puede_elegir_subclase(5, clase, None, sub)
            self.assertTrue(puede, f"{clase} → {sub}")


# ─── aplicar_subclase ────────────────────────────────────────────────────────

class TestAplicarSubclase(unittest.TestCase):

    def test_paladin_bonuses(self):
        stats = {"defensa": 5, "hp_max": 100, "hp": 100}
        result = aplicar_subclase(stats, "paladin")
        self.assertEqual(result["defensa"], 7)
        self.assertEqual(result["hp_max"], 115)

    def test_berserker_bonuses(self):
        stats = {"fuerza": 10}
        result = aplicar_subclase(stats, "berserker")
        self.assertEqual(result["fuerza"], 14)

    def test_asesino_bonuses(self):
        stats = {"destreza": 10}
        result = aplicar_subclase(stats, "asesino")
        self.assertEqual(result["destreza"], 13)

    def test_cazador_bonuses(self):
        stats = {"destreza": 10, "constitucion": 10}
        result = aplicar_subclase(stats, "cazador")
        self.assertEqual(result["destreza"], 12)
        self.assertEqual(result["constitucion"], 12)

    def test_hechicero_bonuses(self):
        stats = {"inteligencia": 10}
        result = aplicar_subclase(stats, "hechicero")
        self.assertEqual(result["inteligencia"], 13)

    def test_nigromante_bonuses(self):
        stats = {"inteligencia": 10, "constitucion": 10}
        result = aplicar_subclase(stats, "nigromante")
        self.assertEqual(result["inteligencia"], 12)
        self.assertEqual(result["constitucion"], 12)

    def test_no_modifica_original(self):
        stats = {"fuerza": 10}
        aplicar_subclase(stats, "berserker")
        self.assertEqual(stats["fuerza"], 10)

    def test_subclase_invalida_devuelve_mismo(self):
        stats = {"fuerza": 10}
        result = aplicar_subclase(stats, "druida")
        self.assertEqual(result, stats)


# ─── Habilidades de subclase en HABILIDADES ──────────────────────────────────

class TestHabilidadesSubclase(unittest.TestCase):

    HABS_SUBCLASE = [
        "escudo_divino", "golpe_sagrado",
        "furia_berserker", "golpe_demoledor",
        "golpe_certero", "golpe_letal",
        "instinto_cazador", "trampa_mortal",
        "concentracion_arcana", "nova_arcana",
        "escudo_sombrio", "drenar_esencia",
    ]

    def test_doce_habilidades_nuevas(self):
        for hid in self.HABS_SUBCLASE:
            self.assertIn(hid, HABILIDADES, hid)

    def test_rama_es_subclase(self):
        for hid in self.HABS_SUBCLASE:
            rama = HABILIDADES[hid]["rama"]
            self.assertIn(rama, SUBCLASES, f"{hid} tiene rama desconocida: {rama}")

    def test_pasivas_tienen_efecto(self):
        pasivas = [
            "escudo_divino", "furia_berserker", "golpe_certero",
            "instinto_cazador", "concentracion_arcana", "escudo_sombrio",
        ]
        for hid in pasivas:
            self.assertIn("efecto_pasivo", HABILIDADES[hid], hid)

    def test_activas_no_tienen_efecto_pasivo(self):
        activas = [
            "golpe_sagrado", "golpe_demoledor", "golpe_letal",
            "trampa_mortal", "nova_arcana", "drenar_esencia",
        ]
        for hid in activas:
            self.assertNotIn("efecto_pasivo", HABILIDADES[hid], hid)

    def test_nivel_req_subclase_pasiva(self):
        pasivas = [
            "escudo_divino", "furia_berserker", "golpe_certero",
            "instinto_cazador", "concentracion_arcana", "escudo_sombrio",
        ]
        for hid in pasivas:
            self.assertEqual(HABILIDADES[hid]["nivel_req"], 5, hid)

    def test_nivel_req_subclase_activa(self):
        activas = [
            "golpe_sagrado", "golpe_demoledor", "golpe_letal",
            "trampa_mortal", "nova_arcana", "drenar_esencia",
        ]
        for hid in activas:
            self.assertEqual(HABILIDADES[hid]["nivel_req"], 7, hid)

    def test_coste_dos_puntos(self):
        for hid in self.HABS_SUBCLASE:
            self.assertEqual(HABILIDADES[hid]["coste"], 2, hid)

    def test_ramas_principales_no_contaminadas(self):
        for hid, info in HABILIDADES.items():
            if info["rama"] in RAMAS:
                self.assertNotIn(hid, self.HABS_SUBCLASE)


# ─── Restricciones en puede_aprender ────────────────────────────────────────

class TestRestriccionSubclase(unittest.TestCase):

    def _desbloqueadas_base(self):
        return {"golpe_fuerte", "golpe_rapido"}

    def test_sin_subclase_no_puede_aprender_escudo_divino(self):
        puede, err = puede_aprender(
            "escudo_divino", self._desbloqueadas_base(), 5,
            clase="guerrero", subclase=None
        )
        self.assertFalse(puede)
        self.assertIn("Paladín", err)

    def test_subclase_incorrecta_bloqueada(self):
        puede, err = puede_aprender(
            "escudo_divino", self._desbloqueadas_base(), 5,
            clase="guerrero", subclase="berserker"
        )
        self.assertFalse(puede)
        self.assertIn("Paladín", err)

    def test_subclase_correcta_puede_aprender(self):
        puede, err = puede_aprender(
            "escudo_divino", self._desbloqueadas_base(), 5,
            clase="guerrero", subclase="paladin"
        )
        self.assertTrue(puede, err)

    def test_nivel_insuficiente_bloquea(self):
        puede, err = puede_aprender(
            "escudo_divino", self._desbloqueadas_base(), 4,
            clase="guerrero", subclase="paladin"
        )
        self.assertFalse(puede)
        self.assertIn("nivel", err.lower())

    def test_activa_requiere_pasiva(self):
        desbloqueadas = self._desbloqueadas_base()
        puede, err = puede_aprender(
            "golpe_sagrado", desbloqueadas, 7,
            clase="guerrero", subclase="paladin"
        )
        self.assertFalse(puede)
        self.assertIn("Escudo Divino", err)

    def test_activa_con_pasiva_aprendida(self):
        desbloqueadas = self._desbloqueadas_base() | {"escudo_divino"}
        puede, err = puede_aprender(
            "golpe_sagrado", desbloqueadas, 8,
            clase="guerrero", subclase="paladin"
        )
        # Puede si tiene puntos (nivel 8 = 7 pts, gastados: 0 iniciales + 2 escudo_divino = 2, disponibles: 5)
        self.assertTrue(puede, err)

    def test_aprender_devuelve_set_actualizado(self):
        desbloqueadas = self._desbloqueadas_base()
        exito, nuevas, err = aprender(
            "escudo_divino", desbloqueadas, 5,
            clase="guerrero", subclase="paladin"
        )
        self.assertTrue(exito)
        self.assertIn("escudo_divino", nuevas)

    def test_habilidades_de_clase_normal_no_bloqueadas_por_subclase(self):
        # Un paladín sigue pudiendo aprender embestida
        desbloqueadas = {"golpe_fuerte", "golpe_rapido"}
        puede, err = puede_aprender(
            "embestida", desbloqueadas, 2,
            clase="guerrero", subclase="paladin"
        )
        self.assertTrue(puede, err)


# ─── Motor de combate: nuevas habilidades ────────────────────────────────────

class TestCombateSubclase(unittest.TestCase):

    def _stats(self, fuerza=10, inteligencia=10, nivel=1):
        return {"fuerza": fuerza, "inteligencia": inteligencia,
                "nivel": nivel, "hp": 100, "hp_max": 100}

    def test_golpe_sagrado_x2(self):
        d = _aplicar_habilidad(10, "golpe_sagrado", self._stats())
        self.assertEqual(d, 20)

    def test_golpe_demoledor_x35(self):
        d = _aplicar_habilidad(10, "golpe_demoledor", self._stats())
        self.assertEqual(d, 35)

    def test_golpe_letal_x25(self):
        d = _aplicar_habilidad(10, "golpe_letal", self._stats())
        self.assertEqual(d, 25)

    def test_trampa_mortal_añade_dado(self):
        for _ in range(20):
            d = _aplicar_habilidad(10, "trampa_mortal", self._stats())
            self.assertGreaterEqual(d, 11)
            self.assertLessEqual(d, 14)

    def test_nova_arcana_usa_inteligencia(self):
        stats_int_alta = self._stats(inteligencia=20)
        d_alto = _aplicar_habilidad(10, "nova_arcana", stats_int_alta)
        stats_int_baja = self._stats(inteligencia=10)
        d_bajo = _aplicar_habilidad(10, "nova_arcana", stats_int_baja)
        self.assertGreater(d_alto, d_bajo)

    def test_drenar_esencia_x2(self):
        d = _aplicar_habilidad(10, "drenar_esencia", self._stats())
        self.assertEqual(d, 20)

    def test_efecto_postcombat_golpe_sagrado(self):
        self.assertEqual(efecto_postcombat("golpe_sagrado"), "golpe_sagrado")

    def test_efecto_postcombat_drenar_esencia(self):
        self.assertEqual(efecto_postcombat("drenar_esencia"), "drenar_esencia")

    def test_efecto_postcombat_drenar_vida_intacto(self):
        self.assertEqual(efecto_postcombat("drenar_vida"), "drenar_vida")

    def test_trampa_mortal_aplica_veneno(self):
        self.assertEqual(estado_de_habilidad("trampa_mortal"), "veneno")

    def test_golpe_letal_aplica_sangrado(self):
        self.assertEqual(estado_de_habilidad("golpe_letal"), "sangrado")


# ─── Economía de puntos ──────────────────────────────────────────────────────

class TestEconomiaPuntos(unittest.TestCase):

    def test_subclase_pasiva_cuesta_2(self):
        from systems.skills.engine import puntos_gastados
        base = {"golpe_fuerte", "golpe_rapido"}
        con_sub = base | {"escudo_divino"}
        self.assertEqual(puntos_gastados(con_sub) - puntos_gastados(base), 2)

    def test_subclase_activa_cuesta_2(self):
        from systems.skills.engine import puntos_gastados
        base = {"golpe_fuerte", "golpe_rapido", "escudo_divino"}
        con_activa = base | {"golpe_sagrado"}
        self.assertEqual(puntos_gastados(con_activa) - puntos_gastados(base), 2)

    def test_build_minima_subclase_nivel6(self):
        # Mínimo para aprender la pasiva de subclase: nivel 5 + 2pt disponibles
        desbloqueadas = {"golpe_fuerte", "golpe_rapido"}
        gastados = puntos_gastados(desbloqueadas)
        disponibles = puntos_disponibles(5, gastados)
        self.assertGreaterEqual(disponibles, 2)


if __name__ == "__main__":
    unittest.main()
