# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [Sin publicar]

## [0.14.0] — 2026-06-17

### Añadido
- Nueva zona: **Minas de Hierro Viejo** (3 salas), conectada al oeste del Bosque del Norte.
  - **Boca de la Mina** — exterior, entrada con arañas guardianas.
  - **Galería Principal** — interior, túneles con mineros malditos (no-muertos).
  - **Caverna del Coloso** — interior, guarida del gólem boss.
- Nuevos NPCs de combate:
  - **Araña de Cueva** (nv.3, Horda Salvaje): usa `corte` y `veneno`. Suelta hilo de araña y colmillos.
  - **Minero Maldito** (nv.4, Legión Oscura): cadáver animado con `golpe fuerte` y `embestida`. Suelta mineral de hierro y gemas.
  - **Gólem de Piedra** (nv.7, boss, Legión Oscura): boss colosal con `golpe fuerte`, `embestida` y `golpe maestro`. Suelta núcleo de piedra y pico de minero garantizado.
- Nuevo NPC civil: **Torben el buscador de tesoros** (Gremio de Aventureros) en el Mercado de la Ciudad, con tienda y 2 misiones propias.
- 2 misiones nuevas (dadas por Torben):
  - *La Veta Perdida* (fetch 2 minerales de hierro, nv.3)
  - *El Coloso Despertado* (kill gólem de piedra, nv.6; recompensa: Anillo de Constitución)
- 2 nuevos items de equipo:
  - **Pico de Minero** (arma: FUE+5, CON+1)
  - **Anillo de Constitución** (accesorio: CON+4, HP_MAX+15)
- 2 nuevas recetas de crafteo (loot de la zona):
  - **Antídoto de Araña** (hilo de araña ×2 → Antídoto ×2)
  - **Tónico de Piedra** (mineral de hierro + gema en bruto → Poción de Vida Mayor)
- Zona `mercado` en spawn tables actualizada: incluye BUSCADOR_TESOROS.
- Detalles ocultos en las 3 nuevas salas (percepción 11–16).
- 43 tests unitarios puros + 52 de integración. Suite total: ~1.006 tests.

## [0.13.0] — 2026-06-06

### Añadido
- **Sistema de clima dinámico** con 5 tipos de tiempo: Despejado, Nublado, Lluvia, Tormenta y Niebla.
  - Transiciones probabilísticas: el clima cambia de forma gradual cada 10 minutos reales.
  - Al cambiar de clima, todos los jugadores conectados reciben un mensaje atmosférico de transición.
  - Salas exteriores muestran el texto de ambiente del clima en su descripción (junto al ciclo día/noche).
  - Salas interiores (`db.exterior = False`) no muestran texto de clima.
  - Textos diferenciados por tipo de entorno: `exterior_natural` y `exterior_urbano`.
- Penalizaciones climáticas a la percepción: Niebla −4, Tormenta −2, Lluvia −1 (se acumulan con la penalización nocturna).
- `PerceptionManager.nivel_percepcion/puede_detectar/revelar_detalles/filtrar_visibles` aceptan nuevo parámetro `clima` opcional.
- Comando `clima` (alias `weather`): muestra el tipo de tiempo actual e indica la penalización de percepción activa.
- El comando `percibir` aplica ahora tanto la penalización nocturna como la climática.
- Script global `ClimaScript` (persistente, `features/weather/weather_script.py`): arranca automáticamente en `at_server_start`.
- Módulo puro `systems/weather/weather.py`: `CLIMAS`, `TRANSICIONES`, `PENALIZACION_PERCEPCION`, `MENSAJES_TRANSICION`, `siguiente_clima`, `penalizacion_percepcion`, `texto_ambiente_clima`.
- 55 tests nuevos: 36 unitarios puros + 19 de integración (suite total: ~911 tests).

## [0.12.0] — 2026-06-05

### Añadido
- **Sistema de banco**: los jugadores pueden depositar y retirar objetos del banco cerca de un banquero NPC.
  - Comandos: `banco` (listar), `depositar <objeto>`, `retirar <objeto>`.
  - Los objetos depositados se guardan en el limbo de la base de datos (persistentes entre sesiones).
  - Requiere la presencia de un NPC con `db.es_banquero=True` en la misma sala.
  - No se pueden depositar objetos equipados; la función `limpiar_banco` elimina referencias muertas automáticamente.
