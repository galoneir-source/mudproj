"""
features/combat/handler.py

CombatHandler: Script de Evennia que gestiona un combate activo en una sala.
- Mantiene la cola de turnos
- Lanza el temporizador de turno
- Resuelve acciones y notifica a los participantes
"""
from evennia import DefaultScript
from evennia.utils import logger
from systems.combat.engine import (
    resolver_ataque, calcular_xp_recompensa,
    procesar_subida_de_nivel, STAT_DEFAULTS, efecto_postcombat,
)


TURNO_TIMEOUT = 15   # segundos antes de acción automática (pasar turno)
INTERVALO_TURNO = 1  # segundos entre comprobaciones internas


def _get_stats(obj) -> dict:
    """Lee stats de combate de un objeto Evennia."""
    stats = {}
    for key, default in STAT_DEFAULTS.items():
        stats[key] = getattr(obj.db, key, None)
        if stats[key] is None:
            stats[key] = default
    return stats


def _set_stat(obj, key: str, value):
    setattr(obj.db, key, value)


def _generar_loot(muerto, sala) -> list:
    """
    Lee db.loot del NPC muerto y genera los items en la sala.

    Formato de cada entrada en db.loot:
      {
        "key": "monedas de cobre",       # nombre del item (obligatorio)
        "cantidad": 3,                   # cuántos crear (default: 1)
        "chance": 1.0,                   # probabilidad 0.0-1.0 (default: 1.0)
        "prototype_key": "ESPADA_HIERRO",# spawn desde prototipo (opcional)
        "typeclass": "typeclasses.objects.Object",  # typeclass custom (opcional)
        "desc": "...",                   # descripción del item (opcional)
      }

    Devuelve lista de objetos creados.
    """
    import random
    from evennia.utils.create import create_object as _create_object

    loot_tabla = getattr(muerto.db, "loot", None) or []
    if not loot_tabla:
        return []

    creados = []
    for entrada in loot_tabla:
        if not hasattr(entrada, "get"):
            continue

        chance = float(entrada.get("chance", 1.0))
        if random.random() > chance:
            continue

        cantidad = int(entrada.get("cantidad", 1))
        prototype_key = entrada.get("prototype_key")
        item_key = entrada.get("key", "objeto")
        typeclass = entrada.get("typeclass", "typeclasses.objects.Object")
        desc = entrada.get("desc")

        for _ in range(cantidad):
            try:
                if prototype_key:
                    from evennia.prototypes import spawner
                    obj = spawner.spawn(prototype_key)[0]
                    obj.location = sala
                else:
                    obj = _create_object(typeclass, key=item_key, location=sala)
                    if desc:
                        obj.db.desc = desc
                creados.append(obj)
            except Exception as err:
                from evennia.utils import logger
                logger.log_err(f"_generar_loot: error creando '{item_key}': {err}")

    return creados


