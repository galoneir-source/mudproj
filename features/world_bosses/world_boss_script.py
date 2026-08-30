"""
features/world_bosses/world_boss_script.py

WorldBossScript — script global que gestiona los jefes de mundo.

Tick cada 5 minutos:
  • Para cada jefe sin NPC activo y con cooldown cumplido → spawnear.
  • Anuncio global al aparecer.

distribuir_recompensas_jefe_mundo() es llamada desde CombatHandler cuando
un NPC con db.es_jefe_mundo = True muere. Reparte XP y monedas
proporcionales al daño, da el loot único al top dañador, y anota el
logro en cada participante.
"""

import time

from evennia import DefaultScript, search_object
from evennia.utils import create, logger
from evennia.prototypes import spawner

from systems.world_bosses.world_bosses import (
    JEFES_MUNDO,
    puede_aparecer,
    calcular_recompensas_participante,
)

TICK_INTERVALO = 300   # 5 minutos


class WorldBossScript(DefaultScript):

    def at_script_creation(self):
        self.key = "world_boss_script"
        self.desc = "Gestor de jefes de mundo"
        self.interval = TICK_INTERVALO
        self.persistent = True
        # {boss_id: timestamp_ultimo_muerte | None}
        self.db.ultimo_muerte = {bid: None for bid in JEFES_MUNDO}
        # {boss_id: dbref_npc | None}
        self.db.npc_activo = {bid: None for bid in JEFES_MUNDO}

    # ---------------------------------------------------------------------- #
    #  Tick
    # ---------------------------------------------------------------------- #

    def at_repeat(self):
        for boss_id in JEFES_MUNDO:
            self._comprobar_boss(boss_id)

    # ---------------------------------------------------------------------- #
    #  Comprobación individual
    # ---------------------------------------------------------------------- #

    def _comprobar_boss(self, boss_id: str):
        npc_dbref = (self.db.npc_activo or {}).get(boss_id)

        # Si hay NPC registrado, verificar si sigue vivo
        if npc_dbref:
            npc_list = search_object(npc_dbref)
            if npc_list:
                npc = npc_list[0]
                hp = getattr(npc.db, "hp", 0) or 0
                if hp > 0:
                    return   # El jefe sigue vivo, no hacer nada
            # NPC no encontrado o con HP 0 — ya fue procesado por el handler
            activos = dict(self.db.npc_activo or {})
            activos[boss_id] = None
            self.db.npc_activo = activos

        # Sin NPC activo: comprobar cooldown
        ultimos = dict(self.db.ultimo_muerte or {})
        if not puede_aparecer(boss_id, ultimos.get(boss_id)):
            return

        # Spawnear
        self._spawnear_boss(boss_id)

    # ---------------------------------------------------------------------- #
    #  Spawn
    # ---------------------------------------------------------------------- #

    def _spawnear_boss(self, boss_id: str):
        datos = JEFES_MUNDO[boss_id]
        sala = self._buscar_sala_zona(datos["sala_zona"])
        if not sala:
            logger.log_err(f"WorldBossScript: sala zona '{datos['sala_zona']}' no encontrada.")
            return

        try:
            npc = spawner.spawn(boss_id)[0]
            npc.location = sala
            npc.db.es_jefe_mundo = True
            npc.db.world_boss_id = boss_id
            npc.db.npc_prototipo = None   # Sin respawn automático
            npc.db.dano_por_jugador = {}  # en db: debe sobrevivir a un reload

            # Guardar dbref
            activos = dict(self.db.npc_activo or {})
            activos[boss_id] = npc.dbref
            self.db.npc_activo = activos

            # Anuncio global
            self._anunciar_global(datos["desc_aparicion"])
            logger.log_info(f"WorldBossScript: {datos['nombre']} spawneado en {sala.key}.")
        except Exception as err:
            logger.log_err(f"WorldBossScript: error spawning '{boss_id}': {err}")

    # ---------------------------------------------------------------------- #
    #  Helpers
    # ---------------------------------------------------------------------- #

    def _buscar_sala_zona(self, zona_id: str):
        """Busca la primera sala con db.zona == zona_id."""
        from evennia.objects.models import ObjectDB
        salas_db = ObjectDB.objects.filter(db_typeclass_path__contains="rooms.Room")
        for sala in salas_db:
            if getattr(sala.db, "zona", None) == zona_id:
                return sala
        return None

    def _anunciar_global(self, mensaje: str):
        """Envía un mensaje a todos los jugadores conectados."""
        from evennia import SESSION_HANDLER
        for session in SESSION_HANDLER.get_sessions():
            puppet = session.get_puppet()
            if puppet:
                puppet.msg(f"\n{mensaje}\n")

    def registrar_muerte_boss(self, boss_id: str):
        """Llamado cuando un jefe muere: registra el timestamp."""
        ultimos = dict(self.db.ultimo_muerte or {})
        ultimos[boss_id] = time.time()
        self.db.ultimo_muerte = ultimos

        activos = dict(self.db.npc_activo or {})
        activos[boss_id] = None
        self.db.npc_activo = activos

    def estado_jefes(self) -> tuple[dict, dict]:
        """Devuelve (estados_vivo, ultimos_muertos) para el comando `jefes`."""
        activos = dict(self.db.npc_activo or {})
        estados_vivo = {}
        for bid, dbref in activos.items():
            if dbref:
                npc_list = search_object(dbref)
                estados_vivo[bid] = bool(npc_list and (npc_list[0].db.hp or 0) > 0)
            else:
                estados_vivo[bid] = False
        ultimos = dict(self.db.ultimo_muerte or {})
        return estados_vivo, ultimos


