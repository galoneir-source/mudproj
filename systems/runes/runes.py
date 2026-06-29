"""
systems/runes/runes.py

Lógica pura del sistema de runas. Sin dependencias de Evennia.

Las runas son grabados mágicos que se inscriben en el equipamiento del
personaje (máx. 1 runa por slot). Requieren materiales de profesión y
un coste en monedas para ser grabadas por el Tallador de la ciudad.

Efectos disponibles:
  regen_hp            — Regenera N HP al inicio del turno del portador.
  sangrado_chance     — N% de probabilidad de infligir Sangrado al atacar.
  reduccion_dano      — Reduce N puntos de daño recibido.
  robo_vida           — Recupera N HP por cada golpe exitoso.
  evasion             — N% de probabilidad de esquivar ataques.
  bonus_fuerza        — +N Fuerza mientras el objeto esté equipado.
  resistencia_estados — N% de resistencia a estados negativos.
  bonus_inteligencia  — +N Inteligencia mientras el objeto esté equipado.
"""
from __future__ import annotations

RUNAS: dict[str, dict] = {
    "RUNA_VIGOR": {
        "nombre": "Runa de Vigor",
        "descripcion": "Regeneras 3 HP al inicio de cada uno de tus turnos de combate.",
        "efecto": "regen_hp",
        "valor": 3,
        "slot": None,
        "nivel_req": 1,
        "materiales": {"hierba medicinal": 3},
        "coste_monedas": 30,
    },
    "RUNA_FILO": {
        "nombre": "Runa de Filo",
        "descripcion": "Tus ataques tienen 25% de probabilidad de infligir Sangrado.",
        "efecto": "sangrado_chance",
        "valor": 25,
        "slot": "arma",
        "nivel_req": 3,
        "materiales": {"mineral de hierro": 2, "hierba medicinal": 1},
        "coste_monedas": 60,
    },
    "RUNA_ESCUDO": {
        "nombre": "Runa de Escudo",
        "descripcion": "Reduces 2 puntos de daño recibido en cada ataque.",
        "efecto": "reduccion_dano",
        "valor": 2,
        "slot": "armadura",
        "nivel_req": 3,
        "materiales": {"mineral de hierro": 3},
        "coste_monedas": 60,
    },
    "RUNA_DRENAJE": {
        "nombre": "Runa de Drenaje",
        "descripcion": "Recuperas 2 HP por cada golpe exitoso que propinas.",
        "efecto": "robo_vida",
        "valor": 2,
        "slot": "arma",
        "nivel_req": 5,
        "materiales": {"raíz de pantano": 2, "mineral de hierro": 1},
        "coste_monedas": 100,
    },
    "RUNA_EVASION": {
        "nombre": "Runa de Evasión",
        "descripcion": "Tienes 10% de probabilidad de esquivar ataques.",
        "efecto": "evasion",
        "valor": 10,
        "slot": None,
        "nivel_req": 6,
        "materiales": {"flor silvestre": 2, "esencia vegetal": 1},
        "coste_monedas": 130,
    },
    "RUNA_PODER": {
        "nombre": "Runa de Poder",
        "descripcion": "+5 Fuerza mientras el arma esté equipada.",
        "efecto": "bonus_fuerza",
        "valor": 5,
        "slot": "arma",
        "nivel_req": 7,
        "materiales": {"gema en bruto": 2, "mineral de plata": 1},
        "coste_monedas": 160,
    },
    "RUNA_FIRMEZA": {
        "nombre": "Runa de Firmeza",
        "descripcion": "Los estados negativos tienen 25% de probabilidad de no aplicarse.",
        "efecto": "resistencia_estados",
        "valor": 25,
        "slot": "armadura",
        "nivel_req": 6,
        "materiales": {"mineral de plata": 2, "raíz de pantano": 1},
        "coste_monedas": 130,
    },
    "RUNA_ARCANA": {
        "nombre": "Runa Arcana",
        "descripcion": "+3 Inteligencia mientras el objeto esté equipado.",
        "efecto": "bonus_inteligencia",
        "valor": 3,
        "slot": None,
        "nivel_req": 9,
        "materiales": {"gema arcana": 1, "extracto raro": 1},
        "coste_monedas": 200,
    },
}

SLOTS_VALIDOS = ("arma", "armadura", "accesorio")


def buscar_runa(nombre: str) -> str | None:
    """Busca una runa por ID exacto o nombre parcial. Devuelve el ID o None."""
    nombre_l = nombre.strip().lower()
    for rid, runa in RUNAS.items():
        if rid.lower() == nombre_l or runa["nombre"].lower() == nombre_l:
            return rid
    for rid, runa in RUNAS.items():
        if nombre_l in rid.lower() or nombre_l in runa["nombre"].lower():
            return rid
    return None


