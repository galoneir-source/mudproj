"""
tests/test_logros_system.py

Tests unitarios puros para systems/achievements/achievements.py (v0.17.0).
Sin dependencias de Evennia.

Ejecutar con:
  python -m pytest tests/test_logros_system.py
"""
import unittest

from systems.achievements.achievements import (
    LOGROS,
    JEFES,
    _INICIALES,
    _RAMAS,
    _HABS_SUBCLASE,
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
        "clase":             "",
        "subclase":          "",
        "mascota_nivel_max": 1,
        "gremios_fundados":          0,
        "es_lider_gremio":           False,
        "miembros_gremio":           0,
        "gremio_banco_depositado":   0,
    }
    base.update(kwargs)
    return base


# ─── Catálogo ────────────────────────────────────────────────────────────────

class TestCatalogo(unittest.TestCase):

    def test_hay_81_logros(self):
        self.assertEqual(len(LOGROS), 81)

    def test_todos_tienen_campos_obligatorios(self):
        for lid, logro in LOGROS.items():
            for campo in ("nombre", "descripcion", "titulo", "categoria"):
                self.assertIn(campo, logro, f"{lid} falta '{campo}'")

    def test_categorias_conocidas(self):
        cats_validas = {
            "progresion", "misiones", "combate", "habilidades",
            "encantamiento", "reputacion", "crafteo", "economia",
            "gremio", "mascotas", "subclase", "clase", "jefe_mundo", "mazmorra",
            "arena", "runas", "vivienda", "bestiario", "cartografia", "monturas",
            "coleccion", "apuestas", "cazarrecompensas", "expediciones",
            "alquimia", "desafios",
        }
        for lid, logro in LOGROS.items():
            self.assertIn(logro["categoria"], cats_validas, lid)

    def test_siete_jefes_definidos(self):
        self.assertEqual(len(JEFES), 7)


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

    def test_personaje_paladin_completo_obtiene_31_logros(self):
        # Máximo posible: 20 base + 2 clase + 2 subclase + 2 mascotas + 5 gremio = 31
        datos_maximos = _datos(
            nivel=10,
            quests_entregadas=10,
            habilidades=list(
                _RAMAS["guerrero"] | _RAMAS["mago"] | _HABS_SUBCLASE["paladin"]
            ),
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
            clase="guerrero",
            subclase="paladin",
            mascota_nivel_max=3,
            gremios_fundados=1,
            es_lider_gremio=True,
            miembros_gremio=20,
            gremio_banco_depositado=2000,
        )
        resultado = verificar_todos(datos_maximos)
        self.assertEqual(len(resultado), 31)
        self.assertIn("vocacion_elegida", resultado)
        self.assertIn("maestro_guerrero", resultado)
        self.assertIn("especializacion_elegida", resultado)
        self.assertIn("maestro_paladin", resultado)
        self.assertIn("mascota_nivel_2", resultado)
        self.assertIn("mascota_nivel_3", resultado)
        self.assertIn("gremio_fundado", resultado)
        self.assertIn("gremio_pleno", resultado)
        self.assertIn("gremio_mecenas", resultado)
        self.assertNotIn("maestro_explorador", resultado)
        self.assertNotIn("maestro_berserker", resultado)


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


# ─── Clase ───────────────────────────────────────────────────────────────────

