"""
systems/alchemy/alchemy.py

Lógica pura del sistema de alquimia avanzada. Sin dependencias de Evennia.

Árbol de rangos:
  aprendiz  — disponible desde el inicio (0 pociones elaboradas)
  artesano  — se desbloquea al elaborar 5 pociones
  maestro   — se desbloquea al elaborar 15 pociones

Ingredientes: materiales de herboristería obtenidos con la profesión.
  "hierba medicinal"  — nivel herboristería 1
  "raíz de pantano"   — nivel herboristería 2
  "flor silvestre"    — nivel herboristería 3
  "esencia vegetal"   — nivel herboristería 4
  "extracto raro"     — nivel herboristería 5

db.pociones_elaboradas  en Character: int — total de pociones alquímicas elaboradas
db.rango_alquimia       en Character: str — "aprendiz" | "artesano" | "maestro"
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Rangos
# --------------------------------------------------------------------------- #

RANGOS: list[str] = ["aprendiz", "artesano", "maestro"]

POCIONES_POR_RANGO: dict[str, int] = {
    "artesano": 5,
    "maestro":  15,
}

# --------------------------------------------------------------------------- #
#  Catálogo de recetas
# --------------------------------------------------------------------------- #
#  resultado: dict con los atributos del Consumible creado.
#    efecto          — tipo de efecto del Consumible
#    potencia        — magnitud (HP recuperados, segundos de duración, etc.)
#    stat_buff       — estadística afectada (solo para buff_stat)
#    duracion        — duración en segundos (solo para buff_stat / buff_xp)
#    valor           — precio base de venta (al 50%)

RECETAS: dict[str, dict] = {
    # ── Aprendiz ──────────────────────────────────────────────────────────
    "balsamo_regenerador": {
        "nombre":       "Bálsamo Regenerador",
        "descripcion":  "Un ungüento elaborado con hierbas medicinales. Restaura más vida que una poción básica.",
        "rango":        "aprendiz",
        "ingredientes": {"hierba medicinal": 3},
        "resultado": {
            "key":      "Bálsamo Regenerador",
            "desc":     "Un bálsamo verdoso con aroma a campo. Elaborado por un alquimista experimentado.",
            "efecto":   "curar_hp",
            "potencia": 60,
            "stat_buff": "",
            "duracion": 0,
            "valor":    25,
        },
    },
    "antidoto_reforzado": {
        "nombre":       "Antídoto Reforzado",
        "descripcion":  "Cura el envenenamiento activo y otorga inmunidad al veneno durante el próximo combate.",
        "rango":        "aprendiz",
        "ingredientes": {"hierba medicinal": 1, "raíz de pantano": 1},
        "resultado": {
            "key":      "Antídoto Reforzado",
            "desc":     "Un líquido amargo de color verdoso. Huele a raíz de pantano.",
            "efecto":   "curar_veneno_protegido",
            "potencia": 1,
            "stat_buff": "",
            "duracion": 0,
            "valor":    30,
        },
    },
    "pocion_sigilo_menor": {
        "nombre":       "Poción de Sigilo Menor",
        "descripcion":  "Te vuelve imperceptible para otros en la sala durante 2 minutos.",
        "rango":        "aprendiz",
        "ingredientes": {"raíz de pantano": 2},
        "resultado": {
            "key":      "Poción de Sigilo Menor",
            "desc":     "Un vial con un líquido grisáceo que huele a tierra húmeda.",
            "efecto":   "sigilo",
            "potencia": 120,
            "stat_buff": "",
            "duracion": 0,
            "valor":    35,
        },
    },

    # ── Artesano ──────────────────────────────────────────────────────────
    "pocion_sigilo": {
        "nombre":       "Poción de Sigilo",
        "descripcion":  "Te oculta en la sala durante 5 minutos. El combate rompe el efecto.",
        "rango":        "artesano",
        "ingredientes": {"flor silvestre": 1, "raíz de pantano": 1},
        "resultado": {
            "key":      "Poción de Sigilo",
            "desc":     "Un vial con líquido plateado. Se evapora al descorcharlo.",
            "efecto":   "sigilo",
            "potencia": 300,
            "stat_buff": "",
            "duracion": 0,
            "valor":    60,
        },
    },
    "elixir_reflejos": {
        "nombre":       "Elixir de Reflejos",
        "descripcion":  "Otorga +5 de destreza durante 25 minutos.",
        "rango":        "artesano",
        "ingredientes": {"flor silvestre": 2},
        "resultado": {
            "key":      "Elixir de Reflejos",
            "desc":     "Un elixir azul brillante que hace que los dedos hormigueen.",
            "efecto":   "buff_stat",
            "potencia": 5,
            "stat_buff": "destreza",
            "duracion": 1500,
            "valor":    70,
        },
    },
    "pocion_arcana": {
        "nombre":       "Poción Arcana",
        "descripcion":  "Otorga +6 de inteligencia durante 25 minutos.",
        "rango":        "artesano",
        "ingredientes": {"flor silvestre": 1, "esencia vegetal": 1},
        "resultado": {
            "key":      "Poción Arcana",
            "desc":     "Un vial con energía arcana visible. Brilla levemente en la oscuridad.",
            "efecto":   "buff_stat",
            "potencia": 6,
            "stat_buff": "inteligencia",
            "duracion": 1500,
            "valor":    80,
        },
    },

    # ── Maestro ───────────────────────────────────────────────────────────
    "gran_elixir_vida": {
        "nombre":       "Gran Elixir de Vida",
        "descripcion":  "Restaura todos los puntos de vida de golpe.",
        "rango":        "maestro",
        "ingredientes": {"esencia vegetal": 2},
        "resultado": {
            "key":      "Gran Elixir de Vida",
            "desc":     "Un elixir dorado con destellos verdes. Calienta la mano al sostenerlo.",
            "efecto":   "curar_maximo",
            "potencia": 0,
            "stat_buff": "",
            "duracion": 0,
            "valor":    100,
        },
    },
    "elixir_maestro": {
        "nombre":       "Elixir del Maestro",
        "descripcion":  "Otorga +8 de fuerza durante 35 minutos.",
        "rango":        "maestro",
        "ingredientes": {"esencia vegetal": 1, "extracto raro": 1},
        "resultado": {
            "key":      "Elixir del Maestro",
            "desc":     "Un elixir rojo intenso. Quema la garganta al beberlo pero la potencia es sin igual.",
            "efecto":   "buff_stat",
            "potencia": 8,
            "stat_buff": "fuerza",
            "duracion": 2100,
            "valor":    130,
        },
    },
    "esencia_eternidad": {
        "nombre":       "Esencia de la Eternidad",
        "descripcion":  "Aumenta la experiencia ganada en combate un 25% durante 35 minutos.",
        "rango":        "maestro",
        "ingredientes": {"extracto raro": 2},
        "resultado": {
            "key":      "Esencia de la Eternidad",
            "desc":     "Una esencia translúcida que parece contener pequeñas constelaciones en su interior.",
            "efecto":   "buff_xp",
            "potencia": 0.25,
            "stat_buff": "",
            "duracion": 2100,
            "valor":    180,
        },
    },
}

# --------------------------------------------------------------------------- #
#  Funciones de rango
# --------------------------------------------------------------------------- #

def rango_desde_pociones(pociones: int) -> str:
    """Devuelve el rango alquímico según las pociones elaboradas."""
    if pociones >= POCIONES_POR_RANGO["maestro"]:
        return "maestro"
    if pociones >= POCIONES_POR_RANGO["artesano"]:
        return "artesano"
    return "aprendiz"


def pociones_para_siguiente_rango(rango: str) -> int | None:
    """Devuelve las pociones necesarias para el siguiente rango, o None si ya es maestro."""
    if rango == "aprendiz":
        return POCIONES_POR_RANGO["artesano"]
    if rango == "artesano":
        return POCIONES_POR_RANGO["maestro"]
    return None


def recetas_disponibles(rango: str) -> dict[str, dict]:
    """Devuelve solo las recetas accesibles para el rango dado."""
    orden = RANGOS.index(rango) if rango in RANGOS else 0
    return {
        rid: rec for rid, rec in RECETAS.items()
        if RANGOS.index(rec["rango"]) <= orden
    }

# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_elaborar(
    receta_id: str,
    rango: str,
    inventario: dict[str, int],
) -> tuple[bool, str]:
    """
    Comprueba si el jugador puede elaborar una receta.

    receta_id  — clave de RECETAS
    rango      — rango alquímico actual del jugador
    inventario — dict {nombre_item_lower: cantidad} (como en crafteo)
    """
    if receta_id not in RECETAS:
        return False, f"Receta '|w{receta_id}|n' desconocida. Usa |walquimia lista|n."

    receta = RECETAS[receta_id]
    rango_receta = receta["rango"]
    if RANGOS.index(rango_receta) > RANGOS.index(rango if rango in RANGOS else "aprendiz"):
        return False, (
            f"Esta receta requiere rango |w{rango_receta.capitalize()}|n. "
            f"Tu rango actual es |w{rango.capitalize()}|n."
        )

    faltantes = {}
    for ingr, cantidad_req in receta["ingredientes"].items():
        disponible = inventario.get(ingr.lower(), 0)
        if disponible < cantidad_req:
            faltantes[ingr] = cantidad_req - disponible

    if faltantes:
        falta_txt = ", ".join(f"|w{k}|n x{v}" for k, v in faltantes.items())
        return False, f"Te faltan ingredientes: {falta_txt}."

    return True, ""


def buscar_receta(texto: str) -> str | None:
    """Busca una receta por ID exacto o por nombre (prefijo insensible a mayúsculas)."""
    if texto in RECETAS:
        return texto
    texto_lower = texto.lower()
    candidatos = [
        rid for rid, rec in RECETAS.items()
        if rec["nombre"].lower().startswith(texto_lower) or texto_lower in rid
    ]
    if len(candidatos) == 1:
        return candidatos[0]
    return None

# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

_COLOR_RANGO = {"aprendiz": "|w", "artesano": "|c", "maestro": "|Y"}


def _color_rango(rango: str) -> str:
    return _COLOR_RANGO.get(rango, "|w")


def formatear_recetas(rango: str) -> str:
    """Muestra el libro de recetas con estado de desbloqueo."""
    sep = "|w" + "─" * 54 + "|n"
    pociones_sig = pociones_para_siguiente_rango(rango)
    lineas = [
        f"\n{sep}",
        f"  |cLibro de Alquimia|n  —  Rango: "
        f"{_color_rango(rango)}{rango.capitalize()}|n",
    ]
    if pociones_sig:
        lineas.append(f"  Siguiente rango en |w{pociones_sig}|n pociones elaboradas.")
    lineas.append(sep)

    rango_idx = RANGOS.index(rango) if rango in RANGOS else 0
    for rango_nombre in RANGOS:
        recetas_rango = [(rid, rec) for rid, rec in RECETAS.items() if rec["rango"] == rango_nombre]
        if not recetas_rango:
            continue
        cr = _color_rango(rango_nombre)
        accesible = RANGOS.index(rango_nombre) <= rango_idx
        prefijo = "|g✔|n" if accesible else "|x✗|n"
        lineas.append(f"\n  {cr}{rango_nombre.capitalize()}|n")
        for rid, rec in recetas_rango:
            ingr_txt = ", ".join(f"{n} ×{c}" for n, c in rec["ingredientes"].items())
            if accesible:
                lineas.append(f"    {prefijo} |w{rec['nombre']}|n  —  {rec['descripcion']}")
                lineas.append(f"         Ingredientes: {ingr_txt}")
            else:
                lineas.append(f"    {prefijo} |x{rec['nombre']}  —  {rec['descripcion']}|n")

    lineas.append(f"\n{sep}")
    lineas.append("  Usa |walquimia elaborar <receta>|n para crear una poción.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_info_receta(receta_id: str) -> str:
    if receta_id not in RECETAS:
        return f"|rReceta '|w{receta_id}|r' no encontrada.|n"
    rec = RECETAS[receta_id]
    sep = "|w" + "─" * 54 + "|n"
    ingr_txt = "\n".join(
        f"    • |w{n}|n ×{c}" for n, c in rec["ingredientes"].items()
    )
    cr = _color_rango(rec["rango"])
    return (
        f"\n{sep}\n"
        f"  |Y{rec['nombre']}|n  "
        f"[Rango: {cr}{rec['rango'].capitalize()}|n]\n"
        f"{sep}\n"
        f"  {rec['descripcion']}\n"
        f"\n  Ingredientes:\n{ingr_txt}\n"
        f"\n  Resultado: |w{rec['resultado']['key']}|n\n"
        f"{sep}\n"
    )
