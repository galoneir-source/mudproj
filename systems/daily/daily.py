"""
systems/daily/daily.py

Lógica pura del sistema de Desafíos Diarios.

Los desafíos se generan de forma determinista desde la fecha UTC actual,
de modo que todos los jugadores comparten las mismas 5 tareas cada día.
Las recompensas escalan con la racha de días consecutivos completados.
"""
import random

POOL_DESAFIOS = [
    {
        "id": "kill_bandidos",
        "tipo": "kill_faccion",
        "faccion": "horda_salvaje",
        "objetivo": 5,
        "recompensa_xp": 200,
        "recompensa_monedas": 100,
        "desc": "Derrota a {objetivo} bandidos",
    },
    {
        "id": "kill_no_muertos",
        "tipo": "kill_faccion",
        "faccion": "legion_oscura",
        "objetivo": 5,
        "recompensa_xp": 220,
        "recompensa_monedas": 110,
        "desc": "Elimina a {objetivo} no-muertos",
    },
    {
        "id": "kill_bestias",
        "tipo": "kill_faccion",
        "faccion": "bestias",
        "objetivo": 8,
        "recompensa_xp": 180,
        "recompensa_monedas": 80,
        "desc": "Caza a {objetivo} bestias salvajes",
    },
    {
        "id": "kill_legion",
        "tipo": "kill_faccion",
        "faccion": "legion_oscura",
        "objetivo": 3,
        "recompensa_xp": 300,
        "recompensa_monedas": 150,
        "desc": "Elimina a {objetivo} miembros de la Legión Oscura",
    },
    {
        "id": "kill_pantano",
        "tipo": "kill_faccion",
        "faccion": "sombras_pantano",
        "objetivo": 3,
        "recompensa_xp": 300,
        "recompensa_monedas": 150,
        "desc": "Destruye a {objetivo} criaturas del pantano",
    },
    {
        "id": "kill_horda",
        "tipo": "kill_faccion",
        "faccion": "horda_salvaje",
        "objetivo": 6,
        "recompensa_xp": 200,
        "recompensa_monedas": 90,
        "desc": "Derrota a {objetivo} goblins salvajes",
    },
    {
        "id": "rec_herboristeria",
        "tipo": "recolectar",
        "profesion": "herboristeria",
        "objetivo": 5,
        "recompensa_xp": 150,
        "recompensa_monedas": 80,
        "desc": "Recolecta {objetivo} materiales de herboristería",
    },
    {
        "id": "rec_mineria",
        "tipo": "recolectar",
        "profesion": "mineria",
        "objetivo": 5,
        "recompensa_xp": 150,
        "recompensa_monedas": 80,
        "desc": "Extrae {objetivo} minerales",
    },
    {
        "id": "rec_pesca",
        "tipo": "recolectar",
        "profesion": "pesca",
        "objetivo": 8,
        "recompensa_xp": 120,
        "recompensa_monedas": 60,
        "desc": "Pesca {objetivo} peces",
    },
    {
        "id": "apostar_ganar",
        "tipo": "apostar_ganar",
        "objetivo": 3,
        "recompensa_xp": 100,
        "recompensa_monedas": 250,
        "desc": "Gana {objetivo} apuestas en la taberna",
    },
    {
        "id": "alquimia",
        "tipo": "alquimia",
        "objetivo": 2,
        "recompensa_xp": 200,
        "recompensa_monedas": 100,
        "desc": "Elabora {objetivo} pociones alquímicas",
    },
    {
        "id": "expedicion",
        "tipo": "expedicion",
        "objetivo": 1,
        "recompensa_xp": 500,
        "recompensa_monedas": 300,
        "desc": "Completa {objetivo} expedición grupal",
    },
]

_TIPOS_VALIDOS = frozenset(
    d["tipo"] for d in POOL_DESAFIOS
)


def generar_desafios_del_dia(fecha_str: str) -> list:
    """
    Genera la lista de 5 desafíos para la fecha dada (formato 'YYYY-MM-DD').
    El resultado es determinista: misma fecha → mismos desafíos para todos.
    """
    seed = int(fecha_str.replace("-", ""))
    rng = random.Random(seed)
    seleccionados = rng.sample(POOL_DESAFIOS, min(5, len(POOL_DESAFIOS)))
    return [dict(d) for d in seleccionados]


def progreso_completado(desafio: dict, progreso: int) -> bool:
    """True si el progreso alcanza o supera el objetivo del desafío."""
    return progreso >= desafio.get("objetivo", 1)


