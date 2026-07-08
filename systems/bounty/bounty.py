"""
systems/bounty/bounty.py

Lógica pura del sistema de cazarrecompensas. Sin dependencias de Evennia.

Las recompensas se almacenan globalmente en RecompensasScript (features).
Cada entrada es un dict:
  {
    "objetivo_dbref":  str   — dbref del jugador buscado
    "objetivo_nombre": str   — nombre para mostrar
    "emisor_dbref":    str   — dbref de quien puso la recompensa
    "emisor_nombre":   str   — nombre para mostrar
    "recompensa":      int   — monedas ofrecidas
    "fecha":           float — unix timestamp
  }

db.recompensas_cobradas  en Character: int — recompensas cobradas (cazando)
db.recompensas_recibidas en Character: int — veces que alguien puso precio a su cabeza
"""
from __future__ import annotations
import time as _time

MIN_RECOMPENSA = 100
MAX_RECOMPENSA = 5_000


# --------------------------------------------------------------------------- #
#  Consultas
# --------------------------------------------------------------------------- #

def hay_recompensa(objetivo_dbref: str, bounties: list) -> bool:
    """True si hay al menos una recompensa activa sobre el objetivo."""
    return any(b["objetivo_dbref"] == objetivo_dbref for b in bounties)


def bounties_sobre(objetivo_dbref: str, bounties: list) -> list:
    """Devuelve todas las recompensas activas sobre un objetivo."""
    return [b for b in bounties if b["objetivo_dbref"] == objetivo_dbref]


def total_sobre_objetivo(objetivo_dbref: str, bounties: list) -> int:
    """Suma total de monedas ofrecidas sobre un objetivo."""
    return sum(b["recompensa"] for b in bounties if b["objetivo_dbref"] == objetivo_dbref)


def bounties_de_emisor(emisor_dbref: str, bounties: list) -> list:
    """Devuelve todas las recompensas que un emisor ha puesto."""
    return [b for b in bounties if b["emisor_dbref"] == emisor_dbref]


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_poner(
    emisor_dbref: str,
    objetivo_dbref: str,
    monedas: int,
    cantidad: int,
    bounties: list,
) -> tuple[bool, str]:
    """Comprueba si el emisor puede poner una recompensa sobre el objetivo."""
    if emisor_dbref == objetivo_dbref:
        return False, "No puedes poner una recompensa sobre ti mismo."
    if cantidad < MIN_RECOMPENSA:
        return False, f"La recompensa mínima es |w{MIN_RECOMPENSA}|n monedas."
    if cantidad > MAX_RECOMPENSA:
        return False, f"La recompensa máxima es |w{MAX_RECOMPENSA}|n monedas."
    if cantidad > monedas:
        return False, f"No tienes suficientes monedas (tienes |w{monedas}|n)."
    ya = any(
        b["emisor_dbref"] == emisor_dbref and b["objetivo_dbref"] == objetivo_dbref
        for b in bounties
    )
    if ya:
        return False, "Ya tienes una recompensa activa sobre ese jugador."
    return True, ""


def puede_cancelar(
    emisor_dbref: str,
    objetivo_dbref: str,
    bounties: list,
) -> tuple[bool, str]:
    """Comprueba si el emisor puede cancelar su recompensa sobre el objetivo."""
    tiene = any(
        b["emisor_dbref"] == emisor_dbref and b["objetivo_dbref"] == objetivo_dbref
        for b in bounties
    )
    if not tiene:
        return False, "No tienes ninguna recompensa activa sobre ese jugador."
    return True, ""


# --------------------------------------------------------------------------- #
#  Mutaciones (devuelven listas nuevas, no modifican la original)
# --------------------------------------------------------------------------- #

def añadir_bounty(bounties: list, nueva: dict) -> list:
    """Añade una recompensa y devuelve la lista nueva."""
    return list(bounties) + [dict(nueva)]


def cobrar_bounties(bounties: list, objetivo_dbref: str) -> tuple[list, int]:
    """
    Elimina todas las recompensas sobre el objetivo y devuelve
    (lista_nueva, total_cobrado).
    """
    cobradas = [b for b in bounties if b["objetivo_dbref"] == objetivo_dbref]
    restantes = [b for b in bounties if b["objetivo_dbref"] != objetivo_dbref]
    total = sum(b["recompensa"] for b in cobradas)
    return restantes, total


