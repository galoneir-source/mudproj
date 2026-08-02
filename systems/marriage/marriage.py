"""
systems/marriage/marriage.py

Lógica pura del sistema de matrimonio entre jugadores.
Sin dependencias de Evennia.

db.conyuge_dbref en Character: str | None — dbref del cónyuge actual.
db.fecha_boda en Character: float | None — timestamp (time.time()) de la boda.
db.propuesta_matrimonio en Character (destinatario): dict | None —
    {"proponente_dbref": str, "timestamp": float}

Relación 1-a-1, simétrica y consentida: proponer no basta, hace falta que
el otro acepte dentro del plazo. Un jugador solo puede tener un cónyuge
a la vez; para volver a casarse primero hay que divorciarse.
"""
from __future__ import annotations

TIMEOUT_PROPUESTA_SEGUNDOS = 120  # tiempo para aceptar/rechazar una propuesta


def propuesta_expirada(timestamp: float, ahora: float) -> bool:
    """Comprueba si una propuesta de matrimonio superó el plazo de respuesta."""
    return (ahora - timestamp) >= TIMEOUT_PROPUESTA_SEGUNDOS


def puede_proponer(
    propio_dbref: str,
    objetivo_dbref: str,
    propio_conyuge: str | None,
    objetivo_conyuge: str | None,
    tiene_propuesta_saliente: bool,
    objetivo_tiene_propuesta_entrante: bool,
) -> tuple[bool, str]:
    """Valida si `propio_dbref` puede proponerle matrimonio a `objetivo_dbref`."""
    if propio_dbref == objetivo_dbref:
        return False, "No puedes proponerte matrimonio a ti mismo."
    if propio_conyuge:
        return False, "Ya estás casado/a. Debes divorciarte antes de volver a proponer."
    if objetivo_conyuge:
        return False, "Esa persona ya está casada."
    if tiene_propuesta_saliente:
        return False, "Ya tienes una propuesta de matrimonio pendiente. Espera a que expire o sea respondida."
    if objetivo_tiene_propuesta_entrante:
        return False, "Esa persona ya tiene una propuesta de matrimonio pendiente."
    return True, ""


def puede_divorciarse(propio_conyuge: str | None) -> tuple[bool, str]:
    """Valida si se puede iniciar un divorcio."""
    if not propio_conyuge:
        return False, "No estás casado/a."
    return True, ""


def formatear_propuesta_recibida(nombre_proponente: str) -> str:
    """Mensaje enviado al destinatario de una propuesta."""
    return (
        f"\n|m💍 {nombre_proponente} te propone matrimonio!|n\n"
        f"  |waceptar boda|n  — aceptar\n"
        f"  |wrechazar boda|n — rechazar\n"
        f"(Tienes {TIMEOUT_PROPUESTA_SEGUNDOS} segundos para responder)\n"
    )


def formatear_boda(nombre_a: str, nombre_b: str) -> str:
    """Anuncio de boda, para difundir en la sala."""
    return f"|M💍 ¡{nombre_a} y {nombre_b} se han casado!|n"


def formatear_divorcio(nombre_a: str, nombre_b: str) -> str:
    """Anuncio de divorcio."""
    return f"|x{nombre_a} y {nombre_b} se han divorciado.|n"


def formatear_estado_civil(nombre_conyuge: str | None, fecha_boda_txt: str | None) -> str:
    """Texto del comando 'casado' sin argumentos, mostrando el estado civil propio."""
    if not nombre_conyuge:
        return "|xNo estás casado/a. Usa 'proponer <jugador>' para proponer matrimonio.|n"
    lineas = [f"|wEstás casado/a con {nombre_conyuge}.|n"]
    if fecha_boda_txt:
        lineas.append(f"|xCasados desde: {fecha_boda_txt}|n")
    return "\n".join(lineas)
