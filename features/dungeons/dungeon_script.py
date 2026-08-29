"""
features/dungeons/dungeon_script.py

MazmorraScript — script persistente que gestiona una instancia de mazmorra.

Ciclo de vida:
  1. Se crea en `at_object_creation` vinculado a un objeto global (limbo).
  2. Genera las salas temporales y mueve a los jugadores a la primera.
  3. `avanzar` es llamado por CmdAvanzar; avanza a la sala siguiente o
     completa la mazmorra (recompensas + teleport + limpieza).
  4. El intervalo de 3600s actúa de timeout; `at_repeat` limpia todo.

Salas temporales tienen `db.mazmorra_script_id = script.id` para que el
limpiador de cold_start las identifique.
"""

from evennia import DefaultScript, search_object
from evennia.utils import create, logger
from evennia.prototypes import spawner

from systems.dungeons.dungeons import (
    MAZMORRAS,
    DIFICULTADES,
    NOMBRES_DIFICULTAD,
    calcular_recompensas,
    escalar_hp,
    total_salas,
    es_sala_jefe,
)


class MazmorraScript(DefaultScript):

    def at_script_creation(self):
        self.key = "mazmorra_script"
        self.desc = "Instancia de mazmorra activa"
        self.interval = 3600
        self.start_delay = True
        self.persistent = True
        self.db.mazmorra_id = None
        self.db.dificultad = "normal"
        self.db.jugadores = []      # lista de dbrefs de personajes
        self.db.sala_actual = 0     # índice de la sala actual (0-based)
        self.db.salas = []          # lista de objetos Room creados
        self.db.sala_salida = None  # dbref de la sala vestíbulo (destino al salir)
        self.db.estado = "activa"   # "activa" | "completada"

    # ---------------------------------------------------------------------- #
    #  Inicio de la instancia
    # ---------------------------------------------------------------------- #

    def iniciar(self, mazmorra_id: str, dificultad: str, jugadores: list, sala_salida):
        """
        Crea las salas temporales, spawna los enemigos de la primera sala,
        y mueve a todos los jugadores dentro.

        jugadores  — lista de objetos Character
        sala_salida — Room de vuelta (Vestíbulo del Portal)
        """
        self.db.mazmorra_id = mazmorra_id
        self.db.dificultad = dificultad
        self.db.jugadores = [j.dbref for j in jugadores]
        self.db.sala_salida = sala_salida.dbref if sala_salida else None
        self.db.sala_actual = 0
        self.db.estado = "activa"

        datos_maz = MAZMORRAS.get(mazmorra_id, {})
        salas_datos = datos_maz.get("salas", [])

        # Crear las salas temporales
        salas_creadas = []
        for sala_info in salas_datos:
            sala = create.create_object(
                "typeclasses.rooms.Room",
                key=sala_info["nombre"],
            )
            sala.db.desc = sala_info["desc"]
            sala.db.es_mazmorra = True
            sala.db.mazmorra_script_id = self.id
            sala.db.zona = f"mazmorra_{mazmorra_id}"
            sala.db.enemigos_spawneados = False
            salas_creadas.append(sala)
        self.db.salas = salas_creadas

        # Spawnear enemigos en la primera sala
        self._spawnear_sala(0)

        # Mover jugadores
        nombre_maz = datos_maz.get("nombre", mazmorra_id)
        dif_txt = NOMBRES_DIFICULTAD.get(dificultad, dificultad)
        for jugador in jugadores:
            jugador.move_to(salas_creadas[0], quiet=True)
            jugador.msg(
                f"\n|Y¡Entras en {nombre_maz}!|n (dificultad {dif_txt})\n"
                f"{salas_creadas[0].db.desc}\n"
                f"|xUsa |wavanzar|x cuando hayas derrotado a todos los enemigos.|n"
            )

    # ---------------------------------------------------------------------- #
    #  Avance de sala
    # ---------------------------------------------------------------------- #

    def avanzar(self, jugador):
        """
        Intenta avanzar al siguiente tramo.
        Llamado desde CmdAvanzar tras verificar que el jugador está en la instancia.
        """
        if self.db.estado != "activa":
            jugador.msg("|yEsta mazmorra ya ha concluido.|n")
            return

        sala_idx = self.db.sala_actual
        salas = self.db.salas or []
        if not salas or sala_idx >= len(salas):
            jugador.msg("|rError interno: no se encontraron salas.|n")
            return

        sala_actual = salas[sala_idx]

        # Verificar sala despejada
        if not self._sala_despejada(sala_actual):
            jugador.msg(
                "|rAún quedan enemigos en esta sala. "
                "Derrota a todos antes de avanzar.|n"
            )
            return

        siguiente = sala_idx + 1
        if siguiente >= len(salas):
            # Era la última sala (jefe): completar mazmorra
            self._completar(jugador)
        else:
            self.db.sala_actual = siguiente
            nueva_sala = salas[siguiente]
            # Mover a todos los jugadores presentes en la sala actual
            for dbref in self.db.jugadores:
                chars = search_object(dbref)
                if chars and chars[0].location == sala_actual:
                    chars[0].move_to(nueva_sala, quiet=True)
            self._spawnear_sala(siguiente)
            # Descripción de la nueva sala
            nueva_sala.msg_contents(nueva_sala.db.desc or nueva_sala.key)
            nueva_sala.msg_contents(
                "|xUsa |wavanzar|x cuando hayas derrotado a todos los enemigos.|n"
            )

    # ---------------------------------------------------------------------- #
    #  Salida sin recompensa
    # ---------------------------------------------------------------------- #

    def salir(self, jugador):
        """Expulsa a un jugador de la mazmorra sin recompensa."""
        destino = self._sala_salida()
        if destino:
            jugador.move_to(destino, quiet=True)
            jugador.msg("|yHas abandonado la mazmorra sin recompensa.|n")
        else:
            jugador.msg("|rNo se encontró el vestíbulo de salida.|n")

        # Ya no cuenta como miembro activo: no recibirá recompensas si el
        # resto del grupo completa la mazmorra después.
        dbrefs = list(self.db.jugadores or [])
        if jugador.dbref in dbrefs:
            dbrefs.remove(jugador.dbref)
        self.db.jugadores = dbrefs

        # Si ya no quedan jugadores activos, limpiar
        restantes = self._jugadores_dentro()
        if not restantes:
            self._limpiar()

    # ---------------------------------------------------------------------- #
    #  Timeout (at_repeat)
    # ---------------------------------------------------------------------- #

    def at_repeat(self):
        """Llamado tras 3600s; limpia la instancia por timeout."""
        if self.db.estado == "activa":
            for jugador in self._jugadores_dentro():
                destino = self._sala_salida()
                if destino:
                    jugador.move_to(destino, quiet=True)
                jugador.msg(
                    "|rLa mazmorra ha expirado por tiempo. Has sido expulsado.|n"
                )
        self._limpiar()

    # ---------------------------------------------------------------------- #
    #  Helpers privados
    # ---------------------------------------------------------------------- #

    def _spawnear_sala(self, idx: int):
        salas = self.db.salas or []
        if idx >= len(salas):
            return
        sala = salas[idx]
        if sala.db.enemigos_spawneados:
            return
        sala.db.enemigos_spawneados = True

        datos_maz = MAZMORRAS.get(self.db.mazmorra_id, {})
        salas_datos = datos_maz.get("salas", [])
        if idx >= len(salas_datos):
            return
        sala_info = salas_datos[idx]
        dificultad = self.db.dificultad or "normal"

        for proto_key, cantidad in sala_info.get("enemigos", []):
            for _ in range(cantidad):
                try:
                    npc = spawner.spawn(proto_key)[0]
                    npc.location = sala
                    # Escalar HP
                    base_hp = npc.db.hp_max or npc.db.hp or 50
                    hp_escalado = escalar_hp(base_hp, dificultad)
                    npc.db.hp = hp_escalado
                    npc.db.hp_max = hp_escalado
                    # Evitar respawn en salas temporales
                    npc.db.npc_prototipo = None
                except Exception as err:
                    logger.log_err(f"MazmorraScript: error spawning '{proto_key}': {err}")

    def _sala_despejada(self, sala) -> bool:
        """True si no hay NPCs vivos en la sala."""
        for obj in sala.contents:
            tipo = type(obj).__name__
            if tipo == "NPC":
                hp = getattr(obj.db, "hp", 1)
                if (hp or 0) > 0:
                    return False
        return True

    def _completar(self, jugador_trigger):
        """Reparte recompensas y limpia la instancia."""
        self.db.estado = "completada"
        mazmorra_id = self.db.mazmorra_id
        dificultad = self.db.dificultad or "normal"
        datos_maz = MAZMORRAS.get(mazmorra_id, {})
        nombre_maz = datos_maz.get("nombre", mazmorra_id)
        xp_bonus, monedas_bonus = calcular_recompensas(mazmorra_id, dificultad)
        dif_txt = NOMBRES_DIFICULTAD.get(dificultad, dificultad)
        destino = self._sala_salida()

        # db.jugadores solo se depura en salir() -- cualquier otra forma de
        # abandonar la instancia (viajar, una muerte que manda a casa, etc.)
        # es un move_to() plano que nunca lo toca. Filtrar por presencia real
        # evita recompensar a quien ya no está físicamente en la mazmorra.
        presentes = {c.dbref for c in self._jugadores_dentro()}
        for dbref in (self.db.jugadores or []):
            if dbref not in presentes:
                continue
            chars = search_object(dbref)
            if not chars:
                continue
            char = chars[0]
            # XP
            char.db.experiencia = (char.db.experiencia or 0) + xp_bonus
            # Monedas
            char.db.monedas = (char.db.monedas or 0) + monedas_bonus
            # Registrar mazmorra completada
            completadas = dict(char.db.mazmorras_completadas or {})
            completadas[mazmorra_id] = completadas.get(mazmorra_id, 0) + 1
            char.db.mazmorras_completadas = completadas
            # Marcar legendario
            if dificultad == "legendario":
                char.db.mazmorra_legendario = True

            char.msg(
                f"\n|Y¡¡ {nombre_maz} completada !! |n(dificultad {dif_txt})\n"
                f"|g+{xp_bonus} XP  +{monedas_bonus} monedas|n\n"
            )
            # Subida de nivel — a diferencia de quests/contratos/expediciones,
            # esta recompensa nunca procesaba el XP recién otorgado contra
            # procesar_subida_de_nivel(): el personaje acumulaba experiencia
            # por encima del umbral sin subir de nivel de verdad (ni stats,
            # ni HP máximo, ni el mensaje de subida) hasta su siguiente kill
            # de combate normal, que sí llama a _dar_xp_a_grupo().
            try:
                from features.combat.handler import _get_stats, _set_stat
                from systems.combat.engine import procesar_subida_de_nivel
                stats = _get_stats(char)
                subio, nuevos_stats = procesar_subida_de_nivel(stats)
                if subio:
                    for k, v in nuevos_stats.items():
                        _set_stat(char, k, v)
                    char.msg(
                        f"\n|Y🌟 ¡SUBISTE AL NIVEL {nuevos_stats['nivel']}!|n\n"
                        f"  +1 Fuerza, +1 Constitución, +1 Defensa, +10 HP máximo\n"
                        f"  |gHP restaurado al máximo.|n\n"
                    )
            except Exception:
                logger.log_trace("MazmorraScript: error procesando subida de nivel.")
            # Comprobar logros
            try:
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(char)
            except Exception:
                pass

            if destino:
                char.move_to(destino, quiet=True)

        self._limpiar()

    def _sala_salida(self):
        if not self.db.sala_salida:
            return None
        salas = search_object(self.db.sala_salida)
        return salas[0] if salas else None

    def _jugadores_dentro(self) -> list:
        resultado = []
        salas = self.db.salas or []
        salas_set = set(s.id for s in salas if s)
        for dbref in (self.db.jugadores or []):
            chars = search_object(dbref)
            if chars and chars[0].location and chars[0].location.id in salas_set:
                resultado.append(chars[0])
        return resultado

    def _limpiar(self):
        """Elimina todas las salas temporales y el propio script."""
        for sala in (self.db.salas or []):
            try:
                sala.delete()
            except Exception:
                pass
        self.db.salas = []
        try:
            self.delete()
        except Exception:
            pass
