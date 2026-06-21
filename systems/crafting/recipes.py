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
    "bálsamo sagrado": {
        "ingredientes": {"cristal sagrado": 2},
        "resultado_prototipo": "POCION_VIDA_MAYOR",
        "cantidad": 1,
        "desc_receta": "La luz purificada de dos cristales sagrados destilada en una poción curativa.",
    },
    "tónico del templo": {
        "ingredientes": {"cristal sagrado": 1, "fragmento de alma": 1},
        "resultado_prototipo": "ELIXIR_RESTAURACION",
        "cantidad": 1,
        "desc_receta": "La tensión entre lo sagrado y lo oscuro libera una energía restauradora total.",
    },
    "antídoto de araña": {
        "ingredientes": {"hilo de araña": 2},
        "resultado_prototipo": "ANTIDOTO",
        "cantidad": 2,
        "desc_receta": "El hilo de araña de cueva contiene propiedades antiveneno excepcionales.",
    },
    "tónico de piedra": {
        "ingredientes": {"mineral de hierro": 1, "gema en bruto": 1},
        "resultado_prototipo": "POCION_VIDA_MAYOR",
        "cantidad": 1,
        "desc_receta": "La energía mineral de la roca y los cristales de la gema, destilados en un tónico rejuvenecedor.",
    },
    "esencia de ceniza": {
        "ingredientes": {"cenizas arcanas": 2},
        "resultado_prototipo": "POCION_VIDA_MAYOR",
        "cantidad": 1,
        "desc_receta": "Las cenizas impregnadas de magia residual destilan su energía en un poderoso elixir curativo.",
    },
    "elixir arcano": {
        "ingredientes": {"cenizas arcanas": 1, "fragmento arcano": 1},
        "resultado_prototipo": "ELIXIR_RESTAURACION",
        "cantidad": 1,
        "desc_receta": "La fusión de cenizas mágicas y un fragmento arcano solidificado libera una energía restauradora total.",
    },
    "elixir sombrío": {
        "ingredientes": {"cenizas sombrías": 2, "fragmento de alma oscura": 1},
        "resultado_prototipo": "ELIXIR_RESTAURACION",
        "cantidad": 1,
        "desc_receta": "Las cenizas de magia oscura disueltas en la esencia de un alma atrapada destilan un restaurador total de insólito poder.",
    },
    "tónico de las sombras": {
        "ingredientes": {"cristal de oscuridad": 1, "cenizas sombrías": 1},
        "resultado_prototipo": "POCION_VIDA_MAYOR",
        "cantidad": 2,
        "desc_receta": "El cristal que absorbe la luz y las cenizas sombrías liberan, al fundirse, una cura poderosa y sombría.",
    },
    # --- Equipo ---
    "daga de acero": {
        "tipo": "equipo",
        "ingredientes": {"mineral de hierro": 2, "piel de serpiente": 1},
        "resultado_prototipo": "DAGA_ACERO",
        "cantidad": 1,
        "desc_receta": "Daga forjada con hierro de las minas y cuero de serpiente. La maestría del artesano determina su calidad.",
    },
    "espada del cazador": {
        "tipo": "equipo",
        "ingredientes": {"mineral de hierro": 3, "garra de troll": 1},
        "resultado_prototipo": "ESPADA_CAZADOR",
        "cantidad": 1,
        "desc_receta": "Espada templada con la dureza natural del hierro y reforzada con la esencia de un troll.",
    },
    "vara arcana": {
        "tipo": "equipo",
        "ingredientes": {"cenizas arcanas": 2, "fragmento arcano": 2},
        "resultado_prototipo": "VARA_ARCANA",
        "cantidad": 1,
        "desc_receta": "Canal de madera impregnado con cenizas y fragmentos arcanos. Amplifica el poder mágico del portador.",
    },
    "hacha tallada": {
        "tipo": "equipo",
        "ingredientes": {"mineral de hierro": 2, "escama de lagarto": 2},
        "resultado_prototipo": "HACHA_TALLADA",
        "cantidad": 1,
        "desc_receta": "Hacha de hoja de hierro con empuñadura reforzada con escamas de lagarto para mejor agarre.",
    },
    "coraza de hierro": {
        "tipo": "equipo",
        "ingredientes": {"mineral de hierro": 4, "piel de serpiente": 2},
        "resultado_prototipo": "CORAZA_HIERRO",
        "cantidad": 1,
        "desc_receta": "Coraza de placas de hierro con forro interior de piel de serpiente. Protección seria para combates serios.",
    },
    "túnica del mago": {
        "tipo": "equipo",
        "ingredientes": {"cenizas arcanas": 2, "hilo de araña": 1, "cristal sagrado": 1},
        "resultado_prototipo": "TUNICA_MAGO",
        "cantidad": 1,
        "desc_receta": "Prenda tejida con hilo de araña encantado, impregnada de cenizas arcanas y un cristal sagrado. Canaliza la magia del portador.",
    },
    "amuleto de combate": {
        "tipo": "equipo",
        "ingredientes": {"gema en bruto": 2, "fragmento de alma": 1},
        "resultado_prototipo": "AMULETO_COMBATE",
        "cantidad": 1,
        "desc_receta": "Amuleto forjado con dos gemas en bruto cargadas con la esencia de un alma atrapada.",
    },
    "anillo de sombras": {
        "tipo": "equipo",
        "ingredientes": {"cristal de oscuridad": 1, "cenizas sombrías": 1},
        "resultado_prototipo": "ANILLO_SOMBRAS",
        "cantidad": 1,
        "desc_receta": "Anillo impregnado de oscuridad que agudiza los sentidos y amplifica la magia de las sombras.",
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
    if len(matches) > 1:
        matches.sort(key=lambda x: len(x[0]))
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