class TestLogrosClase(unittest.TestCase):

    def test_vocacion_elegida_sin_clase(self):
        self.assertFalse(_cumple("vocacion_elegida", _datos(clase="")))

    def test_vocacion_elegida_cumple(self):
        self.assertTrue(_cumple("vocacion_elegida", _datos(clase="guerrero")))

    def test_vocacion_elegida_cualquier_clase(self):
        for c in ("guerrero", "explorador", "mago"):
            self.assertTrue(_cumple("vocacion_elegida", _datos(clase=c)), c)

    def test_maestro_guerrero_sin_clase(self):
        self.assertFalse(_cumple("maestro_guerrero", _datos(
            habilidades=list(_RAMAS["guerrero"]), clase=""
        )))

    def test_maestro_guerrero_clase_incorrecta(self):
        self.assertFalse(_cumple("maestro_guerrero", _datos(
            habilidades=list(_RAMAS["guerrero"]), clase="explorador"
        )))

    def test_maestro_guerrero_sin_habilidades_completas(self):
        habs = list(_RAMAS["guerrero"])[:3]  # faltan una
        self.assertFalse(_cumple("maestro_guerrero", _datos(habilidades=habs, clase="guerrero")))

    def test_maestro_guerrero_cumple(self):
        self.assertTrue(_cumple("maestro_guerrero", _datos(
            habilidades=list(_RAMAS["guerrero"]), clase="guerrero"
        )))

    def test_maestro_explorador_sin_clase(self):
        self.assertFalse(_cumple("maestro_explorador", _datos(
            habilidades=list(_RAMAS["explorador"]), clase=""
        )))

    def test_maestro_explorador_clase_incorrecta(self):
        self.assertFalse(_cumple("maestro_explorador", _datos(
            habilidades=list(_RAMAS["explorador"]), clase="mago"
        )))

    def test_maestro_explorador_cumple(self):
        self.assertTrue(_cumple("maestro_explorador", _datos(
            habilidades=list(_RAMAS["explorador"]), clase="explorador"
        )))

    def test_maestro_mago_sin_clase(self):
        self.assertFalse(_cumple("maestro_mago", _datos(
            habilidades=list(_RAMAS["mago"]), clase=""
        )))

    def test_maestro_mago_clase_incorrecta(self):
        self.assertFalse(_cumple("maestro_mago", _datos(
            habilidades=list(_RAMAS["mago"]), clase="guerrero"
        )))

    def test_maestro_mago_cumple(self):
        self.assertTrue(_cumple("maestro_mago", _datos(
            habilidades=list(_RAMAS["mago"]), clase="mago"
        )))

    def test_solo_una_maestria_posible_a_la_vez(self):
        # Un guerrero con todas las habilidades de mago no obtiene maestro_mago
        habs = list(_RAMAS["guerrero"] | _RAMAS["mago"])
        datos = _datos(habilidades=habs, clase="guerrero")
        resultado = verificar_todos(datos)
        self.assertIn("maestro_guerrero", resultado)
        self.assertNotIn("maestro_mago", resultado)
        self.assertNotIn("maestro_explorador", resultado)

    def test_titulos_clase_disponibles(self):
        for lid, titulo_esperado in [
            ("maestro_guerrero",   "el Caballero"),
            ("maestro_explorador", "la Sombra"),
            ("maestro_mago",       "el Archimago"),
        ]:
            tits = titulos_disponibles([lid])
            self.assertIn(titulo_esperado, tits, f"falta título en {lid}")

    def test_vocacion_elegida_sin_titulo(self):
        from systems.achievements.achievements import LOGROS
        self.assertIsNone(LOGROS["vocacion_elegida"]["titulo"])


# ─── Subclase ────────────────────────────────────────────────────────────────

