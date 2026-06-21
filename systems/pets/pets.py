"""
systems/pets/pets.py

Lógica pura del sistema de mascotas de combate (sin dependencias de Evennia).
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #

VINCULO_MAX = 100
VINCULO_MIN = 0
CAPTURA_HP_PCT = 0.20       # HP máximo para poder capturar (20%)
VINCULO_SUBE_VICTORIA = 5   # vínculo ganado por cada kill con mascota presente
COSTE_ALIMENTAR = 10        # monedas para alimentar a la mascota
VINCULO_SUBE_ALIMENTAR = 10 # vínculo ganado al alimentar


# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def puede_capturar(hp_actual: int, hp_max: int) -> bool:
    """True si la criatura tiene ≤ 20 % de HP (apta para captura)."""
    if hp_max <= 0:
        return False
    return (hp_actual / hp_max) <= CAPTURA_HP_PCT


def calcular_daño_mascota(vinculo: int, ataque_base: int) -> int:
    """
    Daño de la mascota por turno.
    Escala desde 50 % del ataque base (vínculo 0) hasta 100 % (vínculo 100).
    """
    v = max(VINCULO_MIN, min(VINCULO_MAX, int(vinculo or 0)))
    factor = 0.5 + v / 200.0
    return max(1, int(ataque_base * factor))


def calcular_nuevo_vinculo(vinculo_actual: int, delta: int) -> int:
    """Aplica delta al vínculo, clampeado entre VINCULO_MIN y VINCULO_MAX."""
    return max(VINCULO_MIN, min(VINCULO_MAX, int(vinculo_actual or 0) + delta))


def vinculo_descripcion(vinculo: int) -> str:
    """Descripción cualitativa del nivel de vínculo."""
    v = int(vinculo or 0)
    if v < 25:
        return "Indiferente"
    if v < 50:
        return "Amistoso"
    if v < 80:
        return "Leal"
    return "Devoto"


def datos_mascota_desde_criatura(
    nombre: str,
    especie: str,
    hp_max: int,
    ataque: int,
    defensa: int,
    vinculo_inicial: int = 10,
) -> dict:
    """Construye el dict de mascota al capturarla (HP restaurado al máximo)."""
    return {
        "nombre": nombre,
        "especie": especie,
        "vinculo": max(VINCULO_MIN, min(VINCULO_MAX, vinculo_inicial)),
        "hp": int(hp_max),
        "hp_max": int(hp_max),
        "ataque": int(ataque),
        "defensa": int(defensa),
    }


def formatear_mascota(mascota: dict) -> str:
    """Líneas de resumen para mostrar al jugador."""
    nombre = mascota.get("nombre", "?")
    especie = mascota.get("especie", "?")
    vinculo = int(mascota.get("vinculo", 0))
    hp = mascota.get("hp", 0)
    hp_max = mascota.get("hp_max", 1)
    ataque = mascota.get("ataque", 0)
    defensa = mascota.get("defensa", 0)
    desc_vinculo = vinculo_descripcion(vinculo)

    lineas = [
        f"\n|w── Mascota: {nombre} ──|n",
        f"  Especie  : {especie}",
        f"  HP       : {hp}/{hp_max}",
        f"  Ataque   : {ataque}",
        f"  Defensa  : {defensa}",
        f"  Vínculo  : {vinculo}/{VINCULO_MAX}  ({desc_vinculo})",
    ]
    return "\n".join(lineas) + "\n"
