"""
systems/events/events.py

Catálogo puro de eventos mundiales y lógica de selección aleatoria.
Sin dependencias de Evennia.

Cada evento tiene:
  nombre          str   — nombre para mostrar al jugador
  descripcion     str   — explicación breve del efecto
  duracion        int   — segundos que dura el evento
  intervalo_min   int   — segundos mínimos entre repeticiones del mismo evento
  peso            int   — probabilidad relativa (mayor peso = más frecuente)
  color           str   — color Evennia para anuncios
  efectos         dict  — efectos mecánicos (ver keys documentadas abajo)
  mensaje_inicio  str   — broadcast al comenzar
  mensaje_fin     str   — broadcast al terminar

Efectos posibles:
  xp_factor              float  — multiplicador de XP para facciones_afectadas
  facciones_afectadas    list   — faccion_ids donde aplica xp_factor
  descuento_tienda       float  — fracción de descuento (0.20 = 20% menos)
  bonus_inteligencia     int    — puntos extra de INT para jugadores en combate
"""
from __future__ import annotations

EVENTOS: dict[str, dict] = {
    "invasion_no_muertos": {
        "nombre":        "Invasión de No-Muertos",
        "descripcion":   "La Legión Oscura avanza. Doble XP al derrotar a sus siervos.",
        "duracion":      1200,    # 20 minutos reales
        "intervalo_min": 7200,    # mínimo 2 horas entre repeticiones
        "peso":          3,
        "color":         "|r",
        "efectos": {
            "xp_factor":           2.0,
            "facciones_afectadas": ["legion_oscura"],
        },
        "mensaje_inicio": (
            "|r⚠  ¡INVASIÓN DE NO-MUERTOS!|n\n"
            "La Legión Oscura avanza sobre las tierras vivas. Los no-muertos se multiplican.\n"
            "|r¡DOBLE XP al derrotar a los siervos de la Legión Oscura durante 20 minutos!|n"
        ),
        "mensaje_fin": (
            "|yLa invasión de no-muertos ha sido contenida... por ahora.|n\n"
            "Los XP vuelven a la normalidad."
        ),
    },

    "feria_mercado": {
        "nombre":        "Feria del Mercado",
        "descripcion":   "Los mercaderes celebran la feria estacional. Precios reducidos un 20%.",
        "duracion":      900,     # 15 minutos reales
        "intervalo_min": 10800,   # mínimo 3 horas entre repeticiones
        "peso":          2,
        "color":         "|g",
        "efectos": {
            "descuento_tienda": 0.20,
        },
        "mensaje_inicio": (
            "|g🛒 ¡FERIA DEL MERCADO!|n\n"
            "Los comerciantes celebran la feria estacional.\n"
            "|g¡20% de descuento en todos los artículos durante 15 minutos!|n"
        ),
        "mensaje_fin": (
            "|yLa Feria del Mercado ha terminado.|n\n"
            "Los precios vuelven a la normalidad."
        ),
    },

    "tormenta_magica": {
        "nombre":        "Tormenta Mágica",
        "descripcion":   "Energía arcana inunda el mundo. Todos los aventureros reciben +3 INT en combate.",
        "duracion":      600,     # 10 minutos reales
        "intervalo_min": 14400,   # mínimo 4 horas entre repeticiones
        "peso":          1,
        "color":         "|c",
        "efectos": {
            "bonus_inteligencia": 3,
        },
        "mensaje_inicio": (
            "|c⚡ ¡TORMENTA MÁGICA!|n\n"
            "Una tormenta de energía arcana azota el mundo.\n"
            "|c¡Todos los aventureros reciben +3 Inteligencia en combate durante 10 minutos!|n"
        ),
        "mensaje_fin": (
            "|yLa tormenta mágica se disipa.|n\n"
            "La energía arcana vuelve a la normalidad."
        ),
    },
}


# ---------------------------------------------------------------------------
# Lógica pura de selección
# ---------------------------------------------------------------------------

def eventos_elegibles(ultimo_por_evento: dict, ahora: float) -> list[tuple[str, int]]:
    """
    Devuelve los eventos cuyos cooldowns han pasado.

    ultimo_por_evento: {event_id: timestamp_fin_ultimo}
    ahora: timestamp Unix actual

    Retorna lista de (event_id, peso) ordenada como en EVENTOS.
    """
    result = []
    for ev_id, ev in EVENTOS.items():
        ultimo_fin = ultimo_por_evento.get(ev_id, 0.0)
        if ahora - ultimo_fin >= ev["intervalo_min"]:
            result.append((ev_id, ev["peso"]))
    return result


def elegir_evento(elegibles: list[tuple[str, int]], r: float) -> str | None:
    """
    Selección ponderada dado r ∈ [0, 1).

    r se escala al peso total: elegibles con mayor peso tienen más probabilidad.
    Devuelve event_id o None si elegibles está vacío.
    """
    if not elegibles:
        return None
    total = sum(p for _, p in elegibles)
    if total <= 0:
        return None
    umbral = r * total
    acum = 0.0
    for ev_id, peso in elegibles:
        acum += peso
        if umbral < acum:
            return ev_id
    return elegibles[-1][0]
