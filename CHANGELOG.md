# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [Sin publicar]

## [0.31.0] — 2026-06-25

### Añadido
- **Logros de subclase** — 7 nuevos logros en la categoría "Subclase":
  - `Elegido` — elige cualquier especialización (sin título).
  - `Escudo Sagrado` (Paladín) → aprende las 2 habilidades de Paladín → título **el Paladín**.
  - `Furia Sin Fin` (Berserker) → aprende las 2 habilidades de Berserker → título **el Berserker**.
  - `Golpe en las Sombras` (Asesino) → aprende las 2 habilidades de Asesino → título **la Sombra Oscura**.
  - `Depredador` (Cazador) → aprende las 2 habilidades de Cazador → título **el Depredador**.
  - `Tormenta Arcana` (Hechicero) → aprende las 2 habilidades de Hechicero → título **la Tormenta**.
  - `Drenador de Almas` (Nigromante) → aprende las 2 habilidades de Nigromante → título **el Nigromante**.
- `comprobar_y_notificar` se llama automáticamente al elegir subclase.
- `_extraer_datos` incluye ahora `subclase` para evaluación de logros.
- La pantalla `logros` muestra la sección **Subclase** (entre Economía y Clase) y acepta `logros subclase` como filtro.
- Los 7 logros de subclase son mutuamente excluyentes entre sí: solo se puede completar la maestría de la propia subclase.
- El máximo alcanzable pasa de 22 a 24 (un personaje puede obtener: 19 base + 1 económico + 1 vocación + 1 maestría clase + 1 especialización + 1 maestría subclase = 24).
- Suite de tests: +24 tests puros (`TestLogrosSubclase`) + 16 tests de integración (`TestLogrosSubclaseIntegracion`). Total de tests puros: 102 en `test_logros.py`.

## [0.30.0] — 2026-06-25

### Añadido
- **Sistema de subclases de personaje**: especialización a partir del nivel 5 (una vez elegida la clase).
  - `subclase` — muestra las subclases disponibles para tu clase y tu estado actual.
  - `subclase <nombre>` — elige una especialización. Solo a nivel 5, solo una vez, requiere clase.
- **Seis subclases** (dos por clase base):
  - **Paladín** (Guerrero): +2 DEF, +15 HP máx. Habilidades: Escudo Divino (+3 DEF pasiva) y Golpe Sagrado (x2 daño + cura 25%).
  - **Berserker** (Guerrero): +4 FUE. Habilidades: Furia Berserker (+3 FUE pasiva) y Golpe Demoledor (x3.5 daño).
  - **Asesino** (Explorador): +3 DES. Habilidades: Golpe Certero (+2 DES pasiva) y Golpe Letal (x2.5 daño + sangrado).
  - **Cazador** (Explorador): +2 DES, +2 CON. Habilidades: Instinto Cazador (+1 DES +1 CON pasiva) y Trampa Mortal (x2 daño + veneno).
  - **Hechicero** (Mago): +3 INT. Habilidades: Concentración Arcana (+2 INT pasiva) y Nova Arcana (x2.5 daño mágico con INT).
  - **Nigromante** (Mago): +2 INT, +2 CON. Habilidades: Escudo Sombrío (+2 CON pasiva) y Drenar Esencia (x2 daño + cura 50%).
- **12 nuevas habilidades** de subclase en `systems/skills/trees.py` (rama = id de subclase, nv.5 pasivas / nv.7 activas, coste 2pt).
- Nuevos efectos de curación en el motor de combate: `golpe_sagrado` (25%) y `drenar_esencia` (50%).
- Nuevos estados en combat handler: `trampa_mortal` → veneno, `golpe_letal` → sangrado.
- El árbol `habilidades` muestra sección **SUBCLASE** con las habilidades propias; `habilidades <subclase>` filtra por subclase.
- Habilidades de subclase ajena muestran `|x[S]|n` (bloqueadas por subclase); las de clase ajena siguen con `|m[C]|n`.
- `systems/subclasses/subclasses.py`: lógica pura — `SUBCLASES`, `puede_elegir_subclase()`, `aplicar_subclase()`, `subclases_de_clase()`.
- `features/subclasses/commands.py`: `CmdSubclase`, `SubclassCmdSet`.
- `db.subclase` inicializado en `Character.at_object_creation`.
- Suite de tests: 58 nuevos tests puros (975 tests puros en total).

