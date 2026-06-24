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

# Evolución
XP_NIVEL_2 = 50        # XP acumulada para evolucionar a nivel 2
XP_NIVEL_3 = 150       # XP acumulada total para evolucionar a nivel 3
NIVEL_MAX_MASCOTA = 3

_XP_UMBRAL: dict[int, int] = {1: XP_NIVEL_2, 2: XP_NIVEL_3}
_MULT_NIVEL: dict[int, float] = {1: 1.0, 2: 1.5, 3: 2.5}
_PREFIJO_NIVEL: dict[int, str] = {2: "Mayor", 3: "Élite"}


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


def xp_para_siguiente_nivel(nivel: int) -> int | None:
    """XP acumulada necesaria para el siguiente nivel. None si ya es nivel máximo."""
    return _XP_UMBRAL.get(nivel)


def _especie_evolucionada(especie_base: str, nivel: int) -> str:
    """Nombre de especie según el nivel de evolución."""
    prefijo = _PREFIJO_NIVEL.get(nivel, "")
    return f"{especie_base} {prefijo}".strip() if prefijo else especie_base


def calcular_evolucion(mascota: dict, xp_ganada: int) -> tuple[dict, bool]:
    """
    Añade xp_ganada al mascota y aplica evoluciones si se alcanzan los umbrales.
    Devuelve (nuevo_dict, evolucionó).
    """
    m = dict(mascota)
    m["xp"] = int(m.get("xp", 0)) + xp_ganada
    evolucionado = False

    while True:
        nivel = int(m.get("nivel", 1))
        umbral = _XP_UMBRAL.get(nivel)
        if umbral is None or m["xp"] < umbral:
            break
        nuevo_nivel = nivel + 1
        ratio = _MULT_NIVEL[nuevo_nivel] / _MULT_NIVEL[nivel]
        m["ataque"] = max(1, int(m.get("ataque", 1) * ratio))
        m["defensa"] = max(0, int(m.get("defensa", 0) * ratio))
        nuevo_hp_max = max(1, int(m.get("hp_max", 1) * ratio))
        m["hp_max"] = nuevo_hp_max
        m["hp"] = nuevo_hp_max
        m["nivel"] = nuevo_nivel
        m["especie"] = _especie_evolucionada(
            m.get("especie_base", m.get("especie", "?")), nuevo_nivel
        )
        evolucionado = True

    return m, evolucionado


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
        "especie_base": especie,
        "nivel": 1,
        "xp": 0,
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
    nivel = int(mascota.get("nivel", 1))
    xp = int(mascota.get("xp", 0))
    desc_vinculo = vinculo_descripcion(vinculo)

    umbral = xp_para_siguiente_nivel(nivel)
    if umbral is not None:
        xp_txt = f"{xp}/{umbral} XP"
    else:
        xp_txt = f"{xp} XP (MAX)"

    lineas = [
        f"\n|w── Mascota: {nombre} ──|n",
        f"  Especie  : {especie}",
        f"  Nivel    : {nivel}  ({xp_txt})",
        f"  HP       : {hp}/{hp_max}",
        f"  Ataque   : {ataque}",
        f"  Defensa  : {defensa}",
        f"  Vínculo  : {vinculo}/{VINCULO_MAX}  ({desc_vinculo})",
    ]
    return "\n".join(lineas) + "\n"