class TestLogrosSubclase(unittest.TestCase):

    # ── especializacion_elegida ───────────────────────────────────────────────

    def test_especializacion_elegida_sin_subclase(self):
        self.assertFalse(_cumple("especializacion_elegida", _datos(subclase="")))

    def test_especializacion_elegida_cumple(self):
        self.assertTrue(_cumple("especializacion_elegida", _datos(subclase="paladin")))

    def test_especializacion_elegida_cualquier_subclase(self):
        for s in ("paladin", "berserker", "asesino", "cazador", "hechicero", "nigromante"):
            self.assertTrue(_cumple("especializacion_elegida", _datos(subclase=s)), s)

    def test_especializacion_elegida_sin_titulo(self):
        from systems.achievements.achievements import LOGROS
        self.assertIsNone(LOGROS["especializacion_elegida"]["titulo"])

    # ── maestro_paladin ───────────────────────────────────────────────────────

    def test_maestro_paladin_sin_subclase(self):
        self.assertFalse(_cumple("maestro_paladin", _datos(
            habilidades=list(_HABS_SUBCLASE["paladin"]), subclase=""
        )))

    def test_maestro_paladin_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_paladin", _datos(
            habilidades=list(_HABS_SUBCLASE["paladin"]), subclase="berserker"
        )))

    def test_maestro_paladin_sin_habilidades_completas(self):
        habs = ["escudo_divino"]  # falta golpe_sagrado
        self.assertFalse(_cumple("maestro_paladin", _datos(
            habilidades=habs, subclase="paladin"
        )))

    def test_maestro_paladin_cumple(self):
        self.assertTrue(_cumple("maestro_paladin", _datos(
            habilidades=list(_HABS_SUBCLASE["paladin"]), subclase="paladin"
        )))

    # ── maestro_berserker ─────────────────────────────────────────────────────

    def test_maestro_berserker_sin_subclase(self):
        self.assertFalse(_cumple("maestro_berserker", _datos(
            habilidades=list(_HABS_SUBCLASE["berserker"]), subclase=""
        )))

    def test_maestro_berserker_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_berserker", _datos(
            habilidades=list(_HABS_SUBCLASE["berserker"]), subclase="paladin"
        )))

    def test_maestro_berserker_cumple(self):
        self.assertTrue(_cumple("maestro_berserker", _datos(
            habilidades=list(_HABS_SUBCLASE["berserker"]), subclase="berserker"
        )))

    # ── maestro_asesino ───────────────────────────────────────────────────────

    def test_maestro_asesino_sin_subclase(self):
        self.assertFalse(_cumple("maestro_asesino", _datos(
            habilidades=list(_HABS_SUBCLASE["asesino"]), subclase=""
        )))

    def test_maestro_asesino_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_asesino", _datos(
            habilidades=list(_HABS_SUBCLASE["asesino"]), subclase="cazador"
        )))

    def test_maestro_asesino_cumple(self):
        self.assertTrue(_cumple("maestro_asesino", _datos(
            habilidades=list(_HABS_SUBCLASE["asesino"]), subclase="asesino"
        )))

    # ── maestro_cazador ───────────────────────────────────────────────────────

    def test_maestro_cazador_sin_subclase(self):
        self.assertFalse(_cumple("maestro_cazador", _datos(
            habilidades=list(_HABS_SUBCLASE["cazador"]), subclase=""
        )))

    def test_maestro_cazador_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_cazador", _datos(
            habilidades=list(_HABS_SUBCLASE["cazador"]), subclase="asesino"
        )))

    def test_maestro_cazador_cumple(self):
        self.assertTrue(_cumple("maestro_cazador", _datos(
            habilidades=list(_HABS_SUBCLASE["cazador"]), subclase="cazador"
        )))

    # ── maestro_hechicero ─────────────────────────────────────────────────────

    def test_maestro_hechicero_sin_subclase(self):
        self.assertFalse(_cumple("maestro_hechicero", _datos(
            habilidades=list(_HABS_SUBCLASE["hechicero"]), subclase=""
        )))

    def test_maestro_hechicero_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_hechicero", _datos(
            habilidades=list(_HABS_SUBCLASE["hechicero"]), subclase="nigromante"
        )))

    def test_maestro_hechicero_cumple(self):
        self.assertTrue(_cumple("maestro_hechicero", _datos(
            habilidades=list(_HABS_SUBCLASE["hechicero"]), subclase="hechicero"
        )))

    # ── maestro_nigromante ────────────────────────────────────────────────────

    def test_maestro_nigromante_sin_subclase(self):
        self.assertFalse(_cumple("maestro_nigromante", _datos(
            habilidades=list(_HABS_SUBCLASE["nigromante"]), subclase=""
        )))

    def test_maestro_nigromante_subclase_incorrecta(self):
        self.assertFalse(_cumple("maestro_nigromante", _datos(
            habilidades=list(_HABS_SUBCLASE["nigromante"]), subclase="hechicero"
        )))

    def test_maestro_nigromante_cumple(self):
        self.assertTrue(_cumple("maestro_nigromante", _datos(
            habilidades=list(_HABS_SUBCLASE["nigromante"]), subclase="nigromante"
        )))

    # ── exclusividad ─────────────────────────────────────────────────────────

    def test_solo_un_maestro_subclase_posible(self):
        # Un paladín con todas las habilidades de berserker no obtiene maestro_berserker
        habs = list(_HABS_SUBCLASE["paladin"] | _HABS_SUBCLASE["berserker"])
        datos = _datos(habilidades=habs, subclase="paladin")
        resultado = verificar_todos(datos)
        self.assertIn("maestro_paladin", resultado)
        self.assertNotIn("maestro_berserker", resultado)
        self.assertNotIn("maestro_asesino", resultado)

    # ── títulos ───────────────────────────────────────────────────────────────

    def test_titulos_subclase_disponibles(self):
        for lid, titulo_esperado in [
            ("maestro_paladin",    "el Paladín"),
            ("maestro_berserker",  "el Berserker"),
            ("maestro_asesino",    "la Sombra Oscura"),
            ("maestro_cazador",    "el Depredador"),
            ("maestro_hechicero",  "la Tormenta"),
            ("maestro_nigromante", "el Nigromante"),
        ]:
            tits = titulos_disponibles([lid])
            self.assertIn(titulo_esperado, tits, f"falta título en {lid}")


# ─── Mascotas ────────────────────────────────────────────────────────────────

