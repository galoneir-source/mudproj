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
    # -------------------------------------------------------------------
    # SUBCLASE GUERRERO: Paladín
    # -------------------------------------------------------------------
    "escudo_divino": {
        "nombre": "Escudo Divino",
        "rama": "paladin",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +3 defensa permanente al aprenderla.",
        "efecto_pasivo": {"defensa": 3},
    },
    "golpe_sagrado": {
        "nombre": "Golpe Sagrado",
        "rama": "paladin",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["escudo_divino"],
        "tipo": "activa",
        "descripcion": "x2 daño y restaura al atacante el 25% del daño infligido.",
    },
    # -------------------------------------------------------------------
    # SUBCLASE GUERRERO: Berserker
    # -------------------------------------------------------------------
    "furia_berserker": {
        "nombre": "Furia Berserker",
        "rama": "berserker",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +3 fuerza permanente al aprenderla.",
        "efecto_pasivo": {"fuerza": 3},
    },
    "golpe_demoledor": {
        "nombre": "Golpe Demoledor",
        "rama": "berserker",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["furia_berserker"],
        "tipo": "activa",
        "descripcion": "Golpe brutal: x3.5 daño. Sin contemplaciones.",
    },
    # -------------------------------------------------------------------
    # SUBCLASE EXPLORADOR: Asesino
    # -------------------------------------------------------------------
    "golpe_certero": {
        "nombre": "Golpe Certero",
        "rama": "asesino",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +2 destreza permanente al aprenderla.",
        "efecto_pasivo": {"destreza": 2},
    },
    "golpe_letal": {
        "nombre": "Golpe Letal",
        "rama": "asesino",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["golpe_certero"],
        "tipo": "activa",
        "descripcion": "x2.5 daño + aplica sangrado al objetivo.",
    },
    # -------------------------------------------------------------------
    # SUBCLASE EXPLORADOR: Cazador
    # -------------------------------------------------------------------
    "instinto_cazador": {
        "nombre": "Instinto Cazador",
        "rama": "cazador",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +1 destreza y +1 constitución permanentes al aprenderla.",
        "efecto_pasivo": {"destreza": 1, "constitucion": 1},
    },
    "trampa_mortal": {
        "nombre": "Trampa Mortal",
        "rama": "cazador",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["instinto_cazador"],
        "tipo": "activa",
        "descripcion": "x2 daño + envenena al objetivo.",
    },
    # -------------------------------------------------------------------
    # SUBCLASE MAGO: Hechicero
    # -------------------------------------------------------------------
    "concentracion_arcana": {
        "nombre": "Concentración Arcana",
        "rama": "hechicero",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +2 inteligencia permanente al aprenderla.",
        "efecto_pasivo": {"inteligencia": 2},
    },
    "nova_arcana": {
        "nombre": "Nova Arcana",
        "rama": "hechicero",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["concentracion_arcana"],
        "tipo": "activa",
        "descripcion": "x2.5 daño mágico usando Inteligencia como base.",
    },
    # -------------------------------------------------------------------
    # SUBCLASE MAGO: Nigromante
    # -------------------------------------------------------------------
    "escudo_sombrio": {
        "nombre": "Escudo Sombrío",
        "rama": "nigromante",
        "nivel_req": 5,
        "coste": 2,
        "requisitos": [],
        "tipo": "pasiva",
        "descripcion": "Pasiva: +2 constitución permanente al aprenderla.",
        "efecto_pasivo": {"constitucion": 2},
    },
    "drenar_esencia": {
        "nombre": "Drenar Esencia",
        "rama": "nigromante",
        "nivel_req": 7,
        "coste": 2,
        "requisitos": ["escudo_sombrio"],
        "tipo": "activa",
        "descripcion": "x2 daño y cura al atacante el 50% del daño infligido.",
    },
}

HABILIDADES_INICIALES: list[str] = ["golpe_fuerte", "golpe_rapido"]
