"""
systems/quests/quests.py

Definición de misiones y lógica pura de validación (sin Evennia).
"""
from __future__ import annotations
from typing import Optional


# --------------------------------------------------------------------------- #
#  Definición de misiones
# --------------------------------------------------------------------------- #

QUESTS: dict[str, dict] = {
    "problema_goblins": {
        "titulo": "El Problema de los Goblins",
        "descripcion": (
            "Los goblins del bosque norte atacan a los viajeros sin descanso. "
            "La guardia necesita que alguien los reduzca."
        ),
        "tipo": "kill",
        "objetivo": {"target": "goblin", "cantidad": 3},
        "dador": "guardia de la ciudad",
        "receptor": "guardia de la ciudad",
        "recompensa": {"xp": 150, "monedas": 25},
        "rep_reward": {"ciudadanos": 250, "horda_salvaje": -150},
        "texto_oferta": (
            "Los goblins del bosque norte son un problema serio. "
            "¿Podrías encargarte de 3 de ellos? Te recompensaremos bien."
        ),
        "texto_progreso": "Llevas {actual} de {total} goblins eliminados. Sigue así.",
        "texto_entrega": "Excelente trabajo, aventurero. La ciudad te lo agradece.",
        "nivel_minimo": 1,
    },
    "mercancia_robada": {
        "titulo": "La Mercancía Robada",
        "descripcion": (
            "Los bandidos del calabozo robaron mercancía valiosa a Mira. "
            "Su capitán debe pagar por ello."
        ),
        "tipo": "kill",
        "objetivo": {"target": "capitán bandido", "cantidad": 1},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 300, "monedas": 60, "prototipo": "ANILLO_DESTREZA"},
        "rep_reward": {"ciudadanos": 300, "horda_salvaje": -200},
        "texto_oferta": (
            "Esos bandidos del calabozo robaron mi mejor mercancía. "
            "Su capitán es el responsable. ¿Le darías una lección?"
        ),
        "texto_progreso": "El capitán aún sigue en el calabozo. Acaba con él.",
        "texto_entrega": "¡Lo lograste! Toma este anillo como recompensa adicional.",
        "nivel_minimo": 3,
    },
    "veneno_del_pantano": {
        "titulo": "Veneno del Pantano",
        "descripcion": (
            "Mira la mercader necesita veneno de pantano para sus preparados alquímicos. "
            "Las serpientes del pantano lo producen."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "veneno de pantano", "cantidad": 2},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 100, "monedas": 30},
        "rep_reward": {"ciudadanos": 150, "gremio_aventureros": 100},
        "texto_oferta": (
            "¿Puedes traerme 2 frascos de veneno de pantano? "
            "Los necesito para mis preparados alquímicos."
        ),
        "texto_progreso": "Aún necesito {faltante} frasco(s) de veneno de pantano.",
        "texto_entrega": "Perfecto, justo lo que necesitaba. Muchas gracias.",
        "nivel_minimo": 2,
    },
    "garra_del_troll": {
        "titulo": "La Garra del Troll",
        "descripcion": (
            "Un alquimista amigo del mesonero paga bien por garras de troll. "
            "Solo los más valientes se atreven a ir al pantano."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "garra de troll", "cantidad": 1},
        "dador": "Gareth el mesonero",
        "receptor": "Gareth el mesonero",
        "recompensa": {"xp": 200, "monedas": 40},
        "rep_reward": {"ciudadanos": 200, "gremio_aventureros": 150, "sombras_pantano": -100},
        "texto_oferta": (
            "Un alquimista amigo paga bien por garras de troll. "
            "Si consigues una, te doy una buena parte del dinero."
        ),
        "texto_progreso": "Mi amigo aún espera esa garra de troll.",
        "texto_entrega": "¡Magnífico! Esto le encantará a mi amigo el alquimista.",
        "nivel_minimo": 5,
    },
    "templo_corrompido": {
        "titulo": "El Templo Corrompido",
        "descripcion": (
            "Las ruinas del antiguo templo al norte del bosque han sido tomadas por espectros. "
            "El Hermano Aldric necesita que alguien purifique el lugar eliminando a esos seres."
        ),
        "tipo": "kill",
        "objetivo": {"target": "espectro", "cantidad": 4},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 200, "monedas": 40},
        "rep_reward": {"ciudadanos": 200, "legion_oscura": -150},
        "texto_oferta": (
            "Los espectros que habitan el templo son almas atrapadas y corrompidas. "
            "Eliminar cuatro de ellos debilitará su presencia. ¿Puedes hacerlo?"
        ),
        "texto_progreso": "Llevas {actual} de {total} espectros eliminados. Sigue adelante.",
        "texto_entrega": "Siento que el templo respira un poco mejor. Gracias, amigo.",
        "nivel_minimo": 3,
    },
    "la_cruz_perdida": {
        "titulo": "La Cruz Perdida",
        "descripcion": (
            "Un símbolo sagrado del templo fue arrebatado por los espectros. "
            "El Hermano Aldric lo necesita para el ritual de purificación."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "símbolo sagrado", "cantidad": 1},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 250, "monedas": 50},
        "rep_reward": {"ciudadanos": 250, "gremio_aventureros": 100},
        "texto_oferta": (
            "El símbolo sagrado del templo debe estar entre los espectros. "
            "Sin él no puedo completar el ritual. ¿Me lo traerías?"
        ),
        "texto_progreso": "El símbolo sagrado sigue perdido entre los espectros. Búscalo bien.",
        "texto_entrega": "¡Es él! Con esto podré iniciar el ritual. Tienes mi gratitud eterna.",
        "nivel_minimo": 3,
    },
    "caballero_sombras": {
        "titulo": "El Caballero de las Sombras",
        "descripcion": (
            "El Barón Morthis regresó como caballero oscuro y gobierna a los espectros desde la cripta. "
            "Debe ser derrotado de forma definitiva para liberar el templo."
        ),
        "tipo": "kill",
        "objetivo": {"target": "caballero oscuro", "cantidad": 1},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 600, "monedas": 120},
        "rep_reward": {"ciudadanos": 600, "gremio_aventureros": 300, "legion_oscura": -400},
        "texto_oferta": (
            "El Barón Morthis corrompió el templo hace siglos y ahora ha regresado. "
            "Si eres lo bastante valiente, baja a la cripta y acaba con él."
        ),
        "texto_progreso": "El Caballero Oscuro sigue en la cripta. Prepárate bien antes de enfrentarlo.",
        "texto_entrega": "Lo lograste. El alma del Barón puede descansar por fin. Eres un verdadero héroe.",
        "nivel_minimo": 6,
    },
    "cristales_sagrados": {
        "titulo": "Los Cristales del Ritual",
        "descripcion": (
            "El Hermano Aldric necesita cristales sagrados para el ritual de sellado del templo. "
            "Solo se encuentran en las ruinas, portados por los espectros."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "cristal sagrado", "cantidad": 2},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 180, "monedas": 35},
        "rep_reward": {"ciudadanos": 150, "gremio_aventureros": 100},
        "texto_oferta": (
            "Necesito dos cristales sagrados para completar el ritual. "
            "Los espectros los portan consigo. ¿Puedes traérmelos?"
        ),
        "texto_progreso": "Aún necesito {faltante} cristal(es) sagrado(s) más.",
        "texto_entrega": "Perfecto. Con estos cristales el ritual de sellado puede comenzar.",
        "nivel_minimo": 4,
    },
    "veta_perdida": {
        "titulo": "La Veta Perdida",
        "descripcion": (
            "Las Minas de Hierro Viejo, al oeste del bosque, llevan siglos clausuradas. "
            "Torben necesita muestras del mineral que se extrae allí para confirmar su calidad."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "mineral de hierro", "cantidad": 2},
        "dador": "Torben el buscador de tesoros",
        "receptor": "Torben el buscador de tesoros",
        "recompensa": {"xp": 200, "monedas": 45},
        "rep_reward": {"gremio_aventureros": 200, "ciudadanos": 100},
        "texto_oferta": (
            "Las minas al oeste del bosque tienen un mineral de hierro de calidad excepcional. "
            "¿Puedes traerme dos trozos para que los examine?"
        ),
        "texto_progreso": "Aún necesito {faltante} trozo(s) de mineral de hierro.",
        "texto_entrega": "¡Magnífico! Esto confirma lo que sospechaba. El mineral es de primera calidad.",
        "nivel_minimo": 3,
    },
    "coloso_despertado": {
        "titulo": "El Coloso Despertado",
        "descripcion": (
            "Un antiguo gólem de piedra guarda las profundidades de las Minas de Hierro Viejo. "
            "Torben ofrece una recompensa considerable a quien sea capaz de derrotarlo."
        ),
        "tipo": "kill",
        "objetivo": {"target": "gólem de piedra", "cantidad": 1},
        "dador": "Torben el buscador de tesoros",
        "receptor": "Torben el buscador de tesoros",
        "recompensa": {"xp": 550, "monedas": 110, "prototipo": "ANILLO_CONSTITUCION"},
        "rep_reward": {"gremio_aventureros": 500, "ciudadanos": 200},
        "texto_oferta": (
            "Hay un gólem de piedra en las profundidades de la mina. "
            "Es un guardián antiguo que no debería seguir activo. "
            "¿Te atreves a enfrentarlo? La recompensa merece el riesgo."
        ),
        "texto_progreso": "El gólem sigue activo en la caverna más profunda. Prepárate bien antes de ir.",
        "texto_entrega": "¡Lo has logrado! Ahora podemos explorar la mina en paz. Toma, esto es tuyo.",
        "nivel_minimo": 6,
    },
    "aprendices_torre": {
        "titulo": "Los Aprendices de la Torre",
        "descripcion": (
            "Los aprendices del archimago Vexthar se han corrompido y vagan peligrosamente "
            "por la torre al este del Claro del Bosque. "
            "El Hermano Aldric pide que se reduzca su número para debilitar a su maestro."
        ),
        "tipo": "kill",
        "objetivo": {"target": "aprendiz corrompido", "cantidad": 3},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 250, "monedas": 50},
        "rep_reward": {"ciudadanos": 250, "legion_oscura": -200},
        "texto_oferta": (
            "Los aprendices de Vexthar son almas perdidas y peligrosas. "
            "Eliminar tres de ellos debilitaría notablemente el poder del archimago. ¿Puedes hacerlo?"
        ),
        "texto_progreso": "Llevas {actual} de {total} aprendices eliminados. Sigue adelante.",
        "texto_entrega": "Bien hecho. La influencia de Vexthar se debilita. Que los dioses guíen tu camino.",
        "nivel_minimo": 4,
    },
    "archimago_caido": {
        "titulo": "El Archimago Caído",
        "descripcion": (
            "El archimago Vexthar lleva décadas atrapado en su torre, "
            "corrompido por la magia prohibida que intentó dominar. "
            "Mira la mercader ofrece una gran recompensa a quien lo detenga definitivamente."
        ),
        "tipo": "kill",
        "objetivo": {"target": "archimago vexthar", "cantidad": 1},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 700, "monedas": 150, "prototipo": "MANTO_ARCANO"},
        "rep_reward": {"ciudadanos": 600, "gremio_aventureros": 400, "legion_oscura": -500},
        "texto_oferta": (
            "Vexthar lleva demasiado tiempo siendo una amenaza. "
            "Si eres lo bastante poderoso para entrar en esa torre y acabar con él, "
            "te pagaré con lo mejor que tengo: su propio manto arcano."
        ),
        "texto_progreso": "El archimago Vexthar sigue en la cámara del ritual. Prepárate muy bien antes de subir.",
        "texto_entrega": "Lo has logrado. Vexthar puede descansar por fin. Toma el manto, te lo has ganado.",
        "nivel_minimo": 7,
    },
    "liche_inmortal": {
        "titulo": "El Liche Inmortal",
        "descripcion": (
            "El liche que gobierna la Ciudadela Oscura lleva siglos convocando no-muertos "
            "y amenazando con expandir su legión hacia las tierras habitadas. "
            "El Hermano Aldric pide a los más valientes que entren en la ciudadela y lo detengan."
        ),
        "tipo": "kill",
        "objetivo": {"target": "liche inmortal", "cantidad": 1},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 900, "monedas": 200},
        "rep_reward": {"ciudadanos": 800, "gremio_aventureros": 500, "legion_oscura": -600},
        "texto_oferta": (
            "La Ciudadela Oscura al norte del templo es el corazón de la Legión Oscura. "
            "Su liche lleva siglos construyendo ese ejército. "
            "Si eres lo bastante poderoso, tienes que detenerlo. Te lo pido en nombre de todos."
        ),
        "texto_progreso": "El liche inmortal sigue en su trono. Prepárate lo mejor que puedas antes de enfrentarlo.",
        "texto_entrega": "Lo hiciste. Llevas siglos de miedo encima y los has vencido. Que los dioses guíen tu descanso.",
        "nivel_minimo": 9,
    },
    "fragmentos_oscuridad": {
        "titulo": "Fragmentos de Oscuridad",
        "descripcion": (
            "Mira la mercader necesita fragmentos de alma oscura para estudiar la magia de no-muerte. "
            "Solo los caballeros de la muerte de la Ciudadela Oscura los portan."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "fragmento de alma oscura", "cantidad": 3},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 400, "monedas": 90},
        "rep_reward": {"gremio_aventureros": 300, "ciudadanos": 200},
        "texto_oferta": (
            "Los fragmentos de alma oscura son rarísimos. "
            "Solo los caballeros de la muerte de la Ciudadela los llevan consigo. "
            "¿Puedes traerme tres? Pagaré bien por ellos."
        ),
        "texto_progreso": "Aún necesito {faltante} fragmento(s) de alma oscura más.",
        "texto_entrega": "¡Impresionante! Con esto podré estudiar la necromancia de primera mano. Gracias.",
        "nivel_minimo": 7,
    },
    # ----------------------------------------------------------------- #
    #  Cadena 1: La Oscuridad se Extiende  (Aldric, empieza desde caballero_sombras)
    # ----------------------------------------------------------------- #
    "ecos_del_baron": {
        "titulo": "Los Ecos del Barón",
        "descripcion": (
            "El caballero oscuro que gobernaba el templo no era sino un reflejo de algo mayor: "
            "la Ciudadela Oscura al norte. "
            "Sus fragmentos de alma guardan el eco del camino hacia allí. "
            "El Hermano Aldric los necesita para rastrear el origen de la corrupción."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "fragmento de alma oscura", "cantidad": 2},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 350, "monedas": 70},
        "rep_reward": {"ciudadanos": 300, "gremio_aventureros": 150, "legion_oscura": -200},
        "texto_oferta": (
            "El barón no actuaba solo. Sus memorias residuales apuntan a la Ciudadela Oscura. "
            "Necesito fragmentos de alma oscura de sus nuevos siervos para rastrear la fuente. "
            "¿Puedes traerme dos?"
        ),
        "texto_progreso": "Aún necesito {faltante} fragmento(s) de alma oscura más.",
        "texto_entrega": "Esto es exactamente lo que necesitaba. Los ecos son clarísimos. La Ciudadela está detrás de todo.",
        "nivel_minimo": 6,
        "requiere": "caballero_sombras",
    },
    "legion_en_marcha": {
        "titulo": "La Legión en Marcha",
        "descripcion": (
            "Los ecos del barón revelan que la Ciudadela envía caballeros de la muerte "
            "como vanguardia para explorar y debilitar los asentamientos cercanos. "
            "El Hermano Aldric pide detener a tres de ellos antes de que avancen más."
        ),
        "tipo": "kill",
        "objetivo": {"target": "caballero de la muerte", "cantidad": 3},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 500, "monedas": 100},
        "rep_reward": {"ciudadanos": 450, "gremio_aventureros": 250, "legion_oscura": -350},
        "texto_oferta": (
            "Los ecos lo confirman: la Ciudadela lanza exploradores al mundo. "
            "Los caballeros de la muerte son su vanguardia. "
            "Detenlos antes de que abran el camino a algo peor. Necesito tres eliminados."
        ),
        "texto_progreso": "Llevas {actual} de {total} caballeros de la muerte eliminados. Continúa.",
        "texto_entrega": "Bien hecho. La presión sobre las fronteras afloja un poco. Pero no es suficiente.",
        "nivel_minimo": 7,
        "requiere": "ecos_del_baron",
    },
    "filo_del_abismo": {
        "titulo": "El Filo del Abismo",
        "descripcion": (
            "Los hechiceros sombríos de la Ciudadela preparan un ritual de invocación masiva "
            "que multiplicaría el ejército de no-muertos. "
            "El Hermano Aldric pide que lo interrumpas derrotando a dos de ellos."
        ),
        "tipo": "kill",
        "objetivo": {"target": "hechicero sombrío", "cantidad": 2},
        "dador": "Hermano Aldric el sacerdote",
        "receptor": "Hermano Aldric el sacerdote",
        "recompensa": {"xp": 650, "monedas": 130, "prototipo": "TUNICA_LICHE"},
        "rep_reward": {"ciudadanos": 600, "gremio_aventureros": 350, "legion_oscura": -500},
        "texto_oferta": (
            "Los hechiceros están preparando algo terrible: un ritual de invocación en masa. "
            "Si lo completan, el ejército de no-muertos se triplicará. "
            "Debes detenerlos. Elimina a dos antes de que sea tarde. "
            "Toma esta túnica como anticipo de mi gratitud."
        ),
        "texto_progreso": "Llevas {actual} de {total} hechiceros sombríos eliminados. Date prisa.",
        "texto_entrega": "El ritual se interrumpió. Salvaste miles de vidas. Toma la túnica, te la mereces.",
        "nivel_minimo": 8,
        "requiere": "legion_en_marcha",
    },

    # ----------------------------------------------------------------- #
    #  Cadena 2: Secretos de la Legión  (Mira, empieza desde archimago_caido)
    # ----------------------------------------------------------------- #
    "secretos_de_la_torre": {
        "titulo": "Secretos de la Torre",
        "descripcion": (
            "Las cenizas sombrías de los hechiceros de la Ciudadela Oscura "
            "contienen la misma impronta arcana que las de Vexthar. "
            "Mira la mercader necesita tres muestras para confirmar su teoría "
            "sobre la conexión entre el archimago caído y el liche inmortal."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "cenizas sombrías", "cantidad": 3},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 400, "monedas": 80},
        "rep_reward": {"gremio_aventureros": 300, "ciudadanos": 200},
        "texto_oferta": (
            "Estudié las cenizas arcanas de Vexthar y reconocí el patrón. "
            "Es el mismo que el de los hechiceros de la Ciudadela. "
            "Están todos conectados. Necesito tres muestras de cenizas sombrías para confirmarlo. "
            "¿Puedes traérmelas?"
        ),
        "texto_progreso": "Aún necesito {faltante} muestra(s) de cenizas sombrías más.",
        "texto_entrega": "¡Lo sabía! El patrón es idéntico. Vexthar y el liche comparten el mismo origen arcano. Esto lo cambia todo.",
        "nivel_minimo": 7,
        "requiere": "archimago_caido",
    },
    "corazon_de_tinieblas": {
        "titulo": "El Corazón de las Tinieblas",
        "descripcion": (
            "La teoría de Mira se confirma: los hechiceros sombríos son el nexo "
            "entre Vexthar y el liche inmortal. "
            "Debilitar ese nexo podría exponer una vulnerabilidad en la Ciudadela."
        ),
        "tipo": "kill",
        "objetivo": {"target": "hechicero sombrío", "cantidad": 2},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 600, "monedas": 120},
        "rep_reward": {"gremio_aventureros": 500, "ciudadanos": 300, "legion_oscura": -400},
        "texto_oferta": (
            "Los hechiceros mantienen vivo el vínculo entre el liche y su origen arcano. "
            "Sin ese vínculo, el liche quedará más expuesto. "
            "Elimina a dos de los más poderosos y busca evidencia de cómo funciona la conexión."
        ),
        "texto_progreso": "Llevas {actual} de {total} hechiceros sombríos eliminados. Avanza.",
        "texto_entrega": "Los encontré. Los vínculos se debilitan. El liche está más vulnerable de lo que cree. Solo falta una cosa.",
        "nivel_minimo": 8,
        "requiere": "secretos_de_la_torre",
    },
    "esencia_del_poder": {
        "titulo": "La Esencia del Poder",
        "descripcion": (
            "Mira necesita la esencia del liche inmortal para completar su investigación. "
            "Solo con ella podrá revelar el secreto detrás de la Legión Oscura "
            "y la verdadera naturaleza de la conexión entre Vexthar y el liche."
        ),
        "tipo": "fetch",
        "objetivo": {"target": "esencia del liche", "cantidad": 1},
        "dador": "Mira la mercader",
        "receptor": "Mira la mercader",
        "recompensa": {"xp": 900, "monedas": 180, "prototipo": "BACULO_ARCHIMAGO"},
        "rep_reward": {"ciudadanos": 700, "gremio_aventureros": 500, "legion_oscura": -600},
        "texto_oferta": (
            "Para cerrar la investigación necesito la esencia del liche inmortal. "
            "Solo el propio liche la porta, y solo muere si alguien muy poderoso lo derrota. "
            "¿Puedes traérmela? A cambio te daré el báculo de Vexthar. "
            "No hay nadie más merecedor de tenerlo que tú."
        ),
        "texto_progreso": "La esencia del liche sigue en manos del liche. Tendrás que enfrentarlo.",
        "texto_entrega": "Lo tengo. La investigación está completa. Y tú tienes el báculo de Vexthar. Úsalo bien, aventurero.",
        "nivel_minimo": 9,
        "requiere": "corazon_de_tinieblas",
    },

    "amenaza_catacumbas": {
        "titulo": "La Amenaza de las Catacumbas",
        "descripcion": (
            "Un liche menor dirige a los no-muertos desde las catacumbas bajo el calabozo. "
            "Es una amenaza para toda la ciudad."
        ),
        "tipo": "kill",
        "objetivo": {"target": "liche menor", "cantidad": 1},
        "dador": "guardia de la ciudad",
        "receptor": "guardia de la ciudad",
        "recompensa": {"xp": 500, "monedas": 100},
        "rep_reward": {"ciudadanos": 500, "gremio_aventureros": 300, "legion_oscura": -300},
        "texto_oferta": (
            "Las catacumbas bajo el calabozo llevan tiempo activas. "
            "Un liche menor dirige a los no-muertos. ¿Te atreves con él?"
        ),
        "texto_progreso": "El liche aún mora en las catacumbas. Sé muy precavido.",
        "texto_entrega": "Increíble. Has salvado a la ciudad de una amenaza real. Eres un héroe.",
        "nivel_minimo": 5,
    },
}


