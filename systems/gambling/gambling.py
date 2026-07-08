"""
systems/gambling/gambling.py

Lógica pura del sistema de apuestas. Sin dependencias de Evennia.

Cuatro juegos disponibles en la Taberna:
  moneda  — cara o cruz, 50 % de ganar, ×2 la apuesta
  dados   — 2d6 jugador vs 2d6 casa, empate → casa gana, ×2 la apuesta
  cartas  — As–Rey (1-13) jugador vs casa, empate → casa gana, ×2 la apuesta
  ruleta  — elegir 1-6, 1/6 de ganar, ×5 la apuesta total (×4 ganancia neta)

Inyección de aleatoriedad:
  Cada función acepta _rng opcional — callable sin argumentos que devuelve
  el valor aleatorio apropiado. Cuando es None usa el módulo random.
  Esto permite tests 100% deterministas sin mocks de módulo.

db.apuestas_jugadas  en Character: int — partidas totales disputadas
db.apuestas_ganadas  en Character: int — partidas ganadas
db.mayor_ganancia    en Character: int — mayor ganancia neta en una partida
"""
from __future__ import annotations
import random as _rnd

MIN_APUESTA = 10
MAX_APUESTA = 1000

# Nombres de naipes para cartas
_NAIPES: dict[int, str] = {1: "As", 11: "J", 12: "Q", 13: "K"}


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_apostar(monedas: int, apuesta: int) -> tuple[bool, str]:
    """Comprueba si la apuesta es válida según monedas y límites."""
    if apuesta < MIN_APUESTA:
        return False, f"La apuesta mínima es |w{MIN_APUESTA}|n monedas."
    if apuesta > MAX_APUESTA:
        return False, f"La apuesta máxima es |w{MAX_APUESTA}|n monedas."
    if apuesta > monedas:
        return False, (
            f"No tienes suficientes monedas "
            f"(apuesta |w{apuesta}|n, tienes |w{monedas}|n)."
        )
    return True, ""


def validar_eleccion_moneda(eleccion: str) -> tuple[bool, str]:
    if eleccion.lower() not in ("cara", "cruz"):
        return False, "Elige |wcara|n o |wcruz|n."
    return True, ""


def validar_numero_ruleta(numero: int) -> tuple[bool, str]:
    if not (1 <= numero <= 6):
        return False, "Elige un número entre |w1|n y |w6|n."
    return True, ""


# --------------------------------------------------------------------------- #
#  Juegos
# --------------------------------------------------------------------------- #

def jugar_moneda(apuesta: int, eleccion: str, _rng=None) -> dict:
    """
    Cara o cruz. El jugador elige 'cara' o 'cruz'.
    _rng: callable() → float [0, 1). Default: random.random.

    Retorna dict con: gano, ganancia_neta, resultado, descripcion.
    """
    fn = _rng if _rng is not None else _rnd.random
    resultado = "cara" if fn() < 0.5 else "cruz"
    gano = resultado == eleccion.lower().strip()
    ganancia = apuesta if gano else -apuesta
    veredicto = "|g¡Acertaste!|n" if gano else "|rFallaste.|n"
    return {
        "juego":         "moneda",
        "gano":          gano,
        "ganancia_neta": ganancia,
        "resultado":     resultado,
        "descripcion":   (
            f"La moneda gira en el aire… muestra |w{resultado}|n. {veredicto}"
        ),
    }


def jugar_dados(apuesta: int, _rng=None) -> dict:
    """
    El jugador lanza 2d6 y la casa también. Quién saque más total gana.
    En empate, gana la casa.
    _rng: callable() → int [1, 6]. Default: random.randint(1,6).
    Llamado 4 veces: dado1_j, dado2_j, dado1_c, dado2_c.

    Retorna dict con: gano, ganancia_neta, dados_jugador, dados_casa,
                      total_jugador, total_casa, descripcion.
    """
    fn = _rng if _rng is not None else lambda: _rnd.randint(1, 6)
    d1j, d2j = fn(), fn()
    d1c, d2c = fn(), fn()
    tj, tc = d1j + d2j, d1c + d2c
    gano = tj > tc
    ganancia = apuesta if gano else -apuesta
    veredicto = "|g¡Ganas!|n" if gano else ("|x¡Empate! La casa gana.|n" if tj == tc else "|rPierdes.|n")
    return {
        "juego":         "dados",
        "gano":          gano,
        "ganancia_neta": ganancia,
        "dados_jugador": (d1j, d2j),
        "dados_casa":    (d1c, d2c),
        "total_jugador": tj,
        "total_casa":    tc,
        "descripcion":   (
            f"Tiras |w{d1j}+{d2j}={tj}|n. "
            f"La casa saca |w{d1c}+{d2c}={tc}|n. {veredicto}"
        ),
    }


