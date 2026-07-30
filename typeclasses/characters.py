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
        # --- Cartografía ---
        self.db.salas_exploradas = []
        # --- Monturas ---
        self.db.monturas = []
        self.db.montura_activa = None
        # --- Coleccionables ---
        self.db.tesoros_encontrados = []
        # --- Apuestas ---
        self.db.apuestas_jugadas  = 0
        self.db.apuestas_ganadas  = 0
        self.db.mayor_ganancia    = 0
        # --- Cazarrecompensas ---
        self.db.recompensas_cobradas  = 0
        self.db.recompensas_recibidas = 0
        # --- Expediciones ---
        self.db.expediciones_completadas = 0
        self.db.fortaleza_completada     = False
        # --- Alquimia ---
        self.db.pociones_elaboradas = 0
        self.db.rango_alquimia      = "aprendiz"
        # --- Desafíos Diarios ---
        self.db.fecha_desafios              = None
        self.db.progreso_desafios           = [0, 0, 0, 0, 0]
        self.db.desafios_completados_hoy    = []
        self.db.racha_desafios              = 0
        self.db.ultimo_dia_desafios         = None
        self.db.total_desafios_completados  = 0
        # --- Amigos ---
        self.db.amigos = []

    def _notificar_amigos(self, mensaje: str):
        """Avisa a los jugadores conectados que te tienen en su lista de amigos."""
        try:
            import evennia
            for session in evennia.SESSION_HANDLER.get_sessions():
                puppet = session.get_puppet()
                if not puppet or puppet == self:
                    continue
                amigos = getattr(puppet.db, "amigos", None) or []
                if self.dbref in amigos:
                    puppet.msg(mensaje)
        except Exception:
            pass

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
        self._notificar_amigos(f"|g{self.key} se ha conectado.|n")

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        """Llamado cuando una cuenta deja de controlar este personaje (logout incluido)."""
        super().at_post_unpuppet(account=account, session=session, **kwargs)
        if self.sessions.count() == 0:
            self._notificar_amigos(f"|y{self.key} se ha desconectado.|n")

    def at_cmdset_get(self, **kwargs):
        """
        Se ejecuta cuando Evennia calcula qué cmdsets tiene el objeto.
        """
        super().at_cmdset_get(**kwargs)

        acct = getattr(self, "account", None)  # Account que lo está puppetando (si lo hay)
        if acct and acct.check_permstring("Builder"):
            # No persistente: si pierde permisos o cambia account, no se queda pegado
            self.cmdset.add(BuilderCmdSet, persistent=False)