class TestLogrosMascotas(unittest.TestCase):

    def test_mascota_nivel_2_no_cumple_con_nivel_1(self):
        self.assertFalse(_cumple("mascota_nivel_2", _datos(mascota_nivel_max=1)))

    def test_mascota_nivel_2_cumple(self):
        self.assertTrue(_cumple("mascota_nivel_2", _datos(mascota_nivel_max=2)))

    def test_mascota_nivel_2_cumple_con_nivel_3(self):
        self.assertTrue(_cumple("mascota_nivel_2", _datos(mascota_nivel_max=3)))

    def test_mascota_nivel_3_no_cumple_con_nivel_2(self):
        self.assertFalse(_cumple("mascota_nivel_3", _datos(mascota_nivel_max=2)))

    def test_mascota_nivel_3_cumple(self):
        self.assertTrue(_cumple("mascota_nivel_3", _datos(mascota_nivel_max=3)))

    def test_mascota_nivel_2_sin_titulo(self):
        self.assertIsNone(LOGROS["mascota_nivel_2"]["titulo"])

    def test_mascota_nivel_3_titulo_domador(self):
        tits = titulos_disponibles(["mascota_nivel_3"])
        self.assertIn("el Domador", tits)

    def test_mascota_nivel_max_0_no_cumple_ninguno(self):
        datos = _datos(mascota_nivel_max=0)
        self.assertFalse(_cumple("mascota_nivel_2", datos))
        self.assertFalse(_cumple("mascota_nivel_3", datos))


# ─── Gremio ──────────────────────────────────────────────────────────────────

class TestLogrosGremio(unittest.TestCase):

    # ── gremio_fundado ────────────────────────────────────────────────────────

    def test_gremio_fundado_sin_gremio(self):
        self.assertFalse(_cumple("gremio_fundado", _datos(gremios_fundados=0)))

    def test_gremio_fundado_cumple(self):
        self.assertTrue(_cumple("gremio_fundado", _datos(gremios_fundados=1)))

    def test_gremio_fundado_sin_titulo(self):
        self.assertIsNone(LOGROS["gremio_fundado"]["titulo"])

    # ── gremio_cinco_miembros ─────────────────────────────────────────────────

    def test_gremio_cinco_miembros_sin_ser_lider(self):
        self.assertFalse(_cumple("gremio_cinco_miembros", _datos(
            es_lider_gremio=False, miembros_gremio=10
        )))

    def test_gremio_cinco_miembros_con_pocos(self):
        self.assertFalse(_cumple("gremio_cinco_miembros", _datos(
            es_lider_gremio=True, miembros_gremio=4
        )))

    def test_gremio_cinco_miembros_cumple(self):
        self.assertTrue(_cumple("gremio_cinco_miembros", _datos(
            es_lider_gremio=True, miembros_gremio=5
        )))

    def test_gremio_cinco_miembros_cumple_con_mas(self):
        self.assertTrue(_cumple("gremio_cinco_miembros", _datos(
            es_lider_gremio=True, miembros_gremio=15
        )))

    # ── gremio_pleno ──────────────────────────────────────────────────────────

    def test_gremio_pleno_sin_ser_lider(self):
        self.assertFalse(_cumple("gremio_pleno", _datos(
            es_lider_gremio=False, miembros_gremio=20
        )))

    def test_gremio_pleno_no_cumple_con_19(self):
        self.assertFalse(_cumple("gremio_pleno", _datos(
            es_lider_gremio=True, miembros_gremio=19
        )))

    def test_gremio_pleno_cumple(self):
        self.assertTrue(_cumple("gremio_pleno", _datos(
            es_lider_gremio=True, miembros_gremio=20
        )))

    def test_gremio_pleno_titulo_comandante(self):
        tits = titulos_disponibles(["gremio_pleno"])
        self.assertIn("el Comandante", tits)

    # ── gremio_tesorero ───────────────────────────────────────────────────────

    def test_gremio_tesorero_no_cumple_con_499(self):
        self.assertFalse(_cumple("gremio_tesorero", _datos(gremio_banco_depositado=499)))

    def test_gremio_tesorero_cumple(self):
        self.assertTrue(_cumple("gremio_tesorero", _datos(gremio_banco_depositado=500)))

    def test_gremio_tesorero_sin_titulo(self):
        self.assertIsNone(LOGROS["gremio_tesorero"]["titulo"])

    # ── gremio_mecenas ────────────────────────────────────────────────────────

    def test_gremio_mecenas_no_cumple_con_1999(self):
        self.assertFalse(_cumple("gremio_mecenas", _datos(gremio_banco_depositado=1999)))

    def test_gremio_mecenas_cumple(self):
        self.assertTrue(_cumple("gremio_mecenas", _datos(gremio_banco_depositado=2000)))

    def test_gremio_mecenas_titulo_mecenas(self):
        tits = titulos_disponibles(["gremio_mecenas"])
        self.assertIn("el Mecenas", tits)

    # ── tesorero implica mecenas no cumplido ──────────────────────────────────

    def test_tesorero_no_implica_mecenas(self):
        datos = _datos(gremio_banco_depositado=500)
        self.assertTrue(_cumple("gremio_tesorero", datos))
        self.assertFalse(_cumple("gremio_mecenas", datos))


