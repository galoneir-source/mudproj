"""
features/contracts/contract_script.py

Script global del tablón de contratos (v0.27.0).
Se renueva automáticamente cada hora, sincronizado con la hora del sistema.
Todos los jugadores ven el mismo tablón para la hora actual.
"""
from evennia import DefaultScript
from evennia.utils import create


class ContractScript(DefaultScript):

    def at_script_creation(self):
        self.key = "tablón_contratos"
        self.desc = "Tablón de contratos global"
        self.persistent = True
        self.interval = 3600
        self.db.contratos = []
        self.db.ultima_seed = -1

    def at_start(self):
        self.renovar()

    def at_repeat(self):
        self.renovar()

    def renovar(self):
        from systems.contracts.contracts import generar_tablón, seed_hora_actual
        seed = seed_hora_actual()
        if seed == (self.db.ultima_seed or -1):
            return
        self.db.contratos = generar_tablón(seed)
        self.db.ultima_seed = seed

    def obtener_contratos(self) -> list:
        """Devuelve la lista actual de contratos, renovando si es necesario."""
        self.renovar()
        return [dict(c) for c in (self.db.contratos or [])]

    def obtener_contrato(self, numero: int) -> dict | None:
        """Devuelve el contrato por número (1-based). None si fuera de rango."""
        contratos = self.obtener_contratos()
        if 1 <= numero <= len(contratos):
            return contratos[numero - 1]
        return None


def obtener_tablón_script() -> ContractScript:
    """Devuelve el script del tablón global, creándolo si no existe."""
    from evennia.scripts.models import ScriptDB
    qs = ScriptDB.objects.filter(db_key="tablón_contratos")
    if qs.exists():
        return qs.first()
    return create.create_script(ContractScript, key="tablón_contratos",
                                persistent=True)
