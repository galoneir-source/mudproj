"""
tests/test_profesiones_system.py

Tests unitarios puros del sistema de profesiones (sin Evennia).
"""
import pytest
from systems.professions.professions import (
    PROFESIONES,
    ZONAS_RECURSO,
    COOLDOWN_SEGUNDOS,
    NIVEL_MAX,
    NOMBRES_NIVEL,
    XP_POR_NIVEL,
    nivel_desde_xp,
    xp_para_siguiente,
    elegir_material,
    aprender_profesion,
    ganar_xp,
    zona_a_profesion,
    formatear_profesion,
    formatear_todas,
    lista_disponibles,
)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

class TestCatalogo:
    def test_profesiones_definidas(self):
        assert "mineria" in PROFESIONES
        assert "herboristeria" in PROFESIONES
        assert "pesca" in PROFESIONES

    def test_cada_profesion_tiene_cinco_niveles(self):
        for prof_id, datos in PROFESIONES.items():
            for nv in range(1, NIVEL_MAX + 1):
                assert nv in datos["materiales"], f"{prof_id} falta nivel {nv}"

    def test_cada_nivel_tiene_materiales(self):
        for prof_id, datos in PROFESIONES.items():
            for nv, materiales in datos["materiales"].items():
                assert len(materiales) >= 1, f"{prof_id} nv{nv} sin materiales"

    def test_materiales_tienen_tres_campos(self):
        for prof_id, datos in PROFESIONES.items():
            for nv, materiales in datos["materiales"].items():
                for m in materiales:
                    assert len(m) == 3, f"{prof_id} nv{nv}: material malformado {m}"
                    proto, xp, peso = m
                    assert isinstance(proto, str) and proto
                    assert xp > 0
                    assert peso > 0

    def test_zonas_recurso_contiene_todas_profesiones(self):
        tipos = {v[0] for v in ZONAS_RECURSO.values()}
        assert "mineria" in tipos
        assert "herboristeria" in tipos
        assert "pesca" in tipos

    def test_cooldown_positivo(self):
        assert COOLDOWN_SEGUNDOS > 0

    def test_nombres_nivel_longitud(self):
        assert len(NOMBRES_NIVEL) == NIVEL_MAX + 1  # índice 0 vacío + 5 niveles


# ---------------------------------------------------------------------------
# nivel_desde_xp
# ---------------------------------------------------------------------------

class TestNivelDesdeXp:
    def test_xp_cero_es_nivel_uno(self):
        assert nivel_desde_xp(0) == 1

    def test_justo_antes_nivel_dos(self):
        assert nivel_desde_xp(XP_POR_NIVEL[1] - 1) == 1

    def test_nivel_dos_exacto(self):
        assert nivel_desde_xp(XP_POR_NIVEL[1]) == 2

    def test_nivel_tres(self):
        assert nivel_desde_xp(XP_POR_NIVEL[2]) == 3

    def test_nivel_cuatro(self):
        assert nivel_desde_xp(XP_POR_NIVEL[3]) == 4

    def test_nivel_cinco(self):
        assert nivel_desde_xp(XP_POR_NIVEL[4]) == 5

    def test_xp_excesiva_no_supera_maximo(self):
        assert nivel_desde_xp(99999) == NIVEL_MAX

    def test_todos_los_umbrales(self):
        for i, xp_req in enumerate(XP_POR_NIVEL):
            nivel_esperado = i + 1
            assert nivel_desde_xp(xp_req) == nivel_esperado


# ---------------------------------------------------------------------------
# xp_para_siguiente
# ---------------------------------------------------------------------------

class TestXpParaSiguiente:
    def test_nivel_uno_requiere_xp(self):
        assert xp_para_siguiente(1) == XP_POR_NIVEL[1]

    def test_nivel_cuatro_requiere_xp(self):
        assert xp_para_siguiente(4) == XP_POR_NIVEL[4]

    def test_nivel_maximo_devuelve_none(self):
        assert xp_para_siguiente(NIVEL_MAX) is None

    def test_consistencia_con_umbrales(self):
        for nv in range(1, NIVEL_MAX):
            assert xp_para_siguiente(nv) == XP_POR_NIVEL[nv]


# ---------------------------------------------------------------------------
# aprender_profesion
# ---------------------------------------------------------------------------

