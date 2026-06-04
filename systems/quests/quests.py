"""
systems/quests/quests.py

Definición de misiones y lógica pura de validación (sin Evennia).
"""
from __future__ import annotations
from typing import Optional


# --------------------------------------------------------------------------- #
#  Definición de misiones
# --------------------------------------------------------------------------- #

QUESTS: dict[str, dict] = {
    "problema_goblins": {
        "titulo": "El Problema de los Goblins",
        "descripcion": (
            "Los goblins del bosque norte atacan a los viajeros sin descanso. "
            "La guardia necesita que alguien los reduzca."
        ),
        "tipo": "kill",
        "objetivo": {"target": "goblin", "cantidad": 3},
        "dador": "guardia de la ciudad",
        "receptor": "guardia de la ciudad",
        "recompensa": {"xp": 150, "monedas": 25},
        "rep_reward": {"ciudadanos": 250, "horda_salvaje": -150},
        "texto_oferta": (
            "Los goblins del bosque norte son un problema serio. "
            "¿Podrías encargarte de 3 de ellos? Te recompensaremos bien."
        ),
        "texto_progreso": "Llevas {actual} de {total} goblins eliminados. Sigue así.",
        "texto_entrega": "Excelente trabajo, aventurero. La ciudad te lo agradece.",
        "nivel_minimo": 1,
    },
    "mercancia_robada": {
        "titulo": "La Mercancía Robada",
        "descripcion": (
            "Los bandidos del calabozo robaron mercancía valiosa a Mira. "
            "Su capitán debe pagar por ello."
        ),
        "tipo": "kill",
        "objetivo": {"target": "capitán bandido", "cantidad": 1},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 300, "monedas": 60, "prototipo": "ANILLO_DESTREZA"},
        "rep_reward": {"ciudadanos": 300, "horda_salvaje": -200},
        "texto_oferta": (
            "Esos bandidos del calabozo robaron mi mejor mercancía. "
            "Su capitán es el responsable. ¿Le darías una lección?"
        ),
        "texto_progreso": "El capitán aún sigue en el calabozo. Acaba con él.",
        "texto_entrega": "¡Lo lograste! Toma este anillo como recompensa adicional.",
        "nivel_minimo": 3,
    },
    "veneno_del_pantano": {
        "titulo": "Veneno del Pantano",
        "descripcion": (
            "Mira la mercader necesita veneno de pantano para sus preparados alquímicos. "
            "Las serpientes del pantano lo producen."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "veneno de pantano", "cantidad": 2},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 100, "monedas": 30},
        "rep_reward": {"ciudadanos": 150, "gremio_aventureros": 100},
        "texto_oferta": (
            "¿Puedes traerme 2 frascos de veneno de pantano? "
            "Los necesito para mis preparados alquímicos."
        ),
        "texto_progreso": "Aún necesito {faltante} frasco(s) de veneno de pantano.",
        "texto_entrega": "Perfecto, justo lo que necesitaba. Muchas gracias.",
        "nivel_minimo": 2,
    },
    "garra_del_troll": {
        "titulo": "La Garra del Troll",
        "descripcion": (
            "Un alquimista amigo del mesonero paga bien por garras de troll. "
            "Solo los más valientes se atreven a ir al pantano."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "garra de troll", "cantidad": 1},
        "dador": "Gareth el mesonero",
        "receptor": "Gareth el mesonero",
        "recompensa": {"xp": 200, "monedas": 40},
        "rep_reward": {"ciudadanos": 200, "gremio_aventureros": 150, "sombras_pantano": -100},
        "texto_oferta": (
            "Un alquimista amigo paga bien por garras de troll. "
            "Si consigues una, te doy una buena parte del dinero."
        ),
        "texto_progreso": "Mi amigo aún espera esa garra de troll.",
        "texto_entrega": "¡Magnífico! Esto le encantará a mi amigo el alquimista.",
        "nivel_minimo": 5,
    },
    "amenaza_catacumbas": {
        "titulo": "La Amenaza de las Catacumbas",
        "descripcion": (
            "Un liche menor dirige a los no-muertos desde las catacumbas bajo el calabozo. "
            "Es una amenaza para toda la ciudad."
        ),
        "tipo": "kill",
        "objetivo": {"target": "liche menor", "cantidad": 1},
        "dador": "guardia de la ciudad",
        "receptor": "guardia de la ciudad",
        "recompensa": {"xp": 500, "monedas": 100},
        "rep_reward": {"ciudadanos": 500, "gremio_aventureros": 300, "legion_oscura": -300},
        "texto_oferta": (
            "Las catacumbas bajo el calabozo llevan tiempo activas. "
            "Un liche menor dirige a los no-muertos. ¿Te atreves con él?"
        ),
        "texto_progreso": "El liche aún mora en las catacumbas. Sé muy precavido.",
        "texto_entrega": "Increíble. Has salvado a la ciudad de una amenaza real. Eres un héroe.",
        "nivel_minimo": 5,
    },
}


