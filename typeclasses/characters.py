"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent

from commands.builder_cmdsets import BuilderCmdSet
from systems.combat.engine import STAT_DEFAULTS
from systems.skills.trees import HABILIDADES_INICIALES


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    def at_object_creation(self):
        super().at_object_creation()
        # --- Inicializar stats de combate ---
        for key, val in STAT_DEFAULTS.items():
            if getattr(self.db, key, None) is None:
                setattr(self.db, key, val)
        self.db.habilidades_desbloqueadas = list(HABILIDADES_INICIALES)
        # --- Equipamiento ---
        self.db.equipamiento = {"arma": None, "armadura": None, "accesorio": None}
        # --- Economía ---
        self.db.monedas = 20
        # --- Estados de combate ---
        self.db.estados = {}
        # --- Misiones ---
        self.db.quests = {}
        # --- Grupo (party) ---
        self.db.lider_partido = None
        self.db.miembros_partido = []
        self.db.invitacion_partido = None
        # --- Reputación ---
        self.db.reputacion = {}
        # --- Banco ---
        self.db.banco = []
        self.db.banco_usado = False
        # --- Clase y subclase de personaje ---
        self.db.clase = None
        self.db.subclase = None
        # --- Logros y títulos ---
        self.db.logros = []
        self.db.titulo_activo = None
        self.db.kills_totales = 0
        self.db.jefes_derrotados = []
        self.db.objetos_crafteados = 0
        self.db.encantamiento_max = 0
        self.db.mascota_nivel_max = 1
        # --- Gremio ---
        self.db.gremios_fundados = 0
        self.db.gremio_banco_depositado = 0
        # --- Buffs temporales ---
        self.db.buffs_activos = []
        # --- Rango de aventurero ---
        self.db.rango = "aprendiz"
        # --- Profesiones de recolección ---
        self.db.profesiones = {}
        # --- Mazmorras instanciadas ---
        self.db.mazmorras_completadas = {}
        self.db.mazmorra_legendario = False
        # --- Jefes de Mundo ---
        self.db.jefes_mundo_derrotados = {}
        # --- Runas de equipamiento ---
        self.db.runas_equipadas = {"arma": None, "armadura": None, "accesorio": None}
        # --- Arena y torneos ---
        self.db.torneos_ganados = 0
        # --- Correo ---
        self.db.correo = []
        # --- Vivienda ---
        self.db.vivienda_dbref    = None
        self.db.vivienda_decorada = False
        # --- Bestiario ---
        self.db.bestiary = {}

    def at_post_puppet(self, **kwargs):
        """Llamado cuando una cuenta puppetea este personaje (login incluido)."""
        super().at_post_puppet(**kwargs)
        try:
            from systems.mail.mail import contar_no_leidas, formatear_notificacion
            bandeja = list(self.db.correo or [])
            no_leidas = contar_no_leidas(bandeja)
            if no_leidas > 0:
                self.msg(formatear_notificacion(no_leidas))
        except Exception:
            pass

    def at_cmdset_get(self, **kwargs):
        """
        Se ejecuta cuando Evennia calcula qué cmdsets tiene el objeto.
        """
        super().at_cmdset_get(**kwargs)

        acct = getattr(self, "account", None)  # Account que lo está puppetando (si lo hay)
        if acct and acct.check_permstring("Builder"):
            # No persistente: si pierde permisos o cambia account, no se queda pegado
            self.cmdset.add(BuilderCmdSet, persistent=False)