# --------------------------------------------------------------------------- #
#  Consulta y búsqueda
# --------------------------------------------------------------------------- #

def buscar_quest(nombre: str) -> tuple[Optional[str], Optional[dict]]:
    """
    Busca una quest por id exacto, título exacto, o coincidencia parcial.
    Normaliza espacios a guiones bajos para coincidir con ids.
    Devuelve (quest_id, quest_dict) o (None, None).
    """
    nombre_lower = nombre.lower().strip()
    nombre_norm = nombre_lower.replace(" ", "_")
    if nombre_lower in QUESTS:
        return nombre_lower, QUESTS[nombre_lower]
    if nombre_norm in QUESTS:
        return nombre_norm, QUESTS[nombre_norm]
    for qid, q in QUESTS.items():
        if nombre_lower == q["titulo"].lower():
            return qid, q
    matches = [(qid, q) for qid, q in QUESTS.items() if nombre_lower in q["titulo"].lower()]
    if len(matches) == 1:
        return matches[0]
    matches = [(qid, q) for qid, q in QUESTS.items()
               if nombre_lower in qid or nombre_norm in qid]
    if len(matches) == 1:
        return matches[0]
    return None, None


def quests_de_npc(npc_key: str) -> list[str]:
    """Devuelve los quest_ids que da este NPC (coincidencia parcial, case-insensitive)."""
    npc_lower = npc_key.lower()
    return [
        qid for qid, q in QUESTS.items()
        if q["dador"].lower() in npc_lower or npc_lower in q["dador"].lower()
    ]