def cancelar_bounty(
    bounties: list, emisor_dbref: str, objetivo_dbref: str
) -> tuple[list, int]:
    """
    Cancela la recompensa del emisor sobre el objetivo.
    Devuelve (lista_nueva, cantidad_reembolsada).
    """
    cancelada = next(
        (b for b in bounties
         if b["emisor_dbref"] == emisor_dbref and b["objetivo_dbref"] == objetivo_dbref),
        None,
    )
    if not cancelada:
        return list(bounties), 0
    nueva = [
        b for b in bounties
        if not (b["emisor_dbref"] == emisor_dbref and b["objetivo_dbref"] == objetivo_dbref)
    ]
    return nueva, cancelada["recompensa"]


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def _tiempo_desde(ts: float) -> str:
    delta = _time.time() - ts
    if delta < 120:
        return "hace un momento"
    if delta < 3600:
        return f"hace {int(delta // 60)} min"
    if delta < 86400:
        return f"hace {int(delta // 3600)}h"
    return f"hace {int(delta // 86400)} días"


def formatear_tablon(bounties: list) -> str:
    """Muestra todas las recompensas activas ordenadas por total."""
    sep = "|w" + "─" * 54 + "|n"
    if not bounties:
        return f"\n{sep}\n  |cTablero de Recompensas|n  —  Sin recompensas activas.\n{sep}\n"

    # Agrupar por objetivo
    objetivos: dict[str, dict] = {}
    for b in bounties:
        key = b["objetivo_dbref"]
        if key not in objetivos:
            objetivos[key] = {"nombre": b["objetivo_nombre"], "total": 0, "emisores": []}
        objetivos[key]["total"] += b["recompensa"]
        objetivos[key]["emisores"].append(b["emisor_nombre"])

    # Ordenar por total descendente
    ordenados = sorted(objetivos.items(), key=lambda x: x[1]["total"], reverse=True)

    lineas = [f"\n{sep}", f"  |cTablero de Recompensas|n  ({len(objetivos)} objetivo/s)", sep]
    for i, (dbref, datos) in enumerate(ordenados, 1):
        emisores_txt = ", ".join(datos["emisores"][:3])
        if len(datos["emisores"]) > 3:
            emisores_txt += f" (+{len(datos['emisores'])-3} más)"
        lineas.append(
            f"  |Y#{i}|n |w{datos['nombre']}|n — "
            f"|r{datos['total']} monedas|n  "
            f"|x(por: {emisores_txt})|n"
        )
    lineas.append(f"\n  Usa |wcazar <jugador>|n para intentar cobrar una recompensa.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_mi_estado(bounties: list, jugador_dbref: str, nombre: str) -> str:
    """Muestra las recompensas puestas por el jugador y las que hay sobre él."""
    sep = "|w" + "─" * 54 + "|n"
    puestas = bounties_de_emisor(jugador_dbref, bounties)
    sobre_mi = bounties_sobre(jugador_dbref, bounties)
    total_sobre = total_sobre_objetivo(jugador_dbref, bounties)

    lineas = [f"\n{sep}", f"  |cMis Recompensas|n — {nombre}", sep]

    if sobre_mi:
        lineas.append(f"\n  |r¡Tienes precio en tu cabeza!|n  Total: |r{total_sobre} monedas|n")
        for b in sobre_mi:
            lineas.append(
                f"    |x•|n |w{b['emisor_nombre']}|n ofrece "
                f"|r{b['recompensa']} m|n  ({_tiempo_desde(b['fecha'])})"
            )
    else:
        lineas.append("\n  Nadie ha puesto precio a tu cabeza.")

    if puestas:
        lineas.append(f"\n  Recompensas que tú has puesto ({len(puestas)}):")
        for b in puestas:
            lineas.append(
                f"    |x•|n Sobre |w{b['objetivo_nombre']}|n: "
                f"|y{b['recompensa']} m|n  ({_tiempo_desde(b['fecha'])})"
            )
    else:
        lineas.append("\n  No has puesto ninguna recompensa.")

    lineas.append(f"\n  Usa |wrecompensa poner <jugador> <cantidad>|n para poner una.")
    lineas.append(f"  Usa |wrecompensa cancelar <jugador>|n para retirar la tuya.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)