# ─── Jefes de Mundo ──────────────────────────────────────────────────────────

class TestLogrosJefeMundo(unittest.TestCase):

    def test_titan_no_derrotado(self):
        self.assertFalse(_cumple("titan_derrotado", _datos(jefes_mundo_derrotados={})))

    def test_titan_derrotado_cumple(self):
        self.assertTrue(_cumple("titan_derrotado", _datos(
            jefes_mundo_derrotados={"TITAN_PANTANO": 1}
        )))

    def test_guardian_derrotado_cumple(self):
        self.assertTrue(_cumple("guardian_derrotado", _datos(
            jefes_mundo_derrotados={"GUARDIAN_FORJA": 1}
        )))

    def test_dragon_derrotado_cumple(self):
        self.assertTrue(_cumple("dragon_derrotado", _datos(
            jefes_mundo_derrotados={"DRAGON_CENIZA": 1}
        )))

    def test_dragon_derrotado_titulo(self):
        tits = titulos_disponibles(["dragon_derrotado"])
        self.assertIn("Cazadragones", tits)

    def test_todos_jefes_mundo_no_cumple_parcial(self):
        self.assertFalse(_cumple("todos_jefes_mundo", _datos(
            jefes_mundo_derrotados={"TITAN_PANTANO": 1, "GUARDIAN_FORJA": 1}
        )))

    def test_todos_jefes_mundo_cumple(self):
        self.assertTrue(_cumple("todos_jefes_mundo", _datos(
            jefes_mundo_derrotados={
                "TITAN_PANTANO": 1, "GUARDIAN_FORJA": 1, "DRAGON_CENIZA": 1,
            }
        )))


# ─── Mazmorras ───────────────────────────────────────────────────────────────

class TestLogrosMazmorra(unittest.TestCase):

    def test_cripta_no_completada(self):
        self.assertFalse(_cumple("cripta_completada", _datos(mazmorras_completadas={})))

    def test_cripta_completada_cumple(self):
        self.assertTrue(_cumple("cripta_completada", _datos(
            mazmorras_completadas={"cripta_ceniza": 1}
        )))

    def test_forja_completada_cumple(self):
        self.assertTrue(_cumple("forja_completada", _datos(
            mazmorras_completadas={"forja_maldita": 1}
        )))

    def test_abismo_completado_cumple(self):
        self.assertTrue(_cumple("abismo_completado", _datos(
            mazmorras_completadas={"abismo_sin_fondo": 1}
        )))

    def test_abismo_completado_titulo(self):
        tits = titulos_disponibles(["abismo_completado"])
        self.assertIn("el Conquistador", tits)

    def test_todas_mazmorras_no_cumple_parcial(self):
        self.assertFalse(_cumple("todas_mazmorras", _datos(
            mazmorras_completadas={"cripta_ceniza": 1, "forja_maldita": 1}
        )))

    def test_todas_mazmorras_cumple(self):
        self.assertTrue(_cumple("todas_mazmorras", _datos(
            mazmorras_completadas={
                "cripta_ceniza": 1, "forja_maldita": 1, "abismo_sin_fondo": 1,
            }
        )))

    def test_mazmorra_legendario_no_cumple(self):
        self.assertFalse(_cumple("mazmorra_legendario", _datos(mazmorra_legendario=False)))

    def test_mazmorra_legendario_cumple(self):
        self.assertTrue(_cumple("mazmorra_legendario", _datos(mazmorra_legendario=True)))


# ─── Arena ───────────────────────────────────────────────────────────────────

class TestLogrosArena(unittest.TestCase):

    def test_campeon_arena_no_cumple(self):
        self.assertFalse(_cumple("campeon_arena", _datos(torneos_ganados=0)))

    def test_campeon_arena_cumple(self):
        self.assertTrue(_cumple("campeon_arena", _datos(torneos_ganados=1)))

    def test_maestro_arena_no_cumple_con_dos(self):
        self.assertFalse(_cumple("maestro_arena", _datos(torneos_ganados=2)))

    def test_maestro_arena_cumple(self):
        self.assertTrue(_cumple("maestro_arena", _datos(torneos_ganados=3)))

    def test_maestro_arena_titulo(self):
        tits = titulos_disponibles(["maestro_arena"])
        self.assertIn("el Imbatible", tits)