## [0.29.0] — 2026-06-23

### Añadido
- **Logros de clase** — 4 nuevos logros en la categoría "Clase":
  - `Llamado` — elige cualquier vocación (sin título).
  - `Caballero de Hierro` — completa el árbol Guerrero siendo Guerrero → título **el Caballero**.
  - `Sombra Veloz` — completa el árbol Explorador siendo Explorador → título **la Sombra**.
  - `Archimago` — completa el árbol Mago siendo Mago → título **el Archimago**.
- `comprobar_y_notificar` se llama automáticamente al elegir clase.
- `_extraer_datos` incluye ahora `clase` para que el motor de logros pueda evaluarlo.
- La pantalla `logros` muestra la sección **Clase** y acepta `logros clase` como filtro.
- El máximo de logros alcanzables por personaje pasa de 20 a 22 (20 base + vocación + una maestría de clase). Los 4 logros de clase son mutuamente excluyentes entre sí.
- Suite de tests: ~2.156 tests (124 nuevos: 42 puros + 82 integración acumulados desde v0.28).

## [0.28.0] — 2026-06-23

### Añadido
- **Sistema de clases de personaje**: tres vocaciones que definen el árbol de habilidades accesible.
  - `clase` — muestra tu clase actual y las disponibles con sus bonificaciones.
  - `clase <guerrero|explorador|mago>` — elige una clase. Solo a nivel 1 y solo una vez.
  - **Guerrero**: +3 FUE, +2 CON, +1 DEF, +20 HP máx. Rama restringida: Guerrero.
  - **Explorador**: +4 DES, +1 CON. Rama restringida: Explorador.
  - **Mago**: +5 INT. Rama restringida: Mago.
- Las habilidades de otras ramas muestran `|m[C]|n` en el árbol (bloqueadas por clase).
- Las habilidades iniciales (`golpe_fuerte`, `golpe_rapido`) siguen siendo gratuitas y no están sujetas a la restricción de clase.
- Sin clase asignada, el sistema funciona exactamente igual que antes (compatible con personajes existentes).
- El comando `perfil` muestra la clase activa con el color de la vocación.
- `db.clase` inicializado en `Character.at_object_creation`.
- `systems/classes/classes.py`: lógica pura — `CLASES`, `clase_valida()`, `puede_aprender_clase()`, `aplicar_clase()`.
- `features/classes/commands.py`: `CmdClase`, `ClassCmdSet`.
- Suite de tests: ~2.032 tests (77 nuevos: 35 puros + 42 integración).

## [0.27.0] — 2026-06-22

### Añadido
- **Tablón de contratos**: misiones procedurales con 5 contratos renovables cada hora, iguales para todos los jugadores en el mismo período.
  - `tablón` — muestra los 5 contratos disponibles con número, dificultad (★☆☆/★★☆/★★★), descripción y recompensa.
  - `tablón aceptar <#>` — acepta el contrato número #. Solo puedes tener uno activo a la vez.
  - `tablón estado` — muestra el progreso de tu contrato activo (kills hechas o materiales disponibles vs. objetivo).
  - `tablón entregar` — entrega el contrato si se ha cumplido el objetivo. Los materiales de entrega se consumen del inventario.
  - `tablón cancelar` — abandona el contrato activo sin penalización.
- **Dos tipos de contratos**:
  - `kill`: elimina N enemigos desde que aceptaste el contrato (tracking por `kills_totales`).
  - `entrega`: lleva N unidades de un material específico al tablón (se consumen al entregar).
- **Dificultad escalada**: nivel 1 (3–6 kills / 2–4 materiales), nivel 2 (8–15 / 4–7), nivel 3 (15–25 / 7–12). Recompensas proporcionales en monedas y XP.
- **Tablón determinista por hora**: todos los jugadores ven el mismo tablón usando `seed = unix_time // 3600`. Se renueva solo al cambiar la hora.
- **Integración completa con XP y subida de nivel**: entregar un contrato otorga XP y puede disparar un nivel al igual que el combate.
- `systems/contracts/contracts.py`: lógica pura — `generar_contrato()`, `generar_tablón()`, `puede_completar_kill()`, `puede_completar_entrega()`, `formatear_contrato()`, `formatear_progreso()`.
- `features/contracts/contract_script.py`: `ContractScript` (interval=3600), `obtener_tablón_script()`.
- `features/contracts/commands.py`: `CmdTablon`, `ContractCmdSet`.
- Suite de tests: ~1.955 tests (~100 nuevos: 59 puros + 41 integración).

