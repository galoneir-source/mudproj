"""
systems/skills/engine.py

Lógica pura del árbol de habilidades.
Sin dependencias de Evennia.
"""
from __future__ import annotations
from typing import Optional

from systems.skills.trees import HABILIDADES, HABILIDADES_INICIALES, RAMAS


def puntos_gastados(desbloqueadas: set) -> int:
    """Suma del coste de las habilidades aprendidas, excluyendo las iniciales (son gratuitas)."""
    total = 0
    for hid in desbloqueadas:
        if hid in HABILIDADES_INICIALES:
            continue
        info = HABILIDADES.get(hid)
        if info:
            total += info["coste"]
    return total


def puntos_disponibles(nivel: int, gastados: int) -> int:
    """
    Puntos disponibles = (nivel - 1) - gastados.
    El nivel 1 no da puntos; cada nivel posterior otorga 1.
    """
    return max(0, (nivel - 1) - gastados)


def puede_aprender(
    skill_id: str,
    desbloqueadas: set,
    nivel: int,
) -> tuple[bool, str]:
    """
    Comprueba si se puede aprender la habilidad.
    Devuelve (puede, mensaje_error).
    """
    if skill_id not in HABILIDADES:
        return False, f"La habilidad '{skill_id}' no existe."
    if skill_id in desbloqueadas:
        return False, "Ya conoces esta habilidad."

    info = HABILIDADES[skill_id]

    if nivel < info["nivel_req"]:
        return False, f"Necesitas nivel {info['nivel_req']} (tienes {nivel})."

    for req in info["requisitos"]:
        if req not in desbloqueadas:
            req_nombre = HABILIDADES.get(req, {}).get("nombre", req)
            return False, f"Requiere aprender primero: {req_nombre}."

    gastados = puntos_gastados(desbloqueadas)
    disponibles = puntos_disponibles(nivel, gastados)
    coste = info["coste"]
    if disponibles < coste:
        return False, f"Puntos insuficientes (necesitas {coste}, tienes {disponibles})."

    return True, ""


def aprender(
    skill_id: str,
    desbloqueadas: set,
    nivel: int,
) -> tuple[bool, set, str]:
    """
    Intenta desbloquear la habilidad.
    Devuelve (exito, nuevas_desbloqueadas, mensaje_error).
    """
    puede, err = puede_aprender(skill_id, desbloqueadas, nivel)
    if not puede:
        return False, desbloqueadas, err
    return True, set(desbloqueadas) | {skill_id}, ""


def buscar_habilidad(nombre: str) -> tuple[Optional[str], Optional[dict]]:
    """
    Busca por ID exacto, nombre exacto o subcadena.
    Devuelve (skill_id, info) o (None, None).
    """
    nombre_lower = nombre.lower().strip()
    nombre_norm = nombre_lower.replace(" ", "_")

    if nombre_norm in HABILIDADES:
        return nombre_norm, HABILIDADES[nombre_norm]
    if nombre_lower in HABILIDADES:
        return nombre_lower, HABILIDADES[nombre_lower]

    for hid, info in HABILIDADES.items():
        if nombre_lower == info["nombre"].lower():
            return hid, info

    matches = [
        (hid, info) for hid, info in HABILIDADES.items()
        if nombre_lower in info["nombre"].lower() or nombre_lower in hid
    ]
    if len(matches) == 1:
        return matches[0]

    return None, None


def habilidades_por_rama(rama: str) -> list[tuple[str, dict]]:
    """Habilidades de una rama ordenadas por nivel_req."""
    result = [(hid, info) for hid, info in HABILIDADES.items() if info["rama"] == rama]
    result.sort(key=lambda x: x[1]["nivel_req"])
    return result
