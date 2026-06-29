"""
systems/dungeons/dungeons.py

Catálogo puro de mazmorras instanciadas. Sin dependencias de Evennia.

Tres mazmorras con 3 salas cada una (2 salas normales + 1 de jefe).
Los jugadores avanzan sala a sala usando el comando `avanzar`.
Al derrotar al jefe y usar `avanzar`, la mazmorra se completa y se reparten
recompensas escaladas por dificultad.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

MAZMORRAS: dict[str, dict] = {
    "cripta_ceniza": {
        "nombre":       "Cripta de Ceniza",
        "desc":         "Una cripta ancestral donde los muertos se niegan a descansar en paz.",
        "nivel_min":    3,
        "jugadores_max": 4,
        "salas": [
            {
                "nombre": "Entrada de la Cripta",
                "desc": (
                    "Un corredor de piedra cenicienta iluminado por antorchas que no producen calor. "
                    "Los nichos funerarios están vacíos; sus ocupantes se han marchado por su cuenta."
                ),
                "enemigos": [("ESQUELETO", 2)],
            },
            {
                "nombre": "Nave Funeraria",
                "desc": (
                    "Una sala amplia con un altar profanado en el centro. "
                    "Inscripciones de maldición recubren cada piedra. "
                    "Una energía oscura hace vibrar el aire y apaga cualquier luz cálida."
                ),
                "enemigos": [("ESQUELETO", 2), ("LICHE_MENOR", 1)],
            },
            {
                "nombre": "Capilla del Señor de las Cenizas",
                "desc": (
                    "La cámara más profunda. Un trono de huesos y ceniza ocupa el centro "
                    "y la figura del Señor de las Cenizas aguarda inmóvil, "
                    "como si te hubiera esperado desde siempre."
                ),
                "enemigos": [("SENOR_CENIZAS", 1)],
                "es_jefe": True,
            },
        ],
        "xp_bonus":      150,
        "monedas_bonus":  40,
    },

    "forja_maldita": {
        "nombre":       "Forja Maldita",
        "desc":         "Una antigua forja corrompida donde el metal y la magia se mezclaron con sangre.",
        "nivel_min":    5,
        "jugadores_max": 4,
        "salas": [
            {
                "nombre": "Taller Corrompido",
                "desc": (
                    "Un taller de herrero en ruinas. Herramientas oxidadas flotan en el aire "
                    "movidas por magia residual. Algo se arrastra entre las sombras del fondo."
                ),
                "enemigos": [("MINERO_MALDITO", 2), ("ARANA_CUEVA", 1)],
            },
            {
                "nombre": "Cámara de la Fundición",
                "desc": (
                    "Un horno de piedra que lleva décadas ardiendo sin combustible visible. "
                    "El calor es casi insoportable. El suelo vibra con pasos colosales."
                ),
                "enemigos": [("MINERO_MALDITO", 2), ("GOLEM_PIEDRA", 1)],
            },
            {
                "nombre": "Trono del Maestro Forjador",
                "desc": (
                    "La sala del maestro. Cada herramienta fue templada con sangre y magia oscura. "
                    "El Maestro Forjador te observa con ojos que ya no son humanos, "
                    "empuñando un mazo que late como un corazón."
                ),
                "enemigos": [("MAESTRO_FORJADOR", 1)],
                "es_jefe": True,
            },
        ],
        "xp_bonus":      250,
        "monedas_bonus":  70,
    },

    "abismo_sin_fondo": {
        "nombre":       "Abismo Sin Fondo",
        "desc":         "Un portal al vacío primordial donde la oscuridad toma forma y voluntad.",
        "nivel_min":    7,
        "jugadores_max": 4,
        "salas": [
            {
                "nombre": "Umbral del Abismo",
                "desc": (
                    "El suelo se vuelve invisible aquí; una pasarela de piedra negra flota "
                    "sobre una oscuridad sin fondo. El frío es absoluto. "
                    "Figuras armadas bloquean el paso sin decir una sola palabra."
                ),
                "enemigos": [("CABALLERO_MUERTE", 2), ("HECHICERO_SOMBRIO", 1)],
            },
            {
                "nombre": "Corredor de las Almas",
                "desc": (
                    "Almas atrapadas en cristales negros iluminan un corredor sin fin aparente. "
                    "Sus lamentos apenas son audibles. Los guardianes no conocen la piedad."
                ),
                "enemigos": [("CABALLERO_MUERTE", 2), ("HECHICERO_SOMBRIO", 2)],
            },
            {
                "nombre": "Cámara del Señor del Abismo",
                "desc": (
                    "El corazón del abismo. La realidad aquí es inestable: "
                    "las paredes pulsan con una energía de no-existencia. "
                    "El Señor del Abismo no es un ser... es una ausencia con voluntad propia."
                ),
                "enemigos": [("SENOR_ABISMO", 1)],
                "es_jefe": True,
            },
        ],
        "xp_bonus":      400,
        "monedas_bonus": 120,
    },
}

# --------------------------------------------------------------------------- #
#  Dificultades
# --------------------------------------------------------------------------- #

DIFICULTADES: dict[str, dict] = {
    "normal":    {"hp_mult": 1.0, "xp_mult": 1.0, "monedas_mult": 1.0},
    "dificil":   {"hp_mult": 1.5, "xp_mult": 1.5, "monedas_mult": 1.5},
    "legendario":{"hp_mult": 2.0, "xp_mult": 2.5, "monedas_mult": 2.0},
}

NOMBRES_DIFICULTAD = {
    "normal":    "|wnormal|n",
    "dificil":   "|ydifícil|n",
    "legendario":"|rlegendario|n",
}

# Nombre de la sala portal (usada para devolver a los jugadores al salir)
SALA_PORTAL = "Vestíbulo del Portal"

# --------------------------------------------------------------------------- #
#  Funciones puras
# --------------------------------------------------------------------------- #

def buscar_mazmorra(nombre: str) -> tuple[str | None, dict | None]:
    """
    Busca mazmorra por ID exacto, luego por nombre parcial, luego por startswith.
    Devuelve (id, datos) o (None, None).
    """
    lower = nombre.lower().strip()
    if lower in MAZMORRAS:
        return lower, MAZMORRAS[lower]
    for mid, datos in MAZMORRAS.items():
        if lower in datos["nombre"].lower():
            return mid, datos
    matches = [(k, v) for k, v in MAZMORRAS.items() if k.startswith(lower)]
    if len(matches) == 1:
        return matches[0]
    return None, None


def puede_entrar(nivel: int, mazmorra_id: str) -> tuple[bool, str]:
    """Verifica si un jugador de ese nivel puede entrar a la mazmorra."""
    maz = MAZMORRAS.get(mazmorra_id)
    if not maz:
        return False, "Mazmorra desconocida."
    nivel_min = maz.get("nivel_min", 1)
    if nivel < nivel_min:
        return False, (
            f"Necesitas nivel |w{nivel_min}|n para entrar a esta mazmorra "
            f"(tienes nivel |w{nivel}|n)."
        )
    return True, ""


def calcular_recompensas(mazmorra_id: str, dificultad: str) -> tuple[int, int]:
    """Devuelve (xp_bonus, monedas_bonus) escalados por dificultad."""
    maz = MAZMORRAS.get(mazmorra_id, {})
    dif = DIFICULTADES.get(dificultad, DIFICULTADES["normal"])
    xp      = int(maz.get("xp_bonus", 100)     * dif["xp_mult"])
    monedas = int(maz.get("monedas_bonus", 30)  * dif["monedas_mult"])
    return xp, monedas


def escalar_hp(hp_base: int, dificultad: str) -> int:
    """Escala el HP base de un enemigo según la dificultad."""
    mult = DIFICULTADES.get(dificultad, {}).get("hp_mult", 1.0)
    return max(1, int(hp_base * mult))


def total_salas(mazmorra_id: str) -> int:
    return len(MAZMORRAS.get(mazmorra_id, {}).get("salas", []))


def es_sala_jefe(mazmorra_id: str, idx: int) -> bool:
    salas = MAZMORRAS.get(mazmorra_id, {}).get("salas", [])
    if 0 <= idx < len(salas):
        return bool(salas[idx].get("es_jefe"))
    return False


def formatear_lista() -> str:
    lineas = ["|wMazmorras disponibles:|n"]
    for mid, datos in MAZMORRAS.items():
        lineas.append(
            f"  |c{datos['nombre']}|n (|w{mid}|n) — "
            f"Nv.mín |w{datos['nivel_min']}|n — {datos['desc']}"
        )
    lineas.append(
        "\n|xDificultades: |wnormal|x / |ydifícil|x / |rlegendario|x"
        " (más dificultad = más recompensa)|n"
    )
    return "\n".join(lineas)


def formatear_info(mazmorra_id: str) -> str:
    maz = MAZMORRAS.get(mazmorra_id)
    if not maz:
        return f"|rMazmorra '{mazmorra_id}' no encontrada.|n"
    lineas = [
        f"|c{maz['nombre']}|n",
        f"|x{maz['desc']}|n",
        f"Nivel mínimo: |w{maz['nivel_min']}|n  ·  Hasta |w{maz['jugadores_max']}|n jugadores",
        "\n|wSalas:|n",
    ]
    for i, sala in enumerate(maz["salas"], 1):
        jefe = " |r[JEFE]|n" if sala.get("es_jefe") else ""
        enemigos = ", ".join(f"|w{c}|n× {p.lower().replace('_', ' ')}" for p, c in sala["enemigos"])
        lineas.append(f"  {i}. {sala['nombre']}{jefe} — {enemigos}")
    xp, mon = calcular_recompensas(mazmorra_id, "normal")
    xp_dif, mon_dif = calcular_recompensas(mazmorra_id, "dificil")
    xp_leg, mon_leg = calcular_recompensas(mazmorra_id, "legendario")
    lineas += [
        "\n|wRecompensas por dificultad:|n",
        f"  Normal:    +|w{xp}|n XP, |w{mon}|n monedas",
        f"  Difícil:   +|w{xp_dif}|n XP, |w{mon_dif}|n monedas",
        f"  Legendario:+|w{xp_leg}|n XP, |w{mon_leg}|n monedas",
    ]
    return "\n".join(lineas)