## [0.26.0] — 2026-06-22

### Añadido
- **Mascotas de combate**: los jugadores pueden capturar criaturas debilitadas para que les acompañen en batalla.
  - `capturar` — durante tu turno de combate, si el enemigo tiene ≤ 20 % de HP, lo capturas como mascota. Solo una mascota a la vez.
  - `mascota` — muestra estadísticas de tu mascota: especie, HP, ataque, defensa y vínculo con descripción cualitativa.
  - `mascota liberar` — libera a la mascota.
  - `mascota alimentar` — gasta 10 monedas para aumentar el vínculo en 10 puntos.
  - `mascota nombre <nuevo>` — renombra a tu mascota.
- **Sistema de vínculo**: escala de 0 a 100. Afecta directamente al daño de la mascota (50 % con vínculo 0, 100 % con vínculo 100). Ganas +5 por cada enemigo derrotado con la mascota presente; +10 al alimentarla.
  - Descripciones cualitativas: Indiferente (0–24) / Amistoso (25–49) / Leal (50–79) / Devoto (80–100).
- **Ataque de mascota en CombatHandler**: si el jugador tiene mascota y su ataque principal aterriza sin matar al enemigo, la mascota ataca automáticamente ese mismo turno. Puede dar el golpe de gracia.
- La opción `capturar` aparece en las acciones disponibles del turno si el jugador no tiene mascota aún.
- `systems/pets/pets.py`: lógica pura — `puede_capturar()`, `calcular_daño_mascota()`, `calcular_nuevo_vinculo()`, `vinculo_descripcion()`, `datos_mascota_desde_criatura()`, `formatear_mascota()`.
- `features/pets/commands.py`: `CmdCapturar`, `CmdMascota`, `PetsCmdSet`.
- Suite de tests: ~1.855 tests (~86 nuevos: 56 puros + 30 integración).

## [0.25.0] — 2026-06-21

### Añadido
- **Mercado global de jugadores**: sistema de compraventa asíncrona donde los jugadores pueden vender objetos aunque estén desconectados.
  - `mercado` — listado de todos los anuncios activos con ID, nombre del objeto, precio y vendedor.
  - `mercado vender <objeto> <precio>` — poner un objeto del inventario a la venta. El objeto pasa a reserva hasta que se venda o se retire.
  - `mercado comprar <#>` — comprar el anuncio con ese número. El dinero se transfiere al instante y el vendedor recibe notificación si está conectado.
  - `mercado retirar <#>` — recuperar tu propio anuncio; el objeto vuelve al inventario.
  - `mercado mis ventas` — ver solo tus anuncios activos.
  - Comisión del 5% sobre el precio de venta (redondeada hacia arriba). El vendedor siempre cobra aunque esté offline.
  - Límite de 10 anuncios simultáneos por jugador.
  - Precio válido: 1 – 999.999 monedas.
- `MarketScript`: script persistente sin intervalo (contenedor de datos puro), key `"mercado_global"`. Se inicializa al arrancar el servidor.
- `systems/market/market.py`: lógica pura — `validar_precio()`, `calcular_comision()`, `calcular_ganancia()`, `formatear_listing()`.
- `features/market/market_script.py`: `MarketScript` + `obtener_mercado_script()`.
- `features/market/commands.py`: `CmdMercado` + `MarketCmdSet`.
- Suite de tests: ~1.769 tests (~95 nuevos: 44 puros + 51 integración).

## [0.24.0] — 2026-06-21

### Añadido
- **Crafteo de equipo con calidades**: los personajes ahora pueden craftear armas, armaduras y accesorios. La calidad del objeto escala con la experiencia del artesano (`db.objetos_crafteados`).
  - **Calidades**: Normal (0–14 crafteados), Fino (+1 a todos los stats, 15–29), Magistral (+2 a todos los stats, 30+).
  - El nombre del objeto refleja la calidad: `"daga de acero (Fino)"`, `"espada del cazador (Magistral)"`.
  - `db.calidad` guardado en el objeto para referencia.
  - Mensaje especial al craftear calidad Fino o Magistral.
