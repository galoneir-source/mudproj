"""
sistemas/buffs/buffs.py — Lógica pura de buffs temporales.

Cada buff se almacena en db.buffs_activos como:
    {"tipo": "buff_stat"|"buff_xp",
     "bonus": int|float,
     "expira": float,   # unix timestamp
     "nombre": str,
     "stat": str}       # sólo en buff_stat ("fuerza"|"destreza"|"inteligencia")
"""

import time

_STATS_BUFF = ("fuerza", "destreza", "inteligencia")


def buffs_vigentes(buffs_lista: list) -> list:
    """Devuelve sólo los buffs cuyo timestamp de expiración no ha pasado."""
    ahora = time.time()
    return [b for b in buffs_lista if b.get("expira", 0) > ahora]


def aplicar_buff(buffs_lista: list, tipo: str, bonus, nombre: str,
                 duracion: int, stat: str = "") -> list:
    """
    Añade (o sobreescribe) un buff del mismo tipo+stat a la lista.
    Devuelve la nueva lista filtrada y con el buff añadido.
    """
    ahora = time.time()
    # Eliminar buff previo del mismo tipo (y stat si aplica)
    nueva = [
        b for b in buffs_lista
        if not (b.get("tipo") == tipo and b.get("stat", "") == stat)
    ]
    entrada = {
        "tipo": tipo,
        "bonus": bonus,
        "expira": ahora + duracion,
        "nombre": nombre,
        "stat": stat,
    }
    nueva.append(entrada)
    return nueva


def bonus_stat(buffs_lista: list, stat: str) -> int:
    """Suma de bonuses activos de tipo buff_stat para la estadística dada."""
    vigentes = buffs_vigentes(buffs_lista)
    return sum(
        b["bonus"] for b in vigentes
        if b.get("tipo") == "buff_stat" and b.get("stat") == stat
    )


def factor_xp(buffs_lista: list) -> float:
    """Multiplicador de XP basado en buffs_xp activos (1.0 si no hay ninguno)."""
    vigentes = buffs_vigentes(buffs_lista)
    factor = 1.0
    for b in vigentes:
        if b.get("tipo") == "buff_xp":
            factor += b["bonus"]
    return factor


def hay_buffs(buffs_lista: list) -> bool:
    return bool(buffs_vigentes(buffs_lista))


def formatear_buffs(buffs_lista: list) -> list[str]:
    """Devuelve lista de strings legibles con tiempo restante para cada buff activo."""
    ahora = time.time()
    vigentes = buffs_vigentes(buffs_lista)
    if not vigentes:
        return []
    lineas = []
    for b in vigentes:
        resto = int(b["expira"] - ahora)
        minutos = resto // 60
        segundos = resto % 60
        nombre = b.get("nombre", b.get("tipo", "?"))
        if b["tipo"] == "buff_stat":
            stat = b.get("stat", "?")
            lineas.append(f"|c{nombre}|n: +{b['bonus']} {stat} ({minutos}m {segundos}s)")
        else:
            pct = int(b["bonus"] * 100)
            lineas.append(f"|c{nombre}|n: +{pct}% XP ({minutos}m {segundos}s)")
    return lineas