def quests_para_entregar(npc_key: str, quests_personaje: dict) -> list[str]:
    """Quest_ids completados que este NPC recibe."""
    npc_lower = npc_key.lower()
    return [
        qid for qid, q in QUESTS.items()
        if (q["receptor"].lower() in npc_lower or npc_lower in q["receptor"].lower())
        and quests_personaje.get(qid, {}).get("estado") == "completada"
    ]


# --------------------------------------------------------------------------- #
#  Validación
# --------------------------------------------------------------------------- #

def quest_disponible(quest_id: str, nivel: int, quests_personaje: dict) -> tuple[bool, str]:
    """
    Comprueba si una quest está disponible para el personaje.
    Devuelve (disponible, motivo_si_no).
    """
    quest = QUESTS.get(quest_id)
    if not quest:
        return False, "Misión inexistente."
    estado = quests_personaje.get(quest_id, {}).get("estado")
    if estado == "entregada":
        return False, "Ya completaste esta misión."
    if estado in ("activa", "completada"):
        return False, "Ya tienes esta misión en curso."
    requiere = quest.get("requiere")
    if requiere:
        estado_req = quests_personaje.get(requiere, {}).get("estado")
        if estado_req != "entregada":
            titulo_req = QUESTS.get(requiere, {}).get("titulo", requiere)
            return False, f"Primero debes completar: |c{titulo_req}|n."
    if nivel < quest.get("nivel_minimo", 1):
        return False, f"Necesitas nivel {quest['nivel_minimo']} para esta misión."
    return True, ""


