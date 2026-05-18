"""
commands/general_commands.py

Comandos generales de interacción que no pertenecen a combate ni puertas:
  hablar    — dirigirse a un NPC y activar su sistema de diálogo
  descansar — recuperar HP fuera de combate
  perfil    — ficha completa del personaje
  percibir  — inspección activa de la sala para detectar detalles ocultos
"""

import time
from evennia import Command, CmdSet
from systems.utils import barra as _barra


# --------------------------------------------------------------------------- #
#  Comando: hablar
# --------------------------------------------------------------------------- #

class CmdHablar(Command):
    """
    Hablar con un NPC presente en la sala.

    Uso:
      hablar <npc>
      hablar <npc> = <mensaje>

    Sin mensaje muestra los temas de conversación disponibles del NPC.
    Con mensaje intenta obtener una respuesta basada en las palabras clave
    del NPC.

    Ejemplos:
      hablar guardia
      hablar guardia = hola
      hablar mesonero = bebida
    """
    key = "hablar"
    aliases = ["talk", "conversar"]
    locks = "cmd:all()"
    help_category = "Interacción"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("¿Con quién quieres hablar? Uso: |whablar <npc>|n")
            return

        # Separar "npc = mensaje" si hay '='
        if "=" in self.args:
            partes = self.args.split("=", 1)
            nombre_npc = partes[0].strip()
            mensaje = partes[1].strip()
        else:
            nombre_npc = self.args.strip()
            mensaje = None

        objetivo = caller.search(nombre_npc, location=caller.location)
        if not objetivo:
            return

        # Solo funciona con NPCs (objetos con dialogo definido)
        dialogo = getattr(objetivo.db, "dialogo", None)
        if dialogo is None:
            caller.msg(f"{objetivo.key} no parece querer hablar.")
            return

        if not mensaje:
            # Mostrar temas disponibles
            if dialogo:
                temas = ", ".join(f"|w{k}|n" for k in dialogo.keys())
                caller.msg(
                    f"{objetivo.key} puede responder sobre: {temas}\n"
                    f"Usa |whablar {nombre_npc} = <tema>|n para hablar."
                )
            else:
                caller.msg(f"{objetivo.key} asiente pero no dice nada.")
            # Hint de misiones disponibles desde este NPC
            from systems.quests.quests import quests_de_npc, quest_disponible, QUESTS
            nivel = getattr(caller.db, "nivel", 1) or 1
            quests_char = getattr(caller.db, "quests", {}) or {}
            ids_disponibles = [
                qid for qid in quests_de_npc(objetivo.key)
                if quest_disponible(qid, nivel, quests_char)[0]
            ]
            ids_entregar = [
                qid for qid in quests_de_npc(objetivo.key)
                if quests_char.get(qid, {}).get("estado") == "completada"
            ]
            if ids_entregar:
                titulos = ", ".join(f"|g{QUESTS[q]['titulo']}|n" for q in ids_entregar)
                caller.msg(f"|g¡Tienes misiones listas para entregar!|n {titulos}")
            if ids_disponibles:
                caller.msg(
                    f"|y{objetivo.key} tiene misiones disponibles.|n "
                    f"Usa |whablar {nombre_npc} = misión|n para conocerlas."
                )
            return

        # Keyword especial: mostrar misiones del NPC
        if mensaje.lower() in ("misión", "mision", "misiones", "quest", "trabajo", "encargo"):
            self._mostrar_misiones_npc(objetivo, caller, nombre_npc)
            return

        # Enviar el mensaje al NPC para que su at_msg_receive lo procese
        caller.location.msg_contents(
            f"|w{caller.key}|n le dice a {objetivo.key}: \"{mensaje}\"",
            exclude=caller,
        )
        caller.msg(f"Le dices a {objetivo.key}: \"{mensaje}\"")
        objetivo.at_msg_receive(mensaje, from_obj=caller)

    def _mostrar_misiones_npc(self, npc, caller, nombre_npc):
        from systems.quests.quests import QUESTS, quests_de_npc, quest_disponible, quests_para_entregar
        nivel = getattr(caller.db, "nivel", 1) or 1
        quests_char = dict(getattr(caller.db, "quests", {}) or {})

        ids_npc = quests_de_npc(npc.key)
        disponibles = [qid for qid in ids_npc if quest_disponible(qid, nivel, quests_char)[0]]
        activas = [qid for qid in ids_npc if quests_char.get(qid, {}).get("estado") == "activa"]
        entregables = quests_para_entregar(npc.key, quests_char)

        lineas = [f"\n{npc.key} te mira y habla:"]

        if entregables:
            lineas.append("  |g¡Tienes misiones listas para entregar!|n")
            for qid in entregables:
                lineas.append(f"    |c·|n {QUESTS[qid]['titulo']}  — |wentregar {QUESTS[qid]['titulo']}|n")

        if activas:
            lineas.append("  |yMisiones en curso:|n")
            for qid in activas:
                lineas.append(f"    |c·|n {QUESTS[qid]['titulo']}  — |wmisiones {QUESTS[qid]['titulo']}|n")

        if disponibles:
            lineas.append("  |wMisiones disponibles:|n")
            for qid in disponibles:
                q = QUESTS[qid]
                lineas.append(
                    f"    |c·|n {q['titulo']} (Nv.{q['nivel_minimo']}+)\n"
                    f"       \"{q['texto_oferta']}\"\n"
                    f"       |waceptar {q['titulo']}|n para aceptar."
                )

        if not disponibles and not activas and not entregables:
            lineas.append("  \"No tengo nada para ti en este momento.\"")

        lineas.append("")
        caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  Comando: descansar
