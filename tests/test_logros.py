"""
tests/test_logros.py

Tests unitarios puros para systems/achievements/achievements.py (v0.17.0).
Sin dependencias de Evennia.

Ejecutar con:
  python -m pytest tests/test_logros.py
"""
import unittest

from systems.achievements.achievements import (
    LOGROS,
    JEFES,
    _INICIALES,
    _RAMAS,
    _cumple,
    verificar_todos,
    nuevos_logros,
    titulos_disponibles,
)

TODOS_JEFES = list(JEFES)


def _datos(**kwargs) -> dict:
    base = {
        "nivel":             1,
        "quests_entregadas": 0,
        "habilidades":       ["golpe_fuerte", "golpe_rapido"],
        "reputacion":        {},
        "kills_totales":     0,
        "jefes_derrotados":  [],
        "objetos_crafteados":0,
        "encantamiento_max": 0,
        "banco_usado":       False,
    }
    base.update(kwargs)
    return base


# ─── Catálogo ────────────────────────────────────────────────────────────────

class TestCatalogo(unittest.TestCase):

    def test_hay_20_logros(self):
        self.assertEqual(len(LOGROS), 20)

    def test_todos_tienen_campos_obligatorios(self):
        for lid, logro in LOGROS.items():
            for campo in ("nombre", "descripcion", "titulo", "categoria"):
                self.assertIn(campo, logro, f"{lid} falta '{campo}'")

    def test_categorias_conocidas(self):
        cats_validas = {
            "progresion", "misiones", "combate", "habilidades",
            "encantamiento", "reputacion", "crafteo", "economia",
        }
        for lid, logro in LOGROS.items():
            self.assertIn(logro["categoria"], cats_validas, lid)

    def test_seis_jefes_definidos(self):
        self.assertEqual(len(JEFES), 6)


# ─── Progresión ──────────────────────────────────────────────────────────────

class TestProgresion(unittest.TestCase):

    def test_nivel_2_no_cumple_nivel_1(self):
        self.assertFalse(_cumple("nivel_2", _datos(nivel=1)))

    def test_nivel_2_cumple(self):
        self.assertTrue(_cumple("nivel_2", _datos(nivel=2)))

    def test_nivel_2_cumple_nivel_superior(self):
        self.assertTrue(_cumple("nivel_2", _datos(nivel=7)))

    def test_nivel_5_no_cumple(self):
        self.assertFalse(_cumple("nivel_5", _datos(nivel=4)))

    def test_nivel_5_cumple(self):
        self.assertTrue(_cumple("nivel_5", _datos(nivel=5)))

    def test_nivel_10_no_cumple(self):
        self.assertFalse(_cumple("nivel_10", _datos(nivel=9)))

    def test_nivel_10_cumple(self):
        self.assertTrue(_cumple("nivel_10", _datos(nivel=10)))


# ─── Misiones ────────────────────────────────────────────────────────────────

class TestMisiones(unittest.TestCase):

    def test_primera_mision_sin_entregas(self):
        self.assertFalse(_cumple("primera_mision", _datos()))

    def test_primera_mision_cumple(self):
        self.assertTrue(_cumple("primera_mision", _datos(quests_entregadas=1)))

    def test_cinco_misiones_no_cumple(self):
        self.assertFalse(_cumple("cinco_misiones", _datos(quests_entregadas=4)))

    def test_cinco_misiones_cumple(self):
        self.assertTrue(_cumple("cinco_misiones", _datos(quests_entregadas=5)))

    def test_diez_misiones_cumple(self):
        self.assertTrue(_cumple("diez_misiones", _datos(quests_entregadas=10)))

    def test_diez_misiones_no_cumple(self):
        self.assertFalse(_cumple("diez_misiones", _datos(quests_entregadas=9)))


# ─── Combate ─────────────────────────────────────────────────────────────────