def puede_grabar(nivel: int, runa_id: str) -> tuple[bool, str]:
    """Comprueba si el personaje tiene nivel suficiente para grabar la runa."""
    runa = RUNAS.get(runa_id)
    if not runa:
        return False, "Runa desconocida."
    req = runa["nivel_req"]
    if nivel < req:
        return False, f"Necesitas nivel {req} para grabar la {runa['nombre']}."
    return True, ""


def slot_compatible(runa_id: str, slot: str) -> bool:
    """Devuelve True si la runa puede grabarse en ese slot de equipamiento."""
    runa = RUNAS.get(runa_id)
    if not runa:
        return False
    runa_slot = runa["slot"]
    return runa_slot is None or runa_slot == slot


def tiene_materiales(inventario: dict, runa_id: str) -> tuple[bool, list]:
    """
    Comprueba si el inventario tiene los materiales para grabar la runa.
    inventario: {nombre_item_lower: cantidad_disponible}
    Devuelve (ok, lista_de_faltantes).
    """
    runa = RUNAS.get(runa_id)
    if not runa:
        return False, ["Runa desconocida."]
    faltantes = []
    for mat, cant_req in runa["materiales"].items():
        disponible = inventario.get(mat.lower(), 0)
        if disponible < cant_req:
            falta = cant_req - disponible
            faltantes.append(f"{mat} ×{falta}")
    return (not faltantes), faltantes


def obtener_efectos(runas_equipadas: dict) -> dict:
    """
    Devuelve el dict de efectos activos a partir de las runas equipadas.
    runas_equipadas: {"arma": runa_id|None, "armadura": ..., "accesorio": ...}
    Resultado: {"regen_hp": N, "evasion": N, ...}
    """
    efectos: dict = {}
    for _slot, runa_id in (runas_equipadas or {}).items():
        if not runa_id:
            continue
        runa = RUNAS.get(runa_id)
        if not runa:
            continue
        efecto = runa["efecto"]
        valor = runa["valor"]
        efectos[efecto] = efectos.get(efecto, 0) + valor
    return efectos


def formatear_lista() -> str:
    sep = "|w" + "─" * 56 + "|n"
    slots_txt = {
        "arma": "|carma|n",
        "armadura": "|carmadura|n",
        "accesorio": "|caccesorio|n",
        None: "|ctodos|n",
    }
    lineas = [f"\n{sep}", "  |cCatálogo de Runas|n", sep]
    for rid, runa in RUNAS.items():
        slot_str = slots_txt.get(runa["slot"], str(runa["slot"]))
        mats = ", ".join(f"{m} ×{c}" for m, c in runa["materiales"].items())
        lineas.append(
            f"\n  |w{runa['nombre']}|n  [|Y{rid}|n]\n"
            f"  {runa['descripcion']}\n"
            f"  Slot: {slot_str}  •  Nivel: |w{runa['nivel_req']}|n"
            f"  •  Coste: |w{runa['coste_monedas']}|n monedas\n"
            f"  Materiales: |x{mats}|n"
        )
    lineas.append(f"\n{sep}")
    lineas.append(f"  Uso: |wrunas grabar <ID> en <slot>|n\n{sep}\n")
    return "\n".join(lineas)


def formatear_runa(runa_id: str) -> str:
    runa = RUNAS.get(runa_id)
    if not runa:
        return f"|rRuna '{runa_id}' desconocida.|n"
    sep = "|w" + "─" * 46 + "|n"
    slot_txt = runa["slot"] or "cualquier slot"
    mats = "\n".join(f"    • {m} ×{c}" for m, c in runa["materiales"].items())
    return (
        f"\n{sep}\n"
        f"  |w{runa['nombre']}|n  [|Y{runa_id}|n]\n"
        f"  {runa['descripcion']}\n\n"
        f"  Slot compatible: |c{slot_txt}|n\n"
        f"  Nivel requerido: |w{runa['nivel_req']}|n\n"
        f"  Coste de grabado: |w{runa['coste_monedas']} monedas|n\n"
        f"  Materiales necesarios:\n{mats}\n"
        f"{sep}\n"
    )


def formatear_runas_equipadas(runas: dict) -> str:
    sep = "|w" + "─" * 46 + "|n"
    lineas = [f"\n{sep}", "  |cRunas Grabadas|n", sep]
    for slot in SLOTS_VALIDOS:
        runa_id = (runas or {}).get(slot)
        if runa_id and runa_id in RUNAS:
            runa = RUNAS[runa_id]
            lineas.append(
                f"  |c{slot.capitalize()}:|n |w{runa['nombre']}|n"
                f"  — {runa['descripcion']}"
            )
        else:
            lineas.append(f"  |c{slot.capitalize()}:|n |x— vacío —|n")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)
