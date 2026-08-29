"""
features/expeditions/expedition_script.py

ExpedicionScript — script instanciado por grupo al iniciar una expedición.
Gestiona la creación de sala temporal, el spawn de oleadas y las recompensas.

Ciclo de vida:
  1. Líder ejecuta `expedicion iniciar <tipo>`
  2. Se crea el script y se llama a iniciar(lider, miembros)
  3. Se crea sala temporal (db.es_expedicion=True)
  4. Los miembros son teleportados a la sala
  5. Primera oleada spawneada
  6. El script hace tick cada 5s: si no hay NPCs vivos → siguiente oleada
  7. Tras la última oleada → completar() → recompensas → teleport al origen

Timeout: 30 minutos (interval=1800). Si expira, limpia sin recompensa.
"""
from evennia import DefaultScript
from evennia.utils import logger
from evennia.utils.create import create_object, create_script


_TIMEOUT_SEGS = 1800
_TICK_SEGS = 5
_PAUSA_ENTRE_OLEADAS = 8  # segundos de aviso antes de la siguiente oleada


class ExpedicionScript(DefaultScript):

    def at_script_creation(self):
        self.key = "expedicion_script"
        self.desc = "Gestiona una expedición grupal activa"
        self.persistent = False
        self.interval = _TICK_SEGS
        self.db.tipo_id = None
        self.db.lider_dbref = None
        self.db.miembros_dbrefs = []
        self.db.origenes = {}       # {dbref: sala_dbref_origen}
        self.db.sala_dbref = None
        self.db.oleada_actual = 0
        self.db.activo = False
        self.db.completada = False
        self.db.ticks_pausa = 0     # ticks de espera entre oleadas
        self.db.tiempo_inicio = 0

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def iniciar(self, lider, miembros):
        """
        Punto de entrada. Crea la sala temporal, teleporta a los miembros
        y lanza la primera oleada.
        miembros: lista de Character (incluye al líder).
        """
        import time
        from systems.expeditions.expeditions import EXPEDICIONES, OLEADAS

        tipo_id = self.db.tipo_id
        exp = EXPEDICIONES[tipo_id]

        self.db.lider_dbref = lider.dbref
        self.db.miembros_dbrefs = [m.dbref for m in miembros]
        self.db.origenes = {m.dbref: m.location.dbref for m in miembros if m.location}
        self.db.oleada_actual = 0
        self.db.activo = True
        self.db.tiempo_inicio = time.time()

        # Crear sala temporal
        from typeclasses.rooms import Room
        sala = create_object(
            Room,
            key=exp["zona_nombre"],
            nohome=True,
        )
        sala.db.desc = (
            f"Un lugar apartado donde el grupo se enfrenta a una expedición. "
            f"El peligro es real y solo la valentía os sacará de aquí."
        )
        sala.db.es_expedicion = True
        sala.db.expedicion_script_id = self.id
        self.db.sala_dbref = sala.dbref

        # Teleportar miembros
        for m in miembros:
            m.move_to(sala, quiet=True, move_type="teleport")

        total = len(OLEADAS[tipo_id])
        sala.msg_contents(
            f"\n|cExpedición: |Y{exp['nombre']}|n\n"
            f"|w{len(miembros)} aventureros|n se adentran en lo desconocido.\n"
            f"Oleadas totales: |w{total}|n  (la última será el jefe)\n"
        )

        self._lanzar_oleada()

    def abandonar(self, jugador):
        """Un jugador abandona la expedición voluntariamente."""
        sala = self._sala()
        if sala:
            sala.msg_contents(
                f"|r{jugador.key} abandona la expedición.|n"
            )
        self._teleportar_a_origen(jugador)

        dbrefs = list(self.db.miembros_dbrefs or [])
        if jugador.dbref in dbrefs:
            dbrefs.remove(jugador.dbref)
        self.db.miembros_dbrefs = dbrefs

        if not dbrefs:
            self._limpiar(exito=False)

    # ------------------------------------------------------------------ #
    #  Tick principal
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        if self.db.completada:
            # Expedición ya superada: cuenta atrás antes de teleportar y limpiar.
            if self.db.ticks_pausa > 0:
                self.db.ticks_pausa -= 1
                if self.db.ticks_pausa == 0:
                    self._limpiar(exito=True)
            return

        if not self.db.activo:
            return

        # Comprobar timeout global
        import time
        if time.time() - (self.db.tiempo_inicio or 0) > _TIMEOUT_SEGS:
            sala = self._sala()
            if sala:
                sala.msg_contents(
                    "|rEl tiempo límite de la expedición ha expirado. "
                    "El grupo es expulsado sin recompensa.|n"
                )
            self._limpiar(exito=False)
            return

        # ¿Estamos en pausa entre oleadas?
        if self.db.ticks_pausa > 0:
            self.db.ticks_pausa -= 1
            if self.db.ticks_pausa == 0:
                self._lanzar_oleada()
            return

        # Comprobar si todos los NPCs de la sala están muertos
        sala = self._sala()
        if not sala:
            self._limpiar(exito=False)
            return

        npcs_vivos = [
            obj for obj in sala.contents
            if getattr(obj, "is_typeclass", lambda _: False)("typeclasses.npc.NPC")
            and (getattr(obj.db, "hp", 1) or 1) > 0
        ]
        if npcs_vivos:
            return  # oleada en curso, esperar

        # Oleada superada
        oleada_idx = self.db.oleada_actual
        self._recompensar_oleada(oleada_idx)

        from systems.expeditions.expeditions import total_oleadas
        if oleada_idx >= total_oleadas(self.db.tipo_id) - 1:
            # Era la última → completar
            self._completar()
        else:
            # Siguiente oleada tras pausa
            self.db.oleada_actual = oleada_idx + 1
            sala.msg_contents(
                f"\n|g¡Oleada {oleada_idx + 1} superada!|n  "
                f"La siguiente comienza en |w{_PAUSA_ENTRE_OLEADAS}|n segundos...\n"
            )
            self.db.ticks_pausa = max(1, _PAUSA_ENTRE_OLEADAS // _TICK_SEGS)

    # ------------------------------------------------------------------ #
    #  Oleadas
    # ------------------------------------------------------------------ #

    def _lanzar_oleada(self):
        from systems.expeditions.expeditions import (
            OLEADAS, total_oleadas, es_oleada_jefe, formatear_progreso
        )
        from features.spawn.manager import spawn_npc

        tipo_id = self.db.tipo_id
        oleada_idx = self.db.oleada_actual
        sala = self._sala()
        if not sala:
            return

        sala.msg_contents(formatear_progreso(tipo_id, oleada_idx))

        es_jefe = es_oleada_jefe(tipo_id, oleada_idx)
        if es_jefe:
            sala.msg_contents("|r¡EL JEFE EMERGE!|n  ¡Preparaos!")

        oleada = OLEADAS[tipo_id][oleada_idx]
        for proto_key, cantidad in oleada:
            for _ in range(cantidad):
                try:
                    npc = spawn_npc(proto_key, sala)
                    if npc:
                        npc.db.npc_prototipo = None  # sin respawn
                        npc.db.expedicion_script_id = self.id
                except Exception as e:
                    logger.log_err(f"ExpedicionScript._lanzar_oleada spawn error: {e}")

    # ------------------------------------------------------------------ #
    #  Recompensas
    # ------------------------------------------------------------------ #

    def _recompensar_oleada(self, oleada_idx: int):
        from systems.expeditions.expeditions import calcular_recompensa_oleada
        from systems.combat.engine import procesar_subida_de_nivel
        from features.combat.handler import _get_stats, _set_stat

        tipo_id = self.db.tipo_id
        miembros = self._miembros_en_sala()
        if not miembros:
            return

        rec = calcular_recompensa_oleada(tipo_id, len(miembros))
        for m in miembros:
            xp_actual = getattr(m.db, "experiencia", 0) or 0
            m.db.experiencia = xp_actual + rec["xp"]
            m.db.monedas = (getattr(m.db, "monedas", 0) or 0) + rec["monedas"]
            subio, nuevos_stats = procesar_subida_de_nivel(_get_stats(m))
            if subio:
                for k, v in nuevos_stats.items():
                    _set_stat(m, k, v)
                m.msg(f"\n|Y¡Has subido al nivel {nuevos_stats['nivel']}!|n\n")
                try:
                    from features.achievements.commands import comprobar_y_notificar
                    comprobar_y_notificar(m)
                except Exception:
                    pass

    def _completar(self):
        from systems.expeditions.expeditions import (
            EXPEDICIONES, calcular_bonus_completar
        )
        from systems.combat.engine import procesar_subida_de_nivel
        from features.combat.handler import _get_stats, _set_stat

        tipo_id = self.db.tipo_id
        exp = EXPEDICIONES[tipo_id]
        miembros = self._miembros_en_sala()
        self.db.activo = False
        self.db.completada = True

        sala = self._sala()
        if sala:
            sala.msg_contents(
                f"\n|Y¡EXPEDICIÓN COMPLETADA!|n  "
                f"|c{exp['nombre']}|n ha sido superada.\n"
                f"El grupo será teletransportado en |w5|n segundos.\n"
            )

        # Bonus adicional únicamente -- las recompensas de cada oleada
        # (incluida la del jefe) ya se pagaron una a una en
        # _recompensar_oleada(), que at_repeat() llama para toda oleada que
        # se despeja, sin excluir la última.
        rec = calcular_bonus_completar(tipo_id, max(len(miembros), 1))
        for m in miembros:
            m.db.expediciones_completadas = (
                getattr(m.db, "expediciones_completadas", 0) or 0
            ) + 1
            if tipo_id == "fortaleza_caida":
                m.db.fortaleza_completada = True
            xp_actual = getattr(m.db, "experiencia", 0) or 0
            m.db.experiencia = xp_actual + rec["xp"]
            m.db.monedas = (getattr(m.db, "monedas", 0) or 0) + rec["monedas"]
            subio, nuevos_stats = procesar_subida_de_nivel(_get_stats(m))
            if subio:
                for k, v in nuevos_stats.items():
                    _set_stat(m, k, v)
                m.msg(f"\n|Y¡Has subido al nivel {nuevos_stats['nivel']}!|n\n")
            m.msg(
                f"  Recompensa: |g+{rec['xp']} XP|n  |y+{rec['monedas']} monedas|n"
            )
            try:
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(m)
            except Exception:
                pass
            try:
                from features.daily.daily_script import notificar_progreso
                notificar_progreso(m, "expedicion")
            except Exception:
                pass

        # Pausa de 5s antes de teleportar y limpiar (gestionada en at_repeat
        # cuando self.db.completada es True).
        self.db.ticks_pausa = max(1, 5 // _TICK_SEGS)

    # ------------------------------------------------------------------ #
    #  Limpieza
    # ------------------------------------------------------------------ #

    def _limpiar(self, exito: bool = False):
        self.db.activo = False

        # Teleportar a todos de vuelta
        sala = self._sala()
        if sala:
            for obj in list(sala.contents):
                if hasattr(obj, "has_account") and obj.has_account:
                    self._teleportar_a_origen(obj)
                elif getattr(obj, "is_typeclass", lambda _: False)("typeclasses.npc.NPC"):
                    try:
                        obj.delete()
                    except Exception:
                        pass
            try:
                sala.delete()
            except Exception:
                pass

        try:
            self.delete()
        except Exception:
            pass

    def _teleportar_a_origen(self, jugador):
        from evennia import search_object
        origenes = dict(self.db.origenes or {})
        origen_dbref = origenes.get(jugador.dbref)
        if origen_dbref:
            resultados = search_object(origen_dbref)
            if resultados:
                jugador.move_to(resultados[0], quiet=True, move_type="teleport")
                jugador.msg("|cHas regresado al mundo exterior.|n")
                return
        # Fallback: sala de inicio (zona plaza)
        from evennia import search_object as so
        plazas = so("Plaza de la Ciudad", exact=False)
        if plazas:
            jugador.move_to(plazas[0], quiet=True, move_type="teleport")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _sala(self):
        if not self.db.sala_dbref:
            return None
        from evennia import search_object
        resultados = search_object(self.db.sala_dbref)
        return resultados[0] if resultados else None

    def _miembros_en_sala(self):
        sala = self._sala()
        if not sala:
            return []
        return [
            obj for obj in sala.contents
            if hasattr(obj, "has_account") and obj.has_account
        ]
