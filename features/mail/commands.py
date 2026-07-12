"""
features/mail/commands.py

Comandos del sistema de correo entre jugadores.

  carta <jugador> = <mensaje>
  carta <jugador> adjuntar <objeto> = <mensaje>
  carta <jugador> monedas <N> = <mensaje>
  carta <jugador> adjuntar <objeto> monedas <N> = <mensaje>

  correo                    — lista el buzón
  correo leer <N>           — lee la carta N
  correo reclamar <N>       — recoge el adjunto de la carta N
  correo borrar <N>         — borra la carta (devuelve adjunto si no reclamado)
  correo responder <N> = <texto>  — responde a la carta N
"""

import re
from evennia import Command, CmdSet
from evennia import search_object

from systems.mail.mail import (
    MAX_CARTAS,
    nueva_carta,
    puede_recibir,
    formatear_bandeja,
    formatear_carta,
    formatear_notificacion,
    contar_no_leidas,
    adjunto_pendiente,
    tiene_adjunto,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _buscar_destinatario(nombre: str):
    """Busca un Character por nombre (en línea o en DB). Devuelve (char, error)."""
    from evennia import search_object
    resultados = search_object(nombre, typeclass="typeclasses.characters.Character")
    if not resultados:
        return None, f"|rNo se encontró ningún jugador con el nombre '{nombre}'.|n"
    if len(resultados) > 1:
        nombres = ", ".join(r.key for r in resultados)
        return None, f"|rNombre ambiguo: {nombres}. Sé más específico.|n"
    return resultados[0], ""


def _buscar_obj_inv(caller, nombre: str):
    """Busca objeto en el inventario del remitente."""
    candidatos = [
        obj for obj in caller.contents
        if nombre.lower() in obj.key.lower()
    ]
    if not candidatos:
        return None, f"|rNo tienes ningún objeto con el nombre '{nombre}'.|n"
    if len(candidatos) > 1:
        return None, f"|rNombre ambiguo. Sé más específico.|n"
    return candidatos[0], ""


def _bandeja(char) -> list:
    if char.db.correo is None:
        char.db.correo = []
    return list(char.db.correo or [])


def _guardar_bandeja(char, bandeja: list):
    char.db.correo = bandeja


def _devolver_adjunto(carta: dict):
    """Devuelve objetos y monedas al remitente si no fueron reclamados."""
    if not adjunto_pendiente(carta):
        return
    remitente_dbref = carta.get("remitente_dbref")
    if not remitente_dbref:
        return
    remitente_list = search_object(remitente_dbref)
    if not remitente_list:
        return
    remitente = remitente_list[0]

    # Devolver monedas
    monedas = carta.get("monedas", 0)
    if monedas > 0:
        remitente.db.monedas = (remitente.db.monedas or 0) + monedas
        if remitente.has_account:
            remitente.msg(
                f"|yTe han devuelto {monedas} monedas de una carta borrada sin reclamar.|n"
            )

    # Devolver objetos (están en location=None, los recuperamos por dbref)
    for entrada in carta.get("objetos", []):
        obj_list = search_object(entrada["dbref"])
        if obj_list:
            obj = obj_list[0]
            obj.location = remitente
            if remitente.has_account:
                remitente.msg(
                    f"|yTe han devuelto |w{obj.key}|y de una carta borrada sin reclamar.|n"
                )


# --------------------------------------------------------------------------- #
#  CmdCarta — enviar
# --------------------------------------------------------------------------- #

class CmdCarta(Command):
    """
    Envía una carta a otro jugador, opcionalmente con objetos o monedas adjuntos.

    Uso:
      carta <jugador> = <mensaje>
      carta <jugador> adjuntar <objeto> = <mensaje>
      carta <jugador> monedas <N> = <mensaje>
      carta <jugador> adjuntar <objeto> monedas <N> = <mensaje>

    Ejemplos:
      carta Gandalf = Hola, ¿cómo estás?
      carta Gandalf adjuntar espada de hierro = Toma, esto es tuyo.
      carta Gandalf monedas 50 = Aquí tienes lo que te debía.
      carta Gandalf adjuntar daga monedas 20 = Oferta especial.
    """

    key = "carta"
    aliases = ["mail send", "enviar carta"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        raw = self.args.strip()

        if "=" not in raw:
            caller.msg("|rUso: carta <jugador> [adjuntar <objeto>] [monedas <N>] = <mensaje>|n")
            return

        cabecera, mensaje = raw.split("=", 1)
        mensaje = mensaje.strip()
        if not mensaje:
            caller.msg("|rEl mensaje no puede estar vacío.|n")
            return

        # Parsear cabecera: "<jugador> [adjuntar <obj>] [monedas <N>]"
        cabecera = cabecera.strip()

        # Extraer monedas
        monedas = 0
        m_monedas = re.search(r'\bmonedas\s+(\d+)\b', cabecera, re.IGNORECASE)
        if m_monedas:
            monedas = int(m_monedas.group(1))
            cabecera = cabecera[:m_monedas.start()] + cabecera[m_monedas.end():]
            cabecera = cabecera.strip()

        # Extraer adjuntar
        obj_adjunto = None
        m_adj = re.search(r'\badjuntar\s+(.+)', cabecera, re.IGNORECASE)
        if m_adj:
            nombre_obj = m_adj.group(1).strip()
            cabecera = cabecera[:m_adj.start()].strip()
            obj_adjunto, err = _buscar_obj_inv(caller, nombre_obj)
            if not obj_adjunto:
                caller.msg(err)
                return

        nombre_dest = cabecera.strip()
        if not nombre_dest:
            caller.msg("|rDebes especificar el destinatario.|n")
            return

        # Buscar destinatario
        dest, err = _buscar_destinatario(nombre_dest)
        if not dest:
            caller.msg(err)
            return
        if dest == caller:
            caller.msg("|rNo puedes enviarte cartas a ti mismo.|n")
            return

        # Validar buzón lleno
        bandeja = _bandeja(dest)
        ok, err = puede_recibir(bandeja)
        if not ok:
            caller.msg(f"|r{err}|n")
            return

        # Validar monedas
        if monedas > 0:
            if (caller.db.monedas or 0) < monedas:
                caller.msg(
                    f"|rNo tienes suficientes monedas. "
                    f"Tienes {caller.db.monedas or 0}, intentas enviar {monedas}.|n"
                )
                return

        # Validar objeto equipado
        if obj_adjunto:
            equipamiento = dict(caller.db.equipamiento or {})
            if obj_adjunto in equipamiento.values():
                caller.msg(f"|rDesequipa |w{obj_adjunto.key}|r antes de adjuntarlo.|n")
                return

        # Construir carta
        objetos_carta = []
        if obj_adjunto:
            objetos_carta.append({"dbref": obj_adjunto.dbref, "nombre": obj_adjunto.key})

        carta = nueva_carta(
            remitente=caller.key,
            remitente_dbref=caller.dbref,
            mensaje=mensaje,
            monedas=monedas,
            objetos=objetos_carta,
        )

        # Ejecutar transferencias
        if monedas > 0:
            caller.db.monedas = (caller.db.monedas or 0) - monedas

        if obj_adjunto:
            obj_adjunto.location = None   # "en tránsito"

        # Guardar carta en el buzón del destinatario
        bandeja.append(carta)
        _guardar_bandeja(dest, bandeja)

        # Notificar
        adj_txt = ""
        partes = []
        if obj_adjunto:
            partes.append(f"|w{obj_adjunto.key}|n")
        if monedas > 0:
            partes.append(f"|y{monedas} monedas|n")
        if partes:
            adj_txt = f" (adjunto: {', '.join(partes)})"

        caller.msg(f"|gCarta enviada a |w{dest.key}|g.{adj_txt}|n")

        if dest.has_account:
            no_leidas = contar_no_leidas(_bandeja(dest))
            dest.msg(f"\n|Y● Has recibido una carta de |w{caller.key}|Y.|n Usa |wcorreo|n para leerla.")


# --------------------------------------------------------------------------- #
#  CmdCorreo — gestionar buzón
# --------------------------------------------------------------------------- #

class CmdCorreo(Command):
    """
    Gestiona tu buzón de correo.

    Uso:
      correo                      - Lista todas las cartas
      correo leer <N>             - Lee la carta número N
      correo reclamar <N>         - Recoge el adjunto de la carta N
      correo borrar <N>           - Borra la carta N (devuelve adjunto si no reclamado)
      correo responder <N> = <texto>  - Responde a la carta N
    """

    key = "correo"
    aliases = ["buzón", "inbox", "bandeja"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip().split(None, 1)
        sub = args[0].lower() if args else ""
        resto = args[1].strip() if len(args) > 1 else ""

        bandeja = _bandeja(caller)

        # Sin subcomando: listar
        if not sub or sub == "lista":
            caller.msg(formatear_bandeja(bandeja))
            return

        # --- leer ---
        if sub == "leer":
            carta, idx = self._get_carta(caller, bandeja, resto)
            if carta is None:
                return
            carta["leida"] = True
            bandeja[idx - 1] = carta
            _guardar_bandeja(caller, bandeja)
            caller.msg(formatear_carta(carta, idx))
            return

        # --- reclamar ---
        if sub == "reclamar":
            carta, idx = self._get_carta(caller, bandeja, resto)
            if carta is None:
                return
            if not tiene_adjunto(carta):
                caller.msg("|xEsta carta no tiene adjunto.|n")
                return
            if carta.get("reclamado"):
                caller.msg("|xEl adjunto de esta carta ya fue reclamado.|n")
                return
            self._reclamar(caller, carta)
            carta["reclamado"] = True
            carta["leida"] = True
            bandeja[idx - 1] = carta
            _guardar_bandeja(caller, bandeja)
            return

        # --- borrar ---
        if sub in ("borrar", "eliminar", "delete"):
            carta, idx = self._get_carta(caller, bandeja, resto)
            if carta is None:
                return
            _devolver_adjunto(carta)
            bandeja.pop(idx - 1)
            _guardar_bandeja(caller, bandeja)
            caller.msg(f"|gCarta {idx} eliminada.|n")
            return

        # --- responder ---
        if sub == "responder":
            if "=" not in resto:
                caller.msg("|rUso: correo responder <N> = <mensaje>|n")
                return
            num_txt, mensaje = resto.split("=", 1)
            carta, idx = self._get_carta(caller, bandeja, num_txt.strip())
            if carta is None:
                return
            remitente_dbref = carta.get("remitente_dbref")
            if not remitente_dbref:
                caller.msg("|rNo se puede responder a esta carta (remitente desconocido).|n")
                return
            dest_list = search_object(remitente_dbref)
            if not dest_list:
                caller.msg("|rEl remitente original ya no existe en el juego.|n")
                return
            dest = dest_list[0]
            # Reusar CmdCarta lógica manualmente
            bandeja_dest = _bandeja(dest)
            ok, err = puede_recibir(bandeja_dest)
            if not ok:
                caller.msg(f"|r{err}|n")
                return
            respuesta = nueva_carta(
                remitente=caller.key,
                remitente_dbref=caller.dbref,
                mensaje=f"[Respuesta a tu carta]\n{mensaje.strip()}",
            )
            bandeja_dest.append(respuesta)
            _guardar_bandeja(dest, bandeja_dest)
            caller.msg(f"|gRespuesta enviada a |w{dest.key}|g.|n")
            if dest.has_account:
                dest.msg(f"|Y● Has recibido una respuesta de |w{caller.key}|Y.|n Usa |wcorreo|n para leerla.")
            return

        caller.msg(
            "|rSubcomando desconocido. Usa: |wcorreo|r, |wcorreo leer <N>|r, "
            "|wcorreo reclamar <N>|r, |wcorreo borrar <N>|r, |wcorreo responder <N> = <texto>|r.|n"
        )

    # ---------------------------------------------------------------------- #

    def _get_carta(self, caller, bandeja, num_txt: str):
        """Devuelve (carta_dict, idx_1based) o (None, None) con mensaje de error."""
        try:
            idx = int(num_txt.strip())
        except (ValueError, AttributeError):
            caller.msg("|rEscribe el número de la carta. Ejemplo: correo leer 3|n")
            return None, None
        if idx < 1 or idx > len(bandeja):
            caller.msg(f"|rNo existe carta número {idx}. Tienes {len(bandeja)} carta(s).|n")
            return None, None
        return bandeja[idx - 1], idx

    def _reclamar(self, caller, carta: dict):
        """Mueve adjuntos al inventario del jugador."""
        monedas = carta.get("monedas", 0)
        if monedas > 0:
            caller.db.monedas = (caller.db.monedas or 0) + monedas
            caller.msg(f"|g+{monedas} monedas recibidas.|n")

        for entrada in carta.get("objetos", []):
            obj_list = search_object(entrada["dbref"])
            if obj_list:
                obj = obj_list[0]
                obj.location = caller
                caller.msg(f"|gRecibiste: |w{obj.key}|n")
            else:
                caller.msg(f"|x(El objeto '{entrada['nombre']}' ya no existe.)|n")


# --------------------------------------------------------------------------- #
#  MailCmdSet
# --------------------------------------------------------------------------- #

class MailCmdSet(CmdSet):
    key = "MailCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdCarta)
        self.add(CmdCorreo)