- **8 nuevas recetas de equipo** (campo `tipo: "equipo"` en `RECETAS`):
  - *Armas*: `daga de acero` (hierro + piel serpiente), `espada del cazador` (hierro + garra troll), `vara arcana` (cenizas arcanas + fragmento arcano), `hacha tallada` (hierro + escama lagarto).
  - *Armaduras*: `coraza de hierro` (hierro x4 + piel serpiente), `túnica del mago` (cenizas arcanas + hilo araña + cristal sagrado).
  - *Accesorios*: `amuleto de combate` (gema en bruto + fragmento de alma), `anillo de sombras` (cristal de oscuridad + cenizas sombrías).
- **8 nuevos prototipos** en `world/prototypes.py`: `DAGA_ACERO`, `ESPADA_CAZADOR`, `VARA_ARCANA`, `HACHA_TALLADA`, `CORAZA_HIERRO`, `TUNICA_MAGO`, `AMULETO_COMBATE`, `ANILLO_SOMBRAS`.
- `systems/crafting/equipment.py`: lógica pura — `calcular_calidad()`, `aplicar_bonuses_calidad()`, `nombre_con_calidad()`.
- `CmdRecetas` actualizado: las recetas de equipo aparecen con etiqueta `[equipo]`; el detalle muestra la escala de calidades.
- Suite de tests: ~1.674 tests (~86 nuevos: 51 puros + 35 integración).

## [0.23.0] — 2026-06-21

### Añadido
- **Libro de récords globales**: comando `records` con vista global y personal.
  - `records` — top-5 global en las 5 categorías: Guerrero Supremo (kills), Aventurero Ejemplar (misiones), Cazador de Jefes, Duelista Invicto, Gran Artesano.
  - `records personal` (alias `records yo`) — resumen completo del propio personaje: nivel, gremio, título activo y las 5 estadísticas con valores exactos.
  - `records <categoria>` — top-5 de una sola categoría (kills, misiones, jefes, duelos, crafteo).
  - `RecordsScript`: script persistente que cachea el top-5 por categoría; se actualiza cada 5 min y al arrancar el servidor (`at_server_start`). Solo incluye personajes con cuenta de jugador asociada.
  - Números con separador de miles en convención española (punto).
  - Indicador de tiempo desde la última actualización en el pie del tablón.
- `systems/records/records.py`: lógica pura — definición de `CATEGORIAS`, extractores de stats individuales, `top_n()`, `formatear_posicion()`, `tiempo_desde()`.
- `features/records/records_script.py`: `RecordsScript` + `obtener_records_script()`.
- `features/records/commands.py`: `CmdRecords` + `RecordsCmdSet`.
- Suite de tests: ~1.588 tests (~77 nuevos: 54 puros + 23 integración).

## [0.22.0] — 2026-06-21

### Añadido
- **Sistema de gremios de jugadores**: grupos persistentes con jerarquía de rangos y banco compartido.
  - `crear gremio <nombre>` — funda un gremio por 500 monedas. Hasta 24 caracteres en el nombre.
  - `gremio` — muestra roster completo, descripción, banco y fecha de fundación.
  - `gremio descripcion <texto>` — el Líder puede editar la descripción.
  - `invitar <jugador>` — Líderes y Oficiales pueden invitar jugadores de la misma sala (2 min para responder).
  - `aceptar gremio` / `rechazar gremio` — gestión de invitaciones pendientes.
  - `salir gremio` — abandonar el gremio (el Líder debe transferir el mando primero).
  - `expulsar <jugador>` — Líder expulsa a Oficiales/Miembros; Oficial solo a Miembros.
  - `promover <jugador>` — ascender rangos; promover un Oficial lo convierte en Líder (con traspaso automático).
  - `degradar <jugador>` — el Líder baja un Oficial a Miembro.
  - `gbanco [depositar <n> | retirar <n>]` — banco del gremio; Miembros pueden depositar, Oficiales y Líder pueden retirar.
  - `disolver gremio` — el Líder disuelve el gremio y recupera las monedas del banco.
