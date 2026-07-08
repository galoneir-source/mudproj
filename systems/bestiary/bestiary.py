"""
systems/bestiary/bestiary.py

Lógica pura del bestiario. Sin dependencias de Evennia.

El bestiario registra cada criatura que el jugador ha derrotado al menos
una vez. Para cada entrada se guarda el número de bajas y la fecha del
primer encuentro (unix timestamp).

db.bestiary en Character:
  {prototype_key: {"kills": int, "primera_vez": int}}
"""
from __future__ import annotations
import time

# --------------------------------------------------------------------------- #
#  Catálogo de criaturas conocidas
# --------------------------------------------------------------------------- #

TIPOS: dict[str, str] = {
    "bestia":    "Bestias",
    "humanoide": "Humanoides",
    "no_muerto": "No-Muertos",
    "constructo": "Constructos",
    "oscuro":    "Oscuros",
}

CATALOGO: dict[str, dict] = {

    # ── Bestias ───────────────────────────────────────────────────────────────
    "SERPIENTE_PANTANO": {
        "nombre":      "Serpiente del Pantano",
        "tipo":        "bestia",
        "zona":        "Pantano del Troll",
        "nivel":       2,
        "es_jefe":     False,
        "descripcion": (
            "Una serpiente venenosa de escamas negras y reflejos verdes. "
            "Acecha entre los juncos esperando a que su presa se acerque al agua."
        ),
    },
    "ARANA_CUEVA": {
        "nombre":      "Araña de Cueva",
        "tipo":        "bestia",
        "zona":        "Minas de Hierro Viejo",
        "nivel":       3,
        "es_jefe":     False,
        "descripcion": (
            "Una araña del tamaño de un perro con ocho ojos que brillan en la oscuridad. "
            "Tiende trampas de seda en los túneles antes de atacar."
        ),
    },
    "TROLL": {
        "nombre":      "Troll del Pantano",
        "tipo":        "bestia",
        "zona":        "Guarida del Troll",
        "nivel":       5,
        "es_jefe":     True,
        "descripcion": (
            "Un troll de tres metros de altura, piel verdosa y boca repleta de dientes. "
            "Su carne se regenera con rapidez asombrosa. Solo el fuego puede frenarle."
        ),
    },
    "DRAGON_CENIZA": {
        "nombre":      "Dragón de Ceniza",
        "tipo":        "bestia",
        "zona":        "Claro del Bosque",
        "nivel":       10,
        "es_jefe":     True,
        "descripcion": (
            "Un dragón colosal de escamas grises como la ceniza. "
            "Su aliento convierte todo en polvo. Aparece en el mundo solo cuando el mal lo convoca."
        ),
    },

    # ── Humanoides ────────────────────────────────────────────────────────────
    "GOBLIN": {
        "nombre":      "Goblin",
        "tipo":        "humanoide",
        "zona":        "Bosque del Norte",
        "nivel":       1,
        "es_jefe":     False,
        "descripcion": (
            "Un goblin de piel verdosa, orejas puntiagudas y ojos amarillos. "
            "Cobarde en solitario, peligroso en manada."
        ),
    },
    "GOBLIN_JEFE": {
        "nombre":      "Jefe Goblin",
        "tipo":        "humanoide",
        "zona":        "Claro del Bosque",
        "nivel":       3,
        "es_jefe":     True,
        "descripcion": (
            "El mayor y más brutal de los goblins del bosque. "
            "Porta una armadura improvisada con piezas robadas y dirige a su tribu con puño de hierro."
        ),
    },
    "BANDIDO": {
        "nombre":      "Bandido",
        "tipo":        "humanoide",
        "zona":        "Calabozo",
        "nivel":       2,
        "es_jefe":     False,
        "descripcion": (
            "Un delincuente de mirada fría y cicatrices en el rostro. "
            "Trabaja para el Capitán y no tiene escrúpulos."
        ),
    },
    "BANDIDO_CAPITAN": {
        "nombre":      "Capitán Bandido",
        "tipo":        "humanoide",
        "zona":        "Celda Abandonada",
        "nivel":       4,
        "es_jefe":     True,
        "descripcion": (
            "El jefe de los bandidos del calabozo, veterano de cien asaltos. "
            "Lucha con una mezcla de fuerza bruta y astucia sucia."
        ),
    },
    "HOMBRE_LAGARTO": {
        "nombre":      "Hombre Lagarto",
        "tipo":        "humanoide",
        "zona":        "Pantano Cenagoso",
        "nivel":       3,
        "es_jefe":     False,
        "descripcion": (
            "Una criatura bípeda de escamas verdosas y larga cola. "
            "Los hombres lagarto son tribales y protegen ferozmente su territorio en el pantano."
        ),
    },
    "APRENDIZ_CORRUPTO": {
        "nombre":      "Aprendiz Corrompido",
        "tipo":        "humanoide",
        "zona":        "Torre del Mago Caído",
        "nivel":       5,
        "es_jefe":     False,
        "descripcion": (
            "Un joven mago que siguió a Vexthar en su investigación prohibida. "
            "La magia oscura lo ha deformado: sus ojos brillan con un fulgor violeta."
        ),
    },
    "MINERO_MALDITO": {
        "nombre":      "Minero Maldito",
        "tipo":        "humanoide",
        "zona":        "Minas de Hierro Viejo",
        "nivel":       4,
        "es_jefe":     False,
        "descripcion": (
            "Un antiguo minero atrapado en la mina cuando el gólem despertó. "
            "La magia de la forja lo ha transformado en algo a medio camino entre vivo y muerto."
        ),
    },

    # ── No-Muertos ────────────────────────────────────────────────────────────
    "ESQUELETO": {
        "nombre":      "Esqueleto",
        "tipo":        "no_muerto",
        "zona":        "Catacumbas",
        "nivel":       3,
        "es_jefe":     False,
        "descripcion": (
            "Un esqueleto animado por magia oscura. "
            "Sin voluntad propia, obedece ciegamente a quien lo invocó."
        ),
    },
    "LICHE_MENOR": {
        "nombre":      "Liche Menor",
        "tipo":        "no_muerto",
        "zona":        "Catacumbas",
        "nivel":       5,
        "es_jefe":     False,
        "descripcion": (
            "Un mago que buscó la inmortalidad a través de la necromancia. "
            "Solo alcanzó un estado de semi-muerte que lo ata a estas catacumbas."
        ),
    },
    "ESPECTRO": {
        "nombre":      "Espectro",
        "tipo":        "no_muerto",
        "zona":        "Ruinas del Templo",
        "nivel":       4,
        "es_jefe":     False,
        "descripcion": (
            "El alma en pena de un clérigo que murió protegiendo el templo. "
            "Su toque drena la vitalidad de los vivos."
        ),
    },
    "CABALLERO_MUERTE": {
        "nombre":      "Caballero de la Muerte",
        "tipo":        "no_muerto",
        "zona":        "Ciudadela Oscura",
        "nivel":       8,
        "es_jefe":     False,
        "descripcion": (
            "Un antiguo paladín caído que el Liche transformó en su guardia personal. "
            "Combate con disciplina y sin rastro de la compasión que una vez tuvo."
        ),
    },
    "LICHE_INMORTAL": {
        "nombre":      "Liche Inmortal",
        "tipo":        "no_muerto",
        "zona":        "Altar del Liche",
        "nivel":       10,
        "es_jefe":     True,
        "descripcion": (
            "El Rey Morthis, corrompido hace cuatro siglos por el deseo de inmortalidad. "
            "Mientras su filoacteria exista, no puede morir de verdad."
        ),
    },
    "SENOR_CENIZAS": {
        "nombre":      "Señor de las Cenizas",
        "tipo":        "no_muerto",
        "zona":        "Cripta de Ceniza",
        "nivel":       5,
        "es_jefe":     True,
        "descripcion": (
            "El antiguo guardián de la cripta, reducido a cenizas y reconstituido "
            "por una maldición que no encuentra descanso."
        ),
    },

    # ── Constructos ───────────────────────────────────────────────────────────
    "GOLEM_PIEDRA": {
        "nombre":      "Gólem de Piedra",
        "tipo":        "constructo",
        "zona":        "Minas de Hierro Viejo",
        "nivel":       7,
        "es_jefe":     True,
        "descripcion": (
            "Un gólem invocado hace siglos para custodiar las minas. "
            "Su creador murió y la orden de detenerse nunca llegó."
        ),
    },
    "GUARDIAN_ARCANO": {
        "nombre":      "Guardián Arcano",
        "tipo":        "constructo",
        "zona":        "Torre del Mago Caído",
        "nivel":       6,
        "es_jefe":     False,
        "descripcion": (
            "Un constructo mágico que Vexthar creó para proteger la base de su torre. "
            "Sigue cumpliendo su función aunque su creador haya caído."
        ),
    },
    "TITAN_PANTANO": {
        "nombre":      "Titán del Pantano",
        "tipo":        "constructo",
        "zona":        "Pantano Cenagoso",
        "nivel":       8,
        "es_jefe":     True,
        "descripcion": (
            "Un constructo elemental de lodo y piedra que emergió del corazón del pantano. "
            "Aparece en el mundo solo cuando el equilibrio se rompe."
        ),
    },
    "GUARDIAN_FORJA": {
        "nombre":      "Guardián de la Forja",
        "tipo":        "constructo",
        "zona":        "Caverna del Coloso",
        "nivel":       9,
        "es_jefe":     True,
        "descripcion": (
            "Un gólem de metal fundido construido por los enanos para custodiar "
            "los secretos de la gran forja. Su calor es insoportable."
        ),
    },
    "MAESTRO_FORJADOR": {
        "nombre":      "Maestro Forjador",
        "tipo":        "constructo",
        "zona":        "Forja Maldita",
        "nivel":       7,
        "es_jefe":     True,
        "descripcion": (
            "El espíritu de un maestro herrero que quedó atrapado en su propia forja "
            "cuando una maldición la consumió. Ahora es metal y fuego."
        ),
    },

    # ── Oscuros ───────────────────────────────────────────────────────────────
    "CABALLERO_OSCURO": {
        "nombre":      "Caballero Oscuro",
        "tipo":        "oscuro",
        "zona":        "Ruinas del Templo",
        "nivel":       6,
        "es_jefe":     True,
        "descripcion": (
            "Un caballero que vendió su alma a las fuerzas de la oscuridad. "
            "Su armadura absorbe la luz y irradia un frío sobrenatural."
        ),
    },
    "HECHICERO_SOMBRIO": {
        "nombre":      "Hechicero Sombrío",
        "tipo":        "oscuro",
        "zona":        "Ciudadela Oscura",
        "nivel":       9,
        "es_jefe":     False,
        "descripcion": (
            "Un mago de la Legión Oscura especializado en magia de sombras. "
            "Sus hechizos canalizan directamente la energía del vacío."
        ),
    },
    "ARCHIMAGO_VEXTHAR": {
        "nombre":      "Archimago Vexthar",
        "tipo":        "oscuro",
        "zona":        "Cámara del Ritual",
        "nivel":       9,
        "es_jefe":     True,
        "descripcion": (
            "El archimago del Gremio Arcano, atrapado en su propia jaula arcana hace décadas. "
            "Su poder es inmenso pero su mente lleva años al borde de la locura."
        ),
    },
    "SENOR_ABISMO": {
        "nombre":      "Señor del Abismo",
        "tipo":        "oscuro",
        "zona":        "Abismo Sin Fondo",
        "nivel":       9,
        "es_jefe":     True,
        "descripcion": (
            "Una entidad que surgió del abismo cuando alguien abrió un portal "
            "demasiado profundo. No tiene nombre propio; el abismo lo define."
        ),
    },
}

