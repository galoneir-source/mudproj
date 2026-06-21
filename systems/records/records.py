"""
systems/records/records.py

Lógica pura del sistema de récords globales.
Sin dependencias de Evennia.
"""

TOP_N = 5  # posiciones en cada categoría

CATEGORIAS = {
    "kills": {
        "titulo": "Guerrero Supremo",
        "descripcion": "kills totales",
        "icono": "|r⚔|n",
    },
    "misiones": {
        "titulo": "Aventurero Ejemplar",
        "descripcion": "misiones entregadas",
        "icono": "|y📜|n",
    },
    "jefes": {
        "titulo": "Cazador de Jefes",
        "descripcion": "jefes únicos derrotados",
        "icono": "|Y♦|n",
    },
    "duelos": {
        "titulo": "Duelista Invicto",
        "descripcion": "duelos ganados",
        "icono": "|c⚔|n",
    },
    "crafteo": {
        "titulo": "Gran Artesano",
        "descripcion": "objetos crafteados",
        "icono": "|g⚒|n",
    },
}

CAT_IDS = tuple(CATEGORIAS.keys())


# ---------------------------------------------------------------------------
# Extracción de stats desde datos de un personaje
# ---------------------------------------------------------------------------

def extraer_stat_kills(kills_totales) -> int:
    return int(kills_totales or 0)


def extraer_stat_misiones(quests_dict: dict) -> int:
    """Cuenta quests en estado 'entregada'."""
    if not quests_dict:
        return 0
    return sum(1 for q in quests_dict.values() if q.get("estado") == "entregada")


def extraer_stat_jefes(jefes_list) -> int:
    return len(list(jefes_list or []))


def extraer_stat_duelos(duelos_ganados) -> int:
    return int(duelos_ganados or 0)


def extraer_stat_crafteo(objetos_crafteados) -> int:
    return int(objetos_crafteados or 0)


_EXTRACTORES = {
    "kills":    lambda db: extraer_stat_kills(db.get("kills_totales")),
    "misiones": lambda db: extraer_stat_misiones(db.get("quests", {})),
    "jefes":    lambda db: extraer_stat_jefes(db.get("jefes_derrotados", [])),
    "duelos":   lambda db: extraer_stat_duelos(db.get("duelos_ganados")),
    "crafteo":  lambda db: extraer_stat_crafteo(db.get("objetos_crafteados")),
}


def extraer_stat(cat_id: str, db_dict: dict) -> int:
    """Extrae el valor de una categoría a partir de un dict de atributos."""
    extractor = _EXTRACTORES.get(cat_id)
    return extractor(db_dict) if extractor else 0


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------

def top_n(entradas: list, n: int = TOP_N) -> list:
    """
    Ordena una lista de (nombre, valor) de mayor a menor y devuelve los n primeros.
    """
    return sorted(entradas, key=lambda x: x[1], reverse=True)[:n]


# ---------------------------------------------------------------------------
# Formateo
# ---------------------------------------------------------------------------

def formatear_numero(valor: int) -> str:
    """Formatea un entero con separadores de miles (punto, convención española)."""
    return f"{valor:,}".replace(",", ".")


def formatear_posicion(pos: int, nombre: str, valor: int, ancho: int = 20) -> str:
    """Devuelve '  1. Nombre               1.247'"""
    return f"  {pos}. {nombre:<{ancho}} {formatear_numero(valor):>8}"


def tiempo_desde(ts: float, ahora: float) -> str:
    """Devuelve texto legible del tiempo transcurrido desde ts hasta ahora."""
    if not ts:
        return "desconocido"
    seg = int(ahora - ts)
    if seg < 60:
        return f"hace {seg}s"
    if seg < 3600:
        return f"hace {seg // 60} min"
    return f"hace {seg // 3600}h"
