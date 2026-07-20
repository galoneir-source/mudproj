"""
systems/arena/arena.py

Lógica pura del sistema de torneos de arena. Sin dependencias de Evennia.

Torneos de eliminación directa (single elimination) con soporte para 2–8
jugadores. Los espacios sobrantes se rellenan con "byes" (avances automáticos)
hasta la siguiente potencia de 2.

Estado del bracket (dict serializable):
  rondas          list[list[tuple]]  — lista de rondas; cada ronda es lista de
                                       parejas (dbref1, dbref2); None = bye
  ronda_actual    int                — índice de la ronda en disputa
  combate_actual  int                — índice del combate dentro de la ronda
  ganadores_ronda list[str]          — ganadores acumulados de la ronda actual
  campeon         str | None         — dbref del campeón (None si en curso)
"""
from __future__ import annotations
import random

INSCRIPCION_FEE = 100   # monedas que cuesta inscribirse
MIN_JUGADORES   = 2
MAX_JUGADORES   = 8


# --------------------------------------------------------------------------- #
#  Helpers internos
# --------------------------------------------------------------------------- #

def _siguiente_potencia_de_2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def _nombre_ronda(total_combates: int) -> str:
    nombres = {1: "Final", 2: "Semifinales", 4: "Cuartos de final"}
    return nombres.get(total_combates, f"Ronda ({total_combates} combates)")


# --------------------------------------------------------------------------- #
#  API pública
# --------------------------------------------------------------------------- #

def puede_inscribirse(dbrefs_inscritos: list, dbref: str) -> tuple[bool, str]:
    if dbref in dbrefs_inscritos:
        return False, "Ya estás inscrito en el torneo."
    if len(dbrefs_inscritos) >= MAX_JUGADORES:
        return False, f"El torneo ya alcanzó el máximo de {MAX_JUGADORES} jugadores."
    return True, ""


def generar_bracket(inscritos: list) -> dict:
    """
    Genera el bracket inicial dado una lista de dbrefs de jugadores inscritos.
    Mezcla aleatoriamente y reparte un bye (None) por pareja como máximo,
    hasta la siguiente potencia de 2.

    Repartir los byes uno por pareja (en vez de agruparlos al final y
    emparejar en bloques de dos consecutivos) evita que dos byes caigan en
    la misma pareja: con 5 o 6 inscritos (3 y 2 byes respectivamente,
    ambos > 1), emparejar consecutivamente produce una pareja (None, None)
    — un combate "fantasma" sin ningún jugador real, que además le regala
    un bye extra e injusto al jugador que le toque enfrentarse a ese hueco
    en la siguiente ronda (avanza sin jugar un combate real).
    """
    j = list(inscritos)
    random.shuffle(j)
    p2 = _siguiente_potencia_de_2(len(j))
    byes = p2 - len(j)

    primera_ronda = [(j[i], None) for i in range(byes)]
    resto = j[byes:]
    primera_ronda += [(resto[i], resto[i + 1]) for i in range(0, len(resto), 2)]

    return {
        "rondas":           [primera_ronda],
        "ronda_actual":     0,
        "combate_actual":   0,
        "ganadores_ronda":  [],
        "campeon":          None,
    }


def siguiente_combate(bracket: dict) -> tuple | None:
    """
    Devuelve (p1_dbref, p2_dbref) del próximo combate.
    p2_dbref puede ser None (bye: p1 avanza automáticamente).
    Devuelve None si el torneo ya terminó.
    """
    rondas = bracket.get("rondas", [])
    ra = bracket.get("ronda_actual", 0)
    ca = bracket.get("combate_actual", 0)

    if ra >= len(rondas):
        return None
    ronda = rondas[ra]
    if ca >= len(ronda):
        return None
    return ronda[ca]


def registrar_ganador(bracket: dict, ganador_dbref: str) -> dict:
    """
    Registra el ganador del combate actual y avanza el estado del bracket.
    Cuando completa una ronda, genera automáticamente la siguiente.
    Devuelve el bracket actualizado.
    """
    rondas = bracket["rondas"]
    ra = bracket["ronda_actual"]
    ca = bracket["combate_actual"]

    ganadores = list(bracket.get("ganadores_ronda", []))
    ganadores.append(ganador_dbref)
    bracket["combate_actual"] = ca + 1

    ronda_actual = rondas[ra]
    if bracket["combate_actual"] >= len(ronda_actual):
        # Ronda completa
        if len(ganadores) == 1:
            bracket["campeon"] = ganadores[0]
        else:
            # Generar siguiente ronda
            g = list(ganadores)
            p2 = _siguiente_potencia_de_2(len(g))
            while len(g) < p2:
                g.append(None)
            siguiente = [(g[i], g[i + 1]) for i in range(0, len(g), 2)]
            rondas.append(siguiente)
            bracket["rondas"] = rondas
            bracket["ronda_actual"] = ra + 1
            bracket["combate_actual"] = 0
            bracket["ganadores_ronda"] = []
    else:
        bracket["ganadores_ronda"] = ganadores

    return bracket


