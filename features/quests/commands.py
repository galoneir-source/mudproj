"""
features/quests/commands.py

Comandos del sistema de misiones: misiones, aceptar, entregar.
"""
from evennia import Command, CmdSet


# --------------------------------------------------------------------------- #
#  Helpers internos
# --------------------------------------------------------------------------- #

def _buscar_npc_en_sala(caller, npc_key_buscado: str):
    """Busca un NPC por key en la sala (coincidencia parcial, case-insensitive)."""
    if not caller.location:
        return None
    buscado = npc_key_buscado.lower()
    for obj in caller.location.contents:
        if obj == caller:
            continue
        key_lower = obj.key.lower()
        if buscado in key_lower or key_lower in buscado:
            return obj
    return None


def _inventario_dict(caller) -> dict:
    """Devuelve {nombre_lower: cantidad} del inventario del caller."""
    inv: dict = {}
    for obj in caller.contents:
        k = obj.key.lower()
        inv[k] = inv.get(k, 0) + 1
    return inv


def _dar_reputacion(caller, rep_reward: dict):
    """Aplica las recompensas de reputación de un quest y notifica al caller."""
    if not rep_reward:
        return
    from systems.reputation.engine import aplicar_rep_quest
    from systems.reputation.factions import FACCIONES

    rep = dict(getattr(caller.db, "reputacion", {}) or {})
    nueva_rep, cambios = aplicar_rep_quest(rep, rep_reward)
    caller.db.reputacion = nueva_rep

    for faccion_id, delta, titulo, color, cambio_titulo in cambios:
        nombre = FACCIONES.get(faccion_id, {}).get("nombre", faccion_id)
        signo = "+" if delta >= 0 else ""
        caller.msg(f"  Reputación: |y{signo}{delta}|n con |c{nombre}|n → {color}{titulo}|n")
        if cambio_titulo and delta > 0:
            caller.msg(f"  |Y¡Nuevo rango con {nombre}: {titulo}!|n")


def _dar_recompensa(caller, recompensa: dict):
    """Aplica XP, monedas e items de recompensa al caller."""
    from features.combat.handler import _get_stats_base, _set_stat
    from systems.combat.engine import procesar_subida_de_nivel

    xp = recompensa.get("xp", 0)
    monedas = recompensa.get("monedas", 0)
    prototipo = recompensa.get("prototipo")

    if xp:
        xp_actual = getattr(caller.db, "experiencia", 0) or 0
        caller.db.experiencia = xp_actual + xp
        caller.msg(f"|g+{xp} XP|n (Total: {caller.db.experiencia})")
        stats = _get_stats_base(caller)
        subio, nuevos = procesar_subida_de_nivel(stats)
        if subio:
            for k, v in nuevos.items():
                _set_stat(caller, k, v)
            caller.msg(
                f"\n|Y🌟 ¡SUBISTE AL NIVEL {nuevos['nivel']}!|n\n"
                f"  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo\n"
                f"  |gHP restaurado al máximo.|n\n"
            )

    if monedas:
        caller.db.monedas = (getattr(caller.db, "monedas", 0) or 0) + monedas
        caller.msg(f"|y+{monedas} monedas|n (Total: {caller.db.monedas})")

    if prototipo:
        from evennia.prototypes import spawner
        from evennia.utils import logger
        try:
            obj = spawner.spawn(prototipo)[0]
            obj.location = caller
            caller.msg(f"Recibes: |y{obj.key}|n")
        except Exception as err:
            logger.log_err(f"_dar_recompensa: error spawning '{prototipo}': {err}")


# --------------------------------------------------------------------------- #
#  Comando: misiones
# --------------------------------------------------------------------------- #