def actualizar_progreso(
    desafios: list,
    progreso: list,
    completados_idx: list,
    tipo: str,
    datos: dict,
) -> tuple:
    """
    Función pura. Procesa un evento e incrementa el progreso de los desafíos que apliquen.

    Parámetros:
        desafios       — lista de 5 dicts del día
        progreso       — lista de 5 ints (progreso actual)
        completados_idx — índices ya finalizados (no se vuelven a contar)
        tipo           — tipo de evento: 'kill_faccion', 'recolectar', 'apostar_ganar',
                          'alquimia', 'expedicion'
        datos          — dict con claves opcionales: 'faccion', 'profesion'

    Retorna:
        (nuevo_progreso, nuevos_completados_idx, indices_avanzados)
    """
    nuevo_progreso = list(progreso)
    while len(nuevo_progreso) < len(desafios):
        nuevo_progreso.append(0)

    nuevos_completados = []
    avanzados = []

    completados_set = set(completados_idx)

    for i, desafio in enumerate(desafios):
        if i in completados_set:
            continue
        if desafio["tipo"] != tipo:
            continue

        if tipo == "kill_faccion":
            faccion_evento = datos.get("faccion", "")
            faccion_desafio = desafio.get("faccion", "")
            if faccion_desafio.lower() != faccion_evento.lower():
                continue
        elif tipo == "recolectar":
            prof_evento = datos.get("profesion", "")
            prof_desafio = desafio.get("profesion", "")
            if prof_desafio.lower() != prof_evento.lower():
                continue

        nuevo_progreso[i] += 1
        avanzados.append(i)
        if progreso_completado(desafio, nuevo_progreso[i]):
            nuevos_completados.append(i)

    return nuevo_progreso, nuevos_completados, avanzados


def calcular_multiplicador_racha(racha: int) -> float:
    """Multiplicador de XP bonus al completar los 5 desafíos en un día."""
    if racha <= 1:
        return 1.0
    if racha == 2:
        return 1.25
    if racha == 3:
        return 1.5
    return 2.0


def bonus_racha_monedas(racha: int) -> int:
    """Bonus en monedas al completar todos los desafíos del día según la racha."""
    if racha <= 1:
        return 0
    if racha == 2:
        return 50
    if racha == 3:
        return 100
    if racha == 4:
        return 200
    return 300


def bonus_racha_xp(racha: int) -> int:
    """Bonus en XP al completar todos los desafíos del día según la racha."""
    if racha <= 1:
        return 0
    if racha == 2:
        return 100
    if racha == 3:
        return 200
    if racha == 4:
        return 400
    return 600


def formatear_desafios(
    desafios: list,
    progreso: list,
    completados_idx: list,
    racha: int,
    fecha_str: str,
) -> str:
    """Formatea la lista de desafíos del día con progreso del jugador."""
    sep = "|w" + "─" * 58 + "|n"
    completados_set = set(completados_idx)
    lineas = [
        f"\n{sep}",
        f"  |cDesafíos del Día|n — |w{fecha_str}|n",
        sep,
    ]
    for i, d in enumerate(desafios):
        prog = progreso[i] if i < len(progreso) else 0
        obj = d["objetivo"]
        hecho = i in completados_set
        desc = d["desc"].format(objetivo=obj)
        barra = f"[{min(prog, obj)}/{obj}]"
        marca = " |g✔|n" if hecho else ""
        recomp = f"|g+{d['recompensa_xp']} XP|n |y+{d['recompensa_monedas']}m|n"
        lineas.append(f"  |w[{i + 1}]|n {desc:<38} {barra}{marca}")
        lineas.append(f"       Recompensa: {recomp}")
    lineas.append(sep)
    total_hoy = len(completados_set)
    racha_str = f"|Y{racha}|n día{'s' if racha != 1 else ''} consecutivo{'s' if racha != 1 else ''}"
    lineas.append(f"  Racha: {racha_str}   |  Hoy: |w{total_hoy}/5|n completados")
    bonus_m = bonus_racha_monedas(racha + (1 if total_hoy < 5 else 0))
    bonus_x = bonus_racha_xp(racha + (1 if total_hoy < 5 else 0))
    if bonus_m > 0 or bonus_x > 0:
        lineas.append(
            f"  Bonus al completar los 5: |g+{bonus_x} XP|n  |y+{bonus_m} monedas|n"
        )
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_racha(racha: int, ultimo_dia: str, total_completados: int) -> str:
    """Muestra el historial de racha del jugador."""
    sep = "|w" + "─" * 42 + "|n"
    lineas = [
        f"\n{sep}",
        "  |cDesafíos — Tu Racha|n",
        sep,
        f"  Racha actual:      |Y{racha}|n día{'s' if racha != 1 else ''}",
        f"  Último día completo: |w{ultimo_dia or 'nunca'}|n",
        f"  Total completados:  |w{total_completados}|n desafíos",
        f"{sep}\n",
    ]
    return "\n".join(lineas)