class TestCombate(unittest.TestCase):

    def test_diez_kills_no_cumple(self):
        self.assertFalse(_cumple("diez_kills", _datos(kills_totales=9)))

    def test_diez_kills_cumple(self):
        self.assertTrue(_cumple("diez_kills", _datos(kills_totales=10)))

    def test_cincuenta_kills_no_cumple(self):
        self.assertFalse(_cumple("cincuenta_kills", _datos(kills_totales=49)))

    def test_cincuenta_kills_cumple(self):
        self.assertTrue(_cumple("cincuenta_kills", _datos(kills_totales=50)))

    def test_tres_jefes_no_cumple_con_dos(self):
        self.assertFalse(_cumple("tres_jefes", _datos(jefes_derrotados=TODOS_JEFES[:2])))

    def test_tres_jefes_cumple(self):
        self.assertTrue(_cumple("tres_jefes", _datos(jefes_derrotados=TODOS_JEFES[:3])))

    def test_tres_jefes_ignora_no_jefes(self):
        self.assertFalse(_cumple("tres_jefes", _datos(jefes_derrotados=["FALSO1", "FALSO2", "FALSO3"])))

    def test_todos_jefes_no_cumple_parcial(self):
        self.assertFalse(_cumple("todos_jefes", _datos(jefes_derrotados=TODOS_JEFES[:-1])))

    def test_todos_jefes_cumple(self):
        self.assertTrue(_cumple("todos_jefes", _datos(jefes_derrotados=TODOS_JEFES)))

    def test_todos_jefes_cumple_con_extra(self):
        self.assertTrue(_cumple("todos_jefes", _datos(jefes_derrotados=TODOS_JEFES + ["EXTRA"])))


# ─── Habilidades ─────────────────────────────────────────────────────────────

class TestHabilidades(unittest.TestCase):

    def test_primera_habilidad_solo_iniciales(self):
        self.assertFalse(_cumple("primera_habilidad", _datos()))

    def test_primera_habilidad_cumple(self):
        self.assertTrue(_cumple("primera_habilidad", _datos(
            habilidades=["golpe_fuerte", "golpe_rapido", "embestida"]
        )))

    def test_seis_habilidades_no_cumple(self):
        self.assertFalse(_cumple("seis_habilidades", _datos(
            habilidades=["golpe_fuerte", "golpe_rapido", "embestida", "corte", "veneno"]
        )))

    def test_seis_habilidades_cumple(self):
        self.assertTrue(_cumple("seis_habilidades", _datos(
            habilidades=["golpe_fuerte", "golpe_rapido", "embestida", "escudo_fe", "corte", "veneno"]
        )))

    def test_rama_completa_guerrero(self):
        self.assertTrue(_cumple("rama_completa", _datos(
            habilidades=list(_RAMAS["guerrero"])
        )))

    def test_rama_completa_mago(self):
        self.assertTrue(_cumple("rama_completa", _datos(
            habilidades=list(_RAMAS["mago"])
        )))

    def test_rama_completa_no_cumple_parcial(self):
        self.assertFalse(_cumple("rama_completa", _datos(
            habilidades=["golpe_fuerte", "embestida", "escudo_fe"]  # falta golpe_maestro
        )))


# ─── Encantamiento ────────────────────────────────────────────────────────────

class TestEncantamiento(unittest.TestCase):

    def test_primer_encantamiento_no_cumple(self):
        self.assertFalse(_cumple("primer_encantamiento", _datos(encantamiento_max=0)))

    def test_primer_encantamiento_cumple(self):
        self.assertTrue(_cumple("primer_encantamiento", _datos(encantamiento_max=1)))

    def test_encantamiento_max_no_cumple_nivel_2(self):
        self.assertFalse(_cumple("encantamiento_max", _datos(encantamiento_max=2)))

    def test_encantamiento_max_cumple(self):
        self.assertTrue(_cumple("encantamiento_max", _datos(encantamiento_max=3)))


# ─── Reputación ──────────────────────────────────────────────────────────────

class TestReputacion(unittest.TestCase):

    def test_honrado_ciudadanos_no_cumple_neutral(self):
        self.assertFalse(_cumple("honrado_ciudadanos", _datos(
            reputacion={"ciudadanos": 1500}
        )))

    def test_honrado_ciudadanos_cumple(self):
        self.assertTrue(_cumple("honrado_ciudadanos", _datos(
            reputacion={"ciudadanos": 3000}
        )))

    def test_honrado_ciudadanos_cumple_exaltado(self):
        self.assertTrue(_cumple("honrado_ciudadanos", _datos(
            reputacion={"ciudadanos": 15000}
        )))

    def test_diplomatico_no_cumple_dos_facciones(self):
        self.assertFalse(_cumple("diplomatico", _datos(
            reputacion={"ciudadanos": 1000, "gremio_aventureros": 2000}
        )))

    def test_diplomatico_cumple_tres_facciones(self):
        self.assertTrue(_cumple("diplomatico", _datos(
            reputacion={
                "ciudadanos": 1000,
                "gremio_aventureros": 2000,
                "sombras_pantano": 5000,
            }
        )))

    def test_diplomatico_no_cumple_con_facciones_enemigas(self):
        self.assertFalse(_cumple("diplomatico", _datos(
            reputacion={
                "ciudadanos": 1000,
                "gremio_aventureros": -500,  # neutral, no llega
                "horda_salvaje": 500,        # neutral, no llega
            }
        )))