def campeon(bracket: dict) -> str | None:
    """Devuelve el dbref del campeón, o None si el torneo sigue en curso."""
    return bracket.get("campeon")


def calcular_premio(n_jugadores: int) -> int:
    """Premio total en monedas (100% del pot de inscripciones + bonus)."""
    return n_jugadores * INSCRIPCION_FEE


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_inscripcion(dbrefs: list, nombres: dict) -> str:
    """nombres: {dbref: nombre_jugador}"""
    sep = "|w" + "─" * 50 + "|n"
    lineas = [f"\n{sep}", "  |cTorneo de la Arena — Inscripción|n", sep]
    if dbrefs:
        lineas.append(f"  Inscritos ({len(dbrefs)}/{MAX_JUGADORES}):")
        for i, d in enumerate(dbrefs, 1):
            lineas.append(f"    {i}. |w{nombres.get(d, '???')}|n")
    else:
        lineas.append("  |xNadie inscrito aún.|n")
    pot = len(dbrefs) * INSCRIPCION_FEE
    lineas.append(f"  Pot actual: |Y{pot} monedas|n")
    lineas.append(f"  Inscripción: |w{INSCRIPCION_FEE} monedas|n")
    lineas.append(f"  Mínimo para iniciar: |w{MIN_JUGADORES} jugadores|n")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_bracket(bracket: dict, nombres: dict) -> str:
    """Muestra el bracket completo con el estado de cada combate."""
    sep = "|w" + "─" * 50 + "|n"
    lineas = [f"\n{sep}", "  |cTorneo de la Arena — Bracket|n", sep]

    rondas = bracket.get("rondas", [])
    ra = bracket.get("ronda_actual", 0)
    ca = bracket.get("combate_actual", 0)
    campeon_dbref = bracket.get("campeon")
    gan_ronda = set(bracket.get("ganadores_ronda", []))

    for ri, ronda in enumerate(rondas):
        n_comb = len(ronda)
        nombre_ronda = _nombre_ronda(n_comb)
        estado_ronda = "|g[completada]|n" if ri < ra else ("|c[en curso]|n" if ri == ra else "|x[pendiente]|n")
        lineas.append(f"\n  |w{nombre_ronda}|n  {estado_ronda}")
        for ci, (p1, p2) in enumerate(ronda):
            nom1 = nombres.get(p1, "BYE") if p1 else "BYE"
            nom2 = nombres.get(p2, "BYE") if p2 else "BYE"
            if p2 is None:
                lineas.append(f"    |x{nom1}|n avanza automáticamente (bye)")
            elif ri < ra:
                # Ronda completada — marcar ganador
                if p1 in gan_ronda or p2 in gan_ronda:
                    gan = p1 if p1 in gan_ronda else p2
                    per = p2 if p1 == gan else p1
                    lineas.append(
                        f"    |g✔|n |w{nombres.get(gan,'???')}|n  vs  "
                        f"|x✗ {nombres.get(per,'???')}|n"
                    )
                else:
                    lineas.append(f"    {nom1}  vs  {nom2}")
            elif ri == ra:
                if ci < ca:
                    lineas.append(f"    |g✔|n {nom1}  vs  {nom2}")
                elif ci == ca:
                    lineas.append(f"    |Y► {nom1}|n  vs  |Y{nom2} ◄|n  |c(en curso)|n")
                else:
                    lineas.append(f"    |x{nom1}  vs  {nom2}|n  (pendiente)")
            else:
                lineas.append(f"    |x??? vs ???|n  (pendiente)")

    if campeon_dbref:
        lineas.append(
            f"\n  |Y🏆 CAMPEÓN: {nombres.get(campeon_dbref, '???')}|n"
        )

    lineas.append(f"\n{sep}\n")
    return "\n".join(lineas)
