"""
systems/housing/housing.py

Lógica pura del sistema de vivienda. Sin dependencias de Evennia.

Una vivienda es una sala privada, permanente, comprada por el jugador.
El jugador puede decorarla, gestionar quién tiene acceso y teletransportarse
a ella en cualquier momento.
"""
from __future__ import annotations

PRECIO_VIVIENDA = 500   # monedas, compra única (sin alquiler periódico)
MAX_INVITADOS   = 10
MAX_DESC_LEN    = 500


# --------------------------------------------------------------------------- #
#  Validaciones
# --------------------------------------------------------------------------- #

def puede_comprar(monedas: int, ya_tiene: bool) -> tuple[bool, str]:
    if ya_tiene:
        return False, "Ya tienes una vivienda. Usa |wvivienda|n para verla."
    if monedas < PRECIO_VIVIENDA:
        return False, (
            f"Necesitas |w{PRECIO_VIVIENDA} monedas|n para comprar una vivienda. "
            f"Tienes {monedas}."
        )
    return True, ""


def puede_invitar(invitados: list, nuevo_dbref: str) -> tuple[bool, str]:
    if nuevo_dbref in invitados:
        return False, "Ese jugador ya tiene acceso a tu vivienda."
    if len(invitados) >= MAX_INVITADOS:
        return False, f"No puedes dar acceso a más de {MAX_INVITADOS} personas."
    return True, ""


def puede_quitar_acceso(invitados: list, dbref: str) -> tuple[bool, str]:
    if dbref not in invitados:
        return False, "Ese jugador no tiene acceso a tu vivienda."
    return True, ""


def puede_entrar(propietario_dbref: str, invitados: list, visitante_dbref: str) -> bool:
    return visitante_dbref == propietario_dbref or visitante_dbref in invitados


def validar_descripcion(texto: str) -> tuple[bool, str]:
    texto = texto.strip()
    if not texto:
        return False, "La descripción no puede estar vacía."
    if len(texto) > MAX_DESC_LEN:
        return False, f"La descripción no puede superar {MAX_DESC_LEN} caracteres (tienes {len(texto)})."
    return True, texto


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def formatear_estado(
    propietario_nombre: str,
    invitados_nombres: list[str],
    desc: str | None,
    sala_nombre: str,
) -> str:
    sep = "|w" + "─" * 50 + "|n"
    lineas = [f"\n{sep}", f"  |cVivienda: {sala_nombre}|n", sep]
    lineas.append(f"  Propietario : |w{propietario_nombre}|n")
    if desc:
        lineas.append(f"  Descripción : {desc}")
    else:
        lineas.append("  Descripción : |x(sin decorar — usa |wdecorar <texto>|x)|n")
    if invitados_nombres:
        lineas.append(f"  Acceso      : |w{', '.join(invitados_nombres)}|n")
    else:
        lineas.append("  Acceso      : |xnadie invitado|n")
    lineas.append("")
    lineas.append("  Comandos: |wcasa|n (ir a tu vivienda)  |wdecorar <texto>|n")
    lineas.append("            |wvivienda acceso dar <jugador>|n")
    lineas.append("            |wvivienda acceso quitar <jugador>|n")
    lineas.append("            |wvivienda abandonar|n (devuelve la vivienda)")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_sin_vivienda() -> str:
    sep = "|w" + "─" * 50 + "|n"
    return (
        f"\n{sep}\n"
        f"  |cVivienda personal|n\n"
        f"{sep}\n"
        f"  No tienes vivienda. Puedes comprar una en el |wBarrio Residencial|n.\n"
        f"  Coste: |w{PRECIO_VIVIENDA} monedas|n (pago único).\n"
        f"  Usa |wvivienda comprar|n desde el Barrio Residencial.\n"
        f"{sep}\n"
    )
