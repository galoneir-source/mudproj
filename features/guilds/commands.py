"""
features/guilds/commands.py

Comandos del sistema de gremios de jugadores:
  crear gremio, gremio, invitar gremio, aceptar gremio, rechazar gremio,
  salir gremio, expulsar gremio, promover, degradar, gbanco, disolver gremio
"""
import time

from evennia import Command, CmdSet, search_object

from features.guilds.guild_script import (
    GuildScript,
    obtener_gremio_de,
    obtener_gremio_por_nombre,
)
from systems.guilds.guilds import (
    COSTE_CREAR_GREMIO,
    INVITACION_TIMEOUT,
    MAX_MIEMBROS,
    RANGO_LIDER,
    RANGO_MIEMBRO,
    RANGO_OFICIAL,
    indice_rango,
    normalizar_nombre,
    puede_expulsar,
    puede_invitar,
    puede_retirar_banco,
    simbolo_rango,
    validar_nombre_gremio,
)


# --------------------------------------------------------------------------- #
#  Utilidades internas
# --------------------------------------------------------------------------- #

def _tiempo_fundado(ts: float) -> str:
    dias = int((time.time() - ts) / 86400)
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "hace 1 día"
    return f"hace {dias} días"


def _buscar_miembro(gremio, nombre: str):
    """Busca un miembro del gremio por nombre (case-insensitive). Devuelve (char, rango) o (None, None)."""
    for dbref, rango in dict(gremio.db.miembros or {}).items():
        results = search_object(dbref, use_dbref=True)
        if results and results[0].key.lower() == nombre.lower():
            return results[0], rango
    return None, None


def _limpiar_invitacion(char):
    char.db.invitacion_gremio = None


# --------------------------------------------------------------------------- #
#  crear gremio
# --------------------------------------------------------------------------- #

class CmdCrearGremio(Command):
    """
    Fundar un nuevo gremio.

    Uso:
      crear gremio <nombre>

    Cuesta |Y500 monedas|n. El personaje no puede ya pertenecer a un gremio.
    El nombre debe tener entre 3 y 24 caracteres.

    Ejemplo:
      crear gremio Los Guardianes del Alba
    """
    key = "crear gremio"
    aliases = ["fundar gremio"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller
        nombre = self.args.strip()

        if not nombre:
            caller.msg("Uso: |wcrear gremio <nombre>|n")
            return

        ok, motivo = validar_nombre_gremio(nombre)
        if not ok:
            caller.msg(motivo)
            return

        if getattr(caller.db, "gremio", None):
            caller.msg("Ya perteneces a un gremio. Usa |wsalir gremio|n primero.")
            return

        monedas = getattr(caller.db, "monedas", 0) or 0
        if monedas < COSTE_CREAR_GREMIO:
            caller.msg(
                f"Necesitas |Y{COSTE_CREAR_GREMIO} monedas|n para fundar un gremio "
                f"(tienes {monedas})."
            )
            return

        if obtener_gremio_por_nombre(nombre):
            caller.msg(f"Ya existe un gremio llamado '|w{nombre}|n'.")
            return

        from evennia import create_script
        caller.db.monedas = monedas - COSTE_CREAR_GREMIO
        guild = create_script(
            GuildScript,
            key=f"guild_{normalizar_nombre(nombre)}",
            persistent=True,
        )
        guild.db.nombre   = nombre
        guild.db.fundado  = time.time()
        guild.añadir_miembro(caller, RANGO_LIDER)
        caller.db.gremios_fundados = (getattr(caller.db, "gremios_fundados", 0) or 0) + 1

        caller.msg(
            f"\n|Y🏰 ¡Gremio fundado!|n\n"
            f"  Nombre: |w{nombre}|n\n"
            f"  Rango:  {simbolo_rango(RANGO_LIDER)} {RANGO_LIDER}\n"
            f"  Coste:  {COSTE_CREAR_GREMIO} monedas deducidas.\n"
        )
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)


# --------------------------------------------------------------------------- #
#  gremio (info + descripción)
# --------------------------------------------------------------------------- #