# ─── Runas ───────────────────────────────────────────────────────────────────

class TestLogrosRunas(unittest.TestCase):

    def test_primera_runa_sin_runas(self):
        self.assertFalse(_cumple("primera_runa", _datos(
            runas_equipadas={"arma": None, "armadura": None, "accesorio": None}
        )))

    def test_primera_runa_cumple(self):
        self.assertTrue(_cumple("primera_runa", _datos(
            runas_equipadas={"arma": "RUNA_FILO", "armadura": None, "accesorio": None}
        )))

    def test_runas_completas_no_cumple_con_dos(self):
        self.assertFalse(_cumple("runas_completas", _datos(
            runas_equipadas={"arma": "RUNA_FILO", "armadura": "RUNA_ESCUDO", "accesorio": None}
        )))

    def test_runas_completas_cumple(self):
        self.assertTrue(_cumple("runas_completas", _datos(
            runas_equipadas={
                "arma": "RUNA_FILO", "armadura": "RUNA_ESCUDO", "accesorio": "RUNA_PODER",
            }
        )))

    def test_runas_completas_titulo(self):
        tits = titulos_disponibles(["runas_completas"])
        self.assertIn("el Tallador", tits)

    def test_runa_arcana_no_cumple_sin_ella(self):
        self.assertFalse(_cumple("runa_arcana", _datos(
            runas_equipadas={"arma": "RUNA_FILO", "armadura": None, "accesorio": None}
        )))

    def test_runa_arcana_cumple(self):
        self.assertTrue(_cumple("runa_arcana", _datos(
            runas_equipadas={"arma": None, "armadura": None, "accesorio": "RUNA_ARCANA"}
        )))


# ─── Vivienda ────────────────────────────────────────────────────────────────

class TestLogrosVivienda(unittest.TestCase):

    def test_primera_vivienda_no_cumple(self):
        self.assertFalse(_cumple("primera_vivienda", _datos(vivienda_comprada=False)))

    def test_primera_vivienda_cumple(self):
        self.assertTrue(_cumple("primera_vivienda", _datos(vivienda_comprada=True)))

    def test_hogar_decorado_no_cumple(self):
        self.assertFalse(_cumple("hogar_decorado", _datos(vivienda_decorada=False)))

    def test_hogar_decorado_cumple(self):
        self.assertTrue(_cumple("hogar_decorado", _datos(vivienda_decorada=True)))

    def test_hogar_decorado_titulo(self):
        tits = titulos_disponibles(["hogar_decorado"])
        self.assertIn("el Anfitrión", tits)


# ─── Apuestas ────────────────────────────────────────────────────────────────

class TestLogrosApuestas(unittest.TestCase):

    def test_primera_apuesta_no_cumple(self):
        self.assertFalse(_cumple("primera_apuesta", _datos(apuestas_jugadas=0)))

    def test_primera_apuesta_cumple(self):
        self.assertTrue(_cumple("primera_apuesta", _datos(apuestas_jugadas=1)))

    def test_golpe_de_suerte_no_cumple_con_nueve(self):
        self.assertFalse(_cumple("golpe_de_suerte", _datos(apuestas_ganadas=9)))

    def test_golpe_de_suerte_cumple(self):
        self.assertTrue(_cumple("golpe_de_suerte", _datos(apuestas_ganadas=10)))

    def test_gran_tahur_no_cumple_con_499(self):
        self.assertFalse(_cumple("gran_tahur", _datos(mayor_ganancia=499)))

    def test_gran_tahur_cumple(self):
        self.assertTrue(_cumple("gran_tahur", _datos(mayor_ganancia=500)))

    def test_gran_tahur_titulo(self):
        tits = titulos_disponibles(["gran_tahur"])
        self.assertIn("el Tahúr", tits)


# ─── Coleccionables ──────────────────────────────────────────────────────────

