"""
systems/classes/classes.py

Catálogo de clases de personaje y lógica pura de selección.
Sin dependencias de Evennia.

Tres clases que se corresponden con las ramas del árbol de habilidades:
  guerrero   — ofensivo cuerpo a cuerpo, alta FUE/CON/DEF
  explorador — ágil y veloz, alta DES
  mago       — arcano, alta INT
"""
from __future__ import annotations

CLASES: dict[str, dict] = {
    "guerrero": {
        "nombre": "Guerrero",
        "descripcion": "Combatiente resistente que domina la fuerza bruta y el combate cuerpo a cuerpo.",
        "stat_bonus": {
            "fuerza": 3,
            "constitucion": 2,
            "defensa": 1,
            "hp_max": 20,
            "hp": 20,
        },
        "rama": "guerrero",
        "color": "|r",
    },
    "explorador": {
        "nombre": "Explorador",
        "descripcion": "Ágil y veloz, experto en ataques rápidos, emboscadas y venenos.",
        "stat_bonus": {
            "destreza": 4,
            "constitucion": 1,
        },
        "rama": "explorador",
        "color": "|g",
    },
    "mago": {
        "nombre": "Mago",
        "descripcion": "Manipulador de la magia arcana que canaliza su inteligencia en hechizos devastadores.",
        "stat_bonus": {
            "inteligencia": 5,
        },
        "rama": "mago",
        "color": "|c",
    },
}


def clase_valida(clase_id: str) -> bool:
    """True si el identificador corresponde a una clase existente."""
    return clase_id.lower() in CLASES


def puede_aprender_clase(skill_id: str, clase_id: str | None) -> tuple[bool, str]:
    """
    Comprueba si la clase permite aprender la habilidad.

    Sin clase asignada, no hay restricción.
    Con clase, solo se pueden aprender habilidades de la propia rama.
    Devuelve (puede, mensaje_error).
    """
    if not clase_id:
        return True, ""
    clase_id = clase_id.lower()
    if clase_id not in CLASES:
        return True, ""

    from systems.skills.trees import HABILIDADES, HABILIDADES_INICIALES
    if skill_id in HABILIDADES_INICIALES:
        return True, ""

    info = HABILIDADES.get(skill_id)
    if not info:
        return True, ""

    rama_clase = CLASES[clase_id]["rama"]
    if info.get("rama") != rama_clase:
        nombre_clase = CLASES[clase_id]["nombre"]
        nombre_rama = rama_clase.capitalize()
        return False, (
            f"Los {nombre_clase}s solo pueden aprender habilidades "
            f"de la rama {nombre_rama}."
        )

    return True, ""


def aplicar_clase(stats: dict, clase_id: str) -> dict:
    """
    Aplica los bonuses de la clase a un dict de stats.
    Devuelve un dict nuevo con los valores modificados.
    """
    if clase_id not in CLASES:
        return stats
    resultado = dict(stats)
    for stat, valor in CLASES[clase_id]["stat_bonus"].items():
        resultado[stat] = resultado.get(stat, 0) + valor
    return resultado