class CmdMisiones(Command):
    """
    Ver tu registro de misiones activas y completadas.

    Uso:
      misiones
      misiones <nombre>

    Sin argumento muestra el resumen de todas tus misiones.
    Con nombre muestra los detalles y el progreso de esa misión.

    Ejemplos:
      misiones
      misiones problema goblins
    """
    key = "misiones"
    aliases = ["quests", "quest", "log misiones"]
    locks = "cmd:all()"
    help_category = "Misiones"

    def func(self):
        from systems.quests.quests import QUESTS, buscar_quest, texto_progreso
        caller = self.caller
        quests_char = dict(getattr(caller.db, "quests", {}) or {})

        if self.args.strip():
            quest_id, quest = buscar_quest(self.args.strip())
            if not quest:
                caller.msg(f"No se encontró la misión '|w{self.args.strip()}|n'.")
                return
            datos = quests_char.get(quest_id, {})
            estado = datos.get("estado", "desconocido")
            inv = _inventario_dict(caller)
            progreso_txt = texto_progreso(quest_id, quests_char, inv)
            estado_color = {
                "activa": "|yActiva|n",
                "completada": "|g¡Completada!|n (pendiente de entrega)",
                "entregada": "|xEntregada|n",
            }.get(estado, estado)
            recomp = quest["recompensa"]
            recomp_txt = []
            if recomp.get("xp"):
                recomp_txt.append(f"|g{recomp['xp']} XP|n")
            if recomp.get("monedas"):
                recomp_txt.append(f"|y{recomp['monedas']} monedas|n")
            if recomp.get("prototipo"):
                recomp_txt.append(f"|wobjeto especial|n")
            caller.msg(
                f"\n|w{'─'*44}|n\n"
                f"  |c{quest['titulo']}|n\n"
                f"  Estado   : {estado_color}\n"
                f"  Progreso : {progreso_txt}\n"
                f"  Recompensa: {', '.join(recomp_txt)}\n"
                f"\n  {quest['descripcion']}\n"
                f"|w{'─'*44}|n\n"
            )
            return

        activas = [(qid, QUESTS[qid]) for qid, d in quests_char.items()
                   if d.get("estado") == "activa" and qid in QUESTS]
        completadas = [(qid, QUESTS[qid]) for qid, d in quests_char.items()
                       if d.get("estado") == "completada" and qid in QUESTS]
        entregadas = [(qid, QUESTS[qid]) for qid, d in quests_char.items()
                      if d.get("estado") == "entregada" and qid in QUESTS]

        if not quests_char:
            caller.msg("No tienes misiones activas. Habla con los NPCs para conseguir encargos.")
            return

        lineas = [f"\n|w── Registro de Misiones ──|n"]
        if activas:
            lineas.append("  |yActivas:|n")
            for qid, q in activas:
                lineas.append(f"    |c·|n {q['titulo']}")
        if completadas:
            lineas.append("  |gCompletadas (pendientes de entrega):|n")
            for qid, q in completadas:
                lineas.append(f"    |c·|n {q['titulo']}")
        if entregadas:
            lineas.append("  |xEntregadas:|n")
            for qid, q in entregadas:
                lineas.append(f"    |x·|n {q['titulo']}")
        lineas.append("\nUsa |wmisiones <nombre>|n para ver el progreso.\n")
        caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  Comando: aceptar
# --------------------------------------------------------------------------- #

class CmdAceptar(Command):
    """
    Aceptar una misión de un NPC presente en la sala.

    Uso:
      aceptar <misión>

    El NPC que da la misión debe estar en la misma sala que tú.

    Ejemplos:
      aceptar El Problema de los Goblins
      aceptar goblins
      aceptar mercancía
    """
    key = "aceptar"
    aliases = ["accept"]
    locks = "cmd:all()"
    help_category = "Misiones"

    def func(self):
        from systems.quests.quests import QUESTS, buscar_quest, quest_disponible, quests_de_npc
        caller = self.caller

        if not self.args.strip():
            caller.msg("¿Qué misión quieres aceptar? Uso: |waceptar <misión>|n")
            return

        quest_id, quest = buscar_quest(self.args.strip())
        if not quest:
            caller.msg(
                f"No se encontró la misión '|w{self.args.strip()}|n'. "
                f"Habla con los NPCs para descubrir misiones disponibles."
            )
            return

        nivel = getattr(caller.db, "nivel", 1) or 1
        quests_char = dict(getattr(caller.db, "quests", {}) or {})
        disponible, motivo = quest_disponible(quest_id, nivel, quests_char)
        if not disponible:
            caller.msg(f"No puedes aceptar esta misión: {motivo}")
            return

        # El NPC dador debe estar en la sala
        npc = _buscar_npc_en_sala(caller, quest["dador"])
        if not npc:
            caller.msg(
                f"Necesitas hablar con |w{quest['dador']}|n para aceptar esta misión."
            )
            return

        # Aceptar
        quests_char[quest_id] = {"estado": "activa", "progreso": {}}
        caller.db.quests = quests_char

        caller.msg(
            f"\n{npc.key}: \"|w{quest['texto_oferta']}|n\"\n"
            f"|g¡Misión aceptada!|n |c{quest['titulo']}|n\n"
            f"Usa |wmisiones {quest['titulo']}|n para ver el progreso.\n"
        )
        caller.location.msg_contents(
            f"{caller.key} acepta una misión de {npc.key}.",
            exclude=caller,
        )


