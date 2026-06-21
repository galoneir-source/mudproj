"""
features/pets/commands.py

Comandos del sistema de mascotas de combate.
"""
from evennia import Command, CmdSet


class CmdCapturar(Command):
    """
    Intentar capturar a un enemigo debilitado en combate.

    Uso:
      capturar

    Funciona durante tu turno de combate cuando el enemigo tiene
    el 20% o menos de HP. Solo puedes tener una mascota a la vez.

    La mascota capturada te acompañará en futuros combates y atacará
    automáticamente a tus enemigos. Cuida bien el vínculo para que
    sea más poderosa.
    """
    key = "capturar"
    aliases = ["capture"]
    locks = "cmd:all()"
    help_category = "Mascotas"

    def func(self):
        from features.combat.commands import _get_combat_handler
        caller = self.caller

        if caller.db.mascota:
            caller.msg(
                "Ya tienes una mascota. "
                "Usa |wmascota liberar|n si quieres capturar otra."
            )
            return

        if not getattr(caller.db, "en_combate", False):
            caller.msg("Solo puedes capturar durante el combate.")
            return

        handler = _get_combat_handler(caller.location)
        if not handler:
            caller.msg("No hay ningún combate activo aquí.")
            return

        handler.registrar_accion(caller, "capturar")


class CmdMascota(Command):
    """
    Gestionar tu mascota de combate.

    Uso:
      mascota                     - ver estadísticas de tu mascota
      mascota liberar             - liberar a tu mascota
      mascota alimentar           - alimentar (+vínculo, cuesta 10 monedas)
      mascota nombre <nuevo>      - cambiarle el nombre

    La mascota ataca automáticamente en combate. El vínculo mejora
    su daño: 50% del ataque base con vínculo 0, hasta 100% con vínculo 100.
    Ganas +5 de vínculo por cada enemigo derrotado con ella presente.

    Ejemplos:
      mascota
      mascota alimentar
      mascota nombre Fang
    """
    key = "mascota"
    aliases = ["pet", "familiar"]
    locks = "cmd:all()"
    help_category = "Mascotas"

    def func(self):
        from systems.pets.pets import (
            formatear_mascota, calcular_nuevo_vinculo,
            COSTE_ALIMENTAR, VINCULO_SUBE_ALIMENTAR,
        )
        caller = self.caller
        args = self.args.strip()
        args_lower = args.lower()

        mascota = dict(getattr(caller.db, "mascota", None) or {})

        if not args:
            if not mascota:
                caller.msg(
                    "No tienes ninguna mascota. "
                    "Debilita a un enemigo hasta el 20% de HP "
                    "y usa |wcapturar|n durante tu turno."
                )
                return
            caller.msg(formatear_mascota(mascota))
            return

        if args_lower == "liberar":
            if not mascota:
                caller.msg("No tienes ninguna mascota.")
                return
            nombre = mascota.get("nombre", "tu mascota")
            caller.db.mascota = None
            caller.msg(f"Has liberado a |y{nombre}|n. Que sea feliz.")
            return

        if args_lower == "alimentar":
            if not mascota:
                caller.msg("No tienes ninguna mascota.")
                return
            monedas = int(getattr(caller.db, "monedas", 0) or 0)
            if monedas < COSTE_ALIMENTAR:
                caller.msg(
                    f"Necesitas |y{COSTE_ALIMENTAR}|n monedas para alimentar a tu mascota "
                    f"(tienes {monedas})."
                )
                return
            caller.db.monedas = monedas - COSTE_ALIMENTAR
            nuevo_vinculo = calcular_nuevo_vinculo(
                mascota.get("vinculo", 0), VINCULO_SUBE_ALIMENTAR
            )
            mascota["vinculo"] = nuevo_vinculo
            caller.db.mascota = mascota
            nombre = mascota.get("nombre", "tu mascota")
            caller.msg(
                f"Alimentas a |y{nombre}|n. "
                f"Vínculo: |w{nuevo_vinculo}/100|n."
            )
            return

        if args_lower.startswith("nombre "):
            if not mascota:
                caller.msg("No tienes ninguna mascota.")
                return
            nuevo_nombre = args[len("nombre "):].strip()
            if not nuevo_nombre or len(nuevo_nombre) > 24:
                caller.msg("El nombre debe tener entre 1 y 24 caracteres.")
                return
            nombre_anterior = mascota.get("nombre", "tu mascota")
            mascota["nombre"] = nuevo_nombre
            caller.db.mascota = mascota
            caller.msg(f"Tu mascota ahora se llama |y{nuevo_nombre}|n (antes: {nombre_anterior}).")
            return

        caller.msg(
            "Uso: |wmascota|n · |wmascota liberar|n · "
            "|wmascota alimentar|n · |wmascota nombre <nuevo>|n"
        )


# --------------------------------------------------------------------------- #
#  CmdSet
# --------------------------------------------------------------------------- #

class PetsCmdSet(CmdSet):
    key = "PetsCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdCapturar())
        self.add(CmdMascota())