- Nuevo NPC civil: **Cornelio el Banquero** (neutral, Ciudadanos) en la Plaza de la Ciudad, con diálogo.
- `db.banco = []` inicializado en `Character.at_object_creation`.
- Prototipo `BANQUERO` añadido a `world/prototypes.py` y zona `plaza_ciudad` en spawn tables.
- Módulo puro `systems/bank/bank.py`: `puede_depositar`, `limpiar_banco`.
- 15 tests unitarios puros (`tests/test_bank_system.py`) + 20 tests de integración (`tests/test_bank.py`).

## [0.11.0] — 2026-06-05

### Añadido
- Nueva zona: **Ruinas del Templo Antiguo** (3 salas): Camino al Templo, Ruinas del Templo, Cripta del Barón.
  Conectada al norte del Claro del Bosque. La Cripta es interior (`exterior=False`).
- Nuevos NPCs de combate: **Espectro** (nv.4, Legión Oscura) y **Caballero Oscuro** (nv.8, boss, Legión Oscura).
- Nuevo NPC civil: **Hermano Aldric el sacerdote** en la Plaza de la Ciudad, con tienda y misiones propias.
- 4 misiones nuevas (todas vinculadas al sacerdote):
  - *El Templo Corrompido* (kill 4 espectros, nv.3)
  - *La Cruz Perdida* (fetch símbolo sagrado, nv.3)
  - *El Caballero de las Sombras* (kill caballero oscuro, nv.6, boss)
  - *Los Cristales del Ritual* (fetch 2 cristales sagrados, nv.4)
- 2 nuevos items de equipo: **Báculo Arcano Antiguo** (arma, INT+6/DEF−1) y **Escudo de Roble** (armadura, DEF+5/HP+8).
- 2 nuevas recetas de crafteo: **Bálsamo Sagrado** (cristal sagrado ×2 → Poción de Vida Mayor) y **Tónico del Templo** (cristal sagrado + fragmento de alma → Elixir de Restauración).
- Zona `plaza_ciudad` en spawn tables actualizada: incluye SACERDOTE además de GUARDIA.
- Detalles ocultos en las 3 nuevas salas (percepción 10–16).

## [0.10.0] — 2026-06-05

### Añadido
- Ciclo día/noche con 6 períodos: Amanecer (5–7), Mañana (7–12), Mediodía (12–14), Tarde (14–19), Anochecer (19–21), Noche (21–5).
- Tiempo de juego: 1 minuto real = 1 hora de juego → ciclo completo cada 24 minutos reales.
- Script global `RelojMundial` (persistente) que avanza la hora cada minuto y notifica a todos los jugadores conectados al cambiar de período.
- Al cambiar de período, todos los jugadores reciben un mensaje atmosférico de transición.
- Comando `hora` (alias `time`, `tiempo`): muestra la hora de juego y el período actual.
- Textos de ambiente en `return_appearance` de salas exteriores: cambian según el período y el tipo de entorno (`exterior_natural` / `exterior_urbano`).
- Salas interiores (`db.exterior = False`) no muestran texto de ambiente ni sufren penalización nocturna.
- Salas marcadas como urbanas (`db.tipo_ambiente = "exterior_urbano"`): Plaza, Mercado.
- Salas marcadas como interiores: Taberna, Cueva Oscura, Calabozo (entrada/pasillo/celda), Guarida del Troll, Catacumbas (túnel/tumbas/cámara).
- Penalización nocturna a la percepción: Noche −3, Anochecer/Amanecer −1. Solo se aplica en salas exteriores.
- `PerceptionManager.nivel_percepcion`, `puede_detectar` y `revelar_detalles` aceptan parámetro `hora` opcional.
- El reloj se inicia automáticamente en `at_server_start` mediante `obtener_reloj()`.
- Módulo puro `systems/time/clock.py`: períodos, textos de ambiente, penalizaciones, mensajes de transición.
- 34 tests nuevos: 34 unitarios puros + 13 de integración (suite total: ~573 tests).

## [0.9.0] — 2026-06-05

