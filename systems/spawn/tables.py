"""
systems/spawn/tables.py

Definición pura de zonas y sus NPCs. Sin dependencias de Evennia.

Cada entrada de zona indica qué prototipos de NPC deben estar presentes
y en qué cantidad. El manager de spawn usa esta tabla para repoblar salas.

El tag de zona se almacena en sala.db.zona al construir el mundo.
"""
from __future__ import annotations

# zona_id → lista de entradas {prototipo, cantidad}
ZONAS: dict[str, list[dict]] = {
    # ----------------------------------------------------------------- #
    #  Mundo base: Ciudad
    # ----------------------------------------------------------------- #
    "plaza_ciudad": [
        {"prototipo": "GUARDIA", "cantidad": 1},
    ],
    "taberna": [
        {"prototipo": "MESONERO", "cantidad": 1},
    ],
    "mercado": [
        {"prototipo": "MERCADER",          "cantidad": 1},
        {"prototipo": "BUSCADOR_TESOROS",  "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Mundo base: Bosque
    # ----------------------------------------------------------------- #
    "bosque_norte": [
        {"prototipo": "GOBLIN", "cantidad": 2},   # 1 patrulla + 1 espía
    ],
    "claro_bosque": [
        {"prototipo": "GOBLIN_JEFE", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Mundo base: Calabozo
    # ----------------------------------------------------------------- #
    "calabozo_entrada": [
        {"prototipo": "BANDIDO", "cantidad": 1},
    ],
    "calabozo_pasillo": [
        {"prototipo": "BANDIDO", "cantidad": 1},
    ],
    "calabozo_celda": [
        {"prototipo": "BANDIDO_CAPITAN", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Expansión: Pantano del Troll
    # ----------------------------------------------------------------- #
    "senda_fangosa": [
        {"prototipo": "SERPIENTE_PANTANO", "cantidad": 1},
    ],
    "pantano_cenagoso": [
        {"prototipo": "SERPIENTE_PANTANO", "cantidad": 1},
        {"prototipo": "HOMBRE_LAGARTO",    "cantidad": 1},
    ],
    "guarida_troll": [
        {"prototipo": "TROLL", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Expansión: Catacumbas
    # ----------------------------------------------------------------- #
    "sala_tumbas": [
        {"prototipo": "ESQUELETO", "cantidad": 2},
    ],
    "camara_nigromante": [
        {"prototipo": "LICHE_MENOR", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Expansión: Ruinas del Templo
    # ----------------------------------------------------------------- #
    "camino_templo": [
        {"prototipo": "ESPECTRO", "cantidad": 1},
    ],
    "ruinas_templo": [
        {"prototipo": "ESPECTRO", "cantidad": 2},
    ],
    "cripta_baron": [
        {"prototipo": "CABALLERO_OSCURO", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Expansión: Minas de Hierro Viejo
    # ----------------------------------------------------------------- #
    "boca_mina": [
        {"prototipo": "ARANA_CUEVA", "cantidad": 2},
    ],
    "galeria_principal": [
        {"prototipo": "MINERO_MALDITO", "cantidad": 2},
    ],
    "caverna_coloso": [
        {"prototipo": "GOLEM_PIEDRA", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Expansión: Torre del Mago Caído
    # ----------------------------------------------------------------- #
    "base_torre": [
        {"prototipo": "GUARDIAN_ARCANO", "cantidad": 1},
    ],
    "biblioteca_archimago": [
        {"prototipo": "APRENDIZ_CORRUPTO", "cantidad": 2},
    ],
    "camara_ritual": [
        {"prototipo": "ARCHIMAGO_VEXTHAR", "cantidad": 1},
    ],
    # ----------------------------------------------------------------- #
    #  Ciudad (sacerdote y banquero en plaza)
    # ----------------------------------------------------------------- #
    "plaza_ciudad": [
        {"prototipo": "GUARDIA",    "cantidad": 1},
        {"prototipo": "SACERDOTE",  "cantidad": 1},
        {"prototipo": "BANQUERO",   "cantidad": 1},
    ],
}


def npcs_necesarios(zona_id: str) -> dict[str, int]:
    """Devuelve {prototipo: cantidad_total} para la zona dada."""
    total: dict[str, int] = {}
    for entrada in ZONAS.get(zona_id, []):
        proto = entrada["prototipo"]
        total[proto] = total.get(proto, 0) + int(entrada.get("cantidad", 1))
    return total


def calcular_faltantes(zona_id: str, presentes: dict[str, int]) -> dict[str, int]:
    """
    Dados los NPCs actualmente presentes ({prototipo: cantidad}),
    devuelve cuántos faltan por prototipo para cubrir la zona.
    """
    necesarios = npcs_necesarios(zona_id)
    return {
        proto: necesarios[proto] - presentes.get(proto, 0)
        for proto in necesarios
        if necesarios[proto] > presentes.get(proto, 0)
    }
