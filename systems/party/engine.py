"""
systems/party/engine.py

Lógica pura del sistema de grupos. Sin dependencias de Evennia.
Trabaja con primitivos; la integración con objetos Evennia es responsabilidad
de features/party/commands.py.
"""
from __future__ import annotations

MAX_MIEMBROS: int = 4


def xp_por_miembro(xp_total: int, num_miembros: int) -> int:
    """
    Calcula el XP que recibe cada miembro del grupo.
    Bonus de grupo: +20% del total, luego dividido entre miembros.
    Con 1 (o menos) miembro devuelve xp_total sin modificar.
    """
    if num_miembros <= 1:
        return xp_total
    return max(1, int(xp_total * 1.20) // num_miembros)


def puede_invitar_validar(
    invitante_en_partido: bool,
    invitante_es_lider: bool,
    objetivo_en_partido: bool,
    misma_sala: bool,
    objetivo_tiene_invitacion_pendiente: bool = False,
) -> tuple[bool, str]:
    """
    Valida las condiciones para enviar una invitación de grupo.
    Devuelve (ok, motivo_si_no).
    """
    if not misma_sala:
        return False, "El jugador no está en la misma sala."
    if objetivo_en_partido:
        return False, "El jugador ya pertenece a un grupo."
    # objetivo.db.invitacion_partido es un slot único: una segunda
    # invitación de otro líder lo sobrescribiría en silencio sin avisar
    # nunca al primer invitante, que se quedaría esperando una invitación
    # que ya no existe.
    if objetivo_tiene_invitacion_pendiente:
        return False, "El jugador ya tiene una invitación de grupo pendiente."
    if invitante_en_partido and not invitante_es_lider:
        return False, "Solo el líder puede invitar a nuevos miembros."
    return True, ""
