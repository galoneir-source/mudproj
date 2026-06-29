"""
systems/trade/trade.py

Lógica pura del sistema de intercambio entre jugadores. Sin dependencias de Evennia.

Un intercambio tiene dos lados (A y B). Cada lado tiene:
  - objetos ofrecidos (lista de descripciones / IDs)
  - monedas ofrecidas (int)
  - confirmado (bool)

El intercambio se puede ejecutar cuando ambos lados han confirmado.
Cualquier modificación posterior a la confirmación desconfirma a ambas partes.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Estado puro de un lado del intercambio
# --------------------------------------------------------------------------- #

def nuevo_lado() -> dict:
    return {"objetos": [], "monedas": 0, "confirmado": False}


def agregar_objeto(lado: dict, obj_id: str, obj_nombre: str) -> tuple[bool, str]:
    """
    Registra un objeto en la oferta. obj_id es el dbref del objeto.
    Devuelve (ok, mensaje_error).
    """
    if obj_id in [e["id"] for e in lado["objetos"]]:
        return False, f"Ya estás ofreciendo '{obj_nombre}'."
    lado["objetos"].append({"id": obj_id, "nombre": obj_nombre})
    lado["confirmado"] = False
    return True, ""


def retirar_objeto(lado: dict, obj_id: str) -> tuple[bool, str]:
    """Elimina un objeto de la oferta. Devuelve (ok, mensaje_error)."""
    antes = len(lado["objetos"])
    lado["objetos"] = [e for e in lado["objetos"] if e["id"] != obj_id]
    if len(lado["objetos"]) == antes:
        return False, "Ese objeto no estaba en tu oferta."
    lado["confirmado"] = False
    return True, ""


def establecer_monedas(lado: dict, cantidad: int) -> tuple[bool, str]:
    """Establece las monedas ofrecidas. Desconfirma."""
    if cantidad < 0:
        return False, "No puedes ofrecer una cantidad negativa de monedas."
    lado["monedas"] = cantidad
    lado["confirmado"] = False
    return True, ""


def confirmar(lado: dict) -> None:
    lado["confirmado"] = True


def desconfirmar_ambos(lado_a: dict, lado_b: dict) -> None:
    lado_a["confirmado"] = False
    lado_b["confirmado"] = False


def ambos_confirmados(lado_a: dict, lado_b: dict) -> bool:
    return lado_a["confirmado"] and lado_b["confirmado"]


def tiene_oferta(lado: dict) -> bool:
    return bool(lado["objetos"]) or lado["monedas"] > 0


# --------------------------------------------------------------------------- #
#  Validación previa al intercambio (dicts puros)
# --------------------------------------------------------------------------- #

def validar_monedas(lado: dict, monedas_disponibles: int) -> tuple[bool, str]:
    """Verifica que el jugador tiene las monedas que ofrece."""
    if lado["monedas"] > monedas_disponibles:
        return False, (
            f"Ofreces |w{lado['monedas']}|n monedas pero solo tienes "
            f"|w{monedas_disponibles}|n."
        )
    return True, ""


# --------------------------------------------------------------------------- #
#  Formateo de la ventana de intercambio
# --------------------------------------------------------------------------- #

def formatear_intercambio(nombre_a: str, lado_a: dict, nombre_b: str, lado_b: dict) -> str:
    def _lado(nombre, lado):
        lineas = [f"|w{nombre}|n:"]
        if lado["objetos"]:
            for e in lado["objetos"]:
                lineas.append(f"  · {e['nombre']}")
        else:
            lineas.append("  |x(ningún objeto)|n")
        if lado["monedas"] > 0:
            lineas.append(f"  · |y{lado['monedas']} monedas|n")
        estado = "|g✓ Confirmado|n" if lado["confirmado"] else "|xEsperando...|n"
        lineas.append(f"  {estado}")
        return "\n".join(lineas)

    separador = "|x" + "─" * 38 + "|n"
    return (
        f"\n|cIntercambio en curso|n\n"
        f"{separador}\n"
        f"{_lado(nombre_a, lado_a)}\n"
        f"{separador}\n"
        f"{_lado(nombre_b, lado_b)}\n"
        f"{separador}\n"
        f"|xUsa |wofrecer <objeto|monedas>|x, |wconfirmar|x o |wcancelar|x.|n"
    )


def formatear_oferta_simple(lado: dict) -> str:
    """Texto compacto para notificar al otro jugador de cambios en la oferta."""
    partes = [e["nombre"] for e in lado["objetos"]]
    if lado["monedas"] > 0:
        partes.append(f"{lado['monedas']} monedas")
    return ", ".join(partes) if partes else "(nada)"
