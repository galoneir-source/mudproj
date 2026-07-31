"""
systems/bulletin/bulletin.py

Lógica pura del tablón de anuncios global. Sin dependencias de Evennia.

Distinto del tablón de contratos (features/contracts/, comando 'tablón'):
este es un tablón libre donde cualquier jugador publica un mensaje corto
(venta, aviso de gremio, mensaje general), no misiones generadas por el
servidor. Comando de juego: 'cartelera'.

Cada anuncio es un dict con los siguientes campos:
  id            str   — identificador único (timestamp + autor_dbref)
  autor         str   — nombre del autor
  autor_dbref   str   — dbref del autor (para permisos de retiro)
  texto         str   — cuerpo del anuncio
  timestamp     float — momento de publicación (unix time)
  fecha         str   — fecha/hora de publicación (texto)
"""
from __future__ import annotations
import time

MAX_ANUNCIOS = 15                  # capacidad total del tablón
MAX_LONGITUD_TEXTO = 200           # caracteres por anuncio
DURACION_SEGUNDOS = 3 * 24 * 3600  # 3 días de vigencia


# --------------------------------------------------------------------------- #
#  Construcción
# --------------------------------------------------------------------------- #

def crear_anuncio(autor: str, autor_dbref: str, texto: str) -> dict:
    """Crea el dict de un anuncio nuevo."""
    ahora = time.time()
    return {
        "id":          f"{int(ahora)}_{autor_dbref}",
        "autor":       autor,
        "autor_dbref": autor_dbref,
        "texto":       texto.strip(),
        "timestamp":   ahora,
        "fecha":       _formatear_fecha(ahora),
    }


def _formatear_fecha(ts: float) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%d/%m/%Y %H:%M")


# --------------------------------------------------------------------------- #
#  Vigencia
# --------------------------------------------------------------------------- #

def anuncios_vigentes(anuncios: list, ahora: float | None = None) -> list:
    """Devuelve solo los anuncios cuyo plazo de vigencia no ha pasado."""
    if ahora is None:
        ahora = time.time()
    return [a for a in anuncios if ahora - a.get("timestamp", 0) < DURACION_SEGUNDOS]


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_publicar(anuncios_vigentes_actuales: list, texto: str) -> tuple[bool, str]:
    """Valida capacidad del tablón y longitud del texto."""
    texto = (texto or "").strip()
    if not texto:
        return False, "El anuncio no puede estar vacío."
    if len(texto) > MAX_LONGITUD_TEXTO:
        return False, f"El anuncio es demasiado largo (máximo {MAX_LONGITUD_TEXTO} caracteres)."
    if len(anuncios_vigentes_actuales) >= MAX_ANUNCIOS:
        return False, (
            f"La cartelera está llena (máximo {MAX_ANUNCIOS} anuncios vigentes). "
            "Espera a que expire alguno o pide a su autor que lo retire."
        )
    return True, ""


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_cartelera(anuncios: list) -> str:
    if not anuncios:
        return (
            "\n|w── Cartelera de la Ciudad ──|n\n"
            "  No hay anuncios vigentes.\n"
            "  Usa |wcartelera publicar <texto>|n para publicar uno.\n"
        )
    lineas = ["\n|w── Cartelera de la Ciudad ──|n"]
    for i, anuncio in enumerate(sorted(anuncios, key=lambda a: -a.get("timestamp", 0)), 1):
        lineas.append(
            f"  |w{i:>2}.|n |c{anuncio.get('autor', '???'):<16}|n "
            f"({anuncio.get('fecha', '??')})\n"
            f"      {anuncio.get('texto', '')}"
        )
    lineas.append(
        f"\n|xTotal: {len(anuncios)}/{MAX_ANUNCIOS}. "
        f"Usa |wcartelera retirar <#>|n para quitar el tuyo.|n\n"
    )
    return "\n".join(lineas)
