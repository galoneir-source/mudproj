"""
systems/friends/friends.py

Lógica pura del sistema de lista de amigos. Sin dependencias de Evennia.

db.amigos en Character: list[str] — dbrefs de otros personajes.

Relación unidireccional (como una lista de contactos), no una amistad mutua:
agregar a alguien no requiere que te agregue de vuelta ni genera ninguna
invitación. El límite existe solo para evitar listas gigantes.
"""
from __future__ import annotations

MAX_AMIGOS = 30


def es_amigo(amigos: list, dbref: str) -> bool:
    """True si dbref ya está en la lista de amigos."""
    return dbref in amigos


def puede_agregar(amigos: list, dbref: str, propio_dbref: str) -> tuple[bool, str]:
    """Valida si se puede agregar dbref como amigo. Devuelve (ok, error)."""
    if dbref == propio_dbref:
        return False, "No puedes agregarte a ti mismo como amigo."
    if es_amigo(amigos, dbref):
        return False, "Ya tienes a esa persona en tu lista de amigos."
    if len(amigos) >= MAX_AMIGOS:
        return False, f"Tu lista de amigos está llena (máximo {MAX_AMIGOS})."
    return True, ""


def agregar_amigo(amigos: list, dbref: str) -> list:
    """Devuelve una nueva lista con dbref agregado (sin duplicar)."""
    if dbref in amigos:
        return list(amigos)
    return list(amigos) + [dbref]


def quitar_amigo(amigos: list, dbref: str) -> list:
    """Devuelve una nueva lista sin dbref."""
    return [a for a in amigos if a != dbref]


def formatear_lista_amigos(entradas: list[tuple[str, bool]]) -> str:
    """
    Formatea la lista de amigos para mostrar.

    `entradas`: [(nombre, en_linea), ...]. Los conectados aparecen primero,
    y dentro de cada grupo se ordena alfabéticamente.
    """
    if not entradas:
        return "|xNo tienes amigos agregados todavía. Usa 'agregar amigo <nombre>'.|n"
    ordenados = sorted(entradas, key=lambda e: (not e[1], e[0].lower()))
    lineas = ["|wTu lista de amigos:|n"]
    for nombre, en_linea in ordenados:
        estado = "|gEn línea|n" if en_linea else "|xDesconectado|n"
        lineas.append(f"  {nombre:<20} {estado}")
    return "\n".join(lineas)
