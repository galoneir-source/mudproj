"""
systems/combat/states.py

Lógica pura de estados de combate (sin dependencias de Evennia).
Estados disponibles: veneno, sangrado, regeneracion.
"""
from __future__ import annotations
from typing import Optional


# --------------------------------------------------------------------------- #
#  Configuración por defecto de cada estado
# --------------------------------------------------------------------------- #

ESTADO_DEFAULTS: dict[str, dict] = {
    "veneno":       {"dano_por_turno": 5, "turnos_restantes": 3},
    "sangrado":     {"dano_por_turno": 3, "turnos_restantes": 2},
    "regeneracion": {"hp_por_turno": 8,  "turnos_restantes": 4},
}

_NOMBRES_DISPLAY = {
    "veneno":       "veneno",
    "sangrado":     "sangrado",
    "regeneracion": "regeneración",
}

# Habilidades que aplican estado al impactar
_HABILIDAD_A_ESTADO: dict[str, str] = {
    "veneno": "veneno",
    "corte":  "sangrado",
}


# --------------------------------------------------------------------------- #
#  API pública
# --------------------------------------------------------------------------- #

def estado_de_habilidad(habilidad: str) -> Optional[str]:
    """Devuelve el nombre del estado que aplica la habilidad, o None."""
    return _HABILIDAD_A_ESTADO.get(habilidad.lower())


def aplicar_estado(estados: dict, nombre: str, **kwargs) -> dict:
    """
    Añade o renueva un estado.
    Si ya existe, solo renueva los turnos (no acumula daño).
    kwargs sobreescriben los valores por defecto.
    """
    estados = dict(estados)
    config = dict(ESTADO_DEFAULTS.get(nombre, {"turnos_restantes": 1}))
    config.update(kwargs)
    if nombre in estados:
        estados[nombre] = dict(estados[nombre])
        estados[nombre]["turnos_restantes"] = config["turnos_restantes"]
    else:
        estados[nombre] = config
    return estados


def tick_estados(estados: dict, hp: int, hp_max: int) -> tuple[dict, int, list[str]]:
    """
    Aplica un tick a todos los estados activos.
    Devuelve (estados_restantes, nuevo_hp, mensajes).
    El HP resultante puede llegar a 0 (el llamador decide si eso mata).
    """
    estados = dict(estados)
    mensajes: list[str] = []
    nuevo_hp = hp
    a_eliminar: list[str] = []

    for nombre, datos in list(estados.items()):
        datos = dict(datos)

        if nombre == "veneno":
            dano = datos.get("dano_por_turno", 5)
            nuevo_hp = max(0, nuevo_hp - dano)
            mensajes.append(
                f"|rEl veneno te causa {dano} de daño.|n "
                f"HP: |w{nuevo_hp}/{hp_max}|n"
            )
        elif nombre == "sangrado":
            dano = datos.get("dano_por_turno", 3)
            nuevo_hp = max(0, nuevo_hp - dano)
            mensajes.append(
                f"|rSangras y pierdes {dano} de vida.|n "
                f"HP: |w{nuevo_hp}/{hp_max}|n"
            )
        elif nombre == "regeneracion":
            recuperado = min(datos.get("hp_por_turno", 8), hp_max - nuevo_hp)
            if recuperado > 0:
                nuevo_hp += recuperado
                mensajes.append(
                    f"|gTe regeneras y recuperas {recuperado} de vida.|n "
                    f"HP: |w{nuevo_hp}/{hp_max}|n"
                )

        datos["turnos_restantes"] -= 1
        if datos["turnos_restantes"] <= 0:
            a_eliminar.append(nombre)
            display = _NOMBRES_DISPLAY.get(nombre, nombre)
            mensajes.append(f"|yEl efecto de {display} ha expirado.|n")
        else:
            estados[nombre] = datos

    for nombre in a_eliminar:
        estados.pop(nombre, None)

    return estados, nuevo_hp, mensajes


def limpiar_estado(estados: dict, nombre: str) -> dict:
    """Elimina un estado específico."""
    estados = dict(estados)
    estados.pop(nombre, None)
    return estados


def limpiar_todos(_estados: dict) -> dict:
    """Elimina todos los estados."""
    return {}