# --------------------------------------------------------------------------- #
#  Singleton accessor
# --------------------------------------------------------------------------- #

def obtener_world_boss_script() -> WorldBossScript:
    from evennia import ScriptDB
    scripts = ScriptDB.objects.filter(db_key="world_boss_script")
    if scripts:
        return scripts.first()
    from evennia import create_script
    return create_script(
        "features.world_bosses.world_boss_script.WorldBossScript",
        key="world_boss_script",
        persistent=True,
        autostart=True,
    )


# --------------------------------------------------------------------------- #
#  Distribución de recompensas (llamada desde CombatHandler)
# --------------------------------------------------------------------------- #

def distribuir_recompensas_jefe_mundo(npc, tracker: dict, sala, boss_id: str | None):
    """
    Reparte XP y monedas a todos los jugadores que participaron en la pelea.
    Llama a comprobar_y_notificar para logros.
    Hace un anuncio global de la muerte.
    """
    if not boss_id:
        boss_id = getattr(npc.db, "world_boss_id", None)
    if not boss_id or boss_id not in JEFES_MUNDO:
        return

    datos = JEFES_MUNDO[boss_id]
    dano_total = sum(tracker.values()) or 1

    # Identificar participantes (por dbref)
    participantes = []
    for dbref, dano in tracker.items():
        chars = search_object(dbref)
        if chars and getattr(chars[0], "has_account", False):
            participantes.append((chars[0], dano))

    if not participantes:
        return

    # Ordenar por daño para dar loot único al top
    participantes.sort(key=lambda x: x[1], reverse=True)
    top_jugador = participantes[0][0]

    # calcular_recompensas_participante() garantiza un mínimo del 10% del
    # pool a cada participante. Con muchos participantes esos mínimos se
    # solapan y suman más del 100% del pool (p.ej. 20 participantes al 5%
    # cada uno reparten un 200% del pool nominal) — se reescala el conjunto
    # para no superar xp_total/monedas_total, conservando la proporción
    # relativa entre participantes.
    brutas = [
        (jugador, dano, *calcular_recompensas_participante(boss_id, dano, dano_total))
        for jugador, dano in participantes
    ]
    xp_bruto_total = sum(xp for _, _, xp, _ in brutas)
    mon_bruto_total = sum(mon for _, _, _, mon in brutas)
    escala_xp = min(1.0, datos["xp_total"] / xp_bruto_total) if xp_bruto_total > 0 else 1.0
    escala_mon = min(1.0, datos["monedas_total"] / mon_bruto_total) if mon_bruto_total > 0 else 1.0

    for jugador, dano, xp_bruto, mon_bruto in brutas:
        xp = max(1, int(xp_bruto * escala_xp))
        monedas = max(1, int(mon_bruto * escala_mon))
        pct = int(dano / dano_total * 100)

        jugador.db.experiencia = (jugador.db.experiencia or 0) + xp
        jugador.db.monedas = (jugador.db.monedas or 0) + monedas

        # Registrar logro
        derrotados = dict(jugador.db.jefes_mundo_derrotados or {})
        derrotados[boss_id] = derrotados.get(boss_id, 0) + 1
        jugador.db.jefes_mundo_derrotados = derrotados

        jugador.msg(
            f"\n|Y¡Has participado en la derrota de {datos['nombre']}!|n\n"
            f"  Daño infligido: |w{dano}|n ({pct}% del total)\n"
            f"  |g+{xp} XP  +{monedas} monedas|n\n"
        )

        # Subida de nivel — igual que quests/contratos/expediciones/mazmorras,
        # que llaman a procesar_subida_de_nivel() justo tras dar su XP. Sin
        # esto, el XP del jefe de mundo se acumulaba por encima del umbral
        # de nivel sin que nivel/stats/HP máximo se actualizaran de verdad
        # hasta el siguiente kill de combate normal del jugador.
        try:
            from features.combat.handler import _get_stats_base, _set_stat
            from systems.combat.engine import procesar_subida_de_nivel
            stats = _get_stats_base(jugador)
            subio, nuevos_stats = procesar_subida_de_nivel(stats)
            if subio:
                for k, v in nuevos_stats.items():
                    _set_stat(jugador, k, v)
                jugador.msg(
                    f"\n|Y🌟 ¡SUBISTE AL NIVEL {nuevos_stats['nivel']}!|n\n"
                    f"  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo\n"
                    f"  |gHP restaurado al máximo.|n\n"
                )
        except Exception:
            logger.log_trace("WorldBossScript: error procesando subida de nivel.")

        try:
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(jugador)
        except Exception:
            pass

    # Loot único al top dañador
    loot_key = datos.get("loot_unico")
    if loot_key:
        try:
            from evennia.prototypes import spawner as sp
            item = sp.spawn(loot_key)[0]
            item.location = top_jugador
            top_jugador.msg(
                f"|Y★ ¡Has recibido |w{item.key}|Y como mayor dañador!|n"
            )
        except Exception as err:
            logger.log_err(f"World boss loot error ({loot_key}): {err}")

    # Anuncio global de muerte
    from evennia import SESSION_HANDLER
    nombres = ", ".join(j.key for j, _ in participantes)
    mensaje = (
        f"\n{datos['desc_muerte']}\n"
        f"|wParticipantes:|n {nombres}\n"
    )
    for session in SESSION_HANDLER.get_sessions():
        puppet = session.get_puppet()
        if puppet:
            puppet.msg(mensaje)

    # Registrar en el script global
    try:
        script = obtener_world_boss_script()
        script.registrar_muerte_boss(boss_id)
    except Exception as err:
        logger.log_err(f"WorldBossScript.registrar_muerte_boss error: {err}")
