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


def _runas_activas(obj) -> dict:
    """
    Runas grabadas en slots que actualmente tienen un objeto equipado.

    Las runas se graban por slot (arma/armadura/accesorio), no por ítem
    concreto — desequipar el objeto no borra la runa del atributo, así
    que sin este filtro el efecto seguiría activo para siempre, aunque
    varias descripciones de runa prometen "mientras esté equipado".
    """
    runas = dict(getattr(obj.db, "runas_equipadas", None) or {})
    eq = dict(getattr(obj.db, "equipamiento", None) or {})
    return {slot: rid for slot, rid in runas.items() if rid and eq.get(slot)}


# Sentinel para distinguir "el llamador no resolvió el evento activo"
# (se resuelve aquí, comportamiento de siempre) de "ya se resolvió y no hay
# evento activo" (None explícito, no volver a consultar).
_SIN_EVENTO_RESUELTO = object()


def _get_stats(obj, evento_activo=_SIN_EVENTO_RESUELTO) -> dict:
    """
    Lee stats de combate de un objeto Evennia.

    `evento_activo`: id del evento mundial ya resuelto por el llamador (p.
    ej. una sola vez por turno en _resolver_turno, en vez de una vez por
    participante). Si no se pasa, se resuelve aquí como antes.
    """
    stats = {}
    for key, default in STAT_DEFAULTS.items():
        stats[key] = getattr(obj.db, key, None)
        if stats[key] is None:
            stats[key] = default
    # Evento: tormenta mágica (+INT para jugadores)
    if getattr(obj, "has_account", False):
        try:
            from systems.events.events import EVENTOS
            ev_id = evento_activo
            if ev_id is _SIN_EVENTO_RESUELTO:
                from features.events.event_script import obtener_evento_activo
                ev_id = obtener_evento_activo()
            if ev_id:
                bonus = EVENTOS.get(ev_id, {}).get("efectos", {}).get("bonus_inteligencia", 0)
                if bonus:
                    stats["inteligencia"] = (stats.get("inteligencia") or 10) + bonus
        except Exception:
            pass
        # Buffs de taberna
        try:
            from systems.buffs.buffs import bonus_stat
            buffs = list(getattr(obj.db, "buffs_activos", None) or [])
            for stat in ("fuerza", "destreza", "inteligencia"):
                b = bonus_stat(buffs, stat)
                if b:
                    stats[stat] = (stats.get(stat) or 0) + b
        except Exception:
            pass
        # Bonuses de runas (bonus_fuerza, bonus_inteligencia)
        try:
            from systems.runes.runes import obtener_efectos
            ef = obtener_efectos(_runas_activas(obj))
            if ef.get("bonus_fuerza"):
                stats["fuerza"] = (stats.get("fuerza") or 10) + ef["bonus_fuerza"]
            if ef.get("bonus_inteligencia"):
                stats["inteligencia"] = (stats.get("inteligencia") or 10) + ef["bonus_inteligencia"]
        except Exception:
            pass
        # Bonus de montura (pasivo mientras montado)
        try:
            from systems.mounts.mounts import bonus_montura
            montura_id = getattr(obj.db, "montura_activa", None)
            if montura_id:
                for stat, val in bonus_montura(montura_id).items():
                    stats[stat] = (stats.get(stat) or 0) + val
        except Exception:
            pass
    return stats


def _set_stat(obj, key: str, value):
    setattr(obj.db, key, value)


def _subir_vinculo_mascota(char, delta: int):
    """Aumenta (o reduce) el vínculo de la mascota del personaje."""
    mascota = dict(getattr(char.db, "mascota", None) or {})
    if not mascota:
        return
    from systems.pets.pets import calcular_nuevo_vinculo
    mascota["vinculo"] = calcular_nuevo_vinculo(mascota.get("vinculo", 0), delta)
    char.db.mascota = mascota