class TestLogrosColeccion(unittest.TestCase):

    def test_primer_tesoro_no_cumple(self):
        self.assertFalse(_cumple("primer_tesoro", _datos(tesoros_encontrados=0)))

    def test_primer_tesoro_cumple(self):
        self.assertTrue(_cumple("primer_tesoro", _datos(tesoros_encontrados=1)))

    def test_cazatesoros_no_cumple_con_siete(self):
        self.assertFalse(_cumple("cazatesoros", _datos(tesoros_encontrados=7)))

    def test_cazatesoros_cumple(self):
        self.assertTrue(_cumple("cazatesoros", _datos(tesoros_encontrados=8)))

    def test_coleccionista_no_cumple(self):
        self.assertFalse(_cumple("coleccionista", _datos(coleccion_completa=False)))

    def test_coleccionista_cumple(self):
        self.assertTrue(_cumple("coleccionista", _datos(coleccion_completa=True)))

    def test_coleccionista_titulo(self):
        tits = titulos_disponibles(["coleccionista"])
        self.assertIn("el Coleccionista", tits)


# ─── Monturas ────────────────────────────────────────────────────────────────

class TestLogrosMonturas(unittest.TestCase):

    def test_primer_jinete_no_cumple(self):
        self.assertFalse(_cumple("primer_jinete", _datos(monturas_poseidas=0)))

    def test_primer_jinete_cumple(self):
        self.assertTrue(_cumple("primer_jinete", _datos(monturas_poseidas=1)))

    def test_ecuyer_no_cumple_con_dos(self):
        self.assertFalse(_cumple("ecuyer", _datos(monturas_poseidas=2)))

    def test_ecuyer_cumple(self):
        self.assertTrue(_cumple("ecuyer", _datos(monturas_poseidas=3)))

    def test_amo_grifo_no_cumple(self):
        self.assertFalse(_cumple("amo_grifo", _datos(tiene_grifo_real=False)))

    def test_amo_grifo_cumple(self):
        self.assertTrue(_cumple("amo_grifo", _datos(tiene_grifo_real=True)))

    def test_amo_grifo_titulo(self):
        tits = titulos_disponibles(["amo_grifo"])
        self.assertIn("el Jinete", tits)


# ─── Alquimia ────────────────────────────────────────────────────────────────

class TestLogrosAlquimia(unittest.TestCase):

    def test_primer_elixir_no_cumple(self):
        self.assertFalse(_cumple("primer_elixir", _datos(pociones_elaboradas=0)))

    def test_primer_elixir_cumple(self):
        self.assertTrue(_cumple("primer_elixir", _datos(pociones_elaboradas=1)))

    def test_artesano_alquimia_no_cumple_con_cuatro(self):
        self.assertFalse(_cumple("artesano_alquimia", _datos(pociones_elaboradas=4)))

    def test_artesano_alquimia_cumple(self):
        self.assertTrue(_cumple("artesano_alquimia", _datos(pociones_elaboradas=5)))

    def test_maestro_alquimia_no_cumple_con_catorce(self):
        self.assertFalse(_cumple("maestro_alquimia", _datos(pociones_elaboradas=14)))

    def test_maestro_alquimia_cumple(self):
        self.assertTrue(_cumple("maestro_alquimia", _datos(pociones_elaboradas=15)))

    def test_maestro_alquimia_titulo(self):
        tits = titulos_disponibles(["maestro_alquimia"])
        self.assertIn("el Maestro Alquimista", tits)


# ─── Expediciones ────────────────────────────────────────────────────────────

class TestLogrosExpediciones(unittest.TestCase):

    def test_primera_expedicion_no_cumple(self):
        self.assertFalse(_cumple("primera_expedicion", _datos(expediciones_completadas=0)))

    def test_primera_expedicion_cumple(self):
        self.assertTrue(_cumple("primera_expedicion", _datos(expediciones_completadas=1)))

    def test_veterano_expedicion_no_cumple_con_cuatro(self):
        self.assertFalse(_cumple("veterano_expedicion", _datos(expediciones_completadas=4)))

    def test_veterano_expedicion_cumple(self):
        self.assertTrue(_cumple("veterano_expedicion", _datos(expediciones_completadas=5)))

    def test_conquistador_fortaleza_no_cumple(self):
        self.assertFalse(_cumple("conquistador_fortaleza", _datos(fortaleza_completada=False)))

    def test_conquistador_fortaleza_cumple(self):
        self.assertTrue(_cumple("conquistador_fortaleza", _datos(fortaleza_completada=True)))

    def test_conquistador_fortaleza_titulo(self):
        tits = titulos_disponibles(["conquistador_fortaleza"])
        self.assertIn("el Conquistador", tits)


# ─── Desafíos Diarios ────────────────────────────────────────────────────────