class CmdGremio(Command):
    """
    Ver información de tu gremio o cambiar su descripción.

    Uso:
      gremio
      gremio descripcion <texto>

    El Líder puede cambiar la descripción con |wgremio descripcion <texto>|n.
    """
    key = "gremio"
    aliases = ["guild", "gr"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        args = self.args.strip()

        # Subcomando: cambiar descripción
        if args.lower().startswith("descripcion ") or args.lower().startswith("descripción "):
            rango = guild.get_rango(caller)
            if rango != RANGO_LIDER:
                caller.msg("Solo el Líder puede cambiar la descripción del gremio.")
                return
            nueva_desc = args.split(" ", 1)[1].strip()
            guild.db.descripcion = nueva_desc
            caller.msg(f"Descripción actualizada: {nueva_desc}")
            return

        # Mostrar info
        miembros_dict = dict(guild.db.miembros or {})
        n_miembros = len(miembros_dict)
        banco = guild.db.banco or 0
        desc = guild.db.descripcion or "|xSin descripción|n"
        fundado_txt = _tiempo_fundado(guild.db.fundado or time.time())

        lineas = [
            f"\n|w{'=' * 52}|n",
            f"  |c GREMIO: {guild.db.nombre}|n",
            f"|w{'=' * 52}|n",
            f"  |xFundado:|n      {fundado_txt}",
            f"  |xDescripción:|n  {desc}",
            f"  |xBanco:|n        {banco} monedas",
            f"|w{'-' * 52}|n",
            f"  |cMIEMBROS ({n_miembros}/{MAX_MIEMBROS}):|n",
        ]

        # Ordenar: Líder primero, luego Oficial, luego Miembro
        orden = [(indice_rango(r), dbref, r) for dbref, r in miembros_dict.items()]
        orden.sort(key=lambda x: -x[0])
        for _, dbref, rango in orden:
            results = search_object(dbref, use_dbref=True)
            nombre_char = results[0].key if results else f"(#{dbref})"
            sim = simbolo_rango(rango)
            lineas.append(f"  {sim} {rango:<8}  |w{nombre_char}|n")

        lineas.append(f"|w{'=' * 52}|n\n")
        caller.msg("\n".join(lineas))


# --------------------------------------------------------------------------- #
#  invitar
# --------------------------------------------------------------------------- #

class CmdInvitar(Command):
    """
    Invitar a un jugador a unirse al gremio.

    Uso:
      invitar gremio <jugador>

    El jugador debe estar en la misma sala. Tiene 2 minutos para responder.
    """
    key = "invitar gremio"
    aliases = ["invite guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        rango = guild.get_rango(caller)
        if not puede_invitar(rango):
            caller.msg("Necesitas ser al menos Oficial para invitar.")
            return

        if guild.contar_miembros() >= MAX_MIEMBROS:
            caller.msg(f"El gremio está lleno ({MAX_MIEMBROS} miembros).")
            return

        nombre_obj = self.args.strip()
        if not nombre_obj:
            caller.msg("Uso: |winvitar gremio <jugador>|n")
            return

        objetivo = caller.search(nombre_obj, location=caller.location)
        if not objetivo:
            return

        if objetivo == caller:
            caller.msg("No puedes invitarte a ti mismo.")
            return

        if not bool(getattr(objetivo, "account", None)):
            caller.msg(f"|w{objetivo.key}|n no es un jugador.")
            return

        if guild.es_miembro(objetivo):
            caller.msg(f"|w{objetivo.key}|n ya es miembro del gremio.")
            return

        if getattr(objetivo.db, "gremio", None):
            caller.msg(f"|w{objetivo.key}|n ya pertenece a otro gremio.")
            return

        # Solo bloquea si la invitación pendiente sigue vigente: una
        # invitación caducada y nunca aceptada/rechazada no debe impedir
        # invitaciones futuras (de este u otro gremio) para siempre.
        inv_existente = getattr(objetivo.db, "invitacion_gremio", None)
        if inv_existente and (time.time() - inv_existente.get("timestamp", 0)) < INVITACION_TIMEOUT:
            caller.msg(f"|w{objetivo.key}|n ya tiene una invitación de gremio pendiente.")
            return

        objetivo.db.invitacion_gremio = {
            "gremio": guild.db.nombre,
            "invitador_dbref": caller.dbref,
            "timestamp": time.time(),
        }

        caller.msg(f"Has invitado a |w{objetivo.key}|n a unirse al gremio.")
        objetivo.msg(
            f"\n|y🏰 {caller.key} te invita a unirte al gremio |w{guild.db.nombre}|n!\n"
            f"  |waceptar gremio|n  — aceptar\n"
            f"  |wrechazar gremio|n — rechazar\n"
            f"(Tienes {INVITACION_TIMEOUT // 60} minutos para responder)\n"
        )


# --------------------------------------------------------------------------- #
#  aceptar gremio
# --------------------------------------------------------------------------- #

class CmdAceptarGremio(Command):
    """
    Aceptar una invitación de gremio pendiente.

    Uso:
      aceptar gremio
    """
    key = "aceptar gremio"
    aliases = ["aceptar guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        inv = getattr(caller.db, "invitacion_gremio", None)
        if not inv:
            caller.msg("No tienes ninguna invitación de gremio pendiente.")
            return

        if (time.time() - inv.get("timestamp", 0)) >= INVITACION_TIMEOUT:
            caller.msg("La invitación ha expirado.")
            _limpiar_invitacion(caller)
            return

        nombre_gremio = inv.get("gremio", "")
        guild = obtener_gremio_por_nombre(nombre_gremio)
        if not guild:
            caller.msg("El gremio ya no existe.")
            _limpiar_invitacion(caller)
            return

        if getattr(caller.db, "gremio", None):
            caller.msg("Ya perteneces a un gremio. Usa |wsalir gremio|n primero.")
            _limpiar_invitacion(caller)
            return

        if guild.contar_miembros() >= MAX_MIEMBROS:
            caller.msg(f"El gremio está lleno ({MAX_MIEMBROS} miembros).")
            _limpiar_invitacion(caller)
            return

        guild.añadir_miembro(caller)
        _limpiar_invitacion(caller)

        caller.msg(
            f"|g¡Bienvenido al gremio |w{guild.db.nombre}|g!|n\n"
            f"  Rango actual: {simbolo_rango(RANGO_MIEMBRO)} {RANGO_MIEMBRO}"
        )
        guild.notificar_miembros(
            f"|y{caller.key}|n se ha unido al gremio.",
            excluir=caller,
        )
        from features.achievements.commands import comprobar_y_notificar
        comprobar_y_notificar(caller)
        lider = guild.get_lider()
        if lider and lider != caller:
            comprobar_y_notificar(lider)


# --------------------------------------------------------------------------- #
#  rechazar gremio
# --------------------------------------------------------------------------- #

class CmdRechazarGremio(Command):
    """
    Rechazar una invitación de gremio pendiente.

    Uso:
      rechazar gremio
    """
    key = "rechazar gremio"
    aliases = ["rechazar guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        inv = getattr(caller.db, "invitacion_gremio", None)
        if not inv:
            caller.msg("No tienes ninguna invitación de gremio pendiente.")
            return

        invitador_dbref = inv.get("invitador_dbref")
        if invitador_dbref:
            results = search_object(invitador_dbref, use_dbref=True)
            if results and results[0].sessions.count() > 0:
                results[0].msg(f"|y{caller.key}|n ha rechazado la invitación al gremio.")

        _limpiar_invitacion(caller)
        caller.msg("Has rechazado la invitación de gremio.")


# --------------------------------------------------------------------------- #
#  salir gremio
# --------------------------------------------------------------------------- #

class CmdSalirGremio(Command):
    """
    Abandonar el gremio actual.

    Uso:
      salir gremio

    Si eres el Líder y hay otros miembros, debes transferir el liderazgo
    primero con |wpromover <jugador>|n o disolver el gremio con |wdisolver gremio|n.
    """
    key = "salir gremio"
    aliases = ["abandonar gremio", "leave guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        rango = guild.get_rango(caller)
        n = guild.contar_miembros()

        if rango == RANGO_LIDER and n > 1:
            caller.msg(
                "Eres el Líder. Transfiere el liderazgo con |wpromover <jugador>|n "
                "o disuelve el gremio con |wdisolver gremio|n antes de salir."
            )
            return

        nombre_guild = guild.db.nombre
        if rango == RANGO_LIDER and n == 1:
            # Último miembro y es el líder → disolver automáticamente
            guild.disolver(devolver_banco_a=caller)
            caller.msg(f"Has disuelto el gremio |w{nombre_guild}|n y recuperado el banco.")
            return

        guild.notificar_miembros(
            f"|y{caller.key}|n ha abandonado el gremio.",
            excluir=caller,
        )
        guild.eliminar_miembro(caller)
        caller.msg(f"Has abandonado el gremio |w{nombre_guild}|n.")


# --------------------------------------------------------------------------- #
#  expulsar
# --------------------------------------------------------------------------- #

class CmdExpulsar(Command):
    """
    Expulsar a un miembro del gremio.

    Uso:
      expulsar gremio <jugador>

    El Líder puede expulsar a Oficiales y Miembros.
    El Oficial solo puede expulsar a Miembros.
    """
    key = "expulsar gremio"
    aliases = ["kick guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        rango_caller = guild.get_rango(caller)
        nombre_obj = self.args.strip()
        if not nombre_obj:
            caller.msg("Uso: |wexpulsar gremio <jugador>|n")
            return

        objetivo, rango_obj = _buscar_miembro(guild, nombre_obj)
        if not objetivo:
            caller.msg(f"No hay ningún miembro llamado '|w{nombre_obj}|n' en el gremio.")
            return

        if objetivo == caller:
            caller.msg("No puedes expulsarte a ti mismo. Usa |wsalir gremio|n.")
            return

        if not puede_expulsar(rango_caller, rango_obj):
            caller.msg(f"No tienes rango suficiente para expulsar a {objetivo.key}.")
            return

        guild.notificar_miembros(
            f"|r{objetivo.key}|n ha sido expulsado del gremio por {caller.key}.",
            excluir=objetivo,
        )
        guild.eliminar_miembro(objetivo)
        objetivo.msg(f"|rHas sido expulsado del gremio |w{guild.db.nombre}|r.|n")
        caller.msg(f"|w{objetivo.key}|n ha sido expulsado del gremio.")


# --------------------------------------------------------------------------- #
#  promover
# --------------------------------------------------------------------------- #

class CmdPromover(Command):
    """
    Ascender a un miembro en el gremio.

    Uso:
      promover <jugador>

    Miembro  → Oficial  (requiere ser Líder)
    Oficial  → Líder    (transfiere el liderazgo; tú pasas a Oficial)
    """
    key = "promover"
    aliases = ["promote", "ascender"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        if guild.get_rango(caller) != RANGO_LIDER:
            caller.msg("Solo el Líder puede promover miembros.")
            return

        nombre_obj = self.args.strip()
        if not nombre_obj:
            caller.msg("Uso: |wpromover <jugador>|n")
            return

        objetivo, rango_obj = _buscar_miembro(guild, nombre_obj)
        if not objetivo:
            caller.msg(f"No hay ningún miembro llamado '|w{nombre_obj}|n' en el gremio.")
            return

        if objetivo == caller:
            caller.msg("Ya eres el Líder.")
            return

        if rango_obj == RANGO_MIEMBRO:
            guild.cambiar_rango(objetivo, RANGO_OFICIAL)
            msg = f"|y{objetivo.key}|n ha ascendido a |y{RANGO_OFICIAL}|n."
        elif rango_obj == RANGO_OFICIAL:
            # Transferencia de liderazgo
            guild.cambiar_rango(objetivo, RANGO_LIDER)
            guild.cambiar_rango(caller, RANGO_OFICIAL)
            msg = (
                f"|Y{objetivo.key}|n es ahora el nuevo |Y{RANGO_LIDER}|n del gremio. "
                f"{caller.key} pasa a {RANGO_OFICIAL}."
            )
            # El nuevo Líder puede cumplir ya "es_lider_gremio AND
            # miembros_gremio>=N" si el gremio ya tenía suficientes
            # miembros en el momento de la transferencia.
            from features.achievements.commands import comprobar_y_notificar
            comprobar_y_notificar(objetivo)
        else:
            caller.msg(f"{objetivo.key} ya es Líder.")
            return

        guild.notificar_miembros(f"|y[Gremio]|n {msg}")
        caller.msg(msg)


# --------------------------------------------------------------------------- #
#  degradar
# --------------------------------------------------------------------------- #

class CmdDegrading(Command):
    """
    Degradar a un Oficial a Miembro.

    Uso:
      degradar <jugador>

    Solo el Líder puede degradar Oficiales.
    """
    key = "degradar"
    aliases = ["demote"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        if guild.get_rango(caller) != RANGO_LIDER:
            caller.msg("Solo el Líder puede degradar miembros.")
            return

        nombre_obj = self.args.strip()
        if not nombre_obj:
            caller.msg("Uso: |wdegradar <jugador>|n")
            return

        objetivo, rango_obj = _buscar_miembro(guild, nombre_obj)
        if not objetivo:
            caller.msg(f"No hay ningún miembro llamado '|w{nombre_obj}|n' en el gremio.")
            return

        if rango_obj != RANGO_OFICIAL:
            caller.msg(f"|w{objetivo.key}|n no es Oficial.")
            return

        guild.cambiar_rango(objetivo, RANGO_MIEMBRO)
        msg = f"|y{objetivo.key}|n ha sido degradado a {RANGO_MIEMBRO}."
        guild.notificar_miembros(f"|y[Gremio]|n {msg}")
        caller.msg(msg)


# --------------------------------------------------------------------------- #
#  gbanco
# --------------------------------------------------------------------------- #

class CmdBancoGremio(Command):
    """
    Gestionar el banco del gremio.

    Uso:
      gbanco                    — ver saldo
      gbanco depositar <n>      — depositar monedas (cualquier miembro)
      gbanco retirar <n>        — retirar monedas (Líder u Oficial)
    """
    key = "gbanco"
    aliases = ["banco gremio", "guild bank"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        rango = guild.get_rango(caller)
        args = self.args.strip().lower()

        if not args:
            banco = guild.db.banco or 0
            caller.msg(
                f"|y[{guild.db.nombre}]|n Banco del gremio: |Y{banco} monedas|n.\n"
                f"  |wgbanco depositar <n>|n  — depositar\n"
                + (f"  |wgbanco retirar <n>|n   — retirar\n" if puede_retirar_banco(rango) else "")
            )
            return

        if args.startswith("depositar "):
            try:
                cantidad = int(args.split()[1])
            except (IndexError, ValueError):
                caller.msg("Uso: |wgbanco depositar <cantidad>|n")
                return
            if cantidad <= 0:
                caller.msg("La cantidad debe ser positiva.")
                return
            if guild.depositar(caller, cantidad):
                caller.db.gremio_banco_depositado = (
                    getattr(caller.db, "gremio_banco_depositado", 0) or 0
                ) + cantidad
                caller.msg(f"Has depositado |Y{cantidad} monedas|n en el banco del gremio.")
                guild.notificar_miembros(
                    f"|y[Gremio]|n {caller.key} ha depositado {cantidad} monedas.",
                    excluir=caller,
                )
                from features.achievements.commands import comprobar_y_notificar
                comprobar_y_notificar(caller)
            else:
                caller.msg(
                    f"No tienes suficientes monedas "
                    f"(tienes {getattr(caller.db, 'monedas', 0) or 0})."
                )
            return

        if args.startswith("retirar "):
            if not puede_retirar_banco(rango):
                caller.msg("Necesitas ser al menos Oficial para retirar del banco.")
                return
            try:
                cantidad = int(args.split()[1])
            except (IndexError, ValueError):
                caller.msg("Uso: |wgbanco retirar <cantidad>|n")
                return
            if cantidad <= 0:
                caller.msg("La cantidad debe ser positiva.")
                return
            if guild.retirar(caller, cantidad):
                caller.msg(f"Has retirado |Y{cantidad} monedas|n del banco del gremio.")
                guild.notificar_miembros(
                    f"|y[Gremio]|n {caller.key} ha retirado {cantidad} monedas.",
                    excluir=caller,
                )
            else:
                caller.msg(
                    f"El banco no tiene suficientes monedas "
                    f"(disponible: {guild.db.banco or 0})."
                )
            return

        caller.msg("Uso: |wgbanco [depositar <n> | retirar <n>]|n")


# --------------------------------------------------------------------------- #
#  disolver gremio
# --------------------------------------------------------------------------- #

class CmdDisolver(Command):
    """
    Disolver permanentemente el gremio.

    Uso:
      disolver gremio

    Solo el Líder puede disolver el gremio.
    Las monedas del banco se devuelven al Líder.
    Esta acción es irreversible.
    """
    key = "disolver gremio"
    aliases = ["disband guild"]
    locks = "cmd:all()"
    help_category = "Gremios"

    def func(self):
        caller = self.caller

        guild = obtener_gremio_de(caller)
        if not guild:
            caller.msg("No perteneces a ningún gremio.")
            return

        if guild.get_rango(caller) != RANGO_LIDER:
            caller.msg("Solo el Líder puede disolver el gremio.")
            return

        nombre_guild = guild.db.nombre
        guild.notificar_miembros(
            f"|r[Gremio]|n El gremio |w{nombre_guild}|n ha sido disuelto por {caller.key}.",
            excluir=caller,
        )
        guild.disolver(devolver_banco_a=caller)
        caller.msg(
            f"|rEl gremio |w{nombre_guild}|r ha sido disuelto.|n\n"
            f"Las monedas del banco han sido devueltas."
        )


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class GuildCmdSet(CmdSet):
    key = "GuildCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdCrearGremio())
        self.add(CmdGremio())
        self.add(CmdInvitar())
        self.add(CmdAceptarGremio())
        self.add(CmdRechazarGremio())
        self.add(CmdSalirGremio())
        self.add(CmdExpulsar())
        self.add(CmdPromover())
        self.add(CmdDegrading())
        self.add(CmdBancoGremio())
        self.add(CmdDisolver())
