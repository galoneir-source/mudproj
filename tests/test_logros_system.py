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


if __name__ == "__main__":
    unittest.main()