def jugar_cartas(apuesta: int, _rng=None) -> dict:
    """
    El jugador y la casa sacan cada uno una carta (As=1, 2-10, J=11, Q=12, K=13).
    La carta más alta gana. En empate, gana la casa.
    _rng: callable() → int [1, 13]. Default: random.randint(1,13).
    Llamado 2 veces: carta_jugador, carta_casa.

    Retorna dict con: gano, ganancia_neta, carta_jugador, carta_casa,
                      nombre_jugador, nombre_casa, descripcion.
    """
    fn = _rng if _rng is not None else lambda: _rnd.randint(1, 13)
    cj, cc = fn(), fn()
    nj = _NAIPES.get(cj, str(cj))
    nc = _NAIPES.get(cc, str(cc))
    gano = cj > cc
    ganancia = apuesta if gano else -apuesta
    veredicto = "|g¡Ganas!|n" if gano else ("|x¡Empate! La casa gana.|n" if cj == cc else "|rPierdes.|n")
    return {
        "juego":         "cartas",
        "gano":          gano,
        "ganancia_neta": ganancia,
        "carta_jugador": cj,
        "carta_casa":    cc,
        "nombre_jugador": nj,
        "nombre_casa":   nc,
        "descripcion":   (
            f"Tu carta: |w{nj}|n. Casa: |w{nc}|n. {veredicto}"
        ),
    }


def jugar_ruleta(apuesta: int, numero: int, _rng=None) -> dict:
    """
    Ruleta de 6 posiciones (1-6). Acertar devuelve ×5 la apuesta (×4 ganancia neta).
    _rng: callable() → int [1, 6]. Default: random.randint(1,6).

    Retorna dict con: gano, ganancia_neta, resultado, descripcion.
    """
    fn = _rng if _rng is not None else lambda: _rnd.randint(1, 6)
    resultado = fn()
    gano = resultado == numero
    ganancia = apuesta * 4 if gano else -apuesta
    veredicto = f"|g¡El {numero} sale!|n" if gano else f"|rNo sale el {numero}.|n"
    return {
        "juego":         "ruleta",
        "gano":          gano,
        "ganancia_neta": ganancia,
        "resultado":     resultado,
        "descripcion":   (
            f"La ruleta gira… se detiene en |w{resultado}|n. {veredicto}"
        ),
    }


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_reglas() -> str:
    sep = "|w" + "─" * 54 + "|n"
    return "\n".join([
        f"\n{sep}",
        "  |cJuegos de la Taberna|n  —  apuesta mínima |w10|n, máxima |w1000|n monedas",
        sep,
        "",
        "  |wmoneda  <cara|cruz>  <apuesta>|n",
        "    Adivina la cara de la moneda. 50 % de ganar. Premios: ×2.",
        "",
        "  |wdados  <apuesta>|n",
        "    Lanza 2 dados contra la casa. El mayor total gana.",
        "    Empate = casa gana. Premios: ×2.",
        "",
        "  |wcartas  <apuesta>|n",
        "    Saca una carta (As–Rey) contra la casa. La más alta gana.",
        "    Empate = casa gana. Premios: ×2.",
        "",
        "  |wruleta  <1-6>  <apuesta>|n",
        "    Elige un número de la ruleta de 6 posiciones.",
        "    Probabilidad: 1/6. Premios: ×5 (×4 ganancia neta).",
        "",
        f"  Ejemplo: |wapostar dados 100|n",
        f"{sep}\n",
    ])
