"""
systems/mail/mail.py

Lógica pura del sistema de correo entre jugadores. Sin dependencias de Evennia.

Cada carta es un dict con los siguientes campos:
  id            str  — identificador único (timestamp + remitente)
  remitente     str  — nombre del remitente
  remitente_dbref str — dbref para devolver adjuntos si se borra sin reclamar
  mensaje       str  — cuerpo del mensaje
  fecha         str  — fecha/hora de envío (texto)
  monedas       int  — monedas adjuntas (0 si ninguna)
  objetos       list — [{"dbref": str, "nombre": str}]
  leida         bool — si ha sido abierta
  reclamado     bool — si el adjunto ya fue reclamado
"""
from __future__ import annotations
import time

MAX_CARTAS = 20   # máximo de cartas en el buzón


# --------------------------------------------------------------------------- #
#  Construcción
# --------------------------------------------------------------------------- #

def nueva_carta(
    remitente: str,
    remitente_dbref: str,
    mensaje: str,
    monedas: int = 0,
    objetos: list[dict] | None = None,
) -> dict:
    """Crea el dict de una carta nueva."""
    return {
        "id":              f"{int(time.time())}_{remitente_dbref}",
        "remitente":       remitente,
        "remitente_dbref": remitente_dbref,
        "mensaje":         mensaje.strip(),
        "fecha":           _formatear_fecha(time.time()),
        "monedas":         max(0, int(monedas)),
        "objetos":         list(objetos or []),
        "leida":           False,
        "reclamado":       False,
    }


def _formatear_fecha(ts: float) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%d/%m/%Y %H:%M")


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_recibir(bandeja: list) -> tuple[bool, str]:
    """Verifica que el buzón no esté lleno."""
    if len(bandeja) >= MAX_CARTAS:
        return False, (
            f"El buzón del destinatario está lleno "
            f"(máximo {MAX_CARTAS} cartas)."
        )
    return True, ""


def tiene_adjunto(carta: dict) -> bool:
    return bool(carta.get("objetos")) or carta.get("monedas", 0) > 0


def adjunto_pendiente(carta: dict) -> bool:
    """True si hay adjunto y aún no ha sido reclamado."""
    return tiene_adjunto(carta) and not carta.get("reclamado", False)


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_bandeja(cartas: list) -> str:
    if not cartas:
        return "|xTu buzón está vacío.|n"
    lineas = ["|wBuzón de correo:|n"]
    for i, carta in enumerate(cartas, 1):
        leida = " " if carta.get("leida") else "|Y●|n"
        adj = "|c[ADJ]|n" if adjunto_pendiente(carta) else "     "
        fecha = carta.get("fecha", "??")
        remitente = carta.get("remitente", "???")
        lineas.append(
            f"  {leida} |w{i:>2}.|n {adj} De: |c{remitente:<16}|n {fecha}"
        )
    lineas.append(
        f"\n|xTotal: {len(cartas)}/{MAX_CARTAS}. "
        f"Usa |wcorreo leer <N>|x para leer una carta.|n"
    )
    return "\n".join(lineas)


def formatear_carta(carta: dict, idx: int) -> str:
    leida_txt = "" if carta.get("leida") else " |Y[NUEVA]|n"
    lineas = [
        f"|c─────────── Carta {idx} ───────────|n{leida_txt}",
        f"|wDe:|n      {carta.get('remitente', '???')}",
        f"|wFecha:|n   {carta.get('fecha', '???')}",
        f"|c───────────────────────────|n",
        carta.get("mensaje", "(sin mensaje)"),
        f"|c───────────────────────────|n",
    ]
    # Adjuntos
    adj_lineas = []
    if carta.get("monedas", 0) > 0:
        adj_lineas.append(f"  |y{carta['monedas']} monedas|n")
    for obj in carta.get("objetos", []):
        adj_lineas.append(f"  · {obj['nombre']}")
    if adj_lineas:
        estado = "|x(ya reclamado)|n" if carta.get("reclamado") else "|g(pendiente)|n"
        lineas.append(f"|wAdjunto|n {estado}:")
        lineas.extend(adj_lineas)
        if not carta.get("reclamado"):
            lineas.append("|xUsa |wcorreo reclamar <N>|x para recibir el adjunto.|n")
    return "\n".join(lineas)


def formatear_notificacion(n_nuevas: int) -> str:
    if n_nuevas == 1:
        return "|Y● Tienes 1 carta nueva en tu buzón.|n Usa |wcorreo|n para leerla."
    return f"|Y● Tienes {n_nuevas} cartas nuevas en tu buzón.|n Usa |wcorreo|n para leerlas."


def contar_no_leidas(cartas: list) -> int:
    return sum(1 for c in cartas if not c.get("leida", False))