_TOTAL_CATALOGO = len(CATALOGO)


# --------------------------------------------------------------------------- #
#  Lógica pura
# --------------------------------------------------------------------------- #

def registrar_kill(bestiary: dict, proto_key: str) -> dict:
    """
    Registra una baja en el bestiario. Devuelve el dict actualizado.
    Solo registra criaturas presentes en CATALOGO.
    """
    if proto_key not in CATALOGO:
        return bestiary
    bestiary = dict(bestiary)
    entrada = dict(bestiary.get(proto_key, {}))
    entrada["kills"] = entrada.get("kills", 0) + 1
    if "primera_vez" not in entrada:
        entrada["primera_vez"] = int(time.time())
    bestiary[proto_key] = entrada
    return bestiary


def criaturas_registradas(bestiary: dict) -> int:
    """Número de criaturas distintas con al menos 1 baja."""
    return sum(1 for k in bestiary if k in CATALOGO)


def bestiary_completo(bestiary: dict) -> bool:
    """True si todas las criaturas del catálogo han sido derrotadas al menos una vez."""
    return all(k in bestiary and bestiary[k].get("kills", 0) > 0 for k in CATALOGO)


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

def _tiempo_transcurrido(ts: int) -> str:
    delta = int(time.time()) - ts
    if delta < 120:
        return "hace un momento"
    if delta < 3600:
        return f"hace {delta // 60} min"
    if delta < 86400:
        return f"hace {delta // 3600}h"
    dias = delta // 86400
    return f"hace {dias} día{'s' if dias != 1 else ''}"


