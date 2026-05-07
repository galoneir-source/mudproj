"""
systems/combat/engine.py

Motor de combate puro (sin dependencias de Evennia).
Contiene la lógica de resolución de ataques, daño y estados.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
#  Constantes de combate
# --------------------------------------------------------------------------- #

STAT_DEFAULTS = {
    "fuerza": 10,
    "destreza": 10,
    "constitucion": 10,
    "inteligencia": 10,
    "defensa": 5,
    "hp_max": 100,
    "hp": 100,
    "nivel": 1,
    "experiencia": 0,
}

# XP necesaria para subir de nivel (por nivel)
XP_POR_NIVEL = [0, 100, 250, 500, 900, 1400, 2100, 3000, 4200, 5700, 7500]

# Probabilidad base de golpe crítico
CRITICO_BASE = 0.10

# Multiplicador de daño crítico
CRITICO_MULT = 2.0


# --------------------------------------------------------------------------- #
#  Dataclass de resultado de ataque
# --------------------------------------------------------------------------- #

@dataclass
class ResultadoAtaque:
    exito: bool
    dano: int
    critico: bool
    mensaje_atacante: str
    mensaje_defensor: str
    mensaje_sala: str
    hp_restante: int
    muerto: bool = False


# --------------------------------------------------------------------------- #
#  Funciones de resolución
# --------------------------------------------------------------------------- #

def calcular_dano_base(fuerza: int, nivel: int) -> int:
    """Daño base según fuerza y nivel."""
    dado = random.randint(1, 8)
    bonus_fuerza = (fuerza - 10) // 2
    bonus_nivel = nivel // 2
    return max(1, dado + bonus_fuerza + bonus_nivel)


def calcular_esquiva(destreza: int) -> bool:
    """Devuelve True si el defensor esquiva el ataque."""
    prob_esquiva = 0.05 + (destreza - 10) * 0.01
    prob_esquiva = max(0.02, min(0.40, prob_esquiva))
    return random.random() < prob_esquiva


def calcular_critico(destreza_atacante: int) -> bool:
    """Devuelve True si el ataque es crítico."""
    prob = CRITICO_BASE + (destreza_atacante - 10) * 0.005
    prob = max(0.02, min(0.35, prob))
    return random.random() < prob


def reduccion_por_defensa(dano: int, defensa: int) -> int:
    """Reduce el daño según la defensa del objetivo."""
    reduccion = defensa // 3
    return max(1, dano - reduccion)


def resolver_ataque(
    atacante_stats: dict,
    defensor_stats: dict,
    nombre_atacante: str,
    nombre_defensor: str,
    habilidad: Optional[str] = None,
) -> ResultadoAtaque:
    """
    Resuelve un intercambio de ataque completo.
    Devuelve un ResultadoAtaque con todo lo necesario para el combate.
    """
    fuerza_at = atacante_stats.get("fuerza", 10)
    destreza_at = atacante_stats.get("destreza", 10)
    nivel_at = atacante_stats.get("nivel", 1)
    defensa_def = defensor_stats.get("defensa", 5)
    hp_def = defensor_stats.get("hp", 1)

    # ¿Esquiva?
    destreza_def = defensor_stats.get("destreza", 10)
    if calcular_esquiva(destreza_def):
        return ResultadoAtaque(
            exito=False,
            dano=0,
            critico=False,
            mensaje_atacante=f"|yFallas|n el golpe. {nombre_defensor} esquiva tu ataque.",
            mensaje_defensor=f"|g¡Esquivas|n el ataque de {nombre_atacante}!",
            mensaje_sala=f"{nombre_atacante} ataca a {nombre_defensor}, pero falla.",
            hp_restante=hp_def,
        )

    # Calcular daño
    critico = calcular_critico(destreza_at)
    dano_base = calcular_dano_base(fuerza_at, nivel_at)

    if habilidad:
        dano_base = _aplicar_habilidad(dano_base, habilidad, atacante_stats)

    dano_final = reduccion_por_defensa(dano_base, defensa_def)

    if critico:
        dano_final = int(dano_final * CRITICO_MULT)

    nuevo_hp = max(0, hp_def - dano_final)
    muerto = nuevo_hp <= 0

    critico_txt = " |r¡CRÍTICO!|n" if critico else ""
    hab_txt = f" ({habilidad})" if habilidad else ""

    return ResultadoAtaque(
        exito=True,
        dano=dano_final,
        critico=critico,
        mensaje_atacante=(
            f"Atacas a {nombre_defensor}{hab_txt}.{critico_txt} "
            f"|rCausas {dano_final} de daño|n. (HP: {nuevo_hp}/{defensor_stats.get('hp_max', nuevo_hp)})"
        ),
        mensaje_defensor=(
            f"{nombre_atacante} te ataca{hab_txt}.{critico_txt} "
            f"|rRecibes {dano_final} de daño|n. (HP: {nuevo_hp}/{defensor_stats.get('hp_max', nuevo_hp)})"
        ),
        mensaje_sala=(
            f"{nombre_atacante} golpea a {nombre_defensor}{hab_txt}{critico_txt} "
            f"causando {dano_final} de daño."
        ),
        hp_restante=nuevo_hp,
        muerto=muerto,
    )


def _aplicar_habilidad(dano_base: int, habilidad: str, stats: dict) -> int:
    """Modifica el daño base según la habilidad usada."""
    habilidad = habilidad.lower()
    modificadores = {
        "golpe fuerte": lambda d: int(d * 1.5),
        "golpe rapido": lambda d: max(1, d - 2),
        "embestida": lambda d: d + 5,
        "corte": lambda d: int(d * 1.3),
        "veneno": lambda d: d + random.randint(1, 4),
    }
    fn = modificadores.get(habilidad)
    return fn(dano_base) if fn else dano_base


def calcular_xp_recompensa(nivel_enemigo: int) -> int:
    """XP ganada al derrotar un enemigo del nivel dado."""
    base = 20 + nivel_enemigo * 15
    variacion = random.randint(-5, 10)
    return max(5, base + variacion)


def xp_para_siguiente_nivel(nivel_actual: int) -> int:
    """XP total necesaria para llegar al siguiente nivel."""
    if nivel_actual >= len(XP_POR_NIVEL) - 1:
        return 999999
    return XP_POR_NIVEL[nivel_actual]


MAX_NIVEL = len(XP_POR_NIVEL) - 1  # nivel máximo alcanzable (10)


def procesar_subida_de_nivel(stats: dict) -> tuple[bool, dict]:
    nivel = stats.get('nivel', 1)
    xp    = stats.get('experiencia', 0)
    subio = False
    while nivel < MAX_NIVEL and xp >= xp_para_siguiente_nivel(nivel):
        umbral = xp_para_siguiente_nivel(nivel)  # capturar ANTES de subir nivel
        xp    -= umbral
        nivel += 1
        stats  = dict(stats)
        stats['nivel']        = nivel
        stats['fuerza']      += 1
        stats['constitucion'] += 1
        stats['defensa']     += 1
        stats['hp_max']      += 10
        subio = True
    if subio:
        stats['experiencia'] = xp
        stats['hp']          = stats['hp_max']
    return subio, stats