# --------------------------------------------------------------------------- #
#  Comando: entregar
# --------------------------------------------------------------------------- #

class CmdEntregar(Command):
    """
    Entregar una misión completada a su NPC receptor.

    Uso:
      entregar <misión>

    El NPC receptor debe estar en la misma sala. Para misiones de entrega
    de objetos, los items serán consumidos automáticamente.

    Ejemplos:
      entregar veneno del pantano
      entregar mercancía robada
    """
    key = "entregar"
    aliases = ["turnin", "completar misión"]
    locks = "cmd:all()"
    help_category = "Misiones"

    def func(self):
        from systems.quests.quests import QUESTS, buscar_quest, verificar_fetch
        caller = self.caller

        if not self.args.strip():
            caller.msg("¿Qué misión quieres entregar? Uso: |wentregar <misión>|n")
            return

        quest_id, quest = buscar_quest(self.args.strip())
        if not quest:
            caller.msg(f"No se encontró la misión '|w{self.args.strip()}|n'.")
            return

        quests_char = dict(getattr(caller.db, "quests", {}) or {})
        datos = quests_char.get(quest_id, {})
        estado = datos.get("estado")

        if not estado:
            caller.msg("No tienes esta misión activa.")
            return
        if estado == "entregada":
            caller.msg("Ya entregaste esta misión.")
            return

        # Para fetch quests: comprobar inventario en el momento de entregar
        if quest["tipo"] == "fetch" and estado == "activa":
            inv = _inventario_dict(caller)
            ok, actual = verificar_fetch(quest_id, inv)
            if not ok:
                requerido = quest["objetivo"]["cantidad"]
                target = quest["objetivo"]["target"]
                caller.msg(
                    f"Aún te faltan objetos: necesitas {requerido}x |w{target}|n "
                    f"y tienes {actual}."
                )
                return
            # Marcar como completada para poder proceder
            datos = dict(datos)
            datos["estado"] = "completada"
            quests_char[quest_id] = datos

        if quests_char.get(quest_id, {}).get("estado") != "completada":
            caller.msg("Aún no has completado esta misión.")
            return

        # El NPC receptor debe estar en la sala
        npc = _buscar_npc_en_sala(caller, quest["receptor"])
        if not npc:
            caller.msg(
                f"Necesitas hablar con |w{quest['receptor']}|n para entregar esta misión."
            )
            return

        # Consumir items para fetch quests
        if quest["tipo"] == "fetch":
            target = quest["objetivo"]["target"].lower()
            requerido = quest["objetivo"]["cantidad"]
            consumidos = 0
            for obj in list(caller.contents):
                if consumidos >= requerido:
                    break
                if obj.key.lower() == target:
                    obj.delete()
                    consumidos += 1

        # Dar recompensa
        _dar_recompensa(caller, quest.get("recompensa", {}))
        _dar_reputacion(caller, quest.get("rep_reward", {}))

        # Marcar como entregada
        quests_char[quest_id] = dict(quests_char.get(quest_id, {}))
        quests_char[quest_id]["estado"] = "entregada"
        caller.db.quests = quests_char

        caller.msg(f"\n{npc.key}: \"|w{quest['texto_entrega']}|n\"\n")
        caller.location.msg_contents(
            f"{caller.key} completa la misión '{quest['titulo']}'.",
            exclude=caller,
        )

        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class QuestCmdSet(CmdSet):
    key = "QuestCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdMisiones())
        self.add(CmdAceptar())
        self.add(CmdEntregar())
