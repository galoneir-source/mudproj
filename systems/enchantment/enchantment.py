"""
systems/enchantment/enchantment.py

Lógica pura del sistema de encantamiento. Sin dependencias de Evennia.

Permite mejorar ítems Equipo hasta +3 usando materiales del mundo.
Cada nivel añade stats distintos según el slot del ítem.

  arma      +N: +2 al stat con mayor bonus positivo
  armadura  +N: +2 defensa, +5 hp_max
  accesorio +N: +1 a cada stat con valor positivo
"""
from __future__ import annotations

MAX_ENCANTAMIENTO = 3

# Ingredientes necesarios por slot y nivel
COSTES_ENCANTAMIENTO: dict[str, dict[int, dict[str, int]]] = {
    "arma": {
        1: {"mineral de hierro": 2},
        2: {"mineral de hierro": 2, "núcleo de piedra": 1},
        3: {"núcleo de piedra": 1, "núcleo arcano": 1},
    },
    "armadura": {
        1: {"escama de lagarto": 2},
        2: {"escama de lagarto": 2, "fragmento de alma": 1},
        3: {"fragmento de alma": 1, "cenizas arcanas": 2},
    },
    "accesorio": {
        1: {"gema en bruto": 1},
        2: {"gema en bruto": 1, "cristal sagrado": 1},
        3: {"cristal sagrado": 1, "núcleo arcano": 1},
    },
}


def stat_primario(bonuses: dict) -> str | None:
    """Devuelve el stat con mayor valor positivo del dict de bonuses."""
    positivos = {k: v for k, v in bonuses.items() if isinstance(v, (int, float)) and v > 0}
    if not positivos:
        return None
    return max(positivos, key=positivos.__getitem__)


def delta_encantamiento(slot: str, bonuses: dict) -> dict:
    """
    Calcula el incremento que se añade POR NIVEL de encantamiento.

    arma:     +2 al stat de mayor bonus positivo
    armadura: +2 defensa, +5 hp_max
    accesorio: +1 a cada stat con valor positivo en los bonuses actuales
    """
    if slot == "arma":
        primario = stat_primario(bonuses)
        return {primario: 2} if primario else {}
    if slot == "armadura":
        return {"defensa": 2, "hp_max": 5}
    if slot == "accesorio":
        return {k: 1 for k, v in bonuses.items() if isinstance(v, (int, float)) and v > 0}
    return {}


def coste_encantamiento(slot: str, nivel: int) -> dict:
    """Ingredientes necesarios para encantar a ese nivel."""
    return COSTES_ENCANTAMIENTO.get(slot, {}).get(nivel, {})


def puede_encantar(nivel_actual: int) -> tuple[bool, str]:
    """True si el ítem aún puede subir de nivel de encantamiento."""
    if nivel_actual >= MAX_ENCANTAMIENTO:
        return False, f"Este ítem ya está en el nivel máximo de encantamiento (+{MAX_ENCANTAMIENTO})."
    return True, ""


def verificar_ingredientes_encantamiento(
    slot: str, nivel: int, inventario: dict[str, int]
) -> tuple[bool, dict[str, int]]:
    """
    Comprueba si el inventario contiene los materiales requeridos.

    inventario: {nombre_lower: cantidad_disponible}
    Devuelve (ok, faltantes) donde faltantes = {nombre: cantidad_que_falta}.
    """
    coste = coste_encantamiento(slot, nivel)
    if not coste:
        return False, {}
    faltantes: dict[str, int] = {}
    for ingr, req in coste.items():
        disponible = inventario.get(ingr.lower(), 0)
        if disponible < req:
            faltantes[ingr] = req - disponible
    return not faltantes, faltantes


def texto_coste(slot: str, nivel: int) -> str:
    """Texto legible del coste de encantamiento para un slot y nivel."""
    coste = coste_encantamiento(slot, nivel)
    if not coste:
        return "—"
    return ", ".join(f"{ingr} ×{cant}" for ingr, cant in coste.items())