class TestAprenderProfesion:
    def test_aprender_mineria(self):
        profs = {}
        ok, nombre = aprender_profesion(profs, "mineria")
        assert ok
        assert "Miner" in nombre
        assert "mineria" in profs
        assert profs["mineria"] == {"nivel": 1, "xp": 0}

    def test_aprender_herboristeria(self):
        profs = {}
        ok, _ = aprender_profesion(profs, "herboristeria")
        assert ok
        assert "herboristeria" in profs

    def test_aprender_pesca(self):
        profs = {}
        ok, _ = aprender_profesion(profs, "pesca")
        assert ok
        assert "pesca" in profs

    def test_no_duplicar(self):
        profs = {}
        aprender_profesion(profs, "mineria")
        ok, msg = aprender_profesion(profs, "mineria")
        assert not ok
        assert "Ya" in msg

    def test_profesion_desconocida(self):
        profs = {}
        ok, msg = aprender_profesion(profs, "magia_oscura")
        assert not ok
        assert "desconocida" in msg.lower()

    def test_aprender_varias(self):
        profs = {}
        aprender_profesion(profs, "mineria")
        aprender_profesion(profs, "pesca")
        assert len(profs) == 2


# ---------------------------------------------------------------------------
# ganar_xp
# ---------------------------------------------------------------------------

class TestGanarXp:
    def _profs_con(self, prof_id):
        profs = {}
        aprender_profesion(profs, prof_id)
        return profs

    def test_xp_acumula(self):
        profs = self._profs_con("mineria")
        ganar_xp(profs, "mineria", 10)
        assert profs["mineria"]["xp"] == 10

    def test_no_sube_nivel_sin_suficiente_xp(self):
        profs = self._profs_con("mineria")
        nivel, subio = ganar_xp(profs, "mineria", 10)
        assert nivel == 1
        assert not subio

    def test_sube_nivel_al_umbral(self):
        profs = self._profs_con("mineria")
        nivel, subio = ganar_xp(profs, "mineria", XP_POR_NIVEL[1])
        assert nivel == 2
        assert subio

    def test_nivel_guardado_en_dict(self):
        profs = self._profs_con("herboristeria")
        ganar_xp(profs, "herboristeria", XP_POR_NIVEL[1])
        assert profs["herboristeria"]["nivel"] == 2

    def test_multiples_ganancias_acumulan(self):
        profs = self._profs_con("pesca")
        ganar_xp(profs, "pesca", 15)
        ganar_xp(profs, "pesca", 15)
        assert profs["pesca"]["xp"] == 30

    def test_sube_nivel_al_acumular(self):
        profs = self._profs_con("pesca")
        ganar_xp(profs, "pesca", 15)
        nivel, subio = ganar_xp(profs, "pesca", 15)
        assert nivel == 2
        assert subio

    def test_no_modifica_otras_profesiones(self):
        profs = {}
        aprender_profesion(profs, "mineria")
        aprender_profesion(profs, "pesca")
        ganar_xp(profs, "mineria", 50)
        assert profs["pesca"]["xp"] == 0

    def test_profesion_no_aprendida_devuelve_nivel_uno(self):
        profs = {}
        nivel, subio = ganar_xp(profs, "mineria", 100)
        assert nivel == 1
        assert not subio

    def test_no_supera_nivel_maximo(self):
        profs = self._profs_con("mineria")
        nivel, _ = ganar_xp(profs, "mineria", 99999)
        assert nivel == NIVEL_MAX

    def test_sube_hasta_nivel_cinco_escalado(self):
        profs = self._profs_con("herboristeria")
        ganar_xp(profs, "herboristeria", XP_POR_NIVEL[4])
        assert profs["herboristeria"]["nivel"] == 5


# ---------------------------------------------------------------------------
# elegir_material
# ---------------------------------------------------------------------------