# --------------------------------------------------------------------------- #
#  Progreso
# --------------------------------------------------------------------------- #

def registrar_kill(quest_id: str, quests_personaje: dict) -> dict:
    """Incrementa el contador de kills y marca como completada si alcanza el objetivo."""
    quests_personaje = dict(quests_personaje)
    datos = dict(quests_personaje.get(quest_id, {"estado": "activa", "progreso": {}}))
    progreso = dict(datos.get("progreso", {}))
    progreso["kills"] = progreso.get("kills", 0) + 1
    datos["progreso"] = progreso
    quest = QUESTS.get(quest_id)
    if quest and progreso["kills"] >= quest["objetivo"]["cantidad"]:
        datos["estado"] = "completada"
    quests_personaje[quest_id] = datos
    return quests_personaje


def verificar_fetch(quest_id: str, inventario: dict) -> tuple[bool, int]:
    """
    Comprueba si el inventario tiene los items requeridos.
    inventario: {nombre_lower: cantidad}
    Devuelve (completada, cantidad_actual).
    """
    quest = QUESTS.get(quest_id)
    if not quest or quest["tipo"] != "fetch":
        return False, 0
    target = quest["objetivo"]["target"].lower()
    requerido = quest["objetivo"]["cantidad"]
    actual = inventario.get(target, 0)
    return actual >= requerido, actual


def kills_actuales(quest_id: str, quests_personaje: dict) -> int:
    return quests_personaje.get(quest_id, {}).get("progreso", {}).get("kills", 0)


def texto_progreso(quest_id: str, quests_personaje: dict, inventario: Optional[dict] = None) -> str:
    """Devuelve el texto de progreso formateado."""
    quest = QUESTS.get(quest_id)
    if not quest:
        return ""
    tpl = quest["texto_progreso"]
    if quest["tipo"] == "kill":
        actual = kills_actuales(quest_id, quests_personaje)
        total = quest["objetivo"]["cantidad"]
        return tpl.format(actual=actual, total=total)
    if quest["tipo"] == "fetch" and inventario is not None:
        target = quest["objetivo"]["target"].lower()
        requerido = quest["objetivo"]["cantidad"]
        actual = inventario.get(target, 0)
        faltante = max(0, requerido - actual)
        return tpl.format(faltante=faltante, actual=actual, total=requerido)
    return tpl