- Jerarquía de rangos: **Miembro → Oficial → Líder** (3 niveles, controles de permisos por operación).
- `GuildScript`: script persistente sin intervalo, uno por gremio, key `guild_<nombre_normalizado>`.
- `systems/guilds/guilds.py`: lógica pura — validación de nombre, permisos por rango, normalización.
- `features/guilds/guild_script.py`: `GuildScript` + helpers `obtener_gremio_por_nombre()` / `obtener_gremio_de()`.
- Suite de tests: ~1.511 tests (~93 nuevos: 49 puros + 44 integración).

## [0.21.0] — 2026-06-21

### Añadido
- **Sistema de duelos entre jugadores**: combate PvP reglado y sin penalización de muerte.
  - `retar <jugador> [= <monedas>]` — envía un reto de duelo con apuesta opcional. El rival tiene 60 s para responder.
  - `aceptar duelo` / `rechazar duelo` — aceptar o rechazar el reto.
  - `rendirse` — ceder la victoria durante un duelo activo (transfiere la apuesta).
  - El duelo reutiliza el `CombatHandler` existente con `modo_duelo = True`:
    - Termina automáticamente cuando un jugador llega al **10% de HP** (no hay muerte ni envío al inicio).
    - Las opciones de turno muestran `rendirse` en lugar de `huir`.
    - Si alguien usa `huir`, el duelo termina sin ganador y la apuesta se cancela.
  - Estadísticas por personaje: `db.duelos_ganados` y `db.duelos_perdidos`.
  - Validación de apuesta: se comprueba que ambos jugadores tengan las monedas antes de iniciar.
- `features/duels/commands.py`: `CmdRetar`, `CmdAceptarDuelo`, `CmdRechazarDuelo`, `CmdRendirse`, `DuelCmdSet`.
- `systems/duels/duels.py`: lógica pura — `validar_apuesta()`, `calcular_hp_umbral()`, `formatear_resultado()`, `reto_expirado()`.
- Suite de tests: ~1.418 tests (~75 nuevos: 43 puros + 32 integración).

## [0.20.0] — 2026-06-21

### Añadido
- **Sistema de misiones encadenadas**: las quests pueden declarar un campo `requiere` con el ID de otra quest que debe estar en estado `"entregada"` para desbloquearlas.
  - `quest_disponible()` comprueba el prerrequisito antes del nivel mínimo.
  - El comando `hablar <npc> = misión` muestra una sección **"Próximamente disponibles"** con quests bloqueadas solo por prerrequisito cuando la quest requerida ya está en el log del jugador (cualquier estado), permitiendo ver el camino de la cadena.
- **Cadena 1: La Oscuridad se Extiende** (Hermano Aldric, requiere `caballero_sombras`):
  - `ecos_del_baron` (lv.6, fetch 2 "fragmento de alma oscura"): el caballero oscuro apunta a la Ciudadela.
  - `legion_en_marcha` (lv.7, kill 3 "caballero de la muerte"): detener la vanguardia de la Legión.
  - `filo_del_abismo` (lv.8, kill 2 "hechicero sombrío"): interrumpir el ritual de invocación masiva. Recompensa final: `TUNICA_LICHE`.
- **Cadena 2: Secretos de la Legión** (Mira la mercader, requiere `archimago_caido`):
  - `secretos_de_la_torre` (lv.7, fetch 3 "cenizas sombrías"): Mira investiga la conexión entre Vexthar y el liche.
  - `corazon_de_tinieblas` (lv.8, kill 2 "hechicero sombrío"): debilitar el nexo arcano.
  - `esencia_del_poder` (lv.9, fetch 1 "esencia del liche"): completar la investigación de Mira. Recompensa final: `BACULO_ARCHIMAGO`.
- Suite de tests: ~1.343 tests (~56 nuevos: 39 puros + 17 integración).

## [0.19.0] — 2026-06-21

