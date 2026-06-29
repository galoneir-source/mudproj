"""
systems/professions/professions.py

Lógica pura del sistema de profesiones. Sin dependencias de Evennia.

Tres profesiones de recolección:
  - mineria      → zonas de minas (boca_mina, galeria_principal, caverna_coloso)
  - herboristeria → zonas de bosque y pantano (bosque_norte, claro_bosque,
                    senda_fangosa, pantano_cenagoso, guarida_troll)
  - pesca        → zona de río (orilla_rio)

Cada profesión tiene 5 niveles. La XP necesaria es acumulada.
El nivel nunca baja aunque se pierda XP (no previsto actualmente).
"""
from __future__ import annotations
import random

# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

NIVEL_MAX = 5
NOMBRES_NIVEL = ["", "Aprendiz", "Novato", "Artesano", "Experto", "Maestro"]

# XP total acumulada necesaria para alcanzar cada nivel (índice = nivel objetivo).
XP_POR_NIVEL: list[int] = [0, 30, 80, 160, 300]

# Segundos de cooldown entre recolecciones de la misma profesión.
COOLDOWN_SEGUNDOS = 60

# Mapeo zona_id → (prof_id, nivel_mínimo_requerido).
ZONAS_RECURSO: dict[str, tuple[str, int]] = {
    "boca_mina":          ("mineria", 1),
    "galeria_principal":  ("mineria", 2),
    "caverna_coloso":     ("mineria", 3),
    "bosque_norte":       ("herboristeria", 1),
    "claro_bosque":       ("herboristeria", 1),
    "senda_fangosa":      ("herboristeria", 1),
    "pantano_cenagoso":   ("herboristeria", 2),
    "guarida_troll":      ("herboristeria", 3),
    "orilla_rio":         ("pesca", 1),
}

# --------------------------------------------------------------------------- #
#  Catálogo de profesiones
# --------------------------------------------------------------------------- #
#  Cada nivel lista tuplas (prototype_key, xp_ganada, peso_relativo).
#  Un mayor peso significa que ese material sale más a menudo.

PROFESIONES: dict[str, dict] = {
    "mineria": {
        "nombre": "Minería",
        "descripcion": "Extrae minerales y gemas de las profundidades.",
        "materiales": {
            1: [("MINERAL_HIERRO", 5, 10)],
            2: [("MINERAL_HIERRO", 5, 7), ("PIEDRA_AFILADA", 8, 3)],
            3: [("MINERAL_HIERRO", 5, 5), ("PIEDRA_AFILADA", 8, 4), ("MINERAL_PLATA", 12, 2)],
            4: [("PIEDRA_AFILADA", 8, 4), ("MINERAL_PLATA", 12, 4), ("GEMA_BRUTA", 18, 2)],
            5: [("MINERAL_PLATA", 12, 4), ("GEMA_BRUTA", 18, 4), ("GEMA_ARCANA", 25, 1)],
        },
    },
    "herboristeria": {
        "nombre": "Herboristería",
        "descripcion": "Recolecta plantas y hierbas con propiedades medicinales y mágicas.",
        "materiales": {
            1: [("HIERBA_MEDICINAL", 5, 10)],
            2: [("HIERBA_MEDICINAL", 5, 7), ("RAIZ_PANTANO", 8, 3)],
            3: [("HIERBA_MEDICINAL", 5, 4), ("RAIZ_PANTANO", 8, 4), ("FLOR_SILVESTRE", 12, 2)],
            4: [("RAIZ_PANTANO", 8, 3), ("FLOR_SILVESTRE", 12, 5), ("ESENCIA_VEGETAL", 18, 2)],
            5: [("FLOR_SILVESTRE", 12, 4), ("ESENCIA_VEGETAL", 18, 4), ("EXTRACTO_RARO", 25, 1)],
        },
    },
    "pesca": {
        "nombre": "Pesca",
        "descripcion": "Pesca en ríos y lagos para obtener recursos acuáticos.",
        "materiales": {
            1: [("PEZ_COMUN", 5, 10)],
            2: [("PEZ_COMUN", 5, 7), ("PEZ_PLATEADO", 8, 3)],
            3: [("PEZ_COMUN", 5, 4), ("PEZ_PLATEADO", 8, 4), ("PEZ_DORADO", 12, 2)],
            4: [("PEZ_PLATEADO", 8, 3), ("PEZ_DORADO", 12, 5), ("PERLA_RIO", 18, 2)],
            5: [("PEZ_DORADO", 12, 4), ("PERLA_RIO", 18, 4), ("ESCAMA_MAGICA", 25, 1)],
        },
    },
}