### Añadido
- Sistema de reputación con 5 facciones: Ciudadanos, Gremio de Aventureros, Horda Salvaje, Sombras del Pantano y Legión Oscura.
- 7 rangos de reputación: Enemigo → Hostil → Neutral → Amistoso → Honrado → Venerado → Exaltado.
- Comando `reputación` (alias `reputacion`, `facciones`, `rep`): muestra la tabla de reputación con rango actual, puntos y distancia al siguiente rango.
- Las misiones otorgan reputación al entregarse: ganas con la facción del dador y pierdes con la facción enemiga.
- Los comerciantes aplican descuento o recargo según reputación con su facción: Amistoso −5%, Honrado −10%, Venerado −15%, Exaltado −20%, Hostil +20%.
- Los comerciantes se niegan a vender si el jugador tiene reputación Enemigo con su facción.
- El comando `tienda` muestra el precio ajustado y el porcentaje de descuento/recargo activo.
- Los NPCs con facción agreden al jugador al entrar en la sala si la reputación es Enemigo (< −3000 pts), independientemente de su temperamento (excepción: cobardes).
- `db.reputacion = {}` inicializado en `Character.at_object_creation`.
- `db.faccion` añadido a todos los prototipos de NPC de combate y a `NPC.at_object_creation`.
- Módulo puro `systems/reputation/factions.py`: catálogo de facciones, umbrales y límites.
- Módulo puro `systems/reputation/engine.py`: `obtener_rep`, `modificar_rep`, `titulo_reputacion`, `proximo_umbral`, `descuento_tienda`, `es_enemigo`, `aplicar_rep_quest`.
- 56 tests nuevos: 43 unitarios puros + 13 de integración (suite total: ~539 tests).

## [0.8.0] — 2026-05-18

### Añadido
- Sistema de grupos (party) de hasta 4 jugadores.
- Comando `invitar <jugador>`: crea el grupo automáticamente e invita a otro jugador de la misma sala.
- Comando `unirse`: acepta una invitación de grupo pendiente.
- Comando `declinar`: rechaza una invitación pendiente.
- Comando `partido` / `grupo`: muestra la composición del grupo con HP, nivel y ubicación de cada miembro.
- Comando `abandonar`: sale del grupo; si el líder abandona, el liderazgo se transfiere al siguiente miembro.
- Comando `expulsar <jugador>`: el líder expulsa a un miembro.
- Los miembros del grupo se unen automáticamente al combate cuando uno de ellos ataca o es agredido por un NPC en la misma sala.
- El XP se reparte entre todos los miembros del grupo en sala, con un bonus de grupo del +20%.
- Los NPCs solo atacan a jugadores (nunca a otros NPCs), evitando que se peguen entre ellos en combate de grupo.
- Si todos los jugadores mueren o huyen, el combate termina aunque queden NPCs.
- `db.lider_partido`, `db.miembros_partido`, `db.invitacion_partido` inicializados en `Character.at_object_creation`.
- Módulo puro `systems/party/engine.py`: `xp_por_miembro`, `puede_invitar_validar`, `MAX_MIEMBROS`.
- 30 tests nuevos: 13 unitarios puros + 17 de integración (suite total: ~462 tests).

## [0.7.0] — 2026-05-12

### Añadido
- Árbol de habilidades con 12 habilidades distribuidas en tres ramas: Guerrero, Explorador y Mago.
- Los jugadores empiezan con `golpe_fuerte` y `golpe_rapido` desbloqueados de forma gratuita.
- Sistema de puntos de habilidad: se gana 1 punto por cada nivel (a partir del nivel 2).
- Rama **Guerrero**: `golpe_fuerte` → `embestida` → `escudo_fe` (pasiva) → `golpe_maestro`.
- Rama **Explorador**: `golpe_rapido` → `corte` → `veneno` → `ejecutar`.
- Rama **Mago**: `dardo_magico` → `escudo_arcano` (pasiva) → `bola_fuego` → `drenar_vida`.
- Habilidades pasivas (`escudo_fe`, `escudo_arcano`) aplican bonus de defensa al aprenderse.
- `ejecutar` inflige x3 daño si el objetivo tiene menos del 25% de vida.
- `dardo_magico` usa Inteligencia en lugar de Fuerza para calcular el daño.
- `drenar_vida` inflige x1.5 daño y cura al atacante el 50% del daño infligido.
- Comando `habilidades` (alias `skills`): muestra el árbol completo, por rama o detalle de una habilidad.
- Comando `aprender <habilidad>` (alias `learn`): desbloquea la habilidad si se cumplen requisitos.
- `_aplicar_habilidad` normaliza nombres (espacios → guiones bajos) y soporta las 10 habilidades del árbol.
- Mensaje de subida de nivel actualizado: informa del nuevo punto de habilidad disponible.
- `db.habilidades_desbloqueadas` en `Character.at_object_creation` reemplaza `db.habilidades` para jugadores.
- `perfil` y `stats` muestran las habilidades del árbol con nombres legibles.
- `CmdHabilidad` (combate) verifica `habilidades_desbloqueadas` además del legacy `habilidades`.
- Módulo puro `systems/skills/trees.py` con el catálogo y `systems/skills/engine.py` con la lógica.
- 68 tests nuevos: 42 unitarios puros + 26 de integración (suite total: 432 tests).