class CombatHandler(DefaultScript):
    """
    Script que vive en una sala y gestiona el combate por turnos.
    Se crea automáticamente al iniciar un combate y se destruye al terminar.
    """

    def at_script_creation(self):
        self.key = "combat_handler"
        self.desc = "Gestor de combate activo"
        self.interval = INTERVALO_TURNO
        self.persistent = False
        self.db.participantes = []      # lista de objetos (orden de turno)
        self.db.turno_actual = 0        # índice en participantes
        self.db.acciones = {}           # {dbref: {"tipo": ..., "objetivo": ..., "habilidad": ...}}
        self.db.turno_tiempo = 0        # segundos transcurridos en el turno actual
        self.db.activo = True

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def iniciar(self, participantes: list):
        """Inicia el combate con la lista de participantes."""
        self.db.participantes = list(participantes)
        self.db.turno_actual = 0
        self.db.acciones = {}
        self.db.turno_tiempo = 0
        self.db.activo = True

        for p in participantes:
            if hasattr(p, "db"):
                p.db.en_combate = True

        sala = self.obj
        nombres = ", ".join(p.key for p in participantes)
        sala.msg_contents(
            f"\n|r⚔  ¡COMIENZA EL COMBATE!|n\n"
            f"Participantes: {nombres}\n"
            f"Orden de turno determinado.\n"
        )
        self._anunciar_turno()

    def registrar_accion(self, actor, tipo: str, objetivo=None, habilidad: str = None):
        """
        Registra la acción de un participante para este turno.
        tipo: 'atacar' | 'habilidad' | 'huir' | 'pasar'
        """
        if not self.db.activo:
            actor.msg("No hay ningún combate activo.")
            return

        turno_obj = self._participante_actual()
        if turno_obj != actor:
            actor.msg(f"|yAún no es tu turno.|n Espera a que {turno_obj.key} actúe.")
            return

        self.db.acciones[actor.dbref] = {
            "tipo": tipo,
            "objetivo": objetivo,
            "habilidad": habilidad,
        }
        self._resolver_turno()

    def agregar_participante(self, obj):
        """Añade un participante al combate en curso."""
        if obj not in self.db.participantes:
            self.db.participantes.append(obj)
            if hasattr(obj, "db"):
                obj.db.en_combate = True

    def eliminar_participante(self, obj):
        """Elimina un participante (muerto o huido)."""
        # Trabajar sobre una COPIA para forzar el guardado en la BD de Evennia
        parts = list(self.db.participantes)
        if obj in parts:
            parts.remove(obj)
            self.db.participantes = parts  # asignación explícita → persiste
            # Ajustar índice de turno
            if self.db.turno_actual >= len(parts):
                self.db.turno_actual = 0

        if len(parts) <= 1:
            self._terminar_combate()

    # ------------------------------------------------------------------ #
    #  Tick periódico (timeout de turno)
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        if not self.db.activo:
            return
        self.db.turno_tiempo = (self.db.turno_tiempo or 0) + INTERVALO_TURNO
        if self.db.turno_tiempo >= TURNO_TIMEOUT:
            actor = self._participante_actual()
            if actor:
                actor.msg("|yTiempo agotado. Pasas tu turno automáticamente.|n")
                self.db.acciones[actor.dbref] = {"tipo": "pasar", "objetivo": None, "habilidad": None}
                self._resolver_turno()

    # ------------------------------------------------------------------ #
    #  Lógica interna
    # ------------------------------------------------------------------ #

    def _participante_actual(self):
        parts = self.db.participantes or []
        if not parts:
            return None
        idx = self.db.turno_actual % len(parts)
        return parts[idx]

    def _anunciar_turno(self):
        actor = self._participante_actual()
        if not actor:
            return

        # Ticks de estado al inicio del turno; si muere, no anunciar
        if self._aplicar_ticks_estado(actor):
            return

        sala = self.obj
        sala.msg_contents(f"\n|w▶ Turno de: {actor.key}|n")
        # Mostrar opciones al jugador (si tiene sesión)
        if actor.has_account:
            enemigos = [p for p in self.db.participantes if p != actor]
            nombres_enemigos = ", ".join(e.key for e in enemigos)
            actor.msg(
                f"  |cAcciones disponibles:|n\n"
                f"  |watacar <objetivo>|n  — ataque básico\n"
                f"  |whabilidad <nombre> <objetivo>|n  — habilidad especial\n"
                f"  |whuir|n  — intentar escapar\n"
                f"  |wpasar|n  — pasar turno\n"
                f"  Enemigos: {nombres_enemigos}"
            )
        else:
            # NPC — IA reactiva compleja (llamada diferida para no bloquear)
            from evennia.utils import delay
            delay(1, self._ia_npc, actor)

    def _resolver_turno(self):
        actor = self._participante_actual()
        if not actor:
            return
        accion = self.db.acciones.get(actor.dbref, {})
        tipo = accion.get("tipo", "pasar")
        objetivo = accion.get("objetivo")
        habilidad = accion.get("habilidad")

        sala = self.obj

        if tipo == "pasar":
            sala.msg_contents(f"{actor.key} pasa su turno.")

        elif tipo in ("atacar", "habilidad"):
            # Comparar por dbref para sobrevivir recargas del servidor donde
            # Evennia puede devolver nuevos objetos proxy para la misma fila DB.
            partes_dbrefs = {p.dbref for p in (self.db.participantes or [])}
            if not objetivo or objetivo.dbref not in partes_dbrefs:
                actor.msg("Objetivo inválido. Pasas el turno.")
            else:
                stats_at = _get_stats(actor)
                stats_def = _get_stats(objetivo)
                resultado = resolver_ataque(
                    stats_at, stats_def,
                    actor.key, objetivo.key,
                    habilidad if tipo == "habilidad" else None,
                )
                actor.msg(resultado.mensaje_atacante)
                objetivo.msg(resultado.mensaje_defensor)
                # Mensaje a la sala (excluyendo atacante y defensor)
                for p in sala.contents:
                    if p not in (actor, objetivo) and hasattr(p, "msg"):
                        p.msg(resultado.mensaje_sala)

                if resultado.exito:
                    _set_stat(objetivo, "hp", resultado.hp_restante)

                # Efecto drenar vida: cura al atacante el 50% del daño
                if (tipo == "habilidad" and habilidad and resultado.exito
                        and not resultado.muerto):
                    efecto = efecto_postcombat(habilidad)
                    if efecto == "drenar_vida":
                        cura = max(1, resultado.dano // 2)
                        hp_act = getattr(actor.db, "hp", 0) or 0
                        hp_max = getattr(actor.db, "hp_max", 100) or 100
                        nuevo_hp = min(hp_max, hp_act + cura)
                        actor.db.hp = nuevo_hp
                        actor.msg(f"|gDrenas {cura} HP de vida.|n (HP: {nuevo_hp}/{hp_max})")

                # Aplicar estado si la habilidad lo produce (solo en golpe exitoso y no letal)
                if resultado.exito and not resultado.muerto and resultado.estado_aplicado:
                    from systems.combat.states import aplicar_estado
                    nombre_estado = resultado.estado_aplicado
                    estados = dict(getattr(objetivo.db, "estados", {}) or {})
                    objetivo.db.estados = aplicar_estado(estados, nombre_estado)
                    display = {"veneno": "veneno", "sangrado": "sangrado"}.get(nombre_estado, nombre_estado)
                    objetivo.msg(f"|r¡Has sido afectado por {display}!|n")
                    actor.msg(f"|y{objetivo.key} ha sido afectado por {display}.|n")

                if resultado.muerto:
                    self._procesar_muerte(objetivo, asesino=actor)
                    return

        elif tipo == "huir":
            self._intentar_huida(actor)
            return

        # Avanzar al siguiente turno
        self._siguiente_turno()

    def _siguiente_turno(self):
        """Avanza al siguiente participante."""
        self.db.acciones = {}
        self.db.turno_tiempo = 0
        parts = self.db.participantes
        if not parts:
            return
        self.db.turno_actual = (self.db.turno_actual + 1) % len(parts)
        self._anunciar_turno()

    def _procesar_muerte(self, muerto, asesino=None):
        sala = self.obj
        sala.msg_contents(f"\n|r💀 {muerto.key} ha caído en combate.|n\n")

        # Recompensa de XP
        if asesino:
            xp = calcular_xp_recompensa(getattr(muerto.db, "nivel", 1) or 1)
            xp_actual = getattr(asesino.db, "experiencia", 0) or 0
            asesino.db.experiencia = xp_actual + xp
            asesino.msg(f"|g+{xp} XP|n (Total: {asesino.db.experiencia})")

            # Subida de nivel
            stats = _get_stats(asesino)
            subio, nuevos_stats = procesar_subida_de_nivel(stats)
            if subio:
                for k, v in nuevos_stats.items():
                    _set_stat(asesino, k, v)
                asesino.msg(
                    f"\n|Y🌟 ¡SUBISTE AL NIVEL {nuevos_stats['nivel']}!|n\n"
                    f"  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo\n"
                    f"  |g+1 punto de habilidad disponible|n  (usa |whabilidades|n)\n"
                    f"  |gHP restaurado al máximo.|n\n"
                )

        # Loot: objetos ya en el inventario del NPC
        for obj in list(getattr(muerto, "contents", []) or []):
            obj.move_to(sala, quiet=True)

        # Progreso de quests de kill
        if asesino and getattr(asesino, "has_account", False):
            from features.quests.hooks import on_npc_muerte
            on_npc_muerte(asesino, muerto)

        # Loot: generar items desde la tabla db.loot
        items_generados = _generar_loot(muerto, sala)
        if items_generados:
            nombres = ", ".join(f"|y{o.key}|n" for o in items_generados)
            sala.msg_contents(f"{muerto.key} ha dejado caer: {nombres}.")

        # Si es NPC → programar respawn y eliminarlo del mundo
        if not muerto.has_account:
            muerto.db.hp = 0
            self._limpiar_estado_combate(muerto)

            # Programar respawn ANTES de delete (necesitamos leer atributos del NPC)
            from features.respawn.respawn import programar_respawn
            programar_respawn(sala, muerto)

            combate_continuaba = bool(self.db.activo)
            self.eliminar_participante(muerto)
            muerto.delete()
            if combate_continuaba and self.db.activo:
                self._siguiente_turno()
        else:
            # Jugador → enviarlo a sala de inicio con HP mínimo
            self._limpiar_estado_combate(muerto)
            muerto.db.hp = 1
            combate_continuaba = bool(self.db.activo)
            self.eliminar_participante(muerto)
            home = muerto.home or muerto.location
            muerto.move_to(home, quiet=True)
            muerto.msg(
                "|rHas caído en combate.|n Despiertas débil en tu lugar de inicio."
            )
            # Avanzar turno solo si el combate sigue activo tras la eliminación
            if combate_continuaba and self.db.activo:
                self._siguiente_turno()

    def _limpiar_estado_combate(self, participante):
        """Resetea el estado de combate de un participante (jugador o NPC)."""
        if hasattr(participante, "db"):
            participante.db.en_combate = False
            participante.db.enraged = False

    def _intentar_huida(self, actor):
        import random
        sala = self.obj
        if random.random() < 0.50:
            # Buscar salida antes de eliminar del combate
            salidas = [o for o in sala.contents if hasattr(o, "destination") and o.destination]
            if not salidas:
                actor.msg("|yIntentas huir pero no hay salida por donde escapar.|n")
                self._siguiente_turno()
                return
            sala.msg_contents(f"{actor.key} |yhuyó del combate!|n")
            self._limpiar_estado_combate(actor)
            self.eliminar_participante(actor)
            destino = random.choice(salidas).destination
            actor.move_to(destino, quiet=False)
            actor.msg("|yHas escapado del combate.|n")
        else:
            sala.msg_contents(f"{actor.key} intenta huir pero |rfalla|n.")
            self._siguiente_turno()

    def _aplicar_ticks_estado(self, actor) -> bool:
        """
        Aplica ticks de estados activos al actor al inicio de su turno.
        Devuelve True si el actor murió por un estado (la muerte ya fue procesada).
        """
        from systems.combat.states import tick_estados
        estados = dict(getattr(actor.db, "estados", {}) or {})
        if not estados:
            return False

        hp = getattr(actor.db, "hp", 1) or 1
        hp_max = getattr(actor.db, "hp_max", 100) or 100
        nuevos_estados, nuevo_hp, mensajes = tick_estados(estados, hp, hp_max)

        actor.db.estados = nuevos_estados
        actor.db.hp = max(0, nuevo_hp)

        sala = self.obj
        for msg in mensajes:
            actor.msg(msg)
            sala.msg_contents(f"{actor.key}: {msg}", exclude=actor)

        if actor.db.hp <= 0:
            self._procesar_muerte(actor)
            return True
        return False

    def _terminar_combate(self):
        sala = self.obj
        self.db.activo = False
        for participante in list(self.db.participantes or []):
            self._limpiar_estado_combate(participante)
            # Si quedan estados activos, iniciar script fuera de combate
            estados = dict(getattr(participante.db, "estados", {}) or {})
            if estados:
                from features.combat.states_script import programar_estados_script
                programar_estados_script(participante)
        sala.msg_contents("|gEl combate ha terminado.|n\n")
        self.delete()

    # ------------------------------------------------------------------ #
    #  IA de NPC (compleja / reactiva)
    # ------------------------------------------------------------------ #

    def _ia_npc(self, npc):
        """
        IA reactiva para NPCs. Toma decisiones según su estado y el del entorno.
        Niveles de IA:
          - Si HP < 25% → intentar huir
          - Si tiene habilidades → usarlas con cierta probabilidad
          - Objetivo preferido: el jugador con HP más bajo
          - Si está 'enraged': siempre ataca, nunca huye
        """
        if not self.db.activo:
            return

        participantes = self.db.participantes or []
        if npc not in participantes:
            # El NPC ya no está en el combate (murió o huyó); avanzar turno
            if self.db.activo:
                self._siguiente_turno()
            return

        hp_npc = getattr(npc.db, "hp", 100) or 1
        hp_max_npc = getattr(npc.db, "hp_max", 100) or 100
        porcentaje_hp = hp_npc / hp_max_npc
        enraged = bool(getattr(npc.db, "enraged", False))
        habilidades = getattr(npc.db, "habilidades", []) or []

        # Elegir objetivo: el jugador con HP más bajo
        enemigos = [p for p in participantes if p != npc]
        if not enemigos:
            self.registrar_accion(npc, "pasar")
            return

        objetivo = min(
            enemigos,
            key=lambda p: (getattr(p.db, "hp", 100) or 100)
        )

        # Decisión de acción
        import random

        # Huir si HP crítico y no está enraged
        if porcentaje_hp < 0.25 and not enraged:
            if random.random() < 0.40:
                self.registrar_accion(npc, "huir")
                return

        # Entrar en modo enraged si HP < 50%
        if porcentaje_hp < 0.50 and not enraged:
            npc.db.enraged = True
            if npc.location:
                npc.location.msg_contents(
                    f"|r{npc.key} entra en furia!|n Sus ataques serán más feroces."
                )

        # Usar habilidad especial (30% de probabilidad si tiene)
        if habilidades and random.random() < 0.30:
            hab = random.choice(habilidades)
            self.registrar_accion(npc, "habilidad", objetivo=objetivo, habilidad=hab)
            return

        # Ataque básico
        self.registrar_accion(npc, "atacar", objetivo=objetivo)
