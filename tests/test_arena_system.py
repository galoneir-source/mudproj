"""
tests/test_arena_system.py

Tests puros del sistema de torneos de arena (sin dependencias de Evennia/Django).
"""
import pytest
from systems.arena.arena import (
    INSCRIPCION_FEE, MIN_JUGADORES, MAX_JUGADORES,
    _siguiente_potencia_de_2, _nombre_ronda,
    puede_inscribirse, generar_bracket,
    siguiente_combate, registrar_ganador, campeon,
    calcular_premio,
    formatear_inscripcion, formatear_bracket,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _bracket_2():
    return generar_bracket(["#1", "#2"])


def _bracket_4():
    return generar_bracket(["#1", "#2", "#3", "#4"])


# --------------------------------------------------------------------------- #
#  Constantes y helpers internos
# --------------------------------------------------------------------------- #

class TestConstantes:
    def test_fee_positivo(self):
        assert INSCRIPCION_FEE > 0

    def test_min_jugadores(self):
        assert MIN_JUGADORES == 2

    def test_max_jugadores(self):
        assert MAX_JUGADORES == 8

    def test_siguiente_potencia_de_2_exacta(self):
        assert _siguiente_potencia_de_2(4) == 4
        assert _siguiente_potencia_de_2(8) == 8

    def test_siguiente_potencia_de_2_redondea(self):
        assert _siguiente_potencia_de_2(3) == 4
        assert _siguiente_potencia_de_2(5) == 8
        assert _siguiente_potencia_de_2(7) == 8

    def test_siguiente_potencia_de_2_uno(self):
        assert _siguiente_potencia_de_2(1) == 1

    def test_nombre_ronda_final(self):
        assert "Final" in _nombre_ronda(1)

    def test_nombre_ronda_semi(self):
        assert "Semifinal" in _nombre_ronda(2)

    def test_nombre_ronda_cuartos(self):
        assert "Cuartos" in _nombre_ronda(4)

    def test_nombre_ronda_desconocida(self):
        assert "3" in _nombre_ronda(3)


# --------------------------------------------------------------------------- #
#  puede_inscribirse
# --------------------------------------------------------------------------- #

class TestPuedeInscribirse:
    def test_puede_inscribirse(self):
        ok, _ = puede_inscribirse([], "#1")
        assert ok

    def test_ya_inscrito(self):
        ok, msg = puede_inscribirse(["#1"], "#1")
        assert not ok
        assert "ya" in msg.lower()

    def test_maximo_alcanzado(self):
        inscritos = [f"#{i}" for i in range(MAX_JUGADORES)]
        ok, msg = puede_inscribirse(inscritos, "#99")
        assert not ok
        assert str(MAX_JUGADORES) in msg


# --------------------------------------------------------------------------- #
#  generar_bracket
# --------------------------------------------------------------------------- #

class TestGenerarBracket:
    def test_dos_jugadores(self):
        b = _bracket_2()
        assert b["ronda_actual"] == 0
        assert b["combate_actual"] == 0
        assert len(b["rondas"]) == 1
        assert len(b["rondas"][0]) == 1

    def test_cuatro_jugadores(self):
        b = _bracket_4()
        assert len(b["rondas"][0]) == 2

    def test_tres_jugadores_rellena_con_bye(self):
        b = generar_bracket(["#1", "#2", "#3"])
        ronda0 = b["rondas"][0]
        # 3 → potencia 4 → 2 matches
        assert len(ronda0) == 2
        # Uno de los matches debe tener un None (bye)
        nones = sum(1 for p1, p2 in ronda0 if p1 is None or p2 is None)
        assert nones >= 1

    def test_contiene_todos_los_jugadores(self):
        inscritos = ["#1", "#2", "#3", "#4"]
        b = generar_bracket(inscritos)
        participantes = set()
        for p1, p2 in b["rondas"][0]:
            if p1:
                participantes.add(p1)
            if p2:
                participantes.add(p2)
        assert set(inscritos).issubset(participantes)

    def test_no_tiene_campeon_al_inicio(self):
        b = _bracket_4()
        assert campeon(b) is None

    def test_bracket_aleatoreizado(self):
        resultados = set()
        inscritos = ["#1", "#2", "#3", "#4"]
        for _ in range(20):
            b = generar_bracket(inscritos)
            primera = b["rondas"][0][0]
            resultados.add(primera)
        # Con 20 intentos deberían salir distintos órdenes
        assert len(resultados) > 1


# --------------------------------------------------------------------------- #
#  siguiente_combate
# --------------------------------------------------------------------------- #

class TestSiguienteCombate:
    def test_primer_combate_existe(self):
        b = _bracket_4()
        c = siguiente_combate(b)
        assert c is not None
        assert len(c) == 2

    def test_no_combate_en_bracket_vacio(self):
        b = {"rondas": [], "ronda_actual": 0, "combate_actual": 0}
        assert siguiente_combate(b) is None

    def test_dos_jugadores_un_solo_combate(self):
        b = _bracket_2()
        c = siguiente_combate(b)
        assert c is not None
        # Solo hay un combate; los dos participantes no son None
        p1, p2 = c
        assert p1 is not None
        assert p2 is not None


# --------------------------------------------------------------------------- #
#  registrar_ganador y flujo completo
# --------------------------------------------------------------------------- #

class TestRegistrarGanador:
    def test_torneo_2_jugadores_un_resultado(self):
        b = generar_bracket(["#A", "#B"])
        p1, p2 = siguiente_combate(b)
        b = registrar_ganador(b, p1)
        assert campeon(b) == p1

    def test_torneo_4_jugadores_flujo_completo(self):
        inscritos = ["#1", "#2", "#3", "#4"]
        b = generar_bracket(inscritos)

        victorias = 0
        iteraciones = 0
        while campeon(b) is None and iteraciones < 20:
            c = siguiente_combate(b)
            if c is None:
                break
            p1, p2 = c
            # Siempre gana p1 (solo para test determinista)
            ganador = p1 if p1 is not None else p2
            b = registrar_ganador(b, ganador)
            victorias += 1
            iteraciones += 1

        assert campeon(b) is not None
        # 4 jugadores = 3 combates (semi + final)
        assert victorias == 3

    def test_torneo_3_jugadores_con_bye(self):
        inscritos = ["#A", "#B", "#C"]
        b = generar_bracket(inscritos)

        iteraciones = 0
        while campeon(b) is None and iteraciones < 10:
            c = siguiente_combate(b)
            if c is None:
                break
            p1, p2 = c
            if p2 is None:
                # Bye: el ganador es p1
                b = registrar_ganador(b, p1)
            else:
                b = registrar_ganador(b, p1)
            iteraciones += 1

        assert campeon(b) in inscritos

    def test_campeon_es_uno_de_los_inscritos(self):
        inscritos = ["#1", "#2", "#3", "#4"]
        b = generar_bracket(inscritos)
        while campeon(b) is None:
            c = siguiente_combate(b)
            if c is None:
                break
            p1, p2 = c
            gan = p1 if p1 else p2
            b = registrar_ganador(b, gan)
        assert campeon(b) in inscritos

    def test_nueva_ronda_generada_correctamente(self):
        b = generar_bracket(["#1", "#2", "#3", "#4"])
        # Completar primera ronda
        ronda0 = b["rondas"][0]
        for p1, p2 in ronda0:
            gan = p1 if p1 else p2
            b = registrar_ganador(b, gan)
            if campeon(b):
                break
        if not campeon(b):
            # Debe haber generado la siguiente ronda
            assert len(b["rondas"]) == 2


# --------------------------------------------------------------------------- #
#  calcular_premio
# --------------------------------------------------------------------------- #

class TestCalcularPremio:
    def test_premio_dos_jugadores(self):
        assert calcular_premio(2) == 2 * INSCRIPCION_FEE

    def test_premio_cuatro_jugadores(self):
        assert calcular_premio(4) == 4 * INSCRIPCION_FEE

    def test_premio_positivo(self):
        assert calcular_premio(MIN_JUGADORES) > 0


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_formatear_inscripcion_vacia(self):
        resultado = formatear_inscripcion([], {})
        assert "Nadie" in resultado or "inscrito" in resultado.lower()

    def test_formatear_inscripcion_con_jugadores(self):
        dbrefs = ["#1", "#2"]
        nombres = {"#1": "Arthas", "#2": "Lyria"}
        resultado = formatear_inscripcion(dbrefs, nombres)
        assert "Arthas" in resultado
        assert "Lyria" in resultado
        assert str(INSCRIPCION_FEE) in resultado

    def test_formatear_bracket_dos_jugadores(self):
        b = _bracket_2()
        nombres = {p: f"J{i}" for i, (p, _) in enumerate(b["rondas"][0])}
        resultado = formatear_bracket(b, nombres)
        assert "Final" in resultado or "Ronda" in resultado

    def test_formatear_bracket_muestra_campeon(self):
        b = generar_bracket(["#A", "#B"])
        p1, p2 = b["rondas"][0][0]
        b = registrar_ganador(b, p1)
        nombres = {"#A": "Alpha", "#B": "Beta"}
        resultado = formatear_bracket(b, nombres)
        assert "CAMPEÓN" in resultado or "campeón" in resultado.lower()