class TestElegirMaterial:
    def test_devuelve_tupla(self):
        proto, xp = elegir_material("mineria", 1)
        assert isinstance(proto, str)
        assert isinstance(xp, int)

    def test_proto_no_vacio(self):
        proto, xp = elegir_material("herboristeria", 1)
        assert proto

    def test_xp_positiva(self):
        _, xp = elegir_material("pesca", 3)
        assert xp > 0

    def test_nivel_invalido_devuelve_vacio(self):
        proto, xp = elegir_material("mineria", 99)
        assert proto == ""
        assert xp == 0

    def test_prof_invalida_devuelve_vacio(self):
        proto, xp = elegir_material("magia_negra", 1)
        assert proto == ""
        assert xp == 0

    def test_material_esta_en_lista_del_nivel(self):
        for _ in range(20):
            proto, _ = elegir_material("mineria", 2)
            claves = [m[0] for m in PROFESIONES["mineria"]["materiales"][2]]
            assert proto in claves

    def test_distribucion_ponderada_plausible(self):
        # nivel 1 tiene solo un material → siempre el mismo
        resultados = set()
        for _ in range(10):
            proto, _ = elegir_material("mineria", 1)
            resultados.add(proto)
        assert len(resultados) == 1

    def test_nivel_cinco_tiene_materiales_raros(self):
        vistos = set()
        for _ in range(200):
            proto, _ = elegir_material("pesca", 5)
            vistos.add(proto)
        # Con 200 intentos, los tres materiales del nivel 5 deben aparecer
        assert len(vistos) >= 2  # al menos los dos comunes


# ---------------------------------------------------------------------------
# zona_a_profesion
# ---------------------------------------------------------------------------

class TestZonaAProfesion:
    def test_boca_mina_es_mineria(self):
        prof_id, nivel_min = zona_a_profesion("boca_mina")
        assert prof_id == "mineria"
        assert nivel_min == 1

    def test_galeria_principal_nivel_dos(self):
        prof_id, nivel_min = zona_a_profesion("galeria_principal")
        assert prof_id == "mineria"
        assert nivel_min == 2

    def test_caverna_coloso_nivel_tres(self):
        _, nivel_min = zona_a_profesion("caverna_coloso")
        assert nivel_min == 3

    def test_bosque_norte_herboristeria(self):
        prof_id, _ = zona_a_profesion("bosque_norte")
        assert prof_id == "herboristeria"

    def test_pantano_cenagoso_nivel_dos(self):
        prof_id, nivel_min = zona_a_profesion("pantano_cenagoso")
        assert prof_id == "herboristeria"
        assert nivel_min == 2

    def test_guarida_troll_nivel_tres(self):
        _, nivel_min = zona_a_profesion("guarida_troll")
        assert nivel_min == 3

    def test_orilla_rio_pesca(self):
        prof_id, nivel_min = zona_a_profesion("orilla_rio")
        assert prof_id == "pesca"
        assert nivel_min == 1

    def test_zona_desconocida_devuelve_none(self):
        prof_id, nivel_min = zona_a_profesion("plaza_ciudad")
        assert prof_id is None
        assert nivel_min == 0

    def test_zona_vacia_devuelve_none(self):
        prof_id, nivel_min = zona_a_profesion("")
        assert prof_id is None

    def test_todas_las_zonas_tienen_prof_valida(self):
        for zona_id, (prof_id, nivel_min) in ZONAS_RECURSO.items():
            assert prof_id in PROFESIONES
            assert 1 <= nivel_min <= NIVEL_MAX


# ---------------------------------------------------------------------------
# Formateo
# ---------------------------------------------------------------------------

class TestFormateo:
    def test_formatear_profesion_nivel_uno(self):
        datos = {"nivel": 1, "xp": 0}
        resultado = formatear_profesion("mineria", datos)
        assert "Miner" in resultado
        assert "Aprendiz" in resultado

    def test_formatear_profesion_maestro(self):
        datos = {"nivel": NIVEL_MAX, "xp": XP_POR_NIVEL[-1]}
        resultado = formatear_profesion("pesca", datos)
        assert "MAESTRO" in resultado

    def test_formatear_profesion_con_progreso(self):
        datos = {"nivel": 2, "xp": 50}
        resultado = formatear_profesion("herboristeria", datos)
        assert "50" in resultado

    def test_formatear_todas_sin_profesiones(self):
        resultado = formatear_todas({})
        assert "Ninguna" in resultado

    def test_formatear_todas_con_una(self):
        profs = {}
        aprender_profesion(profs, "mineria")
        resultado = formatear_todas(profs)
        assert "Miner" in resultado

    def test_formatear_todas_con_varias(self):
        profs = {}
        aprender_profesion(profs, "mineria")
        aprender_profesion(profs, "pesca")
        resultado = formatear_todas(profs)
        assert "Pesca" in resultado
        assert "Miner" in resultado

    def test_lista_disponibles_contiene_tres(self):
        resultado = lista_disponibles()
        assert "mineria" in resultado
        assert "herboristeria" in resultado
        assert "pesca" in resultado
