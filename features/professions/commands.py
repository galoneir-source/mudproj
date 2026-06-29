"""
features/professions/commands.py

Comandos del sistema de profesiones de recolección.

  profesion / prof             — muestra tus profesiones y niveles
  profesion aprender <id>      — aprende una nueva profesión
  profesion info <id>          — detalle de una profesión (materiales por nivel)
  recolectar / minar / cosechar / pescar
                               — recoge un material en la sala actual
"""
from __future__ import annotations

import time

from evennia import CmdSet
from evennia.prototypes import spawner

from commands.command import Command
from systems.professions.professions import (
    PROFESIONES,
    COOLDOWN_SEGUNDOS,
    NOMBRES_NIVEL,
    aprender_profesion,
    elegir_material,
    formatear_todas,
    ganar_xp,
    lista_disponibles,
    xp_para_siguiente,
    zona_a_profesion,
)


class CmdProfesion(Command):
    """
    Muestra o gestiona tus profesiones de recolección.

    Uso:
      profesion                  — lista tus profesiones activas
      profesion aprender <id>    — aprende una profesión nueva
      profesion info <id>        — muestra los materiales que obtendrás

    Profesiones disponibles: mineria, herboristeria, pesca
    """

    key = "profesion"
    aliases = ["profesiones", "prof"]
    locks = "cmd:all()"

    def func(self):
        char = self.caller
        args = self.args.strip().lower()

        if not args:
            self._mostrar(char)
            return

        if args.startswith("aprender "):
            self._aprender(char, args[9:].strip())
            return

        if args.startswith("info "):
            self._info(char, args[5:].strip())
            return

        # Intento de "profesion <id>" sin subcomando → mostrar info
        self._info(char, args)

    def _mostrar(self, char):
        profesiones = char.db.profesiones or {}
        char.msg("|wTus profesiones:|n")
        char.msg(formatear_todas(profesiones))
        char.msg(f"\n|xDisponibles: {lista_disponibles()}|n")
        char.msg("|xUsa |wprofesion aprender <nombre>|x para aprender una nueva.|n")

    def _aprender(self, char, prof_id):
        if not char.db.profesiones:
            char.db.profesiones = {}
        profesiones = dict(char.db.profesiones)
        ok, msg = aprender_profesion(profesiones, prof_id)
        if not ok:
            char.msg(f"|r{msg}|n")
            return
        char.db.profesiones = profesiones
        nombre = PROFESIONES[prof_id]["nombre"]
        desc = PROFESIONES[prof_id]["descripcion"]
        char.msg(
            f"|gAprendes la profesión de |c{nombre}|g.|n\n"
            f"|x{desc}|n\n"
            f"|xBusca zonas de recolección y usa |wrecolectar|x para practicar.|n"
        )

    def _info(self, char, prof_id):
        if prof_id not in PROFESIONES:
            char.msg(
                f"|rProfesión desconocida: '{prof_id}'.|n "
                f"Disponibles: {lista_disponibles()}"
            )
            return
        datos = PROFESIONES[prof_id]
        char.msg(f"|c{datos['nombre']}|n — {datos['descripcion']}")
        char.msg("|wMateriales por nivel:|n")
        for nv in range(1, 6):
            opciones = datos["materiales"].get(nv, [])
            nombres = [o[0].lower().replace("_", " ") for o in opciones]
            char.msg(f"  Nv.|w{nv}|n ({NOMBRES_NIVEL[nv]}): {', '.join(nombres)}")


class CmdRecolectar(Command):
    """
    Recolecta materiales en la zona actual.

    Uso:
      recolectar     — recoge lo que haya disponible en esta sala
      minar          — alias para zonas de minería
      cosechar       — alias para zonas de herboristería
      pescar         — alias para zonas de pesca

    Requiere conocer la profesión correspondiente a la zona.
    Hay un cooldown de 60 s entre recolecciones.
    """

    key = "recolectar"
    aliases = ["minar", "cosechar", "pescar"]
    locks = "cmd:all()"

    def func(self):
        char = self.caller
        room = char.location
        if not room:
            return

        zona_id = getattr(room.db, "zona", None)
        prof_id, nivel_min = zona_a_profesion(zona_id or "")

        if not prof_id:
            char.msg("No hay recursos que recolectar aquí.")
            return

        profesiones = char.db.profesiones or {}

        if prof_id not in profesiones:
            nombre = PROFESIONES[prof_id]["nombre"]
            char.msg(
                f"Esta zona requiere la profesión de |c{nombre}|n. "
                f"Usa |wprofesion aprender {prof_id}|n para aprenderla."
            )
            return

        nivel_char = profesiones[prof_id].get("nivel", 1)
        if nivel_char < nivel_min:
            nombre = PROFESIONES[prof_id]["nombre"]
            char.msg(
                f"Necesitas nivel |w{nivel_min}|n en {nombre} para recolectar aquí "
                f"(tienes nivel |w{nivel_char}|n)."
            )
            return

        # Cooldown
        cooldowns = char.ndb.cooldown_recolectar or {}
        ahora = time.time()
        ultimo = cooldowns.get(prof_id, 0)
        if ahora - ultimo < COOLDOWN_SEGUNDOS:
            restante = int(COOLDOWN_SEGUNDOS - (ahora - ultimo))
            char.msg(f"Debes esperar |w{restante}s|n antes de volver a recolectar.")
            return

        # Elegir material
        proto_key, xp_ganada = elegir_material(prof_id, nivel_char)
        if not proto_key:
            char.msg("No encuentras nada útil que recolectar.")
            return

        # Crear el objeto
        objs = spawner.spawn(proto_key)
        if not objs:
            char.msg("|rError al crear el objeto. Avisa a un administrador.|n")
            return
        obj = objs[0]
        obj.location = char

        # Actualizar cooldown
        cooldowns[prof_id] = ahora
        char.ndb.cooldown_recolectar = cooldowns

        # Dar XP y comprobar subida de nivel
        prof_datos = dict(profesiones)
        nivel_nuevo, subio = ganar_xp(prof_datos, prof_id, xp_ganada)
        char.db.profesiones = prof_datos

        nombre_prof = PROFESIONES[prof_id]["nombre"]
        char.msg(
            f"|g{nombre_prof}:|n Obtienes |w{obj.name}|n. "
            f"(+|w{xp_ganada}|n XP de profesión)"
        )

        if subio:
            nv_nombre = NOMBRES_NIVEL[nivel_nuevo]
            char.msg(
                f"|Y¡Tu {nombre_prof} sube al nivel {nivel_nuevo} ({nv_nombre})!|n"
            )
            xp_sig = xp_para_siguiente(nivel_nuevo)
            if xp_sig:
                char.msg(
                    f"|xPróximo nivel: |w{xp_sig}|x XP totales.|n"
                )


class ProfessionCmdSet(CmdSet):
    key = "ProfessionCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdProfesion())
        self.add(CmdRecolectar())