# --------------------------------------------------------------------------- #

DESCANSO_COOLDOWN = 60   # segundos entre descansos
DESCANSO_RECUPERA = 0.25  # fracción de hp_max que se recupera


class CmdDescansar(Command):
    """
    Descansar para recuperar puntos de vida.

    Uso:
      descansar

    Solo funciona fuera de combate. Recupera el 25 % de tu HP máximo.
    Tiene un tiempo de espera de 60 segundos entre usos.
    """
    key = "descansar"
    aliases = ["rest", "recuperar"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        # Verificar que no está en combate
        from features.combat.commands import _get_combat_handler
        if _get_combat_handler(caller.location):
            caller.msg("¡No puedes descansar mientras estás en combate!")
            return

        # Verificar cooldown
        ahora = time.time()
        ultimo = getattr(caller.ndb, "ultimo_descanso", 0) or 0
        restante = DESCANSO_COOLDOWN - (ahora - ultimo)
        if restante > 0:
            caller.msg(
                f"Necesitas esperar |w{int(restante)}|n segundos antes de poder descansar."
            )
            return

        hp = getattr(caller.db, "hp", None)
        hp_max = getattr(caller.db, "hp_max", None)

        if hp is None or hp_max is None:
            caller.msg("No puedes descansar.")
            return

        if hp >= hp_max:
            caller.msg("Ya estás en perfectas condiciones. No necesitas descansar.")
            return

        # Recuperar HP
        recuperado = max(1, int(hp_max * DESCANSO_RECUPERA))
        nuevo_hp = min(hp_max, hp + recuperado)
        caller.db.hp = nuevo_hp
        caller.ndb.ultimo_descanso = ahora

        caller.msg(
            f"Descansas un momento y recuperas |g{recuperado}|n puntos de vida. "
            f"HP: |w{nuevo_hp}/{hp_max}|n"
        )
        caller.location.msg_contents(
            f"{caller.key} descansa y recupera fuerzas.",
            exclude=caller,
        )


# --------------------------------------------------------------------------- #
#  Comando: perfil
# --------------------------------------------------------------------------- #

class CmdPerfil(Command):
    """
    Ver la ficha completa de tu personaje.

    Uso:
      perfil
      perfil <personaje>   (solo Builder/Admin puede ver perfiles ajenos)

    Muestra nombre, nivel, XP, estadísticas, habilidades y estado de salud.
    """
    key = "perfil"
    aliases = ["ficha", "who am i", "profile"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if args and (caller.check_permstring("Builder") or caller.check_permstring("Admin")):
            objetivo = caller.search(args)
            if not objetivo:
                return
        else:
            objetivo = caller

        from systems.combat.engine import STAT_DEFAULTS, xp_para_siguiente_nivel

        def _s(k):
            val = getattr(objetivo.db, k, None)
            return val if val is not None else STAT_DEFAULTS.get(k, "?")

        hp      = _s("hp")
        hp_max  = _s("hp_max")
        nivel   = _s("nivel")
        xp      = _s("experiencia")
        xp_sig  = xp_para_siguiente_nivel(nivel)
        fuerza  = _s("fuerza")
        destrez = _s("destreza")
        consti  = _s("constitucion")
        inteli  = _s("inteligencia")
        defensa = _s("defensa")
        desbloqueadas = set(getattr(objetivo.db, "habilidades_desbloqueadas", []) or [])
        if desbloqueadas:
            from systems.skills.trees import HABILIDADES as _H
            habilidades = [_H.get(h, {}).get("nombre", h) for h in sorted(desbloqueadas)]
        else:
            habilidades = getattr(objetivo.db, "habilidades", []) or []
        faction = getattr(objetivo.db, "faction", None)
        temperamento = getattr(objetivo.db, "temperamento", None)

        # Barra de HP
        hp_pct = hp / max(hp_max, 1)
        if hp_pct > 0.75:
            hp_color = "|g"
            hp_estado = "En perfectas condiciones"
        elif hp_pct > 0.50:
            hp_color = "|y"
            hp_estado = "Ligeramente herido"
        elif hp_pct > 0.25:
            hp_color = "|y"
            hp_estado = "Muy herido"
        else:
            hp_color = "|r"
            hp_estado = "Al borde de la muerte"

        hp_bar = _barra(hp, hp_max, 24, hp_color)
        xp_bar = _barra(xp, xp_sig, 24, "|c")

        lineas = [
            f"\n|w{'─'*44}|n",
            f"  |cNombre:|n  {objetivo.key}",
        ]
        if faction:
            lineas.append(f"  |cFacción:|n  {faction}")
        if temperamento and objetivo != caller:
            lineas.append(f"  |cTemperamento:|n {temperamento}")

        lineas += [
            f"|w{'─'*44}|n",
            f"  |cNivel:|n  {nivel}",
            f"  XP:     {xp} / {xp_sig}",
            f"  {xp_bar}",
            f"",
            f"  |rVida:|n  {hp_color}{hp}/{hp_max}|n  — {hp_estado}",
            f"  {hp_bar}",
            f"",
            f"  |w{'─'*22}  Estadísticas  {'─'*4}|n",
            f"  |wFuerza      |n {fuerza:>3}   |wDestreza    |n {destrez:>3}",
            f"  |wConstitución|n {consti:>3}   |wInteligencia|n {inteli:>3}",
            f"  |wDefensa     |n {defensa:>3}",
        ]

        if habilidades:
            lineas += [
                f"",
                f"  |cHabilidades:|n {', '.join(habilidades)}",
            ]

        estados = getattr(objetivo.db, "estados", {}) or {}
        if estados:
            _display = {"veneno": "|rveneno|n", "sangrado": "|rsangrado|n", "regeneracion": "|gRegeneración|n"}
            estados_txt = ", ".join(
                f"{_display.get(n, n)} ({d.get('turnos_restantes', '?')} turnos)"
                for n, d in estados.items()
            )
            lineas += ["", f"  |cEstados:|n  {estados_txt}"]

        lineas.append(f"|w{'─'*44}|n\n")
        caller.msg("\n".join(lineas))




# --------------------------------------------------------------------------- #
#  Comando: usar
# --------------------------------------------------------------------------- #

class CmdUsar(Command):
    """
    Usar un objeto consumible del inventario (poción, elixir, antídoto...).

    Uso:
      usar <objeto>

    Ejemplos:
      usar poción de vida
      usar antídoto
    """
    key = "usar"
    aliases = ["use", "consumir", "beber", "tomar"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("¿Qué quieres usar? Uso: |wusar <objeto>|n")
            return

        obj = caller.search(self.args.strip(), location=caller)
        if not obj:
            return

        from typeclasses.objects import Consumible
        if not isinstance(obj, Consumible):
            caller.msg(f"|w{obj.key}|n no es algo que puedas consumir.")
            return

        caller.location.msg_contents(
            f"{caller.key} usa {obj.key}.",
            exclude=caller,
        )

        if obj.consumir(caller):
            caller.msg(f"El |w{obj.key}|n se ha agotado.")
            obj.delete()


# --------------------------------------------------------------------------- #
#  Comando: percibir
# --------------------------------------------------------------------------- #

class CmdPercibir(Command):
    """
    Examinar la sala con atención para descubrir detalles y entidades ocultas.

    Uso:
      percibir

    Tu nivel de percepción depende de tu inteligencia y tu nivel de personaje.
    Cuanto mayor sea, más detalles podrás descubrir.
    """
    key = "percibir"
    aliases = ["examinar", "inspect", "buscar"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        room = caller.location
        if not room:
            caller.msg("No estás en ningún lugar.")
            return

        from systems.perception.perception_manager import PerceptionManager
        pm = PerceptionManager()
        nivel = pm.nivel_percepcion(caller)

        hallazgos = []

        # 1. Detalles ocultos de la sala
        detalles = pm.revelar_detalles(room, caller)
        hallazgos.extend(detalles)

        # 2. NPCs/objetos ocultos que el personaje puede detectar
        from typeclasses.npc import NPC
        for obj in room.contents:
            if obj == caller:
                continue
            if not getattr(obj.db, "oculto", False):
                continue
            if pm.puede_detectar(caller, obj):
                if isinstance(obj, NPC):
                    hallazgos.append(
                        f"Detectas a |r{obj.key}|n acechando en las sombras. (Nv.{obj.db.nivel or 1})"
                    )
                else:
                    hallazgos.append(f"Descubres |y{obj.key}|n oculto aquí.")

        caller.msg(f"Examinas la sala con atención... |c(Percepción: {nivel})|n")

        if hallazgos:
            caller.msg("\n".join(f"  |w»|n {h}" for h in hallazgos))
        else:
            if nivel < 12:
                caller.msg("  No notas nada especial. Quizás con más experiencia...")
            elif nivel < 16:
                caller.msg("  Examinas cada rincón pero no encuentras nada inusual.")
            else:
                caller.msg("  Tu aguda percepción no detecta nada oculto aquí.")

        # Notificar a la sala (sin revelar qué encontró)
        room.msg_contents(
            f"{caller.key} examina la sala con atención.",
            exclude=caller,
        )


# --------------------------------------------------------------------------- #
#  Comando: inventario (reemplaza al de Evennia)
# --------------------------------------------------------------------------- #

class CmdInventario(Command):
    """
    Ver tu inventario completo.

    Uso:
      inventario
      inv

    Muestra los objetos equipados (con sus bonificaciones) y los que
    llevas en la mochila, agrupados por tipo.
    """
    key = "inventory"
    aliases = ["inventario", "inv", "i"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        from typeclasses.objects import Equipo, Key
        from features.equipment.commands import _get_equipamiento, SLOTS

        eq = _get_equipamiento(caller)

        lineas = [f"\n|w{'─'*44}|n", f"  |cInventario de {caller.key}|n", f"|w{'─'*44}|n"]

        # ── SECCIÓN EQUIPADO ──────────────────────────────────────────────
        lineas.append("  |wEQUIPADO|n")
        for slot in SLOTS:
            item = eq.get(slot)
            if item:
                bonuses = item.db.bonuses or {}
                bonus_txt = ""
                if bonuses:
                    bonus_txt = "  |x(" + ", ".join(f"{k}+{v}" for k, v in bonuses.items()) + ")|n"
                lineas.append(f"  |c{'·':>2} {slot:<10}|n |w{item.key}|n{bonus_txt}")
            else:
                lineas.append(f"  |c{'·':>2} {slot:<10}|n |x(vacío)|n")

        # ── SECCIÓN MOCHILA ───────────────────────────────────────────────
        equipped_ids = {item.id for item in eq.values() if item}
        mochila = [
            obj for obj in caller.contents
            if obj.id not in equipped_ids
            and not getattr(obj, "destination", None)  # excluir exits
        ]

        lineas.append(f"\n  |wMOCHILA|n  ({len(mochila)} {'objeto' if len(mochila) == 1 else 'objetos'})")

        if not mochila:
            lineas.append("  |x  (vacía)|n")
        else:
            from typeclasses.objects import Consumible
            # Agrupar: equipo no equipado, llaves, consumibles, misc
            grupo_equipo      = [o for o in mochila if isinstance(o, Equipo)]
            grupo_llaves      = [o for o in mochila if isinstance(o, Key)]
            grupo_consumibles = [o for o in mochila if isinstance(o, Consumible)]
            grupo_misc        = [o for o in mochila if not isinstance(o, (Equipo, Key, Consumible))]

            for item in grupo_equipo:
                bonuses = item.db.bonuses or {}
                bonus_txt = ""
                if bonuses:
                    bonus_txt = "  |x(" + ", ".join(f"{k}+{v}" for k, v in bonuses.items()) + ")|n"
                slot = item.db.slot or "?"
                lineas.append(f"  |c{'·':>2}|n |c[{slot}]|n |w{item.key}|n{bonus_txt}")

            for item in grupo_llaves:
                keycode = item.db.keycode or ""
                is_master = item.db.is_master or False
                info = " |x(maestra)|n" if is_master else (f" |x({keycode})|n" if keycode else "")
                lineas.append(f"  |c{'·':>2}|n |c[llave]|n  |w{item.key}|n{info}")

            for item in grupo_consumibles:
                efecto = item.db.efecto or "curar_hp"
                potencia = item.db.potencia or 0
                usos = item.db.usos
                efecto_txt = {
                    "curar_hp": f"+{potencia} HP",
                    "curar_maximo": "HP máx.",
                    "curar_veneno": "antivnm.",
                }.get(efecto, efecto)
                usos_txt = f" |xx{usos}|n" if usos != 1 and usos != -1 else ""
                lineas.append(
                    f"  |c{'·':>2}|n |c[consumible]|n |w{item.key}|n"
                    f"  |x({efecto_txt})|n{usos_txt}"
                )

            # Agrupar misc por nombre para mostrar cantidades
            conteo: dict = {}
            for item in grupo_misc:
                conteo.setdefault(item.key, []).append(item)
            for nombre, items in sorted(conteo.items()):
                cantidad = len(items)
                desc = getattr(items[0].db, "desc", "") or ""
                desc_corta = f"  |x{desc[:40]}{'...' if len(desc) > 40 else ''}|n" if desc else ""
                cant_txt = f" |xx{cantidad}|n" if cantidad > 1 else ""
                lineas.append(f"  |c{'·':>2}|n          |w{nombre}|n{cant_txt}{desc_corta}")

        lineas.append(f"|w{'─'*44}|n\n")
        caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  CmdSet general
# --------------------------------------------------------------------------- #

class GeneralCmdSet(CmdSet):
    key = "GeneralCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdHablar())
        self.add(CmdDescansar())
        self.add(CmdPerfil())
        self.add(CmdPercibir())
        self.add(CmdInventario())
        self.add(CmdUsar())
