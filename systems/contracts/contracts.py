"""
systems/contracts/contracts.py

Lógica pura del tablón de contratos (v0.27.0). Sin dependencias de Evennia.
Contratos procedurales con dos tipos: matar N enemigos o entregar N materiales.
Los contratos son deterministas por hora (misma seed = mismo tablón para todos).
"""
import time
from random import Random

TIPOS_CONTRATO = ("kill", "entrega")

VERBOS_KILL = [
    "Elimina", "Derrota", "Acaba con", "Neutraliza", "Caza",
]

MATERIALES = [
    "piel de lobo",
    "garra de troll",
    "mineral de hierro",
    "gema en bruto",
    "hilo de araña",
    "escama de lagarto",
    "cristal sagrado",
    "cenizas arcanas",
    "fragmento arcano",
    "fragmento de alma",
    "hueso de esqueleto",
    "veneno de serpiente",
]

DIFICULTADES = {
    1: {
        "kill_rango":    (3, 6),
        "entrega_rango": (2, 4),
        "monedas":       (40,  80),
        "xp":            (25,  50),
        "etiqueta":      "★☆☆",
    },
    2: {
        "kill_rango":    (8, 15),
        "entrega_rango": (4, 7),
        "monedas":       (100, 200),
        "xp":            (60,  100),
        "etiqueta":      "★★☆",
    },
    3: {
        "kill_rango":    (15, 25),
        "entrega_rango": (7, 12),
        "monedas":       (250, 500),
        "xp":            (150, 250),
        "etiqueta":      "★★★",
    },
}

NUM_CONTRATOS = 5


def seed_hora_actual() -> int:
    """Semilla que cambia cada hora, igual para todos los jugadores."""
    return int(time.time()) // 3600


def generar_contrato(indice: int, seed: int) -> dict:
    """Genera un contrato determinista para el índice y la semilla dados."""
    rng = Random(seed + indice * 997)

    # Pesos: más comunes los fáciles
    dificultad = rng.choices([1, 2, 3], weights=[3, 2, 1])[0]
    tipo = rng.choice(TIPOS_CONTRATO)
    cfg = DIFICULTADES[dificultad]

    if tipo == "kill":
        verbo = rng.choice(VERBOS_KILL)
        cantidad = rng.randint(*cfg["kill_rango"])
        descripcion = f"{verbo} {cantidad} enemigos."
        objetivo = "enemigo"
    else:
        objetivo = rng.choice(MATERIALES)
        cantidad = rng.randint(*cfg["entrega_rango"])
        descripcion = f"Entrega {cantidad} {objetivo}."

    monedas = rng.randint(*cfg["monedas"])
    xp = rng.randint(*cfg["xp"])

    return {
        "id":          f"{seed}_{indice}",
        "tipo":        tipo,
        "descripcion": descripcion,
        "objetivo":    objetivo,
        "cantidad":    cantidad,
        "dificultad":  dificultad,
        "etiqueta":    cfg["etiqueta"],
        "recompensa":  {"monedas": monedas, "xp": xp},
    }


def generar_tablón(seed: int, n: int = NUM_CONTRATOS) -> list:
    """Devuelve una lista de n contratos deterministas para la seed dada."""
    return [generar_contrato(i, seed) for i in range(n)]


def puede_completar_kill(contrato: dict, kills_totales: int) -> tuple[bool, int]:
    """
    Comprueba si el jugador completó un contrato kill.
    Returns (completado, kills_hechas_desde_aceptar).
    """
    kills_al_aceptar = contrato.get("kills_al_aceptar", 0) or 0
    hechas = max(0, kills_totales - kills_al_aceptar)
    return hechas >= contrato["cantidad"], hechas


def puede_completar_entrega(contrato: dict, disponible: int) -> tuple[bool, int]:
    """
    Comprueba si el jugador tiene los materiales para un contrato entrega.
    Returns (completado, disponible).
    """
    return disponible >= contrato["cantidad"], disponible


def formatear_contrato(num: int, contrato: dict) -> str:
    """Devuelve una línea formateada para mostrar en el tablón."""
    r = contrato["recompensa"]
    return (
        f"  |w[{num}]|n {contrato['etiqueta']} {contrato['descripcion']}"
        f"  |y{r['monedas']}m|n / |c{r['xp']} XP|n"
    )


def formatear_progreso(contrato: dict, kills_totales: int = 0,
                       disponible: int = 0) -> str:
    """Muestra el estado de progreso del contrato activo."""
    tipo = contrato["tipo"]
    cantidad = contrato["cantidad"]

    if tipo == "kill":
        _, hechas = puede_completar_kill(contrato, kills_totales)
        progreso = min(hechas, cantidad)
        return (
            f"|w{contrato['descripcion']}|n\n"
            f"  Progreso: |y{progreso}/{cantidad}|n kills"
        )
    else:
        _, disp = puede_completar_entrega(contrato, disponible)
        progreso = min(disp, cantidad)
        return (
            f"|w{contrato['descripcion']}|n\n"
            f"  Materiales: |y{progreso}/{cantidad}|n {contrato['objetivo']}"
        )