# ─── Crafteo ─────────────────────────────────────────────────────────────────

class TestCrafteo(unittest.TestCase):

    def test_primer_crafteo_no_cumple(self):
        self.assertFalse(_cumple("primer_crafteo", _datos(objetos_crafteados=0)))

    def test_primer_crafteo_cumple(self):
        self.assertTrue(_cumple("primer_crafteo", _datos(objetos_crafteados=1)))

    def test_diez_crafteos_no_cumple(self):
        self.assertFalse(_cumple("diez_crafteos", _datos(objetos_crafteados=9)))

    def test_diez_crafteos_cumple(self):
        self.assertTrue(_cumple("diez_crafteos", _datos(objetos_crafteados=10)))


# ─── Economía ────────────────────────────────────────────────────────────────

class TestEconomia(unittest.TestCase):

    def test_primer_deposito_no_cumple(self):
        self.assertFalse(_cumple("primer_deposito", _datos(banco_usado=False)))

    def test_primer_deposito_cumple(self):
        self.assertTrue(_cumple("primer_deposito", _datos(banco_usado=True)))


# ─── verificar_todos ────────────────────────────────────────────────────────

class TestVerificarTodos(unittest.TestCase):

    def test_personaje_inicial_ningun_logro(self):
        resultado = verificar_todos(_datos())
        self.assertEqual(resultado, [])

    def test_personaje_nivel_2_obtiene_logros_nivel(self):
        resultado = verificar_todos(_datos(nivel=2))
        self.assertIn("nivel_2", resultado)
        self.assertNotIn("nivel_5", resultado)

    def test_personaje_completo_todos_los_logros(self):
        datos_maximos = _datos(
            nivel=10,
            quests_entregadas=10,
            habilidades=list(_RAMAS["guerrero"] | _RAMAS["mago"]),
            reputacion={
                "ciudadanos": 5000,
                "gremio_aventureros": 2000,
                "horda_salvaje": 2000,
            },
            kills_totales=50,
            jefes_derrotados=TODOS_JEFES,
            objetos_crafteados=10,
            encantamiento_max=3,
            banco_usado=True,
        )
        resultado = verificar_todos(datos_maximos)
        self.assertEqual(len(resultado), len(LOGROS))


# ─── nuevos_logros ───────────────────────────────────────────────────────────

class TestNuevosLogros(unittest.TestCase):

    def test_sin_cambio_no_hay_nuevos(self):
        datos = _datos(nivel=2)
        ya = ["nivel_2"]
        self.assertEqual(nuevos_logros(datos, ya), [])

    def test_detecta_nuevo_al_subir_nivel(self):
        datos = _datos(nivel=5)
        ya = ["nivel_2"]
        nuevos = nuevos_logros(datos, ya)
        self.assertIn("nivel_5", nuevos)
        self.assertNotIn("nivel_2", nuevos)

    def test_sin_previos_devuelve_todos_los_cumplidos(self):
        datos = _datos(nivel=2, quests_entregadas=1)
        nuevos = nuevos_logros(datos, [])
        self.assertIn("nivel_2", nuevos)
        self.assertIn("primera_mision", nuevos)


# ─── titulos_disponibles ────────────────────────────────────────────────────

class TestTitulosDisponibles(unittest.TestCase):

    def test_sin_logros_sin_titulos(self):
        self.assertEqual(titulos_disponibles([]), [])

    def test_logro_sin_titulo_no_aparece(self):
        # "primera_mision" no tiene título
        self.assertEqual(titulos_disponibles(["primera_mision"]), [])

    def test_logro_con_titulo_aparece(self):
        tits = titulos_disponibles(["nivel_2"])
        self.assertEqual(tits, ["el Novato"])

    def test_varios_logros_sin_duplicados(self):
        tits = titulos_disponibles(["nivel_2", "nivel_5"])
        self.assertEqual(tits, ["el Novato", "el Veterano"])

    def test_orden_preservado(self):
        tits = titulos_disponibles(["nivel_5", "nivel_2"])
        self.assertEqual(tits, ["el Veterano", "el Novato"])


if __name__ == "__main__":
    unittest.main()
