"""
systems/expeditions/expeditions.py

Lógica pura del sistema de expediciones grupales. Sin dependencias de Evennia.

Una expedición es una secuencia de oleadas de enemigos que un grupo (party)
debe superar. Al terminar todas las oleadas, el grupo recibe recompensas.

db.expediciones_completadas   en Character: int — expediciones finalizadas con éxito
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

EXPEDICIONES: dict[str, dict] = {
    "bosque_profundo": {
        "nombre":       "Bosque Profundo",
        "descripcion":  "Las criaturas del bosque se han vuelto peligrosamente agresivas. "
                        "Se necesitan cazadores valientes para limpiar la zona.",
        "nivel_min":    3,
        "miembros_min": 2,
        "miembros_max": 4,
        "zona_nombre":  "Claro de Expedición — Bosque",
    },
    "catacumbas_perdidas": {
        "nombre":       "Catacumbas Perdidas",
        "descripcion":  "Catacumbas antiguas repletas de no-muertos que llevan décadas "
                        "sin ser exploradas. Un grupo experimentado puede hacerse rico.",
        "nivel_min":    5,
        "miembros_min": 2,
        "miembros_max": 4,
        "zona_nombre":  "Cámara de Expedición — Catacumbas",
    },
    "fortaleza_caida": {
        "nombre":       "Fortaleza Caída",
        "descripcion":  "Una fortaleza del reino tomada por bandidos de élite bajo el mando "
                        "del infame Capitán Morgath. Solo los más fuertes sobrevivirán.",
        "nivel_min":    7,
        "miembros_min": 3,
        "miembros_max": 4,
        "zona_nombre":  "Sala de Expedición — Fortaleza",
    },
}

TIPOS_VALIDOS: frozenset[str] = frozenset(EXPEDICIONES)

# Oleadas por expedición: lista de oleadas.
# Cada oleada = lista de (proto_key, cantidad).
# La última oleada es siempre la del jefe.
OLEADAS: dict[str, list[list[tuple[str, int]]]] = {
    "bosque_profundo": [
        [("GOBLIN", 2), ("ARANA_CUEVA", 1)],
        [("GOBLIN", 3), ("BANDIDO", 1)],
        [("GOBLIN_JEFE", 1)],
    ],
    "catacumbas_perdidas": [
        [("ESQUELETO", 2)],
        [("ESQUELETO", 2), ("ESPECTRO", 1)],
        [("ESQUELETO", 1), ("HECHICERO_SOMBRIO", 1)],
        [("CABALLERO_OSCURO", 1)],
    ],
    "fortaleza_caida": [
        [("BANDIDO", 3)],
        [("BANDIDO", 2), ("TROLL", 1)],
        [("CABALLERO_OSCURO", 1), ("BANDIDO", 2)],
        [("CABALLERO_MUERTE", 1), ("HECHICERO_SOMBRIO", 1)],
        [("BANDIDO_CAPITAN", 1)],
    ],
}

# XP y monedas BASE por oleada (se multiplican al completar la expedición entera)
RECOMPENSAS_POR_OLEADA: dict[str, dict] = {
    "bosque_profundo":    {"xp": 80,  "monedas": 50},
    "catacumbas_perdidas": {"xp": 120, "monedas": 80},
    "fortaleza_caida":    {"xp": 180, "monedas": 120},
}

# Bonus adicional por completar todas las oleadas
BONUS_COMPLETAR: dict[str, dict] = {
    "bosque_profundo":    {"xp": 150, "monedas": 100},
    "catacumbas_perdidas": {"xp": 300, "monedas": 200},
    "fortaleza_caida":    {"xp": 500, "monedas": 350},
}


# --------------------------------------------------------------------------- #
#  Consultas
# --------------------------------------------------------------------------- #

def tipos_validos() -> frozenset[str]:
    return TIPOS_VALIDOS


def oleadas_de(tipo_id: str) -> list:
    """Devuelve la lista de oleadas de una expedición."""
    return OLEADAS.get(tipo_id, [])


def total_oleadas(tipo_id: str) -> int:
    """Número total de oleadas (incluido el jefe)."""
    return len(OLEADAS.get(tipo_id, []))


def es_oleada_jefe(tipo_id: str, oleada_idx: int) -> bool:
    """True si la oleada indicada (0-indexed) es la última (jefe)."""
    return oleada_idx == total_oleadas(tipo_id) - 1


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_iniciar(
    tipo_id: str,
    num_miembros: int,
    niveles: list[int],
) -> tuple[bool, str]:
    """
    Comprueba si un grupo puede iniciar una expedición.

    tipo_id     — ID de la expedición
    num_miembros — número de jugadores en el grupo (incluido el líder)
    niveles     — lista de niveles de todos los miembros
    """
    if tipo_id not in EXPEDICIONES:
        return False, f"Expedición '|w{tipo_id}|n' desconocida. Usa |wexpedicion lista|n."

    exp = EXPEDICIONES[tipo_id]
    min_m = exp["miembros_min"]
    max_m = exp["miembros_max"]
    nivel_min = exp["nivel_min"]

    if num_miembros < min_m:
        return False, (
            f"La expedición '|w{exp['nombre']}|n' requiere al menos |w{min_m} jugadores|n "
            f"(tienes {num_miembros})."
        )
    if num_miembros > max_m:
        return False, (
            f"La expedición '|w{exp['nombre']}|n' admite máximo |w{max_m} jugadores|n."
        )

    bajo_nivel = [n for n in niveles if n < nivel_min]
    if bajo_nivel:
        return False, (
            f"Todos los miembros deben ser al menos nivel |w{nivel_min}|n para esta expedición."
        )

    return True, ""


# --------------------------------------------------------------------------- #
#  Recompensas
# --------------------------------------------------------------------------- #

def calcular_recompensa_oleada(tipo_id: str, num_miembros: int) -> dict:
    """XP y monedas por superar UNA oleada (por jugador)."""
    base = RECOMPENSAS_POR_OLEADA.get(tipo_id, {"xp": 50, "monedas": 30})
    factor = 1.0 + (num_miembros - 2) * 0.1
    return {
        "xp":      int(base["xp"] * factor),
        "monedas": int(base["monedas"] * factor),
    }


def calcular_bonus_completar(tipo_id: str, num_miembros: int) -> dict:
    """
    Bonus adicional (por jugador) por completar la expedición entera, sin
    contar las recompensas de oleada -- esas ya se pagan una a una, oleada
    a oleada (incluida la del jefe), a través de calcular_recompensa_oleada().
    """
    bonus = BONUS_COMPLETAR.get(tipo_id, {"xp": 0, "monedas": 0})
    factor = 1.0 + (num_miembros - 2) * 0.1
    return {
        "xp":      int(bonus["xp"] * factor),
        "monedas": int(bonus["monedas"] * factor),
    }


def calcular_recompensa_total(tipo_id: str, num_miembros: int) -> dict:
    """
    XP y monedas acumuladas (por jugador) a lo largo de toda la expedición:
    suma de la recompensa de cada oleada más el bonus de completar. Uso
    informativo/de referencia -- no repartir esto de golpe al completar,
    ya que las oleadas se pagan por separado (ver calcular_bonus_completar).
    """
    por_oleada = calcular_recompensa_oleada(tipo_id, num_miembros)
    n_oleadas = total_oleadas(tipo_id)
    bonus = calcular_bonus_completar(tipo_id, num_miembros)
    return {
        "xp":      por_oleada["xp"] * n_oleadas + bonus["xp"],
        "monedas": por_oleada["monedas"] * n_oleadas + bonus["monedas"],
    }


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def _barra_oleadas(actual: int, total: int) -> str:
    llenas = "█" * actual
    vacias = "░" * (total - actual)
    return f"|g{llenas}|x{vacias}|n"


def formatear_catalogo() -> str:
    sep = "|w" + "─" * 54 + "|n"
    lineas = [f"\n{sep}", "  |cExpediciones Disponibles|n", sep]
    for tid, exp in EXPEDICIONES.items():
        miembros = f"{exp['miembros_min']}–{exp['miembros_max']}"
        n_oleadas = total_oleadas(tid)
        lineas.append(
            f"\n  |Y{exp['nombre']}|n  |x({tid})|n\n"
            f"    {exp['descripcion']}\n"
            f"    Nivel mín: |w{exp['nivel_min']}|n  "
            f"Jugadores: |w{miembros}|n  "
            f"Oleadas: |w{n_oleadas}|n"
        )
    lineas.append(f"\n{sep}")
    lineas.append("  Usa |wexpedicion info <nombre>|n para más detalles.")
    lineas.append(f"  Usa |wexpedicion iniciar <nombre>|n siendo líder del grupo.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_info(tipo_id: str) -> str:
    if tipo_id not in EXPEDICIONES:
        return f"|rExpedición '|w{tipo_id}|r' no encontrada.|n"
    exp = EXPEDICIONES[tipo_id]
    oleadas = OLEADAS[tipo_id]
    bonus = BONUS_COMPLETAR[tipo_id]
    por_oleada = RECOMPENSAS_POR_OLEADA[tipo_id]

    sep = "|w" + "─" * 54 + "|n"
    lineas = [
        f"\n{sep}",
        f"  |Y{exp['nombre']}|n",
        sep,
        f"  {exp['descripcion']}",
        f"\n  Nivel mínimo:  |w{exp['nivel_min']}|n",
        f"  Jugadores:     |w{exp['miembros_min']}–{exp['miembros_max']}|n",
        f"  Oleadas:       |w{len(oleadas)}|n (última = jefe)",
        f"\n  Recompensas por oleada:  |g{por_oleada['xp']} XP|n  |y{por_oleada['monedas']} m|n",
        f"  Bonus al completar:      |g{bonus['xp']} XP|n  |y{bonus['monedas']} m|n",
        f"{sep}\n",
    ]
    return "\n".join(lineas)


def formatear_progreso(tipo_id: str, oleada_actual: int) -> str:
    """Muestra el progreso de la expedición en curso."""
    if tipo_id not in EXPEDICIONES:
        return ""
    exp = EXPEDICIONES[tipo_id]
    total = total_oleadas(tipo_id)
    completadas = oleada_actual
    barra = _barra_oleadas(completadas, total)
    jefe = "  |r[JEFE]|n" if oleada_actual == total - 1 else ""
    sep = "|w" + "─" * 54 + "|n"
    return (
        f"\n{sep}\n"
        f"  |cExpedición: {exp['nombre']}|n{jefe}\n"
        f"  Oleada |w{oleada_actual + 1}/{total}|n  {barra}\n"
        f"{sep}\n"
    )
