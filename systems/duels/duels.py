"""
systems/duels/duels.py

Lógica pura de duelos entre jugadores.
Sin dependencias de Evennia.
"""

DUEL_TIMEOUT = 60       # segundos para aceptar un reto
HP_DUEL_MIN_PCT = 0.10  # % de HP al que se detiene el duelo


def validar_apuesta(monedas_retador: int, monedas_retado: int, apuesta: int) -> tuple:
    """
    Valida que ambos jugadores tengan fondos suficientes para la apuesta.
    Devuelve (True, "") si es válida, (False, motivo) si no.
    """
    if apuesta < 0:
        return False, "La apuesta no puede ser negativa."
    if apuesta == 0:
        return True, ""
    if monedas_retador < apuesta:
        return False, f"No tienes suficientes monedas (necesitas {apuesta})."
    if monedas_retado < apuesta:
        return False, f"Tu rival no tiene suficientes monedas (necesita {apuesta})."
    return True, ""


def calcular_hp_umbral(hp_max: int) -> int:
    """Devuelve el HP umbral al que se detiene el duelo (10% del máximo, mínimo 1)."""
    return max(1, int(hp_max * HP_DUEL_MIN_PCT))


def formatear_resultado(ganador_key: str, perdedor_key: str, apuesta: int) -> str:
    """Genera el mensaje de resultado del duelo."""
    lineas = [
        "\n|Y🏆 ¡DUELO TERMINADO!|n",
        f"|w{ganador_key}|n ha vencido a |w{perdedor_key}|n.",
    ]
    if apuesta:
        lineas.append(
            f"|y{perdedor_key}|n paga |Y{apuesta} monedas|n a |y{ganador_key}|n."
        )
    return "\n".join(lineas) + "\n"


def reto_expirado(timestamp: float, ahora: float) -> bool:
    """Comprueba si un reto ha superado el tiempo límite de aceptación."""
    return (ahora - timestamp) >= DUEL_TIMEOUT