## [0.6.0] — 2026-05-12

### Añadido
- Tabla de zonas pura `systems/spawn/tables.py` con las 13 zonas del mundo (ciudad, bosque, calabozo, pantano, catacumbas) y sus prototipos de NPC.
- Funciones puras `npcs_necesarios()` y `calcular_faltantes()` para calcular qué NPCs faltan en una zona sin depender de Evennia.
- Manager de spawn `features/spawn/manager.py` con `spawn_npc()`, `repoblar_sala()` y `repoblar_mundo()`.
- `spawn_npc()` soporta parámetros opcionales: `oculto`, `nivel_sigilo`, `key_npc` y `patrol_sala_key`.
- `repoblar_sala()` solo crea los NPCs que faltan; no duplica ni elimina los existentes.
- Comando builder `@spawn <prototipo> [cantidad]` para crear NPCs manualmente en la sala actual.
- Comando builder `@repoblar` / `@repoblar/mundo` para repoblar la sala actual o todas las zonas.
- Atributo `db.zona` añadido a todas las salas del mundo en `at_initial_setup` y `build_expansion`.
- 53 tests nuevos: 19 unitarios puros + 34 de integración (suite total: 364 tests).

## [0.5.0] — 2026-05-12

### Añadido
- Sistema de misiones (quests): módulo puro `systems/quests/quests.py` sin dependencias de Evennia.
- 5 misiones iniciales en dos categorías:
  - **Kill**: "El Problema de los Goblins" (nv.1), "La Mercancía Robada" (nv.3), "La Amenaza de las Catacumbas" (nv.5).
  - **Fetch**: "Veneno del Pantano" (nv.2), "La Garra del Troll" (nv.5).
- Comando `misiones` (alias `quests`, `quest`, `log misiones`): muestra el registro de misiones activas, completadas y entregadas; con argumento muestra el detalle y progreso de una misión concreta.
- Comando `aceptar` (alias `accept`): acepta una misión si el NPC dador está en la sala y se cumplen los requisitos de nivel.
- Comando `entregar` (alias `turnin`): entrega una misión completada al NPC receptor; consume automáticamente los objetos en misiones fetch y otorga XP, monedas e items de recompensa.
- Hook `on_npc_muerte`: se llama desde `CombatHandler._procesar_muerte` para actualizar el progreso de kill quests y notificar al jugador.
- Integración con `CmdHablar`: al hablar con un NPC se muestran las misiones disponibles, en curso y listas para entregar; la palabra clave `misión`/`quest` muestra el detalle completo.
- `buscar_quest` normaliza espacios a guiones bajos para que "problema goblins" encuentre "problema_goblins".
- `db.quests = {}` inicializado en `Character.at_object_creation`.
- 66 tests nuevos: 34 unitarios puros + 32 de integración (suite total: 311 tests).

## [0.4.0] — 2026-05-11

