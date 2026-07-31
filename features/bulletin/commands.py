"""
features/bulletin/commands.py

Comando de la cartelera de anuncios global:
  cartelera                    — ver los anuncios vigentes
  cartelera publicar <texto>   — publicar un anuncio
  cartelera retirar <#>        — retirar tu propio anuncio
"""
from evennia import Command, CmdSet

from systems.bulletin.bulletin import formatear_cartelera


class CmdCartelera(Command):
    """
    Cartelera de anuncios de la ciudad: publica avisos cortos que
    cualquier jugador puede leer (ventas, mensajes de gremio, avisos
    generales). Distinta del tablón de contratos ('tablón').

    Uso:
      cartelera                    - ver los anuncios vigentes
      cartelera publicar <texto>   - publicar un anuncio
      cartelera retirar <#>        - retirar tu propio anuncio

    Los anuncios expiran a los 3 días. Solo el autor puede retirar el suyo.
    """
    key = "cartelera"
    aliases = ["mural"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from features.bulletin.bulletin_script import obtener_cartelera_script
        caller = self.caller
        script = obtener_cartelera_script()
        args = self.args.strip()

        if not args:
            self._listar(caller, script)
            return

        args_lower = args.lower()

        if args_lower.startswith("publicar "):
            texto = args[len("publicar "):].strip()
            self._publicar(caller, script, texto)
            return

        if args_lower.startswith("retirar "):
            idx = args[len("retirar "):].strip()
            self._retirar(caller, script, idx)
            return

        caller.msg(
            "Uso: |wcartelera|n · |wcartelera publicar <texto>|n · "
            "|wcartelera retirar <#>|n"
        )

    # ------------------------------------------------------------------ #
    #  Subcomandos
    # ------------------------------------------------------------------ #

    def _listar(self, caller, script):
        anuncios = script.obtener_anuncios()
        caller.msg(formatear_cartelera(anuncios))

    def _publicar(self, caller, script, texto):
        if not texto:
            caller.msg("Uso: |wcartelera publicar <texto>|n")
            return
        ok, msg = script.publicar(caller, texto)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg("|gTu anuncio ha sido publicado en la cartelera.|n")

    def _retirar(self, caller, script, idx_str):
        anuncios = sorted(
            script.obtener_anuncios(), key=lambda a: -a.get("timestamp", 0)
        )
        if not idx_str.isdigit() or not (1 <= int(idx_str) <= len(anuncios)):
            caller.msg(f"|rUso: cartelera retirar <número entre 1 y {len(anuncios)}>|n")
            return

        anuncio = anuncios[int(idx_str) - 1]
        ok, msg = script.retirar(anuncio["id"], caller)
        if not ok:
            caller.msg(f"|r{msg}|n")
            return
        caller.msg("|gAnuncio retirado.|n")


class BulletinCmdSet(CmdSet):
    key = "BulletinCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdCartelera())