def formatear_lista(bestiary: dict) -> str:
    registradas = criaturas_registradas(bestiary)
    sep = "|w" + "─" * 54 + "|n"
    lineas = [
        f"\n{sep}",
        f"  |cBestiario|n  —  |w{registradas}/{_TOTAL_CATALOGO}|n criaturas registradas",
        sep,
    ]

    for tipo_id, tipo_nombre in TIPOS.items():
        entradas_tipo = [
            (k, v) for k, v in CATALOGO.items() if v["tipo"] == tipo_id
        ]
        if not entradas_tipo:
            continue
        lineas.append(f"\n  |y[{tipo_nombre}]|n")
        for proto, info in sorted(entradas_tipo, key=lambda x: x[1]["nivel"]):
            datos = bestiary.get(proto, {})
            kills = datos.get("kills", 0)
            nombre = info["nombre"]
            jefe_tag = " |r[Jefe]|n" if info.get("es_jefe") else ""
            if kills:
                ts = datos.get("primera_vez", 0)
                cuando = f"  |x{_tiempo_transcurrido(ts)}|n" if ts else ""
                lineas.append(
                    f"    |g✔|n |w{nombre}|n{jefe_tag}"
                    f"  |x·|n  {kills} baja{'s' if kills != 1 else ''}{cuando}"
                )
            else:
                lineas.append(f"    |x✗ {nombre}|n{jefe_tag}")

    lineas.append(f"\n  Usa |wbestiario <nombre>|n para ver el detalle de una criatura.")
    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def formatear_entrada(proto_key: str, bestiary: dict) -> str:
    info = CATALOGO.get(proto_key)
    if not info:
        return "|rCriatura no encontrada en el catálogo.|n"

    datos = bestiary.get(proto_key, {})
    kills = datos.get("kills", 0)
    sep = "|w" + "─" * 54 + "|n"
    tipo_nombre = TIPOS.get(info["tipo"], info["tipo"].capitalize())
    jefe_tag = "  |r[Jefe]|n" if info.get("es_jefe") else ""

    lineas = [
        f"\n{sep}",
        f"  |c{info['nombre']}|n{jefe_tag}",
        sep,
        f"  Tipo  : |w{tipo_nombre}|n",
        f"  Zona  : |w{info['zona']}|n",
        f"  Nivel : |w{info['nivel']}|n",
        f"",
        f"  {info['descripcion']}",
        f"",
    ]

    if kills:
        ts = datos.get("primera_vez", 0)
        cuando = f" ({_tiempo_transcurrido(ts)})" if ts else ""
        baja_txt = f"{kills} baja{'s' if kills != 1 else ''}"
        lineas.append(f"  Bajas registradas : |g{baja_txt}|n{cuando}")
    else:
        lineas.append("  |xAún no has derrotado a esta criatura.|n")

    lineas.append(f"{sep}\n")
    return "\n".join(lineas)


def buscar_en_catalogo(nombre: str) -> list[str]:
    """
    Devuelve los prototype_keys cuyo nombre de catálogo contiene el texto dado
    (insensible a mayúsculas). Útil para el comando de búsqueda.
    """
    nombre_lower = nombre.lower()
    return [
        k for k, v in CATALOGO.items()
        if nombre_lower in v["nombre"].lower()
    ]
