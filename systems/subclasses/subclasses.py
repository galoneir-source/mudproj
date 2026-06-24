"""
systems/subclasses/subclasses.py

Catálogo de subclases y lógica pura de especialización.
Sin dependencias de Evennia.

Seis subclases, dos por clase base:
  guerrero   → paladín (DEF/HP) | berserker (FUE)
  explorador → asesino (DES)    | cazador (DES/CON)
  mago       → hechicero (INT)  | nigromante (INT/CON)
"""
from __future__ import annotations

SUBCLASES: dict[str, dict] = {
    "paladin": {
        "nombre": "Paladín",
        "clase_req": "guerrero",
        "color": "|Y",
        "descripcion": "Guerrero sagrado que combina fuerza física y fe divina.",
        "stat_bonus": {"defensa": 2, "hp_max": 15, "hp": 15},
        "habilidades": ["escudo_divino", "golpe_sagrado"],
    },
    "berserker": {
        "nombre": "Berserker",
        "clase_req": "guerrero",
        "color": "|r",
        "descripcion": "Guerrero que canaliza la ira para devastar a sus enemigos.",
        "stat_bonus": {"fuerza": 4},
        "habilidades": ["furia_berserker", "golpe_demoledor"],
    },
    "asesino": {
        "nombre": "Asesino",
        "clase_req": "explorador",
        "color": "|m",
        "descripcion": "Especialista en ataques letales desde las sombras.",
        "stat_bonus": {"destreza": 3},
        "habilidades": ["golpe_certero", "golpe_letal"],
    },
    "cazador": {
        "nombre": "Cazador",
        "clase_req": "explorador",
        "color": "|g",
        "descripcion": "Rastreador experto que combina agilidad y resistencia.",
        "stat_bonus": {"destreza": 2, "constitucion": 2},
        "habilidades": ["instinto_cazador", "trampa_mortal"],
    },
    "hechicero": {
        "nombre": "Hechicero",
        "clase_req": "mago",
        "color": "|c",
        "descripcion": "Especialista en magia de alto impacto arcano.",
        "stat_bonus": {"inteligencia": 3},
        "habilidades": ["concentracion_arcana", "nova_arcana"],
    },
    "nigromante": {
        "nombre": "Nigromante",
        "clase_req": "mago",
        "color": "|W",
        "descripcion": "Mago oscuro que drena la esencia vital de sus víctimas.",
        "stat_bonus": {"inteligencia": 2, "constitucion": 2},
        "habilidades": ["escudo_sombrio", "drenar_esencia"],
    },
}

NIVEL_MIN_SUBCLASE = 5


def subclase_valida(subclase_id: str) -> bool:
    """True si el identificador corresponde a una subclase existente."""
    return subclase_id.lower() in SUBCLASES


def subclases_de_clase(clase_id: str) -> dict[str, dict]:
    """Devuelve las subclases disponibles para una clase base."""
    return {
        sid: info for sid, info in SUBCLASES.items()
        if info["clase_req"] == clase_id
    }


def puede_elegir_subclase(
    nivel: int,
    clase: str | None,
    subclase_actual: str | None,
    subclase_id: str,
) -> tuple[bool, str]:
    """
    Valida si un personaje puede elegir la subclase indicada.
    Devuelve (puede, mensaje_error).
    """
    if not clase:
        return False, "Necesitas una clase antes de elegir subclase (usa |wclase|n)."
    if subclase_actual:
        nombre = SUBCLASES.get(subclase_actual, {}).get("nombre", subclase_actual)
        return False, f"Ya tienes la subclase {nombre}. No puede cambiarse."
    if nivel < NIVEL_MIN_SUBCLASE:
        return (
            False,
            f"Necesitas nivel {NIVEL_MIN_SUBCLASE} para elegir subclase "
            f"(tienes {nivel}).",
        )
    if subclase_id not in SUBCLASES:
        return False, f"Subclase '{subclase_id}' no existe."
    clase_req = SUBCLASES[subclase_id]["clase_req"]
    if clase_req != clase:
        nombre_clase_req = clase_req.capitalize()
        return False, f"Esta subclase requiere ser {nombre_clase_req}."
    return True, ""


def aplicar_subclase(stats: dict, subclase_id: str) -> dict:
    """Aplica los bonuses de la subclase a un dict de stats. Devuelve un dict nuevo."""
    if subclase_id not in SUBCLASES:
        return stats
    resultado = dict(stats)
    for stat, valor in SUBCLASES[subclase_id]["stat_bonus"].items():
        resultado[stat] = resultado.get(stat, 0) + valor
    return resultado