### Añadido
- **Sistema de eventos mundiales**: tres eventos periódicos que afectan a todos los jugadores conectados.
  - **Invasión de No-Muertos** (20 min, cada ≥2h, peso 3): doble XP al derrotar a enemigos de la `legion_oscura`.
  - **Feria del Mercado** (15 min, cada ≥3h, peso 2): 20% de descuento adicional en todas las tiendas.
  - **Tormenta Mágica** (10 min, cada ≥4h, peso 1): +3 Inteligencia en combate para todos los jugadores.
  - Los eventos se disparan aleatoriamente (20% de probabilidad por minuto) si el evento está fuera de su cooldown.
  - La selección es ponderada: eventos con mayor `peso` son más frecuentes.
  - Broadcast global al inicio y fin con mensaje con color.
  - Comando `evento` (alias `eventos`): muestra el evento activo con nombre, efectos y tiempo restante.
- `EventoMundialScript`: script global persistente (tick 60s) que gestiona el ciclo inicio/duración/fin y los cooldowns por evento.
- Módulo puro `systems/events/events.py`: catálogo, `eventos_elegibles()` y `elegir_evento()` testables.
- Integración con tienda: descuento de feria se acumula sobre el factor de reputación.
- Integración con combate:
  - XP multiplicado si la facción del NPC coincide con las `facciones_afectadas` del evento activo.
  - INT del jugador aumentada en `bonus_inteligencia` durante la tormenta (en `_get_stats`).
- Suite de tests: ~1.287 tests (~54 nuevos: 31 puros + 23 integración).

## [0.18.0] — 2026-06-21

### Añadido
- **Zona de endgame: Ciudadela Oscura** — 3 salas conectadas al norte de la Cripta del Barón.
  - **Portal de la Ciudadela**: entrada custodiada por 2 Caballeros de la Muerte (nv.8).
  - **Salón del Trono**: 1 Caballero de la Muerte + 2 Hechiceros Sombríos (nv.9).
  - **Altar del Liche**: cámara final con el Liche Inmortal (boss nv.10, jefe de la Legión Oscura).
- **3 nuevos NPCs** de la Legión Oscura:
  - `CABALLERO_MUERTE` (nv.8): guerrero melee con loot de fragmentos de alma oscura y posibilidad de soltar la Túnica del Liche.
  - `HECHICERO_SOMBRIO` (nv.9): mago oscuro que suelta cenizas sombrías y cristales de oscuridad.
  - `LICHE_INMORTAL` (nv.10, boss, respawn 30 min): con árbol completo de habilidades, loot de Esencia del Liche + Corona Oscura, y diálogo.
- **2 nuevos ítems de endgame**:
  - `CORONA_OSCURA` (slot arma): +10 INT, +2 FUE.
  - `TUNICA_LICHE` (slot armadura): +7 DEF, +5 INT, +15 HP_MAX.
- **2 nuevas misiones**:
  - `liche_inmortal` (kill, nv.9, Aldric): derrotar al Liche Inmortal. Recompensa: 900 XP, 200 monedas.
  - `fragmentos_oscuridad` (fetch, nv.7, Mira): recolectar 3 fragmentos de alma oscura. Recompensa: 400 XP, 90 monedas.
- **2 nuevas recetas de crafteo**:
  - `elixir sombrío`: 2 cenizas sombrías + 1 fragmento de alma oscura → Elixir de Restauración.
  - `tónico de las sombras`: 1 cristal de oscuridad + 1 cenizas sombrías → 2× Poción de Vida Mayor.
- **`LICHE_INMORTAL` añadido a `JEFES`** en el sistema de logros (ahora 7 jefes totales).
  - El logro `todos_jefes` requiere derrotar los 7 jefes del mundo.
- Suite de tests: ~1.233 tests (~67 nuevos: 47 puros + 20 de integración).

## [0.17.0] — 2026-06-21

### Añadido
- **Sistema de logros y títulos**: 20 logros distribuidos en 7 categorías que recompensan el progreso del jugador.
  - Categorías: Progresión, Misiones, Combate, Habilidades, Encantamiento, Reputación, Crafteo, Economía.
  - Cada logro puede otorgar un título equipable que aparece junto al nombre en el perfil.
  - Notificación inmediata al desbloquear un logro (con indicación del título si lo hay).
  - Comando `logros` (alias `achievements`): muestra todos los logros con estado ✔/✗, filtrable por categoría.
  - Comando `titulo <titulo>` (alias `title`): activa un título desbloqueado; sin argumento lo elimina.
  - El título activo aparece junto al nombre en el comando `perfil`.