class TestLogrosDesafios(unittest.TestCase):

    def test_primer_desafio_no_cumple(self):
        self.assertFalse(_cumple("primer_desafio", _datos(total_desafios_completados=0)))

    def test_primer_desafio_cumple(self):
        self.assertTrue(_cumple("primer_desafio", _datos(total_desafios_completados=1)))

    def test_veterano_desafios_no_cumple_con_24(self):
        self.assertFalse(_cumple("veterano_desafios", _datos(total_desafios_completados=24)))

    def test_veterano_desafios_cumple(self):
        self.assertTrue(_cumple("veterano_desafios", _datos(total_desafios_completados=25)))

    def test_racha_legendaria_no_cumple_con_seis(self):
        self.assertFalse(_cumple("racha_legendaria", _datos(racha_desafios=6)))

    def test_racha_legendaria_cumple(self):
        self.assertTrue(_cumple("racha_legendaria", _datos(racha_desafios=7)))

    def test_racha_legendaria_titulo(self):
        tits = titulos_disponibles(["racha_legendaria"])
        self.assertIn("el Constante", tits)


# ─── Cazarrecompensas ────────────────────────────────────────────────────────

class TestLogrosCazarrecompensas(unittest.TestCase):

    def test_primer_cazador_no_cumple(self):
        self.assertFalse(_cumple("primer_cazador", _datos(recompensas_cobradas=0)))

    def test_primer_cazador_cumple(self):
        self.assertTrue(_cumple("primer_cazador", _datos(recompensas_cobradas=1)))

    def test_primer_cazador_titulo(self):
        tits = titulos_disponibles(["primer_cazador"])
        self.assertIn("el Cazador", tits)

    def test_generoso_verdugo_no_cumple_con_dos(self):
        self.assertFalse(_cumple("generoso_verdugo", _datos(recompensas_cobradas=2)))

    def test_generoso_verdugo_cumple(self):
        self.assertTrue(_cumple("generoso_verdugo", _datos(recompensas_cobradas=3)))

    def test_mas_buscado_no_cumple(self):
        self.assertFalse(_cumple("mas_buscado", _datos(recompensas_recibidas=0)))

    def test_mas_buscado_cumple(self):
        self.assertTrue(_cumple("mas_buscado", _datos(recompensas_recibidas=1)))

    def test_mas_buscado_titulo(self):
        tits = titulos_disponibles(["mas_buscado"])
        self.assertIn("el Más Buscado", tits)


# ─── Cartografía ─────────────────────────────────────────────────────────────

class TestLogrosCartografia(unittest.TestCase):

    def test_primer_viaje_no_cumple(self):
        self.assertFalse(_cumple("primer_viaje", _datos(salas_exploradas=0)))

    def test_primer_viaje_cumple(self):
        self.assertTrue(_cumple("primer_viaje", _datos(salas_exploradas=1)))

    def test_explorador_no_cumple_con_nueve(self):
        self.assertFalse(_cumple("explorador", _datos(salas_exploradas=9)))

    def test_explorador_cumple(self):
        self.assertTrue(_cumple("explorador", _datos(salas_exploradas=10)))

    def test_cartografo_no_cumple_con_28(self):
        self.assertFalse(_cumple("cartografo", _datos(salas_exploradas=28)))

    def test_cartografo_cumple(self):
        self.assertTrue(_cumple("cartografo", _datos(salas_exploradas=29)))

    def test_cartografo_titulo(self):
        tits = titulos_disponibles(["cartografo"])
        self.assertIn("el Cartógrafo", tits)


# ─── Bestiario ───────────────────────────────────────────────────────────────

class TestLogrosBestiario(unittest.TestCase):

    def test_primera_presa_no_cumple(self):
        self.assertFalse(_cumple("primera_presa", _datos(criaturas_registradas=0)))

    def test_primera_presa_cumple(self):
        self.assertTrue(_cumple("primera_presa", _datos(criaturas_registradas=1)))

    def test_cazador_experimentado_no_cumple_con_nueve(self):
        self.assertFalse(_cumple("cazador_experimentado", _datos(criaturas_registradas=9)))

    def test_cazador_experimentado_cumple(self):
        self.assertTrue(_cumple("cazador_experimentado", _datos(criaturas_registradas=10)))

    def test_enciclopedista_no_cumple(self):
        self.assertFalse(_cumple("enciclopedista", _datos(bestiary_completo=False)))

    def test_enciclopedista_cumple(self):
        self.assertTrue(_cumple("enciclopedista", _datos(bestiary_completo=True)))

    def test_enciclopedista_titulo(self):
        tits = titulos_disponibles(["enciclopedista"])
        self.assertIn("el Enciclopedista", tits)


if __name__ == "__main__":
    unittest.main()
