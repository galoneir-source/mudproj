"""
systems/crafting/recipes.py

Recetas de crafteo y lógica de validación pura (sin dependencias de Evennia).
"""
from __future__ import annotations


# --------------------------------------------------------------------------- #
#  Definición de recetas
# --------------------------------------------------------------------------- #

RECETAS: dict[str, dict] = {
    "poción de vida": {
        "ingredientes": {"piel de serpiente": 1},
        "resultado_prototipo": "POCION_VIDA",
        "cantidad": 1,
        "desc_receta": "Ungüento curativo extraído de la piel de serpiente.",
    },
    "antídoto": {
        "ingredientes": {"piel de serpiente": 1, "veneno de pantano": 1},
        "resultado_prototipo": "ANTIDOTO",
        "cantidad": 2,
        "desc_receta": "Neutraliza venenos combinando la piel de serpiente con su propio veneno.",
    },
    "poción de vida mayor": {
        "ingredientes": {"garra de troll": 1, "piel de serpiente": 1},
        "resultado_prototipo": "POCION_VIDA_MAYOR",
        "cantidad": 1,
        "desc_receta": "La esencia regenerativa del troll, destilada junto a extracto de serpiente.",
    },
    "elixir de restauración": {
        "ingredientes": {"fragmento de alma": 1, "escama de lagarto": 2},
        "resultado_prototipo": "ELIXIR_RESTAURACION",
        "cantidad": 1,
        "desc_receta": "Magia oscura canalizada a través de escamas de hombre lagarto.",
    },
}


# --------------------------------------------------------------------------- #
#  Funciones de consulta
# --------------------------------------------------------------------------- #

def buscar_receta(nombre: str) -> tuple[str | None, dict | None]:
    """
    Busca una receta por nombre (case-insensitive).
    Primero busca coincidencia exacta, luego por startswith, luego por contains.
    Devuelve (nombre_exacto, receta_dict) o (None, None).
    """
    nombre_lower = nombre.lower().strip()
    if nombre_lower in RECETAS:
        return nombre_lower, RECETAS[nombre_lower]

    matches = [(k, v) for k, v in RECETAS.items() if k.startswith(nombre_lower)]
    if len(matches) == 1:
        return matches[0]

    matches = [(k, v) for k, v in RECETAS.items() if nombre_lower in k]
    if len(matches) == 1:
        return matches[0]

    return None, None


def verificar_ingredientes(inventario: dict[str, int], receta: dict) -> tuple[bool, dict[str, int]]:
    """
    Comprueba si el inventario tiene los ingredientes necesarios.

    inventario : {nombre_lower: cantidad_disponible}
    receta     : entrada de RECETAS

    Devuelve (ok, faltantes) donde faltantes = {nombre: cantidad_que_falta}.
    """
    faltantes: dict[str, int] = {}
    for ingr, req in receta["ingredientes"].items():
        disponible = inventario.get(ingr.lower(), 0)
        if disponible < req:
            faltantes[ingr] = req - disponible
    return len(faltantes) == 0, faltantes
