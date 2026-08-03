"""
features/guild_wars/guild_war_script.py

Script global que gestiona retos y guerras activas entre gremios.
El PvP en sí ya es libre en todo momento (features/combat/handler.py);
este script solo declara el periodo de guerra y cuenta las bajas entre
los dos gremios implicados, cerrando la guerra automáticamente (tick
cada 60s) o por rendición.
"""
import time

from evennia import DefaultScript

TICK_INTERVALO = 60


class GuildWarScript(DefaultScript):

    def at_script_creation(self):
        self.key = "guerras_gremios_global"
        self.desc = "Gestor de guerras entre gremios"
        self.persistent = True
        self.interval = TICK_INTERVALO
        self.db.retos = {}     # {gremio_retado: {gremio_retador, timestamp}}
        self.db.guerras = {}   # {war_id: entry}
        self.db.next_id = 1

    # ------------------------------------------------------------------ #
    #  Tick — cierre automático de guerras expiradas
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        from systems.guild_wars.guild_wars import guerra_expirada
        guerras = dict(self.db.guerras or {})
        ahora = time.time()
        for war_id, entry in list(guerras.items()):
            if guerra_expirada(entry["timestamp_inicio"], ahora):
                self._cerrar_guerra(war_id, entry)

    def _cerrar_guerra(self, war_id: str, entry: dict):
        from systems.guild_wars.guild_wars import formatear_resultado
        from features.guilds.guild_script import obtener_gremio_por_nombre

        guerras = dict(self.db.guerras or {})
        guerras.pop(war_id, None)
        self.db.guerras = guerras

        mensaje = formatear_resultado(entry)
        for nombre in (entry["gremio_a"], entry["gremio_b"]):
            gremio = obtener_gremio_por_nombre(nombre)
            if gremio:
                gremio.notificar_miembros(mensaje)

    # ------------------------------------------------------------------ #
    #  Retos
    # ------------------------------------------------------------------ #

    @staticmethod
    def _ocupado_en_retos(retos: dict, gremio_nombre: str) -> bool:
        """
        True si `gremio_nombre` ya participa en algún reto pendiente, como
        retado (clave de `retos`) o como retador (valor `gremio_retador` de
        cualquier entrada). Un gremio solo puede tener un reto pendiente a
        la vez, en cualquiera de los dos roles.
        """
        if gremio_nombre in retos:
            return True
        return any(reto["gremio_retador"] == gremio_nombre for reto in retos.values())

    def declarar(self, gremio_a_nombre: str, gremio_b_nombre: str) -> tuple[bool, str]:
        if gremio_a_nombre == gremio_b_nombre:
            return False, "No puedes declararle la guerra a tu propio gremio."
        if self.guerra_de(gremio_a_nombre)[0]:
            return False, "Tu gremio ya está en guerra."
        if self.guerra_de(gremio_b_nombre)[0]:
            return False, "Ese gremio ya está en guerra con otro."

        retos = dict(self.db.retos or {})
        if self._ocupado_en_retos(retos, gremio_a_nombre):
            return False, "Tu gremio ya tiene un reto de guerra pendiente. Espera a que expire o sea respondido."
        if self._ocupado_en_retos(retos, gremio_b_nombre):
            return False, "Ese gremio ya tiene un reto de guerra pendiente."

        retos[gremio_b_nombre] = {
            "gremio_retador": gremio_a_nombre,
            "timestamp": time.time(),
        }
        self.db.retos = retos
        return True, ""

    def aceptar(self, gremio_b_nombre: str) -> tuple[bool, str]:
        from systems.guild_wars.guild_wars import reto_expirado

        retos = dict(self.db.retos or {})
        reto = retos.get(gremio_b_nombre)
        if not reto:
            return False, "Tu gremio no tiene ningún reto de guerra pendiente."
        if reto_expirado(reto["timestamp"], time.time()):
            del retos[gremio_b_nombre]
            self.db.retos = retos
            return False, "El reto de guerra ha expirado."

        if self.guerra_de(reto["gremio_retador"])[0]:
            del retos[gremio_b_nombre]
            self.db.retos = retos
            return False, "El gremio que te retó ya está en guerra con otro."

        del retos[gremio_b_nombre]
        self.db.retos = retos

        war_id = str(self.db.next_id or 1)
        self.db.next_id = int(self.db.next_id or 1) + 1

        guerras = dict(self.db.guerras or {})
        guerras[war_id] = {
            "gremio_a":         reto["gremio_retador"],
            "gremio_b":         gremio_b_nombre,
            "kills_a":          0,
            "kills_b":          0,
            "timestamp_inicio": time.time(),
        }
        self.db.guerras = guerras

        from features.guilds.guild_script import obtener_gremio_por_nombre
        mensaje = (
            f"|r⚔ ¡Guerra declarada entre {reto['gremio_retador']} y "
            f"{gremio_b_nombre}!|n Dura 1 hora."
        )
        for nombre in (reto["gremio_retador"], gremio_b_nombre):
            gremio = obtener_gremio_por_nombre(nombre)
            if gremio:
                gremio.notificar_miembros(mensaje)
        return True, ""

    def rechazar(self, gremio_b_nombre: str) -> tuple[bool, str]:
        retos = dict(self.db.retos or {})
        if gremio_b_nombre not in retos:
            return False, "Tu gremio no tiene ningún reto de guerra pendiente."
        del retos[gremio_b_nombre]
        self.db.retos = retos
        return True, ""

    # ------------------------------------------------------------------ #
    #  Guerra activa
    # ------------------------------------------------------------------ #

    def guerra_de(self, gremio_nombre: str):
        """Devuelve (war_id, entry) de la guerra activa de ese gremio, o (None, None)."""
        for war_id, entry in dict(self.db.guerras or {}).items():
            if gremio_nombre in (entry["gremio_a"], entry["gremio_b"]):
                return war_id, entry
        return None, None

    def rendirse(self, gremio_nombre: str) -> tuple[bool, str]:
        from systems.guild_wars.guild_wars import rival_de
        from features.guilds.guild_script import obtener_gremio_por_nombre

        war_id, entry = self.guerra_de(gremio_nombre)
        if not war_id:
            return False, "Tu gremio no está en ninguna guerra."

        rival = rival_de(entry, gremio_nombre)
        guerras = dict(self.db.guerras or {})
        guerras.pop(war_id, None)
        self.db.guerras = guerras

        mensaje = f"|y{gremio_nombre} se ha rendido.|n |Y¡{rival} gana la guerra!|n"
        for nombre in (entry["gremio_a"], entry["gremio_b"]):
            gremio = obtener_gremio_por_nombre(nombre)
            if gremio:
                gremio.notificar_miembros(mensaje)
        return True, ""

    def registrar_kill_si_en_guerra(self, asesino, muerto) -> bool:
        """
        Si asesino y muerto pertenecen a gremios enfrentados en una guerra
        activa, anota la baja y notifica a ambos gremios. Devuelve True si
        se registró.
        """
        from systems.guild_wars.guild_wars import registrar_kill, rival_de

        gremio_asesino = getattr(asesino.db, "gremio", None)
        gremio_muerto = getattr(muerto.db, "gremio", None)
        if not gremio_asesino or not gremio_muerto:
            return False

        guerras = dict(self.db.guerras or {})
        for war_id, entry in guerras.items():
            if rival_de(entry, gremio_asesino) != gremio_muerto:
                continue
            nuevo = registrar_kill(entry, gremio_asesino)
            guerras[war_id] = nuevo
            self.db.guerras = guerras

            from features.guilds.guild_script import obtener_gremio_por_nombre
            mensaje = (
                f"|r⚔ {asesino.key} ({gremio_asesino}) ha derrotado a "
                f"{muerto.key} ({gremio_muerto}) en la guerra de gremios.|n"
            )
            for nombre in (entry["gremio_a"], entry["gremio_b"]):
                gremio = obtener_gremio_por_nombre(nombre)
                if gremio:
                    gremio.notificar_miembros(mensaje)
            return True
        return False


def obtener_guerra_script() -> GuildWarScript:
    """Devuelve el script global de guerras de gremios, creándolo si no existe."""
    from evennia.scripts.models import ScriptDB
    from evennia.utils import create

    script = ScriptDB.objects.filter(db_key="guerras_gremios_global").first()
    if script:
        return script
    return create.create_script(GuildWarScript, key="guerras_gremios_global", persistent=True)