### Añadido
- Sistema de estados de combate: veneno, sangrado y regeneración.
- La habilidad `veneno` aplica envenenamiento al impactar (−5 HP/turno durante 3 turnos).
- La habilidad `corte` aplica sangrado al impactar (−3 HP/turno durante 2 turnos).
- Los estados tickan al inicio del turno del afectado en combate, y cada 5 s fuera de él (`EstadosScript`).
- Fuera de combate el HP nunca baja de 1 por efecto de estado.
- El antídoto (comprable y crafteable) ahora cura el veneno de forma efectiva.
- El comando `perfil` muestra los estados activos con los turnos restantes.
- `ResultadoAtaque` incluye el campo `estado_aplicado`; solo se aplica en golpes exitosos y no letales.
- `db.estados` inicializado en personajes y NPCs al crearse.
- 39 tests nuevos: 27 unitarios puros + 12 de integración (suite total: 245 tests).

## [0.3.0] — 2026-05-11

### Añadido
- Sistema de crafteo: módulo puro `systems/crafting/recipes.py` con 4 recetas y funciones de validación sin dependencias de Evennia.
- Comando `craftear` (alias `fabricar`, `elaborar`) para elaborar objetos consumibles desde el inventario.
- Comando `recetas` (alias `recipes`) para listar y consultar recetas disponibles.
- Búsqueda de receta por nombre exacto, por prefijo y por contenido; detecta ambigüedad y pide más precisión.
- Los objetos equipados nunca se consumen accidentalmente al craftear.
- 4 recetas que dan uso al loot de las zonas de expansión:
  - `piel de serpiente` → poción de vida
  - `piel de serpiente` + `veneno de pantano` → antídoto x2
  - `garra de troll` + `piel de serpiente` → poción de vida mayor
  - `fragmento de alma` + `escama de lagarto x2` → elixir de restauración
- 35 tests nuevos: 19 unitarios puros + 16 de integración (suite total: 206 tests).

## [0.2.0] — 2026-05-11

### Añadido
- Sistema de consumibles: typeclass `Consumible` con efectos `curar_hp`, `curar_maximo` y `curar_veneno`.
- Comando `usar` (alias `beber`, `tomar`, `consumir`) para usar objetos consumibles del inventario.
- Los consumibles con usos finitos se eliminan automáticamente al agotarse.
- 4 prototipos nuevos: `POCION_VIDA` (+30 HP), `POCION_VIDA_MAYOR` (+60 HP), `ELIXIR_RESTAURACION` (HP al máximo), `ANTIDOTO` (cura envenenamiento).
- El mesonero vende poción de vida (15 m) y antídoto (20 m).
- La mercader vende poción de vida mayor (30 m) y elixir de restauración (75 m).
- El inventario muestra los consumibles como grupo propio con el efecto resumido.
- 21 tests de integración para el sistema de consumibles (suite total: 171 tests).

## [0.1.0] — 2026-05-07

### Añadido
- Sistema de combate por turnos con handler por sala, orden de iniciativa y rondas.
- Habilidades de combate configurables por NPC y personaje.
- Sistema de equipamiento con slots `arma`, `armadura` y `accesorio`; bonuses aplicados a stats al equipar/desequipar.
- Sistema de tienda: NPCs con catálogo (`db.tienda`), stock finito o ilimitado, comandos `tienda`, `comprar` y `vender`.
- Typeclass `NPC` con temperamentos (`neutral`, `agresivo`, `cobarde`, `guardián`), diálogo por palabra clave y patrullas por sala.
- Sistema de puertas con llave, puertas secretas y estado persistente.
- Sistema de respawn de NPCs con loot configurable.
- Sistema de percepción: detección de objetos y personajes ocultos.
- Prototipos de objetos y NPCs en `world/prototypes.py`.
- Script de construcción del mundo en `world/build_expansion.py`.
- Entradas de ayuda en español en `world/help_entries.py`.
- API REST básica en `web/api/` para consultas externas.
- Suite de 150 tests de integración con `EvenniaTest`.

### Corregido
- `_get_equipamiento` usaba `isinstance(eq, dict)` que fallaba con `_SaverDict` de Evennia (es `MutableMapping`, no subclase de `dict`); corregido a `isinstance(eq, Mapping)`.
- `_buscar_comerciante` ignoraba NPCs con tienda vacía `[]` por ser falsy; corregido a comparación `is not None`.
- Parser de `comprar` dividía incorrectamente nombres de artículo con `" de "` (ej. `"pocion de vida"`); corregido con búsqueda silenciosa para verificar si el sufijo es un NPC real.
- Parser de `vender` tenía el mismo problema con `" a "` en nombres de artículo; corregido con la misma técnica.
