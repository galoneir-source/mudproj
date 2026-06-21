"""
systems/guilds/guilds.py

Lógica pura del sistema de gremios de jugadores.
Sin dependencias de Evennia.
"""
import re

RANGOS = ("Miembro", "Oficial", "Líder")
RANGO_LIDER   = "Líder"
RANGO_OFICIAL = "Oficial"
RANGO_MIEMBRO = "Miembro"

MAX_MIEMBROS       = 20
COSTE_CREAR_GREMIO = 500   # monedas
INVITACION_TIMEOUT = 120   # segundos para aceptar la invitación

_MIN_NOMBRE = 3
_MAX_NOMBRE = 24
_RE_NOMBRE  = re.compile(r"^[\w\s'\-áéíóúüñÁÉÍÓÚÜÑ]+$")


def validar_nombre_gremio(nombre: str) -> tuple:
    """
    Valida el nombre de un gremio.
    Devuelve (True, "") o (False, motivo).
    """
    nombre = nombre.strip()
    if len(nombre) < _MIN_NOMBRE:
        return False, f"El nombre debe tener al menos {_MIN_NOMBRE} caracteres."
    if len(nombre) > _MAX_NOMBRE:
        return False, f"El nombre no puede superar {_MAX_NOMBRE} caracteres."
    if not _RE_NOMBRE.match(nombre):
        return False, "El nombre contiene caracteres no permitidos."
    return True, ""


def puede_invitar(rango: str) -> bool:
    """Líderes y Oficiales pueden invitar nuevos miembros."""
    return rango in (RANGO_LIDER, RANGO_OFICIAL)


def puede_expulsar(rango_expulsor: str, rango_expulsado: str) -> bool:
    """
    Determina si rango_expulsor puede expulsar a rango_expulsado.
    El Líder puede expulsar a Oficiales y Miembros.
    El Oficial solo puede expulsar a Miembros.
    """
    if rango_expulsor == RANGO_LIDER:
        return rango_expulsado in (RANGO_OFICIAL, RANGO_MIEMBRO)
    if rango_expulsor == RANGO_OFICIAL:
        return rango_expulsado == RANGO_MIEMBRO
    return False


def puede_retirar_banco(rango: str) -> bool:
    """Líderes y Oficiales pueden retirar del banco del gremio."""
    return rango in (RANGO_LIDER, RANGO_OFICIAL)


def indice_rango(rango: str) -> int:
    """Valor numérico del rango: Miembro=0, Oficial=1, Líder=2. -1 si desconocido."""
    try:
        return RANGOS.index(rango)
    except ValueError:
        return -1


def normalizar_nombre(nombre: str) -> str:
    """Convierte el nombre de gremio en clave de script (minúsculas, guiones bajos)."""
    return nombre.strip().lower().replace(" ", "_")


def simbolo_rango(rango: str) -> str:
    """Retorna el símbolo de color para mostrar junto al rango."""
    return {
        RANGO_LIDER:   "|Y♦|n",
        RANGO_OFICIAL: "|y★|n",
        RANGO_MIEMBRO: "|x·|n",
    }.get(rango, "·")