# --------------------------------------------------------------------------- #
#  Funciones de nivel
# --------------------------------------------------------------------------- #

def nivel_desde_xp(xp: int) -> int:
    nivel = 1
    for i, xp_req in enumerate(XP_POR_NIVEL):
        if xp >= xp_req:
            nivel = i + 1
    return min(nivel, NIVEL_MAX)


def xp_para_siguiente(nivel: int) -> int | None:
    """XP total necesaria para alcanzar nivel+1, o None si ya es NIVEL_MAX."""
    if nivel >= NIVEL_MAX:
        return None
    return XP_POR_NIVEL[nivel]


# --------------------------------------------------------------------------- #
#  Obtener material a recolectar
# --------------------------------------------------------------------------- #

def elegir_material(prof_id: str, nivel: int) -> tuple[str, int]:
    """
    Elige un material de la lista del nivel usando pesos.
    Devuelve (prototype_key, xp_ganada).
    """
    opciones = PROFESIONES.get(prof_id, {}).get("materiales", {}).get(nivel, [])
    if not opciones:
        return "", 0
    keys = [o[0] for o in opciones]
    xps  = [o[1] for o in opciones]
    pesos = [o[2] for o in opciones]
    idx = random.choices(range(len(opciones)), weights=pesos, k=1)[0]
    return keys[idx], xps[idx]


# --------------------------------------------------------------------------- #
#  Lógica sobre el personaje (solo dicts, sin Evennia)
# --------------------------------------------------------------------------- #

def aprender_profesion(profesiones: dict, prof_id: str) -> tuple[bool, str]:
    if prof_id not in PROFESIONES:
        return False, "Profesión desconocida."
    if prof_id in profesiones:
        return False, f"Ya conoces la profesión de {PROFESIONES[prof_id]['nombre']}."
    profesiones[prof_id] = {"nivel": 1, "xp": 0}
    return True, PROFESIONES[prof_id]["nombre"]


def ganar_xp(profesiones: dict, prof_id: str, xp_ganada: int) -> tuple[int, bool]:
    """
    Añade XP a la profesión indicada.
    Devuelve (nivel_nuevo, subio_nivel).
    """
    datos = profesiones.get(prof_id)
    if not datos:
        return 1, False
    nivel_antes = datos["nivel"]
    datos["xp"] = datos.get("xp", 0) + xp_ganada
    nivel_nuevo = nivel_desde_xp(datos["xp"])
    datos["nivel"] = nivel_nuevo
    return nivel_nuevo, nivel_nuevo > nivel_antes


def zona_a_profesion(zona_id: str) -> tuple[str | None, int]:
    """Dado un zona_id devuelve (prof_id, nivel_min) o (None, 0)."""
    entry = ZONAS_RECURSO.get(zona_id)
    if not entry:
        return None, 0
    return entry


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_profesion(prof_id: str, datos: dict) -> str:
    info = PROFESIONES.get(prof_id, {})
    nivel = datos.get("nivel", 1)
    xp = datos.get("xp", 0)
    xp_sig = xp_para_siguiente(nivel)
    nombre_nv = NOMBRES_NIVEL[nivel]

    if xp_sig is None:
        progreso = "|yMAESTRO|n"
    else:
        barra_len = 10
        fraccion = (xp - XP_POR_NIVEL[nivel - 1]) / (xp_sig - XP_POR_NIVEL[nivel - 1])
        llenos = int(fraccion * barra_len)
        barra = "|g" + "#" * llenos + "|x" + "-" * (barra_len - llenos) + "|n"
        progreso = f"{barra} |w{xp}|n/|w{xp_sig}|n XP"

    return f"  |c{info.get('nombre', prof_id)}|n — {nombre_nv} (Nv.|w{nivel}|n) {progreso}"


def formatear_todas(profesiones: dict) -> str:
    if not profesiones:
        return "  |xNinguna profesión aprendida.|n"
    return "\n".join(
        formatear_profesion(pid, datos)
        for pid, datos in profesiones.items()
    )


def lista_disponibles() -> str:
    return ", ".join(
        f"|c{d['nombre']}|n (|w{pid}|n)" for pid, d in PROFESIONES.items()
    )