def _dar_xp_mascota(char, xp: int):
    """Otorga XP a la mascota del personaje y gestiona la evolución."""
    mascota = dict(getattr(char.db, "mascota", None) or {})
    if not mascota:
        return
    from systems.pets.pets import calcular_evolucion, NIVEL_MAX_MASCOTA
    nueva, evoluciono = calcular_evolucion(mascota, xp)
    char.db.mascota = nueva
    if evoluciono:
        nivel = nueva.get("nivel", 1)
        especie = nueva.get("especie", "?")
        nombre = nueva.get("nombre", "tu mascota")
        char.msg(
            f"\n|Y✦ ¡{nombre} ha evolucionado!|n  "
            f"|w{especie}|n  (Nivel {nivel}"
            + (f"/{NIVEL_MAX_MASCOTA}" if nivel < NIVEL_MAX_MASCOTA else " — ¡MÁXIMO!")
            + ")\n"
        )
        nivel_max_actual = int(getattr(char.db, "mascota_nivel_max", 1) or 1)
        if nivel > nivel_max_actual:
            char.db.mascota_nivel_max = nivel


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

                # Aplicar rareza sólo a ítems de equipo spawneados desde prototipo
                if prototype_key and obj.is_typeclass("typeclasses.objects.Equipo", exact=False):
                    try:
                        from systems.loot.rarity import (
                            tirar_rareza, aplicar_rareza_bonuses, nombre_con_rareza
                        )
                        rareza = tirar_rareza()
                        obj.db.rareza = rareza
                        if rareza != "comun":
                            bonuses = dict(getattr(obj.db, "bonuses", {}) or {})
                            obj.db.bonuses = aplicar_rareza_bonuses(bonuses, rareza)
                            obj.key = nombre_con_rareza(obj.key, rareza)
                    except Exception:
                        pass

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
        self.db.modo_duelo = False      # True → duelo PvP, termina al 10 % HP

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
                # El combate rompe el sigilo alquímico
                if getattr(p.db, "oculto", False) and getattr(p.db, "nivel_sigilo", 0) == 25:
                    p.db.oculto = False
                    tarea_sigilo = p.ndb.tarea_sigilo
                    if tarea_sigilo:
                        tarea_sigilo.cancel()

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

    def agregar_participante(self, obj) -> bool:
        """
        Añade un participante al combate en curso. Devuelve False sin
        añadir nada si el combate es un duelo PvP (modo_duelo).

        Los duelos son siempre 1 contra 1: fusionar aquí a un tercero ajeno
        (p.ej. un NPC agresivo que reacciona a alguien que entra en la sala
        mientras dos jugadores duelan) rompe la resolución del duelo
        original -- _fin_duelo() se dispara para el primer participante
        que baje al 10% HP, sea quien sea, cerrando el handler sin
        ganador/perdedor entre los duelistas originales y dejando su
        apuesta "fantasma" fija para siempre, igual que el bug de v0.71.2
        pero por una vía distinta.
        """
        if self.db.modo_duelo:
            return False
        if obj not in self.db.participantes:
            self.db.participantes.append(obj)
            if hasattr(obj, "db"):
                obj.db.en_combate = True
        return True

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

        # _terminar_combate() solo limpia apuesta_duelo de quien queda en
        # self.db.participantes tras la baja — el eliminado (p. ej. quien
        # huyó) ya no está en esa lista y se quedaría con una apuesta
        # "fantasma" activa, que se cobraría de verdad en su próximo
        # combate en modo duelo sin apuesta explícita (caza de recompensa,
        # torneo de arena), transfiriendo monedas que nadie apostó.
        if getattr(self.db, "modo_duelo", False) and hasattr(obj, "db"):
            obj.db.apuesta_duelo = 0

        jugadores = [p for p in parts if getattr(p, "has_account", False)]
        if len(parts) <= 1 or not jugadores:
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

        # Runa de Vigor: regeneración de HP al inicio del turno
        if getattr(actor, "has_account", False):
            try:
                from systems.runes.runes import obtener_efectos
                regen = obtener_efectos(_runas_activas(actor)).get("regen_hp", 0)
                if regen:
                    hp = int(getattr(actor.db, "hp", 1) or 1)
                    hp_max = int(getattr(actor.db, "hp_max", 100) or 100)
                    nuevo_hp = min(hp_max, hp + regen)
                    if nuevo_hp > hp:
                        actor.db.hp = nuevo_hp
                        actor.msg(
                            f"|gRuna de Vigor:|n +{regen} HP. (HP: {nuevo_hp}/{hp_max})"
                        )
            except Exception:
                pass

        sala = self.obj
        sala.msg_contents(f"\n|w▶ Turno de: {actor.key}|n")
        # Mostrar opciones al jugador (si tiene sesión)
        if actor.has_account:
            enemigos = [p for p in self.db.participantes if p != actor]
            nombres_enemigos = ", ".join(e.key for e in enemigos)
            if self.db.modo_duelo:
                opciones = (
                    f"  |cAcciones disponibles:|n\n"
                    f"  |watacar <objetivo>|n  — ataque básico\n"
                    f"  |whabilidad <nombre> <objetivo>|n  — habilidad especial\n"
                    f"  |wrendirse|n  — conceder la victoria\n"
                    f"  |wpasar|n  — pasar turno\n"
                    f"  Rival: {nombres_enemigos}"
                )
            else:
                captura_txt = (
                    "  |wcapturar|n  — capturar al enemigo debilitado (≤20% HP)\n"
                    if not actor.db.mascota else ""
                )
                opciones = (
                    f"  |cAcciones disponibles:|n\n"
                    f"  |watacar <objetivo>|n  — ataque básico\n"
                    f"  |whabilidad <nombre> <objetivo>|n  — habilidad especial\n"
                    f"  |whuir|n  — intentar escapar\n"
                    f"{captura_txt}"
                    f"  |wpasar|n  — pasar turno\n"
                    f"  Enemigos: {nombres_enemigos}"
                )
            actor.msg(opciones)
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
                evento_activo = None
                if getattr(actor, "has_account", False) or getattr(objetivo, "has_account", False):
                    from features.events.event_script import obtener_evento_activo
                    evento_activo = obtener_evento_activo()
                stats_at = _get_stats(actor, evento_activo=evento_activo)
                stats_def = _get_stats(objetivo, evento_activo=evento_activo)
                resultado = resolver_ataque(
                    stats_at, stats_def,
                    actor.key, objetivo.key,
                    habilidad if tipo == "habilidad" else None,
                )

                # Runa de Evasión: esquivar extra del defensor
                if resultado.exito:
                    import random as _rnd
                    try:
                        from systems.runes.runes import obtener_efectos
                        evasion = obtener_efectos(_runas_activas(objetivo)).get("evasion", 0)
                        if evasion and _rnd.random() * 100 < evasion:
                            resultado.exito = False
                            resultado.dano = 0
                            resultado.muerto = False
                            resultado.hp_restante = int(
                                getattr(objetivo.db, "hp", 1) or 1
                            )
                            resultado.mensaje_atacante = (
                                f"|y{objetivo.key} esquiva tu golpe con una runa!|n"
                            )
                            resultado.mensaje_defensor = (
                                "|g¡Tu Runa de Evasión esquiva el ataque!|n"
                            )
                            resultado.mensaje_sala = (
                                f"{objetivo.key} esquiva ágilmente el ataque de "
                                f"{actor.key}."
                            )
                    except Exception:
                        pass

                actor.msg(resultado.mensaje_atacante)
                objetivo.msg(resultado.mensaje_defensor)
                # Mensaje a la sala (excluyendo atacante y defensor)
                for p in sala.contents:
                    if p not in (actor, objetivo) and hasattr(p, "msg"):
                        p.msg(resultado.mensaje_sala)

                if resultado.exito:
                    # Duelo: detener al 10 % de HP en lugar de procesar muerte
                    if self.db.modo_duelo:
                        from systems.duels.duels import calcular_hp_umbral
                        hp_max = getattr(objetivo.db, "hp_max", 100) or 100
                        umbral = calcular_hp_umbral(hp_max)
                        if resultado.hp_restante <= umbral:
                            objetivo.db.hp = umbral
                            self._fin_duelo(ganador=actor, perdedor=objetivo)
                            return
                    # Runa de Escudo: reducir daño recibido
                    if resultado.dano and not resultado.muerto:
                        try:
                            from systems.runes.runes import obtener_efectos
                            reduccion = obtener_efectos(_runas_activas(objetivo)).get(
                                "reduccion_dano", 0
                            )
                            if reduccion and resultado.dano > 1:
                                red_real = min(resultado.dano - 1, reduccion)
                                resultado.dano -= red_real
                                resultado.hp_restante = max(
                                    0, resultado.hp_restante + red_real
                                )
                                resultado.muerto = resultado.hp_restante <= 0
                                objetivo.msg(
                                    f"|gRuna de Escudo:|n -{red_real} daño bloqueado."
                                )
                        except Exception:
                            pass

                    _set_stat(objetivo, "hp", resultado.hp_restante)
                    # Tracking de daño en Jefe de Mundo
                    if (getattr(objetivo.db, "es_jefe_mundo", False)
                            and getattr(actor, "has_account", False)
                            and (resultado.dano or 0) > 0):
                        tracker = dict(getattr(objetivo.ndb, "dano_por_jugador", None) or {})
                        tracker[actor.dbref] = tracker.get(actor.dbref, 0) + resultado.dano
                        objetivo.ndb.dano_por_jugador = tracker

                # Runa de Drenaje: robo de vida al golpear
                if resultado.exito and resultado.dano and not resultado.muerto:
                    try:
                        from systems.runes.runes import obtener_efectos
                        robo = obtener_efectos(_runas_activas(actor)).get("robo_vida", 0)
                        if robo:
                            hp_a = int(getattr(actor.db, "hp", 1) or 1)
                            hp_max_a = int(getattr(actor.db, "hp_max", 100) or 100)
                            nuevo = min(hp_max_a, hp_a + robo)
                            if nuevo > hp_a:
                                actor.db.hp = nuevo
                                actor.msg(
                                    f"|gRuna de Drenaje:|n +{robo} HP drenados. "
                                    f"(HP: {nuevo}/{hp_max_a})"
                                )
                    except Exception:
                        pass

                # Efectos de curación post-ataque (drenar vida / sagrado / esencia)
                if (tipo == "habilidad" and habilidad and resultado.exito
                        and not resultado.muerto):
                    efecto = efecto_postcombat(habilidad)
                    if efecto in ("drenar_vida", "drenar_esencia"):
                        cura = max(1, resultado.dano // 2)
                        hp_act = getattr(actor.db, "hp", 0) or 0
                        hp_max = getattr(actor.db, "hp_max", 100) or 100
                        nuevo_hp = min(hp_max, hp_act + cura)
                        actor.db.hp = nuevo_hp
                        if efecto == "drenar_vida":
                            actor.msg(f"|gDrenas {cura} HP de vida.|n (HP: {nuevo_hp}/{hp_max})")
                        else:
                            actor.msg(f"|gDrenas {cura} de esencia vital.|n (HP: {nuevo_hp}/{hp_max})")
                    elif efecto == "golpe_sagrado":
                        cura = max(1, resultado.dano // 4)
                        hp_act = getattr(actor.db, "hp", 0) or 0
                        hp_max = getattr(actor.db, "hp_max", 100) or 100
                        nuevo_hp = min(hp_max, hp_act + cura)
                        actor.db.hp = nuevo_hp
                        actor.msg(f"|gTu fe restaura {cura} HP.|n (HP: {nuevo_hp}/{hp_max})")

                # Aplicar estado si la habilidad lo produce (solo en golpe exitoso y no letal)
                if resultado.exito and not resultado.muerto and resultado.estado_aplicado:
                    from systems.combat.states import aplicar_estado
                    import random as _rnd2
                    nombre_estado = resultado.estado_aplicado
                    # Runa de Firmeza: resistencia a estados negativos
                    estado_bloqueado = False
                    try:
                        from systems.runes.runes import obtener_efectos
                        resist = obtener_efectos(_runas_activas(objetivo)).get(
                            "resistencia_estados", 0
                        )
                        if resist and _rnd2.random() * 100 < resist:
                            estado_bloqueado = True
                            objetivo.msg(
                                "|gRuna de Firmeza:|n resistes el estado negativo."
                            )
                    except Exception:
                        pass
                    if not estado_bloqueado and nombre_estado == "veneno":
                        if getattr(objetivo.db, "inmune_veneno", False):
                            objetivo.db.inmune_veneno = False
                            objetivo.msg("|gEl antídoto reforzado neutraliza el veneno.|n")
                            estado_bloqueado = True
                    if not estado_bloqueado:
                        estados = dict(getattr(objetivo.db, "estados", {}) or {})
                        objetivo.db.estados = aplicar_estado(estados, nombre_estado)
                        display = {"veneno": "veneno", "sangrado": "sangrado"}.get(
                            nombre_estado, nombre_estado
                        )
                        objetivo.msg(f"|r¡Has sido afectado por {display}!|n")
                        actor.msg(f"|y{objetivo.key} ha sido afectado por {display}.|n")

                # Runa de Filo: sangrado aleatorio al golpear
                if resultado.exito and not resultado.muerto:
                    import random as _rnd3
                    try:
                        from systems.runes.runes import obtener_efectos
                        from systems.combat.states import aplicar_estado
                        sangrado_ch = obtener_efectos(_runas_activas(actor)).get(
                            "sangrado_chance", 0
                        )
                        if sangrado_ch and _rnd3.random() * 100 < sangrado_ch:
                            # No aplicar si el objetivo ya tiene sangrado
                            estados_obj = dict(
                                getattr(objetivo.db, "estados", {}) or {}
                            )
                            if "sangrado" not in estados_obj:
                                objetivo.db.estados = aplicar_estado(
                                    estados_obj, "sangrado"
                                )
                                objetivo.msg(
                                    "|rRuna de Filo:|n ¡Tu herida comienza a sangrar!|n"
                                )
                                actor.msg(
                                    f"|yRuna de Filo:|n {objetivo.key} comienza a "
                                    f"sangrar.|n"
                                )
                    except Exception:
                        pass

                # Ataque de mascota: si el jugador tiene mascota y el enemigo sobrevivió
                if (resultado.exito
                        and not resultado.muerto
                        and not self.db.modo_duelo
                        and bool(getattr(actor, "account", None))):
                    self._aplicar_ataque_mascota(actor, objetivo)
                    if (getattr(objetivo.db, "hp", 0) or 0) <= 0:
                        self._procesar_muerte(objetivo, asesino=actor)
                        return

                if resultado.muerto:
                    self._procesar_muerte(objetivo, asesino=actor)
                    return

        elif tipo == "huir":
            self._intentar_huida(actor)
            return

        elif tipo == "capturar":
            self._intentar_captura(actor)
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

    def _avanzar_turno_tras_baja(self, actor_referencia, eliminado):
        """
        Avanza el turno correctamente tras eliminar_participante() (muerte,
        captura o huida) durante la resolución del turno de actor_referencia.

        eliminar_participante() solo reindexa turno_actual con un clamp de
        desbordamiento — da el índice correcto cuando el eliminado estaba
        DESPUÉS de actor_referencia en la lista, pero si estaba antes (o era
        el propio actor_referencia) el hueco ya desplazó ese índice hacia el
        siguiente participante por sí solo; sumarle 1 otra vez (llamando a
        _siguiente_turno() a ciegas, como hacía antes cada punto de llamada)
        salta un participante entero. Aquí se recalcula siempre a partir de
        la posición real de actor_referencia tras el hueco.
        """
        if not self.db.activo:
            return  # eliminar_participante() ya cerró el combate
        parts = self.db.participantes or []
        if not parts:
            return
        if actor_referencia in parts and actor_referencia != eliminado:
            self.db.turno_actual = parts.index(actor_referencia)
            self._siguiente_turno()
        else:
            # El eliminado era actor_referencia (murió o huyó en su propio
            # turno): el índice que dejó eliminar_participante() ya apunta
            # al siguiente participante, no hay que sumar otro paso.
            self.db.acciones = {}
            self.db.turno_tiempo = 0
            self._anunciar_turno()

    def _fin_duelo(self, ganador, perdedor):
        """Cierra un duelo PvP: actualiza estadísticas, transfiere apuesta y elimina el handler."""
        from systems.duels.duels import formatear_resultado
        sala = self.obj

        apuesta = getattr(ganador.db, "apuesta_duelo", 0) or 0
        if not apuesta:
            apuesta = getattr(perdedor.db, "apuesta_duelo", 0) or 0

        pago_real = 0
        if apuesta:
            monedas_perdedor = getattr(perdedor.db, "monedas", 0) or 0
            pago_real = min(apuesta, monedas_perdedor)
            perdedor.db.monedas = monedas_perdedor - pago_real
            ganador.db.monedas = (getattr(ganador.db, "monedas", 0) or 0) + pago_real

        sala.msg_contents(formatear_resultado(ganador.key, perdedor.key, pago_real))

        ganador.db.duelos_ganados = (getattr(ganador.db, "duelos_ganados", 0) or 0) + 1
        perdedor.db.duelos_perdidos = (getattr(perdedor.db, "duelos_perdidos", 0) or 0) + 1

        for p in [ganador, perdedor]:
            p.db.apuesta_duelo = 0

        for p in list(self.db.participantes or []):
            self._limpiar_estado_combate(p)
        self.db.activo = False
        sala.msg_contents("|gEl combate ha terminado.|n\n")

        # Notificar al torneo si este duelo forma parte de uno
        torneo_id = getattr(self.db, "torneo_script_id", None)
        if torneo_id:
            try:
                from features.arena.tournament_script import notificar_resultado_torneo
                notificar_resultado_torneo(torneo_id, ganador, perdedor)
            except Exception as _te:
                logger.log_err(f"Tournament hook: {_te}")

        if getattr(self.db, "es_caza_recompensa", False):
            cazador_dbref = getattr(self.db, "cazador_dbref", None)
            if ganador.dbref == cazador_dbref:
                try:
                    from features.bounty.bounty_script import cobrar_recompensa_por_duelo
                    cobrar_recompensa_por_duelo(ganador, perdedor)
                except Exception as _be:
                    logger.log_err(f"Bounty hook: {_be}")

        self.delete()

    def _procesar_muerte(self, muerto, asesino=None):
        # Capturado antes de tocar self.db.participantes: eliminar_participante()
        # reindexa turno_actual con un clamp que solo es correcto si `muerto`
        # estaba después de este participante en la lista (ver _avanzar_turno_tras_baja).
        actor_referencia = self._participante_actual()
        # Fallback: si un tick de estado (veneno/sangrado) mata a alguien
        # durante un duelo, _aplicar_ticks_estado() llama aquí sin `asesino`
        # (el daño no viene de un golpe con atacante). Sin resolver el rival
        # como ganador en ese caso, este bloque nunca se ejecutaba pese a
        # que el comentario decía cubrirlo: el duelo caía por la rama de
        # "jugador normal" (te manda a home con 1 HP) sin pasar por
        # _fin_duelo, perdiendo la apuesta, las stats de duelo, y sin avisar
        # al torneo/recompensa que dependían de ese resultado.
        if getattr(self.db, "modo_duelo", False) and getattr(muerto, "has_account", False):
            if not asesino:
                rivales = [p for p in (self.db.participantes or []) if p != muerto]
                asesino = rivales[0] if rivales else None
            if asesino:
                from systems.duels.duels import calcular_hp_umbral
                hp_max = getattr(muerto.db, "hp_max", 100) or 100
                muerto.db.hp = calcular_hp_umbral(hp_max)
                self._fin_duelo(ganador=asesino, perdedor=muerto)
                return

        sala = self.obj
        sala.msg_contents(f"\n|r💀 {muerto.key} ha caído en combate.|n\n")

        # Recompensa de XP (individual o repartida entre el grupo)
        if asesino:
            xp_base = calcular_xp_recompensa(getattr(muerto.db, "nivel", 1) or 1)
            # Evento: invasión de no-muertos (XP × factor si la facción coincide)
            try:
                from features.events.event_script import obtener_evento_activo
                from systems.events.events import EVENTOS
                ev_id = obtener_evento_activo()
                if ev_id:
                    ev_efectos = EVENTOS.get(ev_id, {}).get("efectos", {})
                    xp_factor = ev_efectos.get("xp_factor", 1.0)
                    facciones = ev_efectos.get("facciones_afectadas", [])
                    faccion_npc = getattr(muerto.db, "faccion", None)
                    if xp_factor != 1.0 and (not facciones or faccion_npc in facciones):
                        xp_base = int(xp_base * xp_factor)
            except Exception:
                pass
            self._dar_xp_a_grupo(asesino, xp_base)

        # Loot: objetos ya en el inventario del NPC
        for obj in list(getattr(muerto, "contents", []) or []):
            obj.move_to(sala, quiet=True)

        # Kill tracking, boss tracking, progreso de quests y comprobación de
        # logros — para TODO el grupo participante en el combate, no solo
        # quien remató (igual que kills_totales/bestiario/desafíos ya hacían;
        # el progreso de quests de kill quedaba limitado solo al asesino).
        if asesino and getattr(asesino, "has_account", False):
            from systems.achievements.achievements import JEFES
            from features.achievements.commands import comprobar_y_notificar
            from features.quests.hooks import on_npc_muerte
            proto = getattr(muerto.db, "npc_prototipo", None)
            if not proto:
                # Jefes de mundo y enemigos de mazmorra ponen npc_prototipo a
                # None a propósito para desactivar el respawn automático
                # (ver features/respawn/respawn.py), pero eso también los
                # dejaba fuera del bestiario para siempre. El tag que el
                # spawner de Evennia añade automáticamente al crear el objeto
                # sobrevive a ese None y sigue identificando su prototipo.
                from evennia.prototypes.prototypes import PROTOTYPE_TAG_CATEGORY
                tags = muerto.tags.get(category=PROTOTYPE_TAG_CATEGORY, return_list=True) or []
                if tags:
                    proto = tags[0].upper()
            is_boss = bool(proto and proto in JEFES)
            jugadores = [
                p for p in (self.db.participantes or [])
                if getattr(p, "has_account", False)
            ]
            from systems.bestiary.bestiary import registrar_kill
            for j in jugadores:
                on_npc_muerte(j, muerto)
                j.db.kills_totales = (getattr(j.db, "kills_totales", 0) or 0) + 1
                if is_boss:
                    jefes_list = list(getattr(j.db, "jefes_derrotados", []) or [])
                    if proto not in jefes_list:
                        jefes_list.append(proto)
                        j.db.jefes_derrotados = jefes_list
                if proto:
                    j.db.bestiary = registrar_kill(dict(getattr(j.db, "bestiary", {}) or {}), proto)
                _subir_vinculo_mascota(j, 5)
                _dar_xp_mascota(j, getattr(muerto.db, "nivel", 1) or 1)
                comprobar_y_notificar(j)
                # Desafíos diarios — kill_faccion
                faccion_npc = getattr(muerto.db, "faccion", None)
                if faccion_npc:
                    try:
                        from features.daily.daily_script import notificar_progreso
                        notificar_progreso(j, "kill_faccion", faccion=faccion_npc)
                    except Exception as _de:
                        logger.log_err(f"Desafíos kill hook: {_de}")

        # Loot: generar items desde la tabla db.loot
        items_generados = _generar_loot(muerto, sala)
        if items_generados:
            try:
                from systems.loot.rarity import color_rareza, es_notable
                partes = []
                epicos = []
                for o in items_generados:
                    rareza = getattr(o.db, "rareza", "comun") or "comun"
                    partes.append(f"{color_rareza(rareza)}{o.key}|n")
                    if rareza == "epico":
                        epicos.append(o.key)
                nombres = ", ".join(partes)
            except Exception:
                nombres = ", ".join(f"|y{o.key}|n" for o in items_generados)
                epicos = []
            sala.msg_contents(f"{muerto.key} ha dejado caer: {nombres}.")
            for nombre_epico in epicos:
                sala.msg_contents(
                    f"|m✦ ¡OBJETO ÉPICO! |w{nombre_epico}|m — "
                    f"un hallazgo extraordinariamente poderoso.|n"
                )

        # Si es NPC → programar respawn y eliminarlo del mundo
        if not muerto.has_account:
            muerto.db.hp = 0
            self._limpiar_estado_combate(muerto)

            # Jefe de Mundo: distribuir recompensas a participantes
            if getattr(muerto.db, "es_jefe_mundo", False):
                try:
                    from features.world_bosses.world_boss_script import (
                        distribuir_recompensas_jefe_mundo,
                    )
                    tracker = dict(getattr(muerto.ndb, "dano_por_jugador", None) or {})
                    boss_id = getattr(muerto.db, "world_boss_id", None)
                    distribuir_recompensas_jefe_mundo(muerto, tracker, sala, boss_id)
                except Exception as _wb_err:
                    logger.log_err(f"World boss rewards error: {_wb_err}")

            # Programar respawn ANTES de delete (necesitamos leer atributos del NPC)
            from features.respawn.respawn import programar_respawn
            programar_respawn(sala, muerto)

            self.eliminar_participante(muerto)
            muerto.delete()
            self._avanzar_turno_tras_baja(actor_referencia, muerto)
        else:
            # Jugador → enviarlo a sala de inicio con HP mínimo
            if asesino and getattr(asesino, "has_account", False):
                try:
                    from features.guild_wars.guild_war_script import obtener_guerra_script
                    obtener_guerra_script().registrar_kill_si_en_guerra(asesino, muerto)
                except Exception:
                    logger.log_trace("Guild war kill hook error.")
            self._limpiar_estado_combate(muerto)
            muerto.db.hp = 1
            self.eliminar_participante(muerto)
            home = muerto.home or muerto.location
            muerto.move_to(home, quiet=True)
            muerto.msg(
                "|rHas caído en combate.|n Despiertas débil en tu lugar de inicio."
            )
            self._avanzar_turno_tras_baja(actor_referencia, muerto)

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
            self._avanzar_turno_tras_baja(actor, actor)
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

    def _aplicar_ataque_mascota(self, actor, objetivo):
        """Aplica el ataque de la mascota del actor al objetivo."""
        mascota = dict(getattr(actor.db, "mascota", None) or {})
        if not mascota:
            return
        from systems.pets.pets import calcular_daño_mascota
        daño = calcular_daño_mascota(mascota.get("vinculo", 0), mascota.get("ataque", 5))
        if daño <= 0:
            return
        hp_obj = max(0, (getattr(objetivo.db, "hp", 0) or 0) - daño)
        _set_stat(objetivo, "hp", hp_obj)
        # Tracking de daño en Jefe de Mundo (igual que el ataque directo del jugador)
        if (getattr(objetivo.db, "es_jefe_mundo", False)
                and getattr(actor, "has_account", False)):
            tracker = dict(getattr(objetivo.ndb, "dano_por_jugador", None) or {})
            tracker[actor.dbref] = tracker.get(actor.dbref, 0) + daño
            objetivo.ndb.dano_por_jugador = tracker
        nombre_mascota = mascota.get("nombre", "tu mascota")
        self.obj.msg_contents(
            f"|y{nombre_mascota}|n muerde a |r{objetivo.key}|n "
            f"causando |w{daño}|n de daño."
        )

    def _intentar_captura(self, actor):
        """Procesa el intento de captura durante el combate."""
        from systems.pets.pets import puede_capturar, datos_mascota_desde_criatura
        sala = self.obj

        if actor.db.mascota:
            actor.msg(
                "Ya tienes una mascota. "
                "Usa |wmascota liberar|n antes de capturar otra."
            )
            self._siguiente_turno()
            return

        npcs = [
            p for p in (self.db.participantes or [])
            if p != actor and not bool(getattr(p, "account", None))
        ]
        if not npcs:
            actor.msg("No hay ningún enemigo que puedas capturar.")
            self._siguiente_turno()
            return

        # Con más de un NPC en el combate (grupo, oleada, o alguien que se
        # une a un combate ya activo contra otro NPC), hay que elegir el que
        # de verdad esté debilitado — no el primero de la lista sin más, o
        # el jugador podía quedar bloqueado con el mensaje de "aún tiene X%
        # HP" referido a un NPC distinto del que sí cumplía el umbral.
        enemigo = next(
            (p for p in npcs if puede_capturar(
                int(getattr(p.db, "hp", 1) or 1),
                int(getattr(p.db, "hp_max", 100) or 100),
            )),
            npcs[0],
        )

        hp = int(getattr(enemigo.db, "hp", 1) or 1)
        hp_max = int(getattr(enemigo.db, "hp_max", 100) or 100)

        if not puede_capturar(hp, hp_max):
            pct = int(hp / hp_max * 100)
            actor.msg(
                f"|y{enemigo.key}|n aún tiene {pct}% de HP. "
                f"Debilítalo hasta el 20% para capturarlo."
            )
            self._siguiente_turno()
            return

        actor.db.mascota = datos_mascota_desde_criatura(
            nombre=enemigo.key,
            especie=enemigo.key,
            hp_max=hp_max,
            ataque=int(getattr(enemigo.db, "ataque", 5) or 5),
            defensa=int(getattr(enemigo.db, "defensa", 2) or 2),
        )

        sala.msg_contents(
            f"|g{actor.key} ha capturado a |y{enemigo.key}|n|g!|n"
        )
        actor.msg(
            f"|g¡Has capturado a |y{enemigo.key}|n|g! Ahora te acompaña.\n|n"
            f"Usa |wmascota|n para ver sus estadísticas y |wmascota nombre <nuevo>|n "
            f"para ponerle nombre."
        )

        self._limpiar_estado_combate(enemigo)
        from features.respawn.respawn import programar_respawn
        programar_respawn(sala, enemigo)
        self.eliminar_participante(enemigo)
        enemigo.delete()
        self._avanzar_turno_tras_baja(actor, enemigo)

    def _terminar_combate(self):
        sala = self.obj
        self.db.activo = False
        for participante in list(self.db.participantes or []):
            self._limpiar_estado_combate(participante)
            if getattr(self.db, "modo_duelo", False):
                participante.db.apuesta_duelo = 0
            # Si quedan estados activos, iniciar script fuera de combate
            estados = dict(getattr(participante.db, "estados", {}) or {})
            if estados:
                from features.combat.states_script import programar_estados_script
                programar_estados_script(participante)
        if sala:
            sala.msg_contents("|gEl combate ha terminado.|n\n")
        self.delete()

    def _dar_xp_a_grupo(self, asesino, xp_base: int):
        """Reparte XP al asesino y a los miembros de su grupo que estén en la sala."""
        from features.party.commands import esta_en_partido, get_miembros
        from systems.party.engine import xp_por_miembro

        sala = self.obj
        if not getattr(asesino, "has_account", False):
            return

        if esta_en_partido(asesino):
            receptores = [
                m for m in get_miembros(asesino)
                if m.location == sala and getattr(m, "has_account", False)
            ]
        else:
            receptores = [asesino]

        n = len(receptores)
        xp_ind = xp_por_miembro(xp_base, n)

        for m in receptores:
            # Aplicar buff de XP individual
            try:
                from systems.buffs.buffs import factor_xp, buffs_vigentes
                buffs = list(getattr(m.db, "buffs_activos", None) or [])
                f = factor_xp(buffs_vigentes(buffs))
                xp_real = int(xp_ind * f)
            except Exception:
                xp_real = xp_ind
                f = 1.0

            xp_actual = getattr(m.db, "experiencia", 0) or 0
            m.db.experiencia = xp_actual + xp_real
            if n > 1:
                xp_txt = f"|g+{xp_real} XP|n (grupo ×{n}"
                if f > 1.0:
                    xp_txt += f", buff ×{f:.2f}"
                xp_txt += f"; total: {m.db.experiencia})"
            else:
                xp_txt = f"|g+{xp_real} XP|n"
                if f > 1.0:
                    xp_txt += f" |Y(×{f:.2f} buff)|n"
                xp_txt += f" (Total: {m.db.experiencia})"
            m.msg(xp_txt)

            stats = _get_stats(m)
            subio, nuevos_stats = procesar_subida_de_nivel(stats)
            if subio:
                for k, v in nuevos_stats.items():
                    _set_stat(m, k, v)
                m.msg(
                    f"\n|Y🌟 ¡SUBISTE AL NIVEL {nuevos_stats['nivel']}!|n\n"
                    f"  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo\n"
                    f"  |g+1 punto de habilidad disponible|n  (usa |whabilidades|n)\n"
                    f"  |gHP restaurado al máximo.|n\n"
                )

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
        temperamento = getattr(npc.db, "temperamento", "neutral") or "neutral"
        habilidades = getattr(npc.db, "habilidades", []) or []

        # Elegir objetivo: el jugador con HP más bajo
        # Los NPCs solo atacan a jugadores (has_account=True) para no pegarse entre ellos
        enemigos = [p for p in participantes if getattr(p, "has_account", False)]
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

        # Entrar en modo enraged si HP < 50% (los NPC 'cobarde' nunca se
        # enfurecen: si lo hicieran, el umbral de furia (50%) se dispararía
        # antes que el de huida (25%) y el flag 'enraged', que no se
        # resetea hasta el fin del combate, bloquearía la huida para el
        # resto del combate — justo el comportamiento que "cobarde" promete
        # evitar, ver world/help_entries.py: "puede huir si le atacas").
        if porcentaje_hp < 0.50 and not enraged and temperamento != "cobarde":
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
