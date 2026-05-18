"""
systems/skills/trees.py

Catálogo de habilidades y árbol de progresión.
Módulo puro: sin dependencias de Evennia.

Tres ramas: guerrero, explorador, mago.
Cada rama tiene 4 habilidades en cadena.
Los jugadores comienzan con golpe_fuerte y golpe_rapido (nivel 1, gratis).
"""
from __future__ import annotations

RAMAS: list[str] = ["guerrero", "explorador", "mago"]

HABILIDADES: dict[str, dict] = {
    # -------------------------------------------------------------------
    # RAMA GUERRERO
    # -------------------------------------------------------------------
    "golpe_fuerte": {
        "nombre": "Golpe Fuerte",
        "rama": "guerrero",
        "nivel_req": 1,
        "coste": 1,
        "requisitos": [],
        "tipo": "activa",
        "descripcion": "Golpe poderoso: x1.5 daño.",
    },
    "embestida": {
        "nombre": "Embestida",
        "rama": "guerrero",
        "nivel_req": 2,
        "coste": 1,
        "requisitos": ["golpe_fuerte"],
        "tipo": "activa",
        "descripcion": "+5 daño base. Puede desestabilizar al objetivo.",
    },
    "escudo_fe": {
        "nombre": "Escudo de Fe",
        "rama": "guerrero",
        "nivel_req": 3,
        "coste": 1,
        "requisitos": ["embestida"],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +2 defensa permanente al aprenderla.",
        "efecto_pasivo": {"defensa": 2},
    },
    "golpe_maestro": {
        "nombre": "Golpe Maestro",
        "rama": "guerrero",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": ["escudo_fe"],
        "tipo": "activa",
        "descripcion": "Golpe devastador: x2.5 daño.",
    },
    # -------------------------------------------------------------------
    # RAMA EXPLORADOR
    # -------------------------------------------------------------------
    "golpe_rapido": {
        "nombre": "Golpe Rápido",
        "rama": "explorador",
        "nivel_req": 1,
        "coste": 1,
        "requisitos": [],
        "tipo": "activa",
        "descripcion": "Golpe veloz: -2 daño pero más difícil de esquivar.",
    },
    "corte": {
        "nombre": "Corte",
        "rama": "explorador",
        "nivel_req": 2,
        "coste": 1,
        "requisitos": ["golpe_rapido"],
        "tipo": "activa",
        "descripcion": "Herida cortante: x1.3 daño + aplica sangrado.",
    },
    "veneno": {
        "nombre": "Veneno",
        "rama": "explorador",
        "nivel_req": 3,
        "coste": 1,
        "requisitos": ["corte"],
        "tipo": "activa",
        "descripcion": "+1d4 daño extra + envenena al objetivo.",
    },
    "ejecutar": {
        "nombre": "Ejecutar",
        "rama": "explorador",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": ["veneno"],
        "tipo": "activa",
        "descripcion": "x3 daño si el objetivo tiene menos del 25% de vida, x1.5 si no.",
    },
    # -------------------------------------------------------------------
    # RAMA MAGO
    # -------------------------------------------------------------------
    "dardo_magico": {
        "nombre": "Dardo Mágico",
        "rama": "mago",
        "nivel_req": 1,
        "coste": 1,
        "requisitos": [],
        "tipo": "activa",
        "descripcion": "Proyectil arcano: usa Inteligencia en lugar de Fuerza para el daño.",
    },
    "escudo_arcano": {
        "nombre": "Escudo Arcano",
        "rama": "mago",
        "nivel_req": 2,
        "coste": 1,
        "requisitos": ["dardo_magico"],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +3 defensa mágica permanente al aprenderla.",
        "efecto_pasivo": {"defensa": 3},
    },
    "bola_fuego": {
        "nombre": "Bola de Fuego",
        "rama": "mago",
        "nivel_req": 4,
        "coste": 2,
        "requisitos": ["escudo_arcano"],
        "tipo": "activa",
        "descripcion": "Explosión de fuego: x2 daño mágico.",
    },
    "drenar_vida": {
        "nombre": "Drenar Vida",
        "rama": "mago",
        "nivel_req": 6,
        "coste": 2,
        "requisitos": ["bola_fuego"],
        "tipo": "activa",
        "descripcion": "x1.5 daño y cura al atacante el 50% del daño infligido.",
    },
}

HABILIDADES_INICIALES: list[str] = ["golpe_fuerte", "golpe_rapido"]