- Seguimiento de estadísticas nuevas en `Character`:
  - `db.kills_totales` — total de NPCs derrotados.
  - `db.jefes_derrotados` — lista de prototype_key de jefes eliminados (GOBLIN_JEFE, BANDIDO_CAPITAN, TROLL, CABALLERO_OSCURO, GOLEM_PIEDRA, ARCHIMAGO_VEXTHAR).
  - `db.objetos_crafteados` — objetos elaborados en total.
  - `db.encantamiento_max` — nivel de encantamiento más alto alcanzado.
  - `db.banco_usado` — indica si el jugador ha depositado alguna vez en el banco.
- Comprobación automática de logros tras: kill NPC, subida de nivel, entrega de misión, aprendizaje de habilidad, encantamiento, crafteo y depósito en banco.
- Módulo puro `systems/achievements/achievements.py` con toda la lógica de condiciones.
- Suite de tests: ~1.166 tests (~60 nuevos).

## [0.16.0] — 2026-06-18

### Añadido
- **Sistema de encantamiento de equipo**: mejora ítems `Equipo` hasta +3 usando loot del mundo.
  - Comando `encantar [objeto]`: sin argumento lista los ítems mejorables con su coste; con argumento encanta el ítem.
  - Alias: `enchant`, `encantamiento`.
  - Cada nivel añade stats según el slot:
    - **Arma** +N: +2 al stat con mayor bonus positivo.
    - **Armadura** +N: +2 defensa, +5 HP_MAX.
    - **Accesorio** +N: +1 a cada stat con valor positivo.
  - Costes escalan con el nivel; el nivel 3 requiere materiales raros (núcleo arcano / cenizas arcanas).
  - Si el ítem está equipado, el bonus se aplica al personaje inmediatamente.
  - El nombre del ítem se actualiza con el sufijo ` +N` (e.g., `espada de hierro +2`).
  - Módulo puro `systems/enchantment/enchantment.py` con toda la lógica.
  - `features/enchantment/commands.py` integrado en `CharacterCmdSet`.
- Suite de tests: ~1.106 tests (~54 nuevos).

## [0.15.0] — 2026-06-18

### Añadido
- Nueva zona: **Torre del Mago Caído** (3 salas), conectada al este del Claro del Bosque.
  - **Base de la Torre** — exterior, entrada sellada con inscripciones arcanas.
  - **Biblioteca del Archimago** — interior, estanterías quemadas y círculos arcanos.
  - **Cámara del Ritual** — interior, sala superior donde mora el archimago boss.
- Nuevos NPCs de combate:
  - **Aprendiz Corrompido** (nv.5, Legión Oscura): usa `dardo mágico` y `escudo arcano`. Suelta cenizas arcanas y fragmentos de saber.
  - **Guardián Arcano** (nv.6, Legión Oscura): constructo mágico con `golpe fuerte` y `embestida`. Suelta fragmento arcano.
  - **Archimago Vexthar** (nv.9, boss, Legión Oscura): usa `dardo mágico`, `escudo arcano`, `bola de fuego` y `drenar vida`. Suelta núcleo arcano y báculo del archimago garantizados.
- 2 nuevos ítems de equipo:
  - **Báculo del Archimago** (arma: INT+8, DEF+1)
  - **Manto Arcano** (armadura: DEF+5, INT+3, HP_MAX+10)
- 2 nuevas misiones:
  - *Los Aprendices de la Torre* (kill 3 aprendices, nv.4; dador: Hermano Aldric)
  - *El Archimago Caído* (kill Vexthar, nv.7; dador: Mira la mercader; recompensa: Manto Arcano)
- 2 nuevas recetas de crafteo (loot de la zona):
  - **Esencia de Ceniza** (cenizas arcanas ×2 → Poción de Vida Mayor)
  - **Elixir Arcano** (cenizas arcanas ×1 + fragmento arcano ×1 → Elixir de Restauración)
- Descripción del Claro del Bosque actualizada para reflejar la salida este hacia la torre.
- Nuevos diálogos en Mira la mercader y Hermano Aldric sobre la torre y el archimago.
- Detalles ocultos en las 3 nuevas salas (percepción 11–16).
- Suite de tests actualizada: ~1.052 tests (~46 nuevos).

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