# --------------------------------------------------------------------------- #
#  Consulta y búsqueda
# --------------------------------------------------------------------------- #

def buscar_quest(nombre: str) -> tuple[Optional[str], Optional[dict]]:
    """
    Busca una quest por id exacto, título exacto, o coincidencia parcial.
    Normaliza espacios a guiones bajos para coincidir con ids.
    Devuelve (quest_id, quest_dict) o (None, None).
    """
    nombre_lower = nombre.lower().strip()
    nombre_norm = nombre_lower.replace(" ", "_")
    if nombre_lower in QUESTS:
        return nombre_lower, QUESTS[nombre_lower]
    if nombre_norm in QUESTS:
        return nombre_norm, QUESTS[nombre_norm]
    for qid, q in QUESTS.items():
        if nombre_lower == q["titulo"].lower():
            return qid, q
    matches = [(qid, q) for qid, q in QUESTS.items() if nombre_lower in q["titulo"].lower()]
    if len(matches) == 1:
        return matches[0]
    matches = [(qid, q) for qid, q in QUESTS.items()
               if nombre_lower in qid or nombre_norm in qid]
    if len(matches) == 1:
        return matches[0]
    return None, None


def quests_de_npc(npc_key: str) -> list[str]:
    """Devuelve los quest_ids que da este NPC (coincidencia parcial, case-insensitive)."""
    npc_lower = npc_key.lower()
    return [
        qid for qid, q in QUESTS.items()
        if q["dador"].lower() in npc_lower or npc_lower in q["dador"].lower()
    ]


def quests_para_entregar(npc_key: str, quests_personaje: dict) -> list[str]:
    """Quest_ids completados que este NPC recibe."""
    npc_lower = npc_key.lower()
    return [
        qid for qid, q in QUESTS.items()
        if (q["receptor"].lower() in npc_lower or npc_lower in q["receptor"].lower())
        and quests_personaje.get(qid, {}).get("estado") == "completada"
    ]


# --------------------------------------------------------------------------- #
#  Validación
# --------------------------------------------------------------------------- #

def quest_disponible(quest_id: str, nivel: int, quests_personaje: dict) -> tuple[bool, str]:
    """
    Comprueba si una quest está disponible para el personaje.
    Devuelve (disponible, motivo_si_no).
    """
    quest = QUESTS.get(quest_id)
    if not quest:
        return False, "Misión inexistente."
    estado = quests_personaje.get(quest_id, {}).get("estado")
    if estado == "entregada":
        return False, "Ya completaste esta misión."
    if estado in ("activa", "completada"):
        return False, "Ya tienes esta misión en curso."
    if nivel < quest.get("nivel_minimo", 1):
        return False, f"Necesitas nivel {quest['nivel_minimo']} para esta misión."
    return True, ""


# --------------------------------------------------------------------------- #
#  Progreso
# --------------------------------------------------------------------------- #

def registrar_kill(quest_id: str, quests_personaje: dict) -> dict:
    """Incrementa el contador de kills y marca como completada si alcanza el objetivo."""
    quests_personaje = dict(quests_personaje)
    datos = dict(quests_personaje.get(quest_id, {"estado": "activa", "progreso": {}}))
    progreso = dict(datos.get("progreso", {}))
    progreso["kills"] = progreso.get("kills", 0) + 1
    datos["progreso"] = progreso
    quest = QUESTS.get(quest_id)
    if quest and progreso["kills"] >= quest["objetivo"]["cantidad"]:
        datos["estado"] = "completada"
    quests_personaje[quest_id] = datos
    return quests_personaje


def verificar_fetch(quest_id: str, inventario: dict) -> tuple[bool, int]:
    """
    Comprueba si el inventario tiene los items requeridos.
    inventario: {nombre_lower: cantidad}
    Devuelve (completada, cantidad_actual).
    """
    quest = QUESTS.get(quest_id)
    if not quest or quest["tipo"] != "fetch":
        return False, 0
    target = quest["objetivo"]["target"].lower()
    requerido = quest["objetivo"]["cantidad"]
    actual = inventario.get(target, 0)
    return actual >= requerido, actual


def kills_actuales(quest_id: str, quests_personaje: dict) -> int:
    return quests_personaje.get(quest_id, {}).get("progreso", {}).get("kills", 0)


def texto_progreso(quest_id: str, quests_personaje: dict, inventario: Optional[dict] = None) -> str:
    """Devuelve el texto de progreso formateado."""
    quest = QUESTS.get(quest_id)
    if not quest:
        return ""
    tpl = quest["texto_progreso"]
    if quest["tipo"] == "kill":
        actual = kills_actuales(quest_id, quests_personaje)
        total = quest["objetivo"]["cantidad"]
        return tpl.format(actual=actual, total=total)
    if quest["tipo"] == "fetch" and inventario is not None:
        target = quest["objetivo"]["target"].lower()
        requerido = quest["objetivo"]["cantidad"]
        actual = inventario.get(target, 0)
        faltante = max(0, requerido - actual)
        return tpl.format(faltante=faltante, actual=actual, total=requerido)
    return tpl
