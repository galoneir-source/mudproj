# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [Sin publicar]

## [0.71.21] — 2026-08-30

### Corregido
- `_dar_xp_a_grupo()` (`features/combat/handler.py`) reparte XP (y aplica subida de nivel, vía `procesar_subida_de_nivel`) a todos los miembros del grupo presentes en la sala del combate — pero `self.db.participantes` solo incluye al atacante y al objetivo que iniciaron la pelea (`features/combat/commands.py`), no al resto del grupo. `comprobar_y_notificar()` tras la muerte del NPC solo se llama para "jugadores" = `self.db.participantes`, así que un miembro de grupo que sube de nivel gracias al XP compartido de una pelea en la que no participó directamente nunca entraba en ese bucle: los logros de progresión (`nivel_2`, `nivel_5`, `nivel_10`) quedaban sin comprobar hasta la siguiente acción cualquiera de ese personaje que sí disparase el chequeo (kill propio, quest, crafteo...) — mismo patrón de notificación retrasada ya visto y corregido en la transferencia de liderazgo de gremio (ver entrada anterior de logros de gremio). Encontrado auditando el sistema de logros. Fix: `_dar_xp_a_grupo()` llama ahora a `comprobar_y_notificar()` para cada miembro del grupo que recibe XP, no solo para quien remató. 1 test de regresión nuevo en `tests/test_handler.py`.

## [0.71.20] — 2026-08-30

### Corregido
- `puede_invitar_validar()` (`systems/party/engine.py`) no comprobaba si el objetivo de una invitación de grupo YA tenía una invitación pendiente de otro líder. `objetivo.db.invitacion_partido` es un slot único: si un líder A invitaba a un jugador y, antes de que respondiera, un líder B (con un grupo distinto) también lo invitaba, la segunda invitación sobrescribía la primera en silencio, sin avisar nunca al líder A. Si el jugador aceptaba después, se unía al grupo de B (el último en invitar) mientras A se quedaba esperando indefinidamente una invitación que ya no existía, sin ningún mensaje que explicara por qué. Encontrado auditando el sistema de grupos — la lógica de transferencia de liderazgo y disolución de grupo en `_quitar_miembro()` (`features/party/commands.py`) se revisó a fondo en varios escenarios y resultó correcta. Fix: `puede_invitar_validar()` recibe un nuevo parámetro `objetivo_tiene_invitacion_pendiente` (con valor por defecto `False`, compatible con las llamadas existentes) y rechaza la invitación si ya hay una pendiente, mismo criterio de slot único que ya protege el resto de negociaciones 1-a-1 del proyecto (comercio, duelos). 1 test de regresión nuevo en `tests/test_party.py`.

## [0.71.19] — 2026-08-29

### Corregido
- `_dar_recompensa()` (`features/contracts/commands.py`) leía `nuevos_stats['ataque']` en el mensaje de subida de nivel — una clave que no existe en el dict que devuelve `procesar_subida_de_nivel()` (`systems/combat/engine.py`); `STAT_DEFAULTS` no define ningún stat "ataque" en todo el proyecto. Completar un contrato del tablón (matar o entregar) con recompensa de XP suficiente para subir de nivel lanzaba un `KeyError` sin capturar que interrumpía `_entregar()` a medias: la recompensa (monedas, XP y, en un contrato de entrega, los materiales ya consumidos del inventario) ya se había aplicado, pero `contrato_activo` nunca se limpiaba — el jugador se quedaba con "ya tienes un contrato activo" para siempre, sin poder aceptar otro ni ver ningún mensaje de éxito, pese a haber pagado el coste real de completarlo. Encontrado auditando el tablón de contratos — ningún test anterior completaba un contrato con XP suficiente para cruzar el umbral de nivel. Fix: el mensaje usa ahora `nuevos_stats['fuerza']` (la clave real que sí devuelve `procesar_subida_de_nivel()`), igual que el resto de mensajes de subida de nivel del proyecto. 2 tests de regresión nuevos en `tests/test_contratos.py` (rutas de matar y de entrega, ambas comparten `_dar_recompensa()`).

## [0.71.18] — 2026-08-29

### Corregido
- El tracking de daño contra un jefe de mundo (`features/combat/handler.py`) se guardaba en `objetivo.ndb.dano_por_jugador` — memoria del proceso que Evennia no conserva a través de un `evennia reload`, operación rutinaria y publicitada como segura para los jugadores ("recargar sin perder conexiones", ver comandos esenciales del proyecto). Un jefe de mundo tiene mucho HP y una pelea real puede durar más que el intervalo habitual entre reloads del servidor, así que uno ocurriendo a mitad de combate borraba en silencio todo el progreso de daño acumulado hasta ese momento — quien más había golpeado antes del reload podía terminar sin ninguna recompensa (XP, monedas, ni siquiera opción al loot único) si no volvía a golpear después. Encontrado auditando jefes de mundo — el sistema ya tenía otra corrección documentada de una ronda anterior (el mínimo garantizado del 10% del pool por participante, que sin reescalar podía superar el 100% del reparto total con muchos participantes), pero esta fuga de `ndb` nunca se había cubierto. Fix: el tracker pasa a `db` en los tres puntos que lo leen o escriben (golpe directo, ataque de mascota, lectura al morir el jefe) y en su inicialización al spawnear el jefe. 1 test de regresión nuevo en `tests/test_handler.py`; los 2 tests existentes que comprobaban `ndb` en `tests/test_mascotas.py` se actualizaron a `db`.

## [0.71.17] — 2026-08-29

### Corregido
- `TradeSession.ofrecer_objeto()` (`features/trade/trade_session.py`) solo comprobaba `obj.location == jugador` para validar que un objeto ofrecido estuviera en el inventario — pero equipar un objeto no cambia su `location`, así que un arma o armadura equipada pasaba esa comprobación igualmente. A diferencia de banco, mercado, subastas y crafteo (que excluyen explícitamente los objetos equipados vía `_get_equipamiento()`), el intercambio no tenía esa protección: ofrecer y transferir un objeto equipado lo movía de verdad al otro jugador al ejecutarse el intercambio, pero el `equipamiento` de quien lo dio nunca se actualizaba — sus bonuses de stats seguían aplicados permanentemente, y si el receptor también lo equipaba, el bonus quedaba duplicado entre dos personajes. Encontrado auditando intercambio. Fix: `ofrecer_objeto()` rechaza ahora ofrecer un objeto que esté actualmente equipado, mismo criterio que el resto de sistemas económicos del proyecto. 2 tests de regresión nuevos en `tests/test_intercambio.py`.

## [0.71.16] — 2026-08-29

### Corregido
- `casa`/`hogar` y `visitar <jugador>` (`features/housing/commands.py`) no comprobaban `en_combate`, a diferencia de `viajar` (viaje rápido, v0.66.0), que sí lo hace. Cualquier jugador con vivienda propia (500 monedas, pago único, muy accesible) podía teletransportarse a un lugar seguro de forma instantánea, gratuita y con éxito garantizado durante cualquier combate contra un NPC — sin pasar por el 50% de fallo real de `huir`, dejando el hueco del combate colgado (se auto-pasa por el timeout de turno de 15s en vez de resolverse limpiamente) en lugar de escapar de verdad. Encontrado auditando vivienda. Fix: `casa` y `visitar` bloquean ahora la teletransporte mientras `en_combate` es verdadero, mismo criterio que `viajar`. 2 tests de regresión nuevos en `tests/test_vivienda.py`.

## [0.71.15] — 2026-08-29

### Corregido
- `buscar_receta()` (`systems/crafting/recipes.py`) resolvía en silencio una coincidencia ambigua por prefijo eligiendo la receta de nombre más corto, en vez de avisar de la ambigüedad. Varias familias de recetas comparten prefijo (`"elixir"` coincide con "elixir arcano", "elixir de restauración", "elixir sombrío" y "elixir de esencia"; `"antí"` con las tres recetas de antídoto; `"tónico"` con las tres de tónico) — `craftear elixir` consumía siempre los ingredientes de "elixir arcano" (la más corta), sin importar cuál de las cuatro quisiera el jugador ni avisar de que había otras, y sin ningún error que delatara que se había craftado algo distinto de lo esperado. Encontrado auditando crafteo/encantamiento. Fix: una coincidencia ambigua por prefijo se trata ahora como no encontrada, igual que ya hace `buscar_destino()` en viaje rápido — el jugador ve "no existe receta" y puede escribir el nombre completo en vez de recibir un resultado adivinado. 3 tests de regresión nuevos en `tests/test_crafteo_equipo_system.py`.

## [0.71.14] — 2026-08-29

### Corregido
- `recompensa cancelar` (`features/bounty/commands.py`) no comprobaba si el objetivo estaba, en ese mismo instante, en un combate de caza de recompensa activo. `cazar <jugador>` solo lee y consume el total de recompensas al FINAL del combate (`_fin_duelo()` → `cobrar_recompensa_por_duelo()`), nunca al empezarlo — así que el emisor podía ver, por los mensajes de la sala, que su objetivo estaba perdiendo el duelo de caza y cancelar su recompensa a mitad de combate para no pagarla. El cazador ganaba limpiamente pero cobraba menos del premio anunciado al aceptar la caza, o nada en absoluto si era la única recompensa activa sobre el objetivo — sin ningún aviso de por qué. Encontrado auditando cazarrecompensas, el único sistema del catálogo sin ningún test de integración previo (`tests/test_bounty_system.py` solo cubría la lógica pura). Fix: `recompensa cancelar` comprueba ahora si hay un combate `es_caza_recompensa` activo contra el objetivo y, de ser así, rechaza la cancelación hasta que termine. 3 tests de integración nuevos en `tests/test_bounty.py` (primer test de integración de este sistema).

## [0.71.13] — 2026-08-29

### Corregido
- `TorneoScript._siguiente_combate()` (`features/arena/tournament_script.py`) solo comprobaba `has_account` (vía `_resolver_jugador()`) antes de teleportar a los dos jugadores del próximo emparejamiento a la Arena e iniciar un `CombatHandler` nuevo en `modo_duelo` — nunca comprobaba si alguno de los dos ya estaba en OTRO combate en curso (p. ej. peleando contra un monstruo mientras esperaba su turno de bracket, algo perfectamente normal durante la inscripción o entre rondas). Arrastrarlo a la fuerza dejaba su combate anterior con un participante fantasma (su turno se auto-pasa por el timeout de turno, pero el handler nunca lo elimina) y, al terminar el duelo de torneo, `_fin_duelo()` ponía `en_combate=False` para ambos duelistas — desincronizando ese flag del handler anterior, que seguía activo y listándolo como participante: a partir de ahí el jugador podía usar `retar`/`viajar`/comandos de gremio como si no estuviera en combate, aunque su primer combate siguiera vivo. Encontrado auditando torneos de arena. Fix: `_siguiente_combate()` comprueba ahora `en_combate` en ambos jugadores antes de teleportarlos; si alguno sigue ocupado, reintenta en 5s en vez de arrastrarlo, mismo patrón ya usado para esperar a que la sala Arena quede libre. 1 test de regresión nuevo en `tests/test_arena.py`.

## [0.71.12] — 2026-08-29

### Corregido
- Las expediciones grupales (`features/expeditions/expedition_script.py`) estaban completamente rotas desde su implementación, por tres bugs independientes que se enmascaraban entre sí:
  - `_recompensar_oleada()` y `_completar()` llamaban a `procesar_subida_de_nivel(nivel, experiencia)` con dos argumentos posicionales y trataban el resultado como un dict con claves `"subio"`/`"nuevo_nivel"`/`"nuevo_hp_max"`. La función real (`systems/combat/engine.py`, ya usada correctamente en `combat/handler.py`, `quests` y `contracts`) solo acepta un dict de stats y devuelve una tupla `(bool, dict)` con clave `"nivel"` sin prefijo. El resultado era un `TypeError` sin capturar en cuanto se despejaba la primera oleada de cualquier expedición: `at_repeat()` nunca llegaba a avanzar de oleada ni a completar nada, y el grupo quedaba atascado hasta expirar por el timeout de 30 minutos sin ninguna recompensa. Nunca se detectó porque ningún test anterior hacía avanzar el script más allá de `iniciar()`.
  - Una vez corregido ese `TypeError`, `_recompensar_oleada()` resultó no pagar nunca las monedas de recompensa por oleada — solo sumaba la XP (`calcular_recompensa_oleada()` calcula ambas, pero el bucle solo escribía `m.db.experiencia`).
  - `_completar()` usaba `calcular_recompensa_total()`, que por definición ya es la suma de TODAS las oleadas más el bonus (confirmado por su propio test: "El total = por_oleada × num_oleadas + bonus_completar"). Como `at_repeat()` llama a `_recompensar_oleada()` para toda oleada que se despeja, incluida la última (el jefe), antes de comprobar si procede completar, la recompensa de cada oleada se pagaba dos veces: una vez oleada a oleada y otra de golpe al completar.

  Encontrado auditando expediciones — el único sistema del catálogo donde ningún test previo llegaba a ejecutar `at_repeat()` más allá del arranque. Fix: `calcular_bonus_completar()` nueva (`systems/expeditions/expeditions.py`), que devuelve solo el bonus sin las oleadas; `_completar()` la usa en vez de `calcular_recompensa_total()` (que se conserva sin cambios de comportamiento, para quien quiera el total informativo). `_recompensar_oleada()` ahora paga también las monedas y llama a `procesar_subida_de_nivel()` con la firma real, igual que el resto del proyecto. 4 tests de regresión nuevos (2 en `tests/test_expeditions.py`, 2 en `tests/test_expeditions_system.py`).

## [0.71.11] — 2026-08-29

### Corregido
- `CombatHandler.agregar_participante()` (`features/combat/handler.py`) fusionaba a cualquier tercero en el `CombatHandler` ya activo de la sala sin comprobar nunca si ese combate era un duelo PvP (`modo_duelo=True`). Los duelos no aíslan la sala de nada: un NPC agresivo que reacciona (`_agredir()`, `typeclasses/npc.py`) a un tercer jugador que simplemente entra mientras otros dos están duelando metía tanto al NPC como al recién llegado en el mismo handler que el duelo 1v1 en curso. Como `_fin_duelo()` se dispara para el primer participante que baje al 10 % de HP sea quien sea, si esa pelea ajena (NPC vs. recién llegado) terminaba antes que el duelo original, el duelo se cerraba de golpe sin resolverse: sin ganador ni perdedor registrado, y con la apuesta de los dos duelistas originales "fantasma" fija para siempre — el mismo bug de fondo que v0.71.2 (apuesta que se cobra de verdad en el siguiente duelo sin apuesta explícita), pero por una vía que ese fix no cubría, ya que aquí el handler nunca pasa por `eliminar_participante()`. `_iniciar_combate()` (`features/combat/commands.py`) tenía la misma fusión sin comprobar, aunque en la práctica sus dos únicos puntos de llamada ya descartan un handler existente antes de entrar en esa rama. Encontrado auditando duelos. Fix: `agregar_participante()` devuelve ahora `False` sin añadir nada cuando el combate está en `modo_duelo`; ambos puntos de llamada lo comprueban y desisten de fusionar en ese caso (el NPC simplemente no agrede, `_iniciar_combate()` avisa de que hay un duelo privado en curso). 2 tests de regresión nuevos en `tests/test_duelos.py`.

## [0.71.10] — 2026-08-29

### Corregido
- `GuildScript.disolver()` (`features/guilds/guild_script.py`) borraba el gremio sin avisar a `GuildWarScript`. Las guerras y retos de gremios (`features/guild_wars/`) referencian a cada bando por su nombre (string), no por el `GuildScript` en sí — así que en cuanto un gremio en guerra se disolvía, su nombre quedaba libre para que cualquiera fundara un gremio nuevo con él (`obtener_gremio_por_nombre()` ya no encontraba colisión), y ese gremio recién fundado heredaba, sin haberla declarado ni aceptado, cualquier guerra o reto pendiente que siguiera referenciando ese nombre en `self.db.guerras`/`self.db.retos`. Confirmado con un gremio disuelto en plena guerra y refundado al instante con el mismo nombre: las bajas del bando rival empezaban a contar para el "nuevo" gremio de inmediato. Encontrado auditando el sistema de gremios. Fix: `GuildWarScript.cancelar_por_disolucion(nombre)`, llamado desde `disolver()` antes de borrar el script, limpia cualquier reto (saliente o entrante) y cierra cualquier guerra activa de ese nombre, declarando ganador al rival igual que `rendirse()`. 1 test de regresión nuevo en `tests/test_guild_wars.py`.

## [0.71.9] — 2026-08-29

### Corregido
- `CmdRetirar` (`features/bank/commands.py`) dejaba objetos del banco personal permanentemente atrapados en cuanto había dos con el nombre exacto idéntico (p. ej. dos pociones de vida iguales). El matching por nombre solo tomaba la coincidencia exacta cuando había exactamente una (`len(exactas) == 1`); con dos o más caía al fallback de coincidencia parcial, que también encontraba las mismas dos (un nombre exacto siempre es substring de sí mismo) y las reportaba como ambiguas pidiendo "sé más específico" — imposible cuando ambos nombres son idénticos carácter a carácter. `retirar <nombre>` repetía el mismo resultado ambiguo indefinidamente: ninguna de las dos copias podía volver a salir del banco jamás. Encontrado auditando el banco. Fix: cualquier coincidencia exacta (una o varias) se acepta directamente, tomando la primera; el fallback ambiguo queda solo para cuando no hay ninguna coincidencia exacta. 1 test de regresión nuevo en `tests/test_bank.py`.

## [0.71.8] — 2026-08-29

### Corregido
- `AuctionScript.pujar()` (`features/auctions/auction_script.py`) no comprobaba `subasta_expirada()` antes de aceptar una puja — solo lo hacía el tick automático de `at_repeat()` (cada 60s). Cualquier subasta que ya hubiera superado sus 30 minutos pero cuyo cierre automático aún no hubiera corrido (ventana de hasta 59s en cada subasta, siempre presente) seguía aceptando pujas ganadoras con normalidad, a diferencia de retos de duelo y propuestas de matrimonio, que sí comprueban su expiración de forma perezosa (`reto_expirado()`/`propuesta_expirada()`) en el propio comando además del cierre periódico. Encontrado auditando subastas (v0.68.0, nunca revisada desde su implementación — el único sistema restante sin ronda propia, tras viaje rápido v0.66.0 en v0.71.7 y cartelera v0.67.0 en v0.71.6). Fix: `pujar()` comprueba ahora `subasta_expirada()` igual que los demás sistemas de reto/propuesta con expiración, antes de aceptar cualquier puja. 1 test de regresión nuevo en `tests/test_auctions.py`.

## [0.71.7] — 2026-08-29

### Corregido
- `MazmorraScript._completar()` (`features/dungeons/dungeon_script.py`) repartía XP, monedas y el registro de mazmorra completada a todo `db.jugadores` sin comprobar si cada uno seguía físicamente dentro de la instancia. Esa lista solo se depura en `salir()` (comando `mazmorra salir`) — cualquier otra forma de abandonar la mazmorra es un `move_to()` plano que nunca la toca, y `viajar` (viaje rápido, v0.66.0, la única forma de teleportarse fuera de una sala explorada sin restricción de ubicación) no comprueba en ningún momento si el personaje está dentro de una mazmorra activa. Resultado: un jugador podía entrar en grupo, huir con `viajar` justo antes de la sala del jefe y seguir cobrando recompensa completa cuando el resto del grupo terminaba — exactamente el caso que el propio comentario de `salir()` ("ya no cuenta como miembro activo") daba por cubierto, pero solo lo estaba para quien usaba ese comando. Mismo problema, en sentido inverso, en el timeout de `at_repeat()`: al expirar la instancia, se buscaba y teleportaba de vuelta al vestíbulo a todo `db.jugadores` sin comprobar presencia, así que alguien que ya se había ido por su cuenta con `viajar` era arrancado de golpe de dondequiera que estuviese (mercado, gremio, otra mazmorra) para "expulsarlo" de una instancia que ya había abandonado hacía rato. Encontrado auditando viaje rápido (v0.66.0, nunca revisado desde su implementación junto con subastas v0.68.0, el único sistema restante sin ronda propia). Fix: ambos puntos filtran ahora por `_jugadores_dentro()` (ya usado por `salir()` para decidir si limpiar la instancia), que comprueba la ubicación real en vez de fiarse de `db.jugadores`. 1 test de regresión nuevo en `tests/test_mazmorras.py`.

## [0.71.6] — 2026-08-13

### Corregido
- `crear_anuncio()` (`systems/bulletin/bulletin.py`) generaba el `id` de cada anuncio de la cartelera (`cartelera`, v0.67.0) como `f"{int(timestamp)}_{autor_dbref}"`. `cartelera publicar` no tiene ningún cooldown, a diferencia de la mayoría de sistemas del proyecto — así que dos anuncios del mismo autor publicados dentro del mismo segundo (fácil con un cliente rápido o dos comandos pegados) recibían el mismo id. `retirar()` borra por igualdad de id con un filtro de lista (`[a for a in vigentes if a["id"] != anuncio_id]`), así que retirar cualquiera de los dos anuncios colisionados borraba **ambos** de golpe, sin avisar. El único test de unicidad existente (`test_crear_anuncio_id_unico_por_autor_y_momento`) solo comprobaba autores distintos, nunca el mismo autor en el mismo segundo — el hueco real nunca se testeó. Encontrado en la primera ronda de auditoría independiente de la cartelera (nunca revisada tras su implementación, junto con viaje rápido v0.66.0 y subastas v0.68.0, los tres únicos sistemas sin ronda propia). Fix: `BulletinScript.db.next_id`, contador monotónico igual que `MarketScript`/`AuctionScript`; `crear_anuncio()` ya no deriva el id del reloj, lo recibe de quien llama. 1 test de regresión nuevo en `tests/test_bulletin.py`.

## [0.71.5] — 2026-08-09

### Corregido
- `CmdPromover` (`features/guilds/commands.py`) transfería el liderazgo de gremio (`guild.cambiar_rango(objetivo, RANGO_LIDER)`) sin llamar nunca a `comprobar_y_notificar()` para el nuevo Líder. Los logros "Líder Unificador"/"Comandante" dependen de `es_lider_gremio AND miembros_gremio>=5/20` — si el gremio ya tenía suficientes miembros en el momento de la transferencia, el logro no se notificaba en ese instante (a diferencia del bug de logros de Desafíos Diarios de v0.71.4, este se autorreparaba en la siguiente acción cualquiera del nuevo líder que sí disparara el chequeo, así que el impacto era solo una notificación retrasada, no un logro perdido para siempre). Fix: `comprobar_y_notificar(objetivo)` tras la transferencia de liderazgo. 1 test de regresión nuevo en `tests/test_gremios.py`.

## [0.71.4] — 2026-08-09

### Corregido
- `comprobar_y_notificar()` (chequeo de logros) solo se llamaba desde `_completar_todos()` en `features/daily/daily_script.py` — es decir, únicamente cuando un jugador completaba los 5 desafíos diarios el mismo día. Los logros "Primer Desafío" (`total_desafios_completados >= 1`) y "Veterano de Desafíos" (`>= 25`) dependen de ese contador, que sube tras cada desafío individual completado, no solo al llegar a 5/5 — un jugador que nunca completaba los 5 el mismo día (p. ej. hace 1-4 al día de forma habitual) no recibía nunca estos logros, por muchos desafíos que acumulara. Confirmado empíricamente: tras completar 1 solo desafío, `total_desafios_completados=1` pero `"primer_desafio"` nunca entraba en `db.logros`. Fix: `comprobar_y_notificar()` se llama ahora al final de `notificar_progreso()` tras cualquier desafío recién completado (no solo al llegar a 5/5); al ser idempotente, el camino de 5/5 ya existente no cambia de comportamiento. 3 tests de regresión nuevos en `tests/test_daily.py`.

## [0.71.3] — 2026-08-09

### Corregido
- `RelojMundial` (`features/time/clock_script.py`) y `ClimaScript` (`features/weather/weather_script.py`) fijaban `self.interval` sin `self.start_delay = True` — el mismo patrón ya corregido 4 veces antes en este proyecto (mazmorras, torneos, intercambio, ticks de estado de combate). Evennia dispara `at_repeat()` de inmediato al crear el script en vez de esperar el intervalo, así que la primerísima creación de estos scripts (el arranque original del mundo, o cualquier entorno de desarrollo/test nuevo) adelantaba la hora de 8 a 9 y rifaba un cambio de clima en el instante de creación, no tras 60s/600s como se espera. Sin efecto observable en la partida ya en marcha, dado que los reinicios/reloads posteriores respetan el tiempo restante real vía el mecanismo de pausa/reanudación de Evennia — se corrige igualmente por consistencia con el resto del código. Fix: `self.start_delay = True` en ambos scripts. 3 tests de regresión nuevos (`tests/test_time.py`, `tests/test_weather.py`).

## [0.71.2] — 2026-08-09

### Corregido
- `CombatHandler.eliminar_participante()` (`features/combat/handler.py`) no limpiaba `apuesta_duelo` del participante que huía de un duelo con apuesta — solo `_terminar_combate()` limpiaba la de quien se quedaba en `db.participantes`, y el que huyó ya no estaba en esa lista. La apuesta "fantasma" quedaba pegada al personaje y se cobraba de verdad en su siguiente combate en modo duelo sin apuesta explícita (una caza de recompensa con `cazar`, o un combate de torneo de arena), transfiriendo monedas que nadie había apostado. Fix: `eliminar_participante()` limpia ahora `apuesta_duelo` de cualquier participante eliminado mientras el combate esté en modo duelo, cubriendo huida y cualquier otra baja fuera de la resolución de muerte (que ya limpiaba correctamente ambos lados vía `_fin_duelo`). 2 tests de regresión nuevos en `tests/test_duelos.py`.

## [0.71.1] — 2026-08-07

### Corregido
- El reinicio diario de Desafíos (`features/daily/daily_script.py`, `features/daily/commands.py`) calculaba la fecha del día con `date.today()`, que devuelve la fecha de la zona horaria **local del sistema operativo** del servidor — el ajuste `TIME_ZONE = "UTC"` de Django no tiene ningún efecto sobre `datetime`/`date` de la librería estándar, solo sobre `django.utils.timezone.now()` y los campos de fecha del ORM. La ayuda de `desafios` promete explícitamente "Los desafíos se renuevan cada día a medianoche (UTC)"; con el servidor en cualquier zona horaria distinta de UTC (confirmado con el propio entorno de este proyecto, `Europe/Madrid`), el reinicio diario ocurría 1-2 horas antes o después de la medianoche UTC prometida, y ese desfase cambiaría de nuevo si el servidor se desplegara alguna vez en otra zona horaria. Fix: `_hoy()`/`_ayer()` ahora calculan la fecha con `datetime.now(timezone.utc).date()` en vez de `date.today()`. 7 tests de regresión nuevos en `tests/test_daily.py`.

## [0.71.0] — 2026-08-06

### Corregido
- `CombatHandler.eliminar_participante()` (`features/combat/handler.py`) reindexaba `turno_actual` con un simple clamp de desbordamiento tras quitar a un participante (muerte, captura o huida), pero cada punto de llamada (`_procesar_muerte()`, `_intentar_captura()`) volvía a sumar un paso más con `_siguiente_turno()` sin comprobar si ese clamp ya había dejado el índice apuntando al siguiente participante correcto. Cuando el eliminado estaba ANTES del actor en la lista de participantes (p. ej. un jugador de un grupo remata a un enemigo que no era el primero en unirse al combate) — o era el propio actor, como una muerte por tick de veneno/sangrado en su propio turno — la suma extra saltaba por completo el turno de quien le seguía, dándole dos turnos seguidos al mismo participante. Por separado, `_intentar_huida()` nunca llamaba a `_siguiente_turno()`/`_anunciar_turno()` tras una huida exitosa, así que el siguiente turno no se anunciaba (sin mensaje al jugador ni IA del NPC programada) hasta que lo rescataba el timeout automático de turno (hasta 15s de combate aparentemente congelado). Ambos solo son observables en combates de 3 o más participantes (grupos, oleadas, un segundo jugador uniéndose a un combate activo) — con 2 participantes la eliminación siempre termina el combate antes de que el salto sea visible. Fix: `_avanzar_turno_tras_baja()`, un helper único que recalcula siempre a partir de la posición real del actor de referencia tras el hueco, usado por los tres puntos de eliminación. 4 tests de regresión nuevos en `tests/test_handler.py`.

## [0.70.4] — 2026-08-05

### Corregido
- `CombatHandler._procesar_muerte()` (`features/combat/handler.py`) trataba una muerte por tick de estado (veneno/sangrado) durante un duelo como una muerte normal de jugador (te manda a tu sala de inicio con 1 HP), en vez de cerrar el duelo. El único fallback pensado para este caso (el comentario decía explícitamente "si un tick de estado mata a alguien durante un duelo") exigía un `asesino`, pero `_aplicar_ticks_estado()` llama a `_procesar_muerte()` sin ese argumento porque el daño no viene de un golpe con atacante — el fallback nunca se ejecutaba en la práctica. Consecuencias: el duelo mataba de verdad a un jugador pese a que el sistema garantiza que se detiene al 10 % de HP, la apuesta se perdía en vez de transferirse al ganador, `duelos_ganados`/`duelos_perdidos` no se actualizaban, y si era un combate de torneo o de caza de recompensa (`cazar`), ni el torneo avanzaba (quedaba colgado hasta cancelarse solo por timeout, devolviendo las inscripciones de todos) ni se cobraba la recompensa. Ahora, si `asesino` viene vacío pero el combate es un duelo, se resuelve como ganador al otro participante del duelo antes de decidir la rama a seguir. 2 tests de regresión nuevos en `tests/test_combat_states.py`.

## [0.70.3] — 2026-08-04

### Corregido
- `_limpiar_duelo()` (`features/duels/commands.py`) borraba a la vez el slot de reto saliente (`db.duelo_pendiente`) y el entrante (`db.duelo_retador_dbref`/`db.duelo_apuesta_pendiente`) de un jugador, aunque son independientes: un jugador puede tener a la vez un reto que él mismo lanzó y otro que le hicieron (nada en `CmdRetar` lo impide). Si A retaba a B y, por separado, C retaba a A, resolver el reto de C (aceptar o rechazar) borraba también, sin avisar, el reto saliente de A hacia B — B veía luego "el reto ya ha expirado" en vez del motivo real. Mismo bug exacto ya corregido en matrimonio (v0.70.1) y guerra de gremios (v0.70.2); duelos es el sistema más antiguo de los tres (v0.21.0) y probablemente el origen del patrón. Dividida en `_limpiar_duelo_saliente()` / `_limpiar_duelo_entrante()`; cada punto de resolución limpia solo el slot que corresponde. 2 tests de regresión nuevos en `tests/test_duelos.py`.

## [0.70.2] — 2026-08-03

### Corregido
- `GuildWarScript.declarar()` (`features/guild_wars/guild_war_script.py`) no comprobaba si alguno de los dos gremios ya participaba en otro reto de guerra pendiente (ni como retado ni como retador) antes de crear uno nuevo. Como `db.retos` se indexa por gremio retado, declarar la guerra a un gremio que ya tenía un reto entrante de un tercero sobrescribía ese reto en silencio, sin avisar al retador original; y nada impedía que un mismo gremio acumulara varios retos salientes o entrantes a la vez, lo que podía dejarlo en dos guerras activas simultáneas en cuanto ambos retos se aceptaran (la guerra "invisible" seguía contando bajas y cerrándose sola, pero `guerra`/`guerra rendirse` solo veían la primera que encontraba `guerra_de()`). Añadido `_ocupado_en_retos()`: ningún gremio puede tener más de un reto pendiente a la vez, en ningún rol. Además, `aceptar()` revalida en el momento de aceptar que el retador siga libre de guerra (red de seguridad ante condiciones de carrera, mismo patrón que la revalidación de estado civil en `aceptar boda` del sistema de matrimonio). 4 tests de regresión nuevos en `tests/test_guild_wars.py`.

## [0.70.1] — 2026-08-03

### Corregido
- `_limpiar_propuesta()` (`features/marriage/commands.py`) borraba a la vez el slot de propuesta saliente (`db.propuesta_matrimonio_pendiente`) y el entrante (`db.propuesta_matrimonio_proponente_dbref`) de un personaje, aunque son independientes: un personaje puede tener a la vez una propuesta que él mismo lanzó a alguien y otra que le hicieron. Si A proponía a B y, por separado, C proponía a A, al resolver A la propuesta de C (aceptar o rechazar) se borraba también, sin avisar, la propuesta saliente de A hacia B — B veía luego "la propuesta ya ha expirado" en vez del motivo real. Dividida en `_limpiar_propuesta_saliente()` / `_limpiar_propuesta_entrante()`; cada punto de resolución limpia solo el slot que corresponde.

## [0.70.0] — 2026-08-02

Nueva feature de juego: matrimonio entre jugadores.

### Añadido
- `proponer <jugador>` — propone matrimonio a otro jugador (120 segundos para responder). Ninguno de los dos puede estar ya casado ni tener otra propuesta pendiente (propia o entrante).
- `aceptar boda` / `rechazar boda` — el destinatario responde a la propuesta pendiente.
- `divorciarse` — termina el matrimonio actual de inmediato, sin requerir presencia ni acuerdo del cónyuge.
- `casado` — muestra tu estado civil (soltero/a, o cónyuge y fecha de la boda).
- Notificación al cónyuge cuando el otro se conecta o desconecta (mismo mecanismo que la lista de amigos: itera sesiones reales vía `SESSION_HANDLER`, sin depender de `sessions.count()` sobre el objeto resuelto).
- Vínculo 1-a-1, sin coste ni mecánica económica asociada: puramente social, siguiendo el patrón de reto/aceptar/rechazar ya usado en duelos y guerra de gremios.
- Lógica pura en `systems/marriage/marriage.py`, integración sin script (estado guardado directamente en `db.conyuge_dbref`/`db.fecha_boda`/propuestas pendientes de cada personaje, expiración comprobada de forma perezosa como en duelos), comandos en `features/marriage/commands.py`, registrado en `CharacterCmdSet`.

## [0.69.0] — 2026-08-01

Nueva feature de juego: guerra de gremios.

### Añadido
- `guerra` — ver el estado de la guerra activa de tu gremio, o el reto pendiente si lo hay.
- `guerra declarar <gremio>` — el Líder declara la guerra a otro gremio (reto con 5 minutos para responder).
- `guerra aceptar` / `guerra rechazar` — el Líder del gremio retado responde al reto.
- `guerra rendirse` — el Líder concede la guerra activa; el rival gana de inmediato.
- El PvP en sí ya era libre en todo momento (`atacar <jugador>` ya inicia combate real entre jugadores, `features/combat/handler.py`); la guerra no habilita nada nuevo en el combate, solo cuenta las bajas entre los dos gremios enfrentados durante 1 hora y anuncia un ganador (o empate) al cierre automático.
- Gancho en `CombatHandler._procesar_muerte()`: cuando muere un jugador con `db.gremio` a manos de otro jugador con `db.gremio`, si ambos gremios están en guerra entre sí se anota la baja y se notifica a ambos rosters.
- Lógica pura en `systems/guild_wars/guild_wars.py`, script global persistente en `features/guild_wars/guild_war_script.py` (patrón `obtener_guerra_script()`, tick cada 60s para cerrar guerras expiradas, arrancado en `server/conf/at_server_startstop.py`), comandos en `features/guild_wars/commands.py`, registrado en `CharacterCmdSet`.

## [0.68.0] — 2026-08-01

Nueva feature de juego: casa de subastas global.

### Añadido
- `subasta` — ver todas las subastas activas (objeto, mejor puja, mejor postor, tiempo restante).
- `subasta publicar <objeto> <precio>` — pone un objeto a subasta con precio de salida. Duración fija de 30 minutos, hasta 3 subastas activas por jugador.
- `subasta pujar <#> <monto>` — puja por una subasta; la puja mínima es un 5% por encima de la actual. Las monedas quedan retenidas hasta que te superen (reembolso automático) o cierre la subasta.
- `subasta retirar <#>` — retira tu subasta, solo si nadie ha pujado todavía.
- Cierre automático (tick cada 60s, `AuctionScript.at_repeat()`): con puja, el objeto pasa al mejor postor y el vendedor cobra el precio final menos una comisión del 5%; sin puja, el objeto vuelve al vendedor.
- Distinta del mercado (`mercado`, precio fijo, compra inmediata): aquí se compite al alza durante un tiempo límite.
- Lógica pura en `systems/auctions/auctions.py`, script global persistente en `features/auctions/auction_script.py` (patrón `obtener_subastas_script()`, arrancado en `server/conf/at_server_startstop.py`), comandos en `features/auctions/commands.py`, registrado en `CharacterCmdSet`.

## [0.67.0] — 2026-07-31

Nueva feature de juego: cartelera de anuncios global.

### Añadido
- `cartelera` — ver los anuncios vigentes de la ciudad, ordenados del más reciente al más antiguo.
- `cartelera publicar <texto>` — publica un anuncio corto (máximo 200 caracteres). Expira a los 3 días. Tablón con capacidad máxima de 15 anuncios vigentes.
- `cartelera retirar <#>` — retira tu propio anuncio (solo el autor puede hacerlo).
- Distinta del tablón de contratos (comando `tablón`, misiones generadas por el servidor): esta es una cartelera libre donde cualquier jugador publica mensajes de texto (ventas, avisos de gremio, mensajes generales) — de ahí el nombre de comando `cartelera` para evitar la colisión con `tablón`/`tablon`/`board`.
- Lógica pura en `systems/bulletin/bulletin.py`, script global persistente en `features/bulletin/bulletin_script.py` (patrón `obtener_cartelera_script()`, arrancado en `server/conf/at_server_startstop.py`), comandos en `features/bulletin/commands.py`, registrado en `CharacterCmdSet`.

## [0.66.0] — 2026-07-31

Nueva feature de juego: viaje rápido entre zonas ya exploradas.

### Añadido
- `viajar` — lista tus destinos de viaje rápido disponibles (zonas del catálogo de cartografía cuyo dbref ya esté en `db.salas_exploradas`), agrupados por área.
- `viajar <destino>` — teletransporta al jugador a un destino ya explorado, buscando por nombre de sala (exacto o coincidencia parcial única). Cuesta 20 monedas y tiene un cooldown de 30s entre viajes (`char.ndb`, no persistente); bloqueado mientras `db.en_combate` esté activo.
- Lógica pura en `systems/fast_travel/fast_travel.py` (catálogo de destinos, búsqueda, validaciones de coste/cooldown, formateo), integración Evennia en `features/fast_travel/commands.py`, registrado en `CharacterCmdSet`. Reutiliza el catálogo `ZONAS_INFO` y el helper `_zonas_a_dbref()` ya existentes del sistema de cartografía en vez de duplicar el mapeo zona→sala.

## [0.65.0] — 2026-07-31

Nueva feature de juego: sistema de lista de amigos.

### Añadido
- `agregar amigo <jugador>` / `quitar amigo <jugador>` — gestionan tu lista de amigos (`db.amigos`, dbrefs). Relación unidireccional (lista de contactos, sin invitación ni aceptación de la otra parte), con un tope de 30.
- `amigos` — muestra tu lista con estado en línea/desconectado en tiempo real.
- Notificación a tus amigos conectados cuando entrás o salís del juego, reutilizando `at_post_puppet`/`at_post_unpuppet` (`typeclasses/characters.py`) y el mismo patrón de `SESSION_HANDLER.get_sessions()` que ya usan los scripts globales de reloj/clima/eventos para sus anuncios — sin escanear la tabla completa de personajes.
- Lógica pura en `systems/friends/friends.py`, integración Evennia en `features/friends/commands.py`, registrado en `CharacterCmdSet`.

## [0.64.0] — 2026-07-31

Continuación de la ronda de rendimiento: el candidato acotado al turno de combate que había quedado pendiente tras revertir la caché entre llamadas de la v0.63.0.

### Corregido
- `CombatHandler._resolver_turno()` (`features/combat/handler.py`) llamaba `_get_stats()` dos veces por turno (atacante y objetivo), y cada llamada resolvía por separado el evento mundial activo (`obtener_evento_activo()`, una consulta a la base de datos) si el participante tenía cuenta de jugador — hasta 2 queries redundantes por turno en cualquier combate con dos jugadores. `_get_stats()` ahora acepta el evento ya resuelto como parámetro opcional (con un valor centinela por defecto que preserva el comportamiento anterior para el resto de llamadores, que no cambian); `_resolver_turno()` lo resuelve una sola vez por turno y lo pasa a ambas llamadas. A diferencia del intento de la v0.63.0, esta caché no persiste entre llamadas ni turnos — se acota a una sola resolución de turno, así que no tiene el riesgo de "staleness" entre tests que rompió la caché a nivel de módulo.

## [0.63.0] — 2026-07-30

Ronda de rendimiento: se propusieron candidatos de rendimiento (no bugs de comportamiento) y se corrigió el único que resultó seguro de aplicar tras verificación empírica contra la suite de tests.

### Corregido
- `hora_actual()`/`obtener_reloj()` (`features/time/clock_script.py`), `clima_actual()`/`obtener_clima_script()` (`features/weather/weather_script.py`) y `obtener_evento_activo()`/`obtener_evento_script()`/`tiempo_restante_evento()` (`features/events/event_script.py`) hacían `ScriptDB.objects.filter(db_key=...).exists()` seguido de `.first()` — dos consultas a la base de datos para resolver el mismo script singleton. Reducido a una sola consulta (`.first()` y comprobación de `None`). `hora_actual()`/`clima_actual()` se llaman en `Room.return_appearance()` (`typeclasses/rooms.py`), invocado en cada movimiento de cualquier jugador entre salas; `obtener_evento_activo()` se llama hasta dos veces por turno en cada combate activo del servidor (`CombatHandler._get_stats()`). Se evaluó además cachear la referencia al script entre llamadas para eliminar la consulta por completo, pero se descartó tras romper la suite real (5 failures + 31 errors, incluido un `IntegrityError` de SQLite): varios tests de `test_time.py`/`test_weather.py`/`test_eventos.py` borran o mutan el script directamente y esperan que las funciones de acceso reflejen el cambio de inmediato, y el rollback transaccional de `EvenniaTest` no dispara señales `post_delete` que pudieran invalidar una caché de ese tipo.

## [0.62.0] — 2026-07-30

Décima ronda de revisión: `_intentar_captura()` elegía siempre el primer NPC del combate como objetivo, sin comprobar si de verdad estaba debilitado — fallaba en cualquier combate con más de un NPC.

### Corregido
- `CombatHandler._intentar_captura()` (`features/combat/handler.py`) seleccionaba siempre el primer NPC de `participantes` como objetivo de captura, sin comprobar su HP. En un combate con más de un NPC (grupo, oleada de mazmorra/expedición, o un segundo jugador que se une a un combate ya activo atacando a otro NPC), si ese primer NPC no estaba debilitado pero sí lo estaba otro NPC del mismo combate, el jugador recibía "aún tiene X% de HP" sobre el NPC equivocado y no podía capturar al que sí cumplía el umbral (≤20% HP). Ahora se busca el primer NPC que realmente cumpla el umbral de captura; si ninguno lo cumple, se conserva el comportamiento anterior (informar sobre el primero de la lista).

## [0.61.0] — 2026-07-28

Novena ronda de revisión: autorrevisión del propio fix de la ronda anterior (`_limpiar_actividad_huerfana()`, v0.58.0) en vez de código antiguo nunca tocado — 3 bugs reales, dos de ellos solo visibles al escribir un test que forzara de verdad la ruta de fallo.

### Corregido
- `_limpiar_actividad_huerfana()` (`server/conf/at_server_startstop.py`, añadida en la limpieza de actividad huérfana tras reinicio) envolvía el bucle entero de cada tipo de script (combates/torneos/expediciones huérfanos) en un único try/except, en vez del patrón ya establecido de un try/except por elemento (como los 9 scripts globales de más arriba en el mismo archivo). Si `_terminar_combate()`/`_cancelar()`/`_limpiar()` fallaba para UN script huérfano, la excepción abortaba la limpieza de todos los demás del mismo tipo — justo el bug de "actividad congelada para siempre" que este mecanismo existe para prevenir, disparado por otra vía. Ahora cada script se limpia en su propio try/except.
- Ese mismo bloque `except` llamaba a `logger.log_trace(...)` sin importar `logger` en el ámbito de la función — cualquier fallo real habría producido un `NameError` en vez de loguearse y continuar, propagando la excepción hacia arriba. Añadido el import que faltaba.
- `CombatHandler._terminar_combate()` (`features/combat/handler.py`) llamaba `sala.msg_contents(...)` sin comprobar antes si `self.obj` (la sala) seguía existiendo — si la sala fue borrada, la llamada lanzaba `AttributeError` después de limpiar el estado de los participantes pero antes de que el script se borrara a sí mismo. Ahora comprueba `if sala:` antes de anunciar, igual que el resto de métodos de limpieza del proyecto.

## [0.60.0] — 2026-07-28

Octava ronda de revisión: cross-check exhaustivo de `world/help_entries.py` contra el código real (mismo método que encontró el bug de "cobarde" en la ronda anterior) — solo un hallazgo menor, el resto del archivo coincide exactamente con la implementación.

### Corregido
- `help percibir` (`world/help_entries.py`) documentaba la fórmula de percepción como `Inteligencia + Nivel ÷ 2` sin mencionar que `PerceptionManager.nivel_percepcion()` también aplica una penalización por hora del día (noche/anochecer/amanecer) y por clima (lluvia/tormenta/niebla). Añadida la mención de la penalización a la entrada de ayuda; sin cambios de lógica.

## [0.59.0] — 2026-07-28

Séptima ronda de revisión: IA reactiva de NPC (`_ia_npc`) y conectividad del grafo de salidas del mundo — la segunda salió limpia, sin cambios de código.

### Corregido
- IA de NPC (`_ia_npc`, `features/combat/handler.py`): cualquier NPC entraba en modo `enraged` (furia) al bajar de 50% HP, sin mirar su temperamento. Como `enraged` no se resetea hasta el fin del combate y bloquea la rama de huida (HP < 25%, con condición `not enraged`), un NPC con temperamento `cobarde` que perdiera HP de forma gradual —el caso normal, cruzando primero el 50% y luego el 25%— nunca llegaba a poder huir, pese a que `world/help_entries.py` promete explícitamente "cobarde... puede huir si le atacas". Los NPC `cobarde` ya no entran en modo `enraged`, dejando su rama de huida alcanzable; el resto de temperamentos no cambia de comportamiento.

## [0.58.0] — 2026-07-28

Sexta ronda de revisión: qué ocurre con los scripts `persistent=False` (CombatHandler, TorneoScript, ExpedicionScript) durante un `evennia reload` o reinicio. Confirma un mecanismo más sutil de lo esperado: Evennia no borra la fila del script al reiniciar, solo detiene su temporizador — el script queda "zombie", devuelto como actividad activa pero incapaz de resolverse solo.

### Corregido
- `CombatHandler`, `TorneoScript` y `ExpedicionScript` son `persistent=False`: Evennia para su temporizador incondicionalmente en cada arranque del servidor (reload, cold start o tras una caída) sin borrar la fila de la base de datos, dejando un script "zombie" — sigue siendo devuelto como la actividad activa, pero su timer nunca vuelve a dispararse. Si nadie vuelve a actuar, la actividad queda congelada para siempre: un combate deja `db.en_combate=True` de forma permanente en los jugadores implicados (bloqueando invitar/expulsar de grupo y todos los comandos de duelo), un torneo deja las cuotas de inscripción cobradas sin forma de recuperarlas, y una expedición puede dejar al grupo atrapado en la sala temporal. Se añade una limpieza en el arranque del servidor que resuelve cada actividad huérfana con su propio método de cancelación ya existente (el mismo que se usa para el timeout normal).

## [0.57.0] — 2026-07-27

Quinta ronda de revisión: barrido sistemático de dos patrones de bug ya conocidos (sin código nuevo desde la ronda anterior) — scripts persistentes sin `start_delay` y bloques `except Exception` silenciosos. 73 sitios inspeccionados, 2 hallazgos reales, ambos confirmados en verde en CI.

### Corregido
- `EstadosScript` (efectos de veneno/sangrado/regeneración fuera de combate) fijaba su `interval` sin `start_delay=True`, así que el primer tick se aplicaba de inmediato al terminar el combate en lugar de esperar los 5s esperados — daño o curación un tick antes de lo previsto. Mismo patrón que los bugs de temporizador ya corregidos en mazmorras y arena.
- Eliminado código muerto en `TorneoScript.inscribir()` (`features/arena/tournament_script.py`): un `import` sin usar, un bucle `for ... pass` sin efecto y un `try/except` que importaba `evtable` sin usarlo nunca.

## [0.56.0] — 2026-07-27

Ronda de revisión sobre áreas fuera del código de juego propiamente dicho: dependencias, pipeline de CI, contenido de mundo no cubierto en la ronda anterior, locks/permisos, y temporizadores de scripts (concurrencia). 7 commits, todos confirmados en verde en CI (incluida una regresión propia detectada y revertida en el mismo ciclo).

### Corregido
- **Arena y Torneos PvP**: el timeout de combate (`TIMEOUT_COMBATE`, 5 min) solo se arrancaba una vez al iniciar el torneo y nunca se reiniciaba entre rondas, así que en la práctica era un presupuesto de 5 minutos para *todo* el torneo en vez de "por combate" como indica su nombre — un torneo de varias rondas cuyo tiempo total de combates superase los 5 minutos se cancelaba entero (con devolución de cuotas) aunque los combates fueran avanzando con normalidad. Ahora el timer se reinicia en cada ronda.
- Dos NPCs mago (`APRENDIZ_CORRUPTO`, y el jefe `ARCHIMAGO_VEXTHAR`) tenían `"escudo arcano"` en su lista de habilidades de combate, pero esa habilidad está definida como pasiva (solo otorga +3 defensa al aprenderla) y no tiene ningún efecto en el motor de combate: un 30% de sus turnos de "habilidad especial" resultaban en un ataque normal disfrazado con un texto de habilidad, sin ningún efecto real.
- La documentación de `TradeSession` (intercambio entre jugadores) afirmaba explícitamente "no usa interval/timeout propio", justo lo contrario de lo que hace el código (`interval=120` + `at_repeat` que cancela la sesión). Corregida para reflejar el comportamiento real: un límite fijo de 120s desde la creación, no reiniciable por actividad.
- El pipeline de CI no declaraba permisos explícitos para `GITHUB_TOKEN` ni un límite de tiempo por job; ahora usa `permissions: contents: read` (mínimo privilegio) y `timeout-minutes: 60`.
- Variable muerta en `world/build_expansion.py` (`lagarto = _find_room(...)`, nunca usada) eliminada.

### Nota
- Un intento de fijar versión en `requirements.txt` (`evennia~=5.0.1`) rompió el job de Python 3.12 en CI: esa versión de evennia importa `distutils` sin condición, eliminado de la stdlib en 3.12. Revertido de inmediato a `evennia`/`pytest` sin pin (el estado previo, verificado). Ver detalles en el commit `3fda747`.

## [0.55.0] — 2026-07-24

Continuación de la ronda de revisión de código tras el cierre de v0.54.0: núcleo compartido (`typeclasses/`), contenido y ayuda del juego (`world/`), rendimiento, seguridad, y los hooks restantes de `server/conf/` (confirmados como plantilla intacta, sin cambios). 2 commits de fixes reales, ambos confirmados en verde en CI.

### Corregido
- El efecto de sigilo de las pociones de alquimia se cortaba antes de tiempo: si se bebía una segunda poción antes de que expirase la primera, el temporizador viejo disparaba igual a su hora original y avisaba de que "el sigilo ha expirado" pese a haberse renovado con una duración nueva. El mismo aviso falso podía aparecer también justo después de que el sigilo se rompiera al entrar en combate.
- La ayuda del juego (`help`) documentaba tres comandos que nunca habían existido — `decir`, `coger` y `soltar` — así que cualquiera que la siguiera al pie de la letra se encontraba con "no entiendo ese comando". Ahora existen de verdad, como alias en español de los comandos base del juego.
- Corregido un error tipográfico en la ayuda del comando para ver el estado de una puerta (`estadopuerta`).
- La pantalla de conexión seguía siendo la plantilla en inglés por defecto de Evennia, sin traducir pese al resto del juego.

## [0.54.0] — 2026-07-23

Ronda de revisión de código de todo el proyecto (2026-07-18 a 2026-07-23): auditoría sistema por sistema de `systems/`+`features/`, un barrido de patrones de bug conocidos repetido sobre todo el código, y una revisión de la infraestructura fuera de `systems/features/` (cmdsets, arranque del servidor, construcción del mundo, API web, configuración). 17 commits de fixes reales, todos confirmados en verde en CI.

### Seguridad
- La API REST (`/api/rooms/`, `/api/rooms/<dbref>/`) rechazaba con 403 a **todo el mundo**, incluidos administradores y Builders legítimos, desde que se escribió: la comprobación de permisos accedía a un atributo inexistente (`request.user.db_object`) y el error quedaba silenciado, devolviendo siempre "acceso denegado". Corregido — además, `/api/rooms/<dbref>/` ya no confunde el dbref de un personaje o de cualquier otro objeto con el de una sala.

### Corregido
- **Runas de equipamiento**: los efectos de una runa grabada seguían activos indefinidamente tras desequipar el objeto (arma, armadura o accesorio), o incluso combatiendo a manos desnudas.
- **Desafíos Diarios**: el bonus de racha previsualizado en `desafios` no comprobaba si la racha seguía viva (si se completó ayer), prometiendo un bonus mayor del que realmente se otorgaba al terminar los 5 desafíos del día.
- **Arena y Torneos PvP**: con 5 o 6 jugadores inscritos, el bracket podía generar un combate contra un jugador fantasma; además, el temporizador interno de combate nunca sustituía de verdad al timeout de inscripción, así que un torneo en curso podía cancelarse de golpe (devolviendo las cuotas) diez minutos después de crearse, incluso en pleno combate.
- **Correo entre jugadores**: adjuntar un objeto a una carta rechazaba como "ambiguo" un nombre exacto si existía otro objeto con ese nombre como subcadena (p. ej. "daga" junto a "daga oxidada").
- **Intercambio entre jugadores**: el mismo problema de nombre ambiguo afectaba a la búsqueda de jugador y de objeto de inventario al ofrecer algo en un intercambio.
- **Clases y Subclases**: `CmdClase`/`CmdSubclase` reimplementaban a mano la lógica de aplicar bonuses en vez de usar la función pura ya existente, con riesgo de que ambas rutas divergieran.
- **Combate**: los hechizos "dardo mágico" y "nova arcana" sumaban el bonus de Fuerza del personaje en vez de sustituirlo por el de Inteligencia, infravalorando el daño de los personajes orientados a magia.
- **Jefes de Mundo**: el daño infligido por la mascota de un jugador contra un jefe de mundo no contaba para las recompensas de participación.
- **Arranque del servidor**: los scripts globales (reloj, clima, mercado, contratos, jefes de mundo, vivienda, cazarrecompensas...) silenciaban cualquier error al arrancar sin registrar nada; ahora cualquier fallo queda en el log.

## [0.53.0] — 2026-07-01

### Añadido
- **Sistema de Desafíos Diarios** — 5 tareas que se renuevan cada día a medianoche UTC, generadas de forma determinista (misma fecha = mismos desafíos para todos los jugadores).
  - Tipos de desafío: matar X enemigos de una facción, recolectar con una profesión, ganar apuestas, elaborar pociones alquímicas, completar una expedición grupal.
  - Cada desafío completado otorga XP y monedas inmediatamente.
  - Al completar los 5 en el mismo día se activa el bonus de racha (escalado: racha 2→+50m/100xp, racha 3→+100m/200xp, racha 4→+200m/400xp, racha 5+→+300m/600xp).
  - `desafios` — lista los 5 desafíos del día con progreso personal.
  - `desafios racha` — muestra tu racha de días consecutivos y total de desafíos completados.
  - Hooks integrados en: combate (kill_faccion vía `db.faccion` del NPC), profesiones (recolectar), apuestas (victoria), alquimia (elaborar), expediciones (completar).
  - `DesafiosDiariosScript` global persistente (tick horario).
  - 3 nuevos logros en categoría "Desafíos Diarios": *Primer Desafío*, *Veterano de Desafíos* (25 completados, título "el Incansable"), *Racha Legendaria* (7 días, título "el Constante").

## [0.52.0] — 2026-07-01

### Añadido
- **Sistema de Alquimia Avanzada** — árbol de recetas de tres rangos (Aprendiz / Artesano / Maestro) que produce pociones únicas usando materiales de herboristería. Complementa el crafteo básico con efectos que no existían en el juego.
  - `alquimia [lista]` — libro de recetas con estado de desbloqueo por rango.
  - `alquimia info <receta>` — ingredientes y descripción de una receta.
  - `alquimia elaborar <receta>` — consume los ingredientes del inventario y crea la poción.
  - Al subir de rango se notifica al jugador y se desbloquean nuevas recetas.
- **9 recetas** divididas en 3 rangos:
  - *Aprendiz* (0 pociones): Bálsamo Regenerador (cura 60 HP), Antídoto Reforzado (cura veneno + inmunidad), Poción de Sigilo Menor (oculto 2 min).
  - *Artesano* (≥5 pociones): Poción de Sigilo (oculto 5 min), Elixir de Reflejos (+5 DES 25 min), Poción Arcana (+6 INT 25 min).
  - *Maestro* (≥15 pociones): Gran Elixir de Vida (HP al máximo), Elixir del Maestro (+8 FUE 35 min), Esencia de la Eternidad (+25% XP 35 min).
- **2 efectos nuevos** añadidos a `Consumible`:
  - `sigilo` — hace al jugador invisible en `look` de sala durante N segundos. El combate rompe el efecto automáticamente. Timer resuelto con `evennia.utils.delay`.
  - `curar_veneno_protegido` — cura el veneno activo y activa `db.inmune_veneno = True` (el siguiente veneno que llegue es bloqueado y consume la inmunidad).
- Hook de inmunidad al veneno en `CombatHandler` (antes de `aplicar_estado`).
- Sigilo se limpia automáticamente al entrar en combate (`CombatHandler.iniciar`).
- `db.pociones_elaboradas = 0`, `db.rango_alquimia = "aprendiz"` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "alquimia"): `primer_elixir` (1 poción), `artesano_alquimia` (5 pociones — título "el Alquimista"), `maestro_alquimia` (15 pociones — título "el Maestro Alquimista").
- `systems/alchemy/alchemy.py`: lógica pura — 9 recetas, funciones de rango, validación, formateo. 61 tests puros en `tests/test_alchemy_system.py`.
- `features/alchemy/commands.py`: `CmdAlquimia`, `AlchemyCmdSet`.

## [0.51.0] — 2026-07-01

### Añadido
- **Sistema de Expediciones Grupales** — secuencias de oleadas de enemigos para grupos (party). Tres expediciones con dificultad creciente.
  - `expedicion [lista]` — muestra el catálogo de expediciones con nivel mínimo, tamaño de grupo y número de oleadas.
  - `expedicion info <tipo>` — detalles y recompensas de una expedición concreta.
  - `expedicion iniciar <tipo>` — el líder del grupo inicia la expedición; todos los miembros son teletransportados a la sala de combate temporal.
  - `expedicion estado` — muestra la oleada actual y la barra de progreso.
  - `expedicion abandonar` — un miembro puede salir y regresa a su sala de origen. Si todos abandonan, la expedición termina.
  - Las oleadas progresan automáticamente (cada 5 s de comprobación) cuando todos los enemigos están derrotados.
  - Pausa de ~8 s entre oleadas con aviso en sala.
  - Al completar la expedición: XP y monedas por oleada + bonus de finalización, luego teleport al origen.
  - Timeout de 30 minutos. Sala temporal eliminada al finalizar o al expirar.
- **Tres expediciones**:
  - `bosque_profundo` — nivel ≥3, 2–4 jugadores, 3 oleadas. Jefe: Goblin Jefe.
  - `catacumbas_perdidas` — nivel ≥5, 2–4 jugadores, 4 oleadas. Jefe: Caballero Oscuro.
  - `fortaleza_caida` — nivel ≥7, 3–4 jugadores, 5 oleadas. Jefe: Capitán Bandido.
- `db.expediciones_completadas = 0`, `db.fortaleza_completada = False` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "expediciones"): `primera_expedicion` (1 completada), `veterano_expedicion` (5 completadas — título "el Expedicionario"), `conquistador_fortaleza` (completar Fortaleza Caída — título "el Conquistador").
- `systems/expeditions/expeditions.py`: lógica pura — catálogo, oleadas, validaciones, recompensas, formateo. 54 tests puros en `tests/test_expeditions_system.py`.
- `features/expeditions/expedition_script.py`: `ExpedicionScript` (tick 5 s, timeout 30 min).
- `features/expeditions/commands.py`: `CmdExpedicion`, `ExpeditionCmdSet`.

## [0.50.0] — 2026-07-01

### Añadido
- **Sistema de Cazarrecompensas** — permite a los jugadores poner precio a la cabeza de otros y cobrar recompensas mediante duelos de caza.
  - `recompensa` / `recompensa tablon` — muestra el tablón global ordenado por precio total.
  - `recompensa poner <jugador> <cantidad>` — publica una recompensa (mín. 100, máx. 5 000 monedas). Se descuenta al instante. Solo una recompensa por par emisor/objetivo.
  - `recompensa cancelar <jugador>` — retira tu recompensa y recuperas el importe.
  - `recompensa mias` — tus recompensas puestas y las que hay sobre ti.
  - `cazar <jugador>` — inicia un duelo de caza contra un objetivo con recompensa activa. Al ganar se cobran automáticamente todas las recompensas sobre ese objetivo.
  - El objetivo recibe aviso inmediato cuando alguien pone precio a su cabeza (si está conectado).
- `RecompensasScript` — script global persistente que almacena la lista de recompensas activas; arrancado en `at_server_start`.
- `db.recompensas_cobradas = 0`, `db.recompensas_recibidas = 0` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "cazarrecompensas"): `primer_cazador` (1 recompensa cobrada — título "el Cazador"), `generoso_verdugo` (3 cobradas), `mas_buscado` (alguien pone precio a tu cabeza — título "el Más Buscado").
- `systems/bounty/bounty.py`: lógica pura — `puede_poner`, `puede_cancelar`, `hay_recompensa`, `bounties_sobre`, `total_sobre_objetivo`, `añadir_bounty`, `cobrar_bounties`, `cancelar_bounty`, `formatear_tablon`, `formatear_mi_estado`. 54 tests puros en `tests/test_bounty_system.py`.
- `features/bounty/bounty_script.py`: `RecompensasScript`, `obtener_recompensas_script`, `cobrar_recompensa_por_duelo`.
- `features/bounty/commands.py`: `CmdRecompensa`, `CmdCazar`, `BountyCmdSet`.
- Hook de caza en `_fin_duelo` de `CombatHandler` (idéntico al patrón del torneo).

## [0.49.0] — 2026-07-01

### Añadido
- **Sistema de Apuestas / Minijuegos** — cuatro juegos de azar disponibles en la Taberna El Jabalí Borracho.
  - `apostar` — muestra las reglas y límites de todos los juegos.
  - `apostar moneda <cara|cruz> <N>` — adivina la cara de una moneda. 50 % de ganar. Premio: ×2.
  - `apostar dados <N>` — lanza 2d6 contra la casa. El mayor total gana; empate = casa gana. Premio: ×2.
  - `apostar cartas <N>` — saca una carta (As–Rey) contra la casa. La más alta gana; empate = casa gana. Premio: ×2.
  - `apostar ruleta <1-6> <N>` — elige un número de la ruleta de 6 posiciones. Prob. 1/6; premio: ×5 (ganancia neta ×4).
  - Apuesta mínima 10 monedas, máxima 1000. Solo en la Taberna (`db.zona == "taberna"`).
  - Aleatoriedad inyectable (`_rng`) para tests 100 % deterministas.
- `db.apuestas_jugadas = 0`, `db.apuestas_ganadas = 0`, `db.mayor_ganancia = 0` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "apuestas"): `primera_apuesta` (1 partida), `golpe_de_suerte` (10 victorias), `gran_tahur` (ganar ≥500 monedas en una partida — título "el Tahúr").
- `systems/gambling/gambling.py`: lógica pura — `puede_apostar`, `jugar_moneda`, `jugar_dados`, `jugar_cartas`, `jugar_ruleta`, `formatear_reglas`. 45 tests puros en `tests/test_gambling_system.py`.
- `features/gambling/commands.py`: `CmdApostar`, `GamblingCmdSet`.

## [0.48.0] — 2026-07-01

### Añadido
- **Sistema de Coleccionables / Tesoros Ocultos** — 15 objetos únicos escondidos en salas del mundo que el jugador descubre con el comando `buscar`.
  - `buscar` — registra el tesoro de la sala actual si se cumplen los requisitos. Cooldown de 30 s entre búsquedas.
  - `buscar pistas` — muestra las pistas de todos los tesoros aún no hallados.
  - `coleccion` — progreso de coleccionables con barra de avance.
  - **15 tesoros** progresivos (nv.1 Ciudad → nv.10 Ciudadela Oscura). Tres requieren haber derrotado al guardián de la zona: TROLL (`corona_lodo`), CABALLERO_OSCURO (`sello_baron`), LICHE_INMORTAL (`ceniza_liche`). Recompensa: monedas (60–500) al encontrarlos.
  - Sinergias: requiere exploración (cartografía) y combate (bestiario) para los tesoros bloqueados por guardián.
- `db.tesoros_encontrados = []` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "coleccion"): `primer_tesoro` (1 tesoro), `cazatesoros` (8 tesoros), `coleccionista` (15 tesoros — título "el Coleccionista").
- `systems/collectibles/collectibles.py`: lógica pura — `TESOROS`, `ZONA_A_TESORO`, `tesoro_de_zona`, `ya_encontrado`, `puede_buscar`, `total_tesoros`, `tesoros_encontrados_count`, `coleccion_completa`, `formatear_coleccion`, `formatear_pistas`. 47 tests puros en `tests/test_collectibles_system.py`.
- `features/collectibles/commands.py`: `CmdBuscar`, `CmdColeccion`, `CollectiblesCmdSet`.

## [0.47.0] — 2026-07-01

### Añadido
- **Sistema de Monturas** — los jugadores pueden adquirir e invocar monturas que otorgan bonus pasivos en combate.
  - `montura` — muestra la montura activa y la cuadra propia.
  - `montura lista` — catálogo completo con requisitos, coste y bonus de cada montura.
  - `montura comprar <nombre>` — adquiere una montura si se cumplen los requisitos.
  - `montura invocar <nombre>` — monta una montura poseída; su bonus se aplica inmediatamente.
  - `montura desmontar` — desmonta la montura actual, eliminando el bonus.
  - **7 monturas** en el catálogo: Poni Viejo (+1 DEF, 200m, nv.1), Corcel de Guerra (+2 DEF +1 FUE, 600m, nv.4), Lobo Cazador (+3 DES, 900m, nv.5), Hipogrifo (+2 DES +2 DEF, 1500m, nv.6, Honrado/Ciudadanos), Corcel Oscuro (+3 FUE +1 INT, 2000m, nv.8), Dragón de Ceniza (+3 INT +2 DEF, gratis, requiere derrotar DRAGON_CENIZA), Grifo Real (+4 DEF +2 DES, 3000m, nv.10).
  - Los bonus se aplican pasivamente en `CombatHandler._get_stats` junto a los de buffs y runas.
- `db.monturas = []` y `db.montura_activa = None` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "monturas"): `primer_jinete` (1 montura), `ecuyer` (3 monturas), `amo_grifo` (Grifo Real — título "el Jinete").
- `systems/mounts/mounts.py`: lógica pura — `MONTURAS`, `puede_comprar`, `puede_invocar`, `puede_desmontar`, `bonus_montura`, `monturas_poseidas_count`, `formatear_estado`, `formatear_catalogo`. 46 tests puros en `tests/test_mounts_system.py`.
- `features/mounts/commands.py`: `CmdMontura`, `MountCmdSet`.

## [0.46.0] — 2026-07-01

### Añadido
- **Cartografía / exploración del mundo** — los jugadores acumulan un mapa personal de las salas que han visitado.
  - `mapa` — muestra todas las zonas del mundo agrupadas por área con estado ✔/✗ y barra de progreso global.
  - `mapa resumen` — muestra solo el conteo de salas exploradas.
  - El registro se actualiza automáticamente en `Room.at_object_receive` al entrar en cualquier sala con `db.zona` en el catálogo. Excluye salas instanciadas (mazmorras) y privadas (viviendas).
  - **29 zonas rastreadas** en 10 áreas: Ciudad (3), Bosque (2), Calabozo (3), Pantano del Troll (3), Catacumbas (2), Ruinas del Templo (3), Minas de Hierro Viejo (3), Torre del Mago Caído (3), Ciudadela Oscura (3), Zonas Especiales (4).
- `db.salas_exploradas = []` en `Character.at_object_creation`. Estructura: `list[str]` de dbrefs únicos.
- **3 logros nuevos** (categoría "cartografia"): `primer_viaje` (1 sala), `explorador` (10 salas), `cartografo` (29 salas — título "el Cartógrafo").
- `systems/cartography/cartography.py`: lógica pura — `ZONAS_INFO`, `ZONAS_VALIDAS`, `TOTAL_SALAS`, `registrar_sala`, `total_exploradas`, `es_zona_explorable`, `formatear_mapa`, `_barra`. 33 tests puros en `tests/test_cartography_system.py`.
- `features/cartography/commands.py`: `CmdMapa`, `CartographyCmdSet`.

## [0.45.0] — 2026-06-30

### Añadido
- **Bestiario / enciclopedia de criaturas** — los jugadores acumulan un registro personal de las criaturas que han derrotado.
  - `bestiario` — lista todas las criaturas del catálogo agrupadas por tipo (Bestias / Humanoides / No-Muertos / Constructos / Oscuros), con estado ✔/✗, número de bajas y tiempo desde el primer encuentro.
  - `bestiario <nombre>` — ficha detallada de una criatura: descripción, zona, nivel, tipo, bajas registradas y fecha de primer encuentro. Soporta búsqueda parcial e insensible a mayúsculas.
  - **24 criaturas en el catálogo**: GOBLIN, GOBLIN_JEFE, BANDIDO, BANDIDO_CAPITAN, HOMBRE_LAGARTO, APRENDIZ_CORRUPTO, MINERO_MALDITO (humanoides); SERPIENTE_PANTANO, ARANA_CUEVA, TROLL, DRAGON_CENIZA (bestias); ESQUELETO, LICHE_MENOR, ESPECTRO, CABALLERO_MUERTE, LICHE_INMORTAL, SENOR_CENIZAS (no-muertos); GOLEM_PIEDRA, GUARDIAN_ARCANO, TITAN_PANTANO, GUARDIAN_FORJA, MAESTRO_FORJADOR (constructos); CABALLERO_OSCURO, HECHICERO_SOMBRIO, ARCHIMAGO_VEXTHAR, SENOR_ABISMO (oscuros).
  - El registro se actualiza automáticamente en `CombatHandler._procesar_muerte` para todos los participantes del grupo. Solo se registran criaturas del catálogo (criaturas con `db.npc_prototipo` reconocido).
- `db.bestiary = {}` en `Character.at_object_creation`. Estructura: `{proto_key: {"kills": int, "primera_vez": unix_ts}}`.
- **3 logros nuevos** (categoría "bestiario"): `primera_presa` (1 criatura), `cazador_experimentado` (10 criaturas distintas), `enciclopedista` (catálogo completo — título "el Enciclopedista").
- `systems/bestiary/bestiary.py`: lógica pura — `CATALOGO`, `TIPOS`, `registrar_kill`, `criaturas_registradas`, `bestiary_completo`, `buscar_en_catalogo`, `formatear_lista`, `formatear_entrada`. 45 tests puros en `tests/test_bestiary_system.py`.
- `features/bestiary/commands.py`: `CmdBestiario`, `BestiaryCmdSet`.

## [0.44.0] — 2026-06-30

### Añadido
- **Sistema de vivienda personal** — los jugadores pueden comprar una sala privada permanente.
  - `vivienda` — muestra el estado de tu vivienda (descripción, propietario, lista de acceso).
  - `vivienda comprar` — adquiere una vivienda por **500 monedas** (pago único, sin alquiler periódico). Solo se puede tener una.
  - `vivienda abandonar` — devuelve la vivienda de forma permanente (sin reembolso); los objetos se trasladan al Barrio Residencial. Pide confirmación doble.
  - `vivienda acceso dar <jugador>` / `vivienda acceso quitar <jugador>` — gestiona quién puede entrar (máximo 10 invitados).
  - `casa` / `hogar` — teletransporte instantáneo a tu vivienda desde cualquier lugar.
  - `visitar <jugador>` — visita la vivienda de otro jugador si te ha dado acceso.
  - `decorar <texto>` — cambia la descripción de la sala (máx. 500 caracteres); debes estar dentro.
- **Zona nueva**: Barrio Residencial (1 sala, al noreste de la Plaza de la Ciudad). Las salas de vivienda se crean dinámicamente dentro de esta zona con una salida permanente de vuelta al barrio.
- `db.vivienda_dbref = None` y `db.vivienda_decorada = False` en `Character.at_object_creation`.
- `GestorViviendasScript` (script persistente global, key `"gestor_viviendas"`): administra el ciclo de vida de todas las viviendas (creación, eliminación, accesos, decoración).
- **2 logros nuevos** (categoría "vivienda"): `primera_vivienda` ("Propietario") y `hogar_decorado` ("Toque Personal" — título "el Anfitrión").
- `systems/housing/housing.py`: lógica pura — `puede_comprar`, `puede_invitar`, `puede_quitar_acceso`, `puede_entrar`, `validar_descripcion`, formateo. 37 tests puros en `tests/test_vivienda_system.py`.
- `features/housing/housing_script.py`: `GestorViviendasScript` + `obtener_gestor_script()`.
- `features/housing/commands.py`: `CmdVivienda`, `CmdCasa`, `CmdVisitar`, `CmdDecorar`, `HousingCmdSet`.

## [0.43.0] — 2026-06-29

### Añadido
- **Arena y Torneos PvP** — torneos de eliminación directa en la Arena de la Ciudad.
  - `arena` / `torneo` — muestra el estado del torneo actual.
  - `arena inscribir` — inscribe al jugador por **100 monedas** (el pot completo va al campeón).
  - `arena salir` — cancela la inscripción antes de que empiece el torneo.
  - `arena iniciar` — arranca el torneo con los jugadores inscritos.
  - `TorneoScript` (no persistente): gestiona inscripciones, bracket y combates. Bracket de eliminación directa (2–8 jugadores, byes automáticos hasta la siguiente potencia de 2).
  - Combates resueltos con el `CombatHandler` existente en `modo_duelo=True`; hook en `_fin_duelo()` notifica el resultado al `TorneoScript`.
  - Anuncios globales en inscripción, inicio, cada combate y resultado final.
  - Timeout de 10 min (inscripción) / 5 min (combate) con cancelación y devolución de cuotas automática. Forfeit automático si un jugador se desconecta.
- Nueva sala "Arena de la Ciudad" (al este de la Plaza) con NPC Maestro de Arena.
- `db.torneos_ganados = 0` en `Character.at_object_creation`.
- **2 logros nuevos** (categoría "arena"): `campeon_arena` (título "el Campeón de la Arena"), `maestro_arena` (3 victorias, título "el Imbatible").
- `systems/arena/arena.py` + `features/arena/tournament_script.py` + `features/arena/commands.py`. 34 tests puros en `tests/test_arena_system.py`.

## [0.42.0] — 2026-06-29

### Añadido
- **Sistema de Runas** — runas inscribibles en equipamiento (arma/armadura/accesorio) con efectos activos en combate.
  - `runas` — lista/info/estado/grabar/borrar. Grabar consume materiales de profesión + monedas.
  - **8 runas**: Vigor (regen_hp), Filo (sangrado 25%, arma), Escudo (reducción de daño, armadura), Drenaje (robo de vida, arma), Evasión (esquiva 10%), Poder (bonus fuerza, arma), Firmeza (resistencia a estados, armadura), Arcana (bonus inteligencia).
  - Integración en combate: `_get_stats()` aplica bonus de fuerza/inteligencia; `_anunciar_turno()` regenera HP con Vigor; `_resolver_turno()` resuelve evasión, reducción de daño, robo de vida, resistencia a estados y sangrado de Filo.
- `db.runas_equipadas = {"arma": None, "armadura": None, "accesorio": None}` en `Character.at_object_creation`.
- **3 logros nuevos** (categoría "runas"): `primera_runa`, `runas_completas` (título "el Tallador"), `runa_arcana` (título "el Maestro Rúnico").
- `systems/runes/runes.py` + `features/runes/commands.py`. 51 tests puros.

## [0.41.0] — 2026-06-29

### Añadido
- **Sistema de jefes de mundo** — tres world bosses que aparecen en zonas fijas del mapa tras un cooldown real, con anuncio global y recompensas proporcionales al daño.
  - **Titán del Pantano** (`pantano_cenagoso`, nv.req 4, 6h cooldown, 2000 HP): loot único ESCAMA_TITAN.
  - **Guardián de la Forja** (`caverna_coloso`, nv.req 6, 7h cooldown, 3000 HP): loot único NUCLEO_GUARDIAN.
  - **Dragón de Ceniza** (`claro_bosque`, nv.req 8, 8h cooldown, 5000 HP): loot único GARRA_DRAGON.
  - Tracking de daño por jugador en `npc.ndb.dano_por_jugador`. Todos los participantes reciben XP y monedas proporcionales (mínimo 10%). El mayor dañador se lleva el loot único.
  - Anuncio global al aparecer y al morir, con lista de participantes.
  - `WorldBossScript` (global, tick 5 min): detecta muerte y respawnea tras cooldown.
  - `jefes` — muestra estado de cada jefe (vivo / tiempo hasta próximo spawn).
- **4 nuevos logros** (categoría "jefe_mundo"): `titan_derrotado`, `guardian_derrotado`, `dragon_derrotado` (título "Cazadragones"), `todos_jefes_mundo` (título "el Azote").
- **3 ítems únicos**: ESCAMA_TITAN (accesorio), NUCLEO_GUARDIAN (arma), GARRA_DRAGON (arma — el mejor ítem del juego).
- `db.jefes_mundo_derrotados = {}` en `Character.at_object_creation`.
- Modificaciones mínimas en `features/combat/handler.py`: tracking de daño en `_resolver_turno` y hook en `_procesar_muerte` para distribución de rewards.
- `systems/world_bosses/world_bosses.py`: catálogo puro + lógica (27 tests pasando).
- `features/world_bosses/world_boss_script.py`: `WorldBossScript` + `distribuir_recompensas_jefe_mundo`.
- `features/world_bosses/commands.py`: `CmdJefesMundo`, `WorldBossCmdSet`.

## [0.40.0] — 2026-06-29

### Añadido
- **Sistema de correo entre jugadores** — envía cartas a cualquier jugador (en línea u offline) con adjuntos opcionales.
  - `carta <jugador> = <mensaje>` — carta simple.
  - `carta <jugador> adjuntar <objeto> = <mensaje>` — adjunta un objeto del inventario.
  - `carta <jugador> monedas <N> = <mensaje>` — adjunta monedas.
  - `carta <jugador> adjuntar <objeto> monedas <N> = <mensaje>` — adjunta ambos.
  - `correo` — lista el buzón con indicador de no leídas y adjuntos pendientes.
  - `correo leer <N>` — lee y marca como leída la carta N.
  - `correo reclamar <N>` — mueve el adjunto (objetos/monedas) al inventario.
  - `correo borrar <N>` — borra la carta; si tiene adjunto no reclamado, lo devuelve al remitente.
  - `correo responder <N> = <texto>` — responde directamente a la carta N.
  - Notificación automática al hacer login si hay cartas no leídas.
  - Máximo 20 cartas en el buzón. Los objetos adjuntos viajan sin ubicación (`location=None`) hasta ser reclamados.
- `db.correo = []` inicializado en `Character.at_object_creation`.
- Hook `at_post_puppet` en `Character` para notificación de correo al conectarse.
- `systems/mail/mail.py`: lógica pura — `nueva_carta`, `puede_recibir`, `tiene_adjunto`, `adjunto_pendiente`, `contar_no_leidas`, formateo.
- `features/mail/commands.py`: `CmdCarta`, `CmdCorreo`, `MailCmdSet`.
- 33 tests puros pasando (`tests/test_correo_system.py`).

## [0.39.0] — 2026-06-29

### Añadido
- **Sistema de intercambio entre jugadores** — dos jugadores en la misma sala pueden intercambiar objetos y monedas con confirmación mutua.
  - `intercambiar <jugador>` — propone el intercambio; el destinatario acepta con `intercambiar aceptar` o lo cancela.
  - `ofrecer <objeto>` / `ofrecer <N> monedas` — añade objetos o monedas a tu oferta.
  - `retirar oferta <objeto>` — quita un objeto de tu oferta.
  - `confirmar` — cuando ambos confirman, el intercambio se ejecuta de forma atómica.
  - `cancelar` / `intercambiar cancelar` — aborta la sesión.
  - Timeout automático de 2 minutos; se cancela también en server reload.
  - Validaciones: el objeto debe estar en el inventario del ofertante, las monedas ofrecidas no pueden superar el saldo disponible; ambas comprobaciones se repiten en el momento de ejecución.
- `systems/trade/trade.py`: lógica pura — `nuevo_lado`, `agregar_objeto`, `retirar_objeto`, `establecer_monedas`, `confirmar`, `desconfirmar_ambos`, `ambos_confirmados`, `validar_monedas`, `formatear_intercambio`, `formatear_oferta_simple`, `tiene_oferta`.
- `features/trade/trade_session.py`: `TradeSession` (DefaultScript, persistent=False, interval=120 = timeout).
- `features/trade/commands.py`: `CmdIntercambiar`, `CmdOfrecer`, `CmdRetirarOferta`, `CmdConfirmarIntercambio`, `TradeCmdSet`.
- 36 tests puros pasando (`tests/test_intercambio_system.py`).

## [0.38.0] — 2026-06-29

### Añadido
- **Sistema de mazmorras instanciadas** — tres mazmorras de 3 salas cada una (2 normales + 1 jefe), sala por sala, con dificultad configurable.
  - `cripta_ceniza` (nv.mín 3): Entrada de la Cripta → Nave Funeraria → Capilla del Señor de las Cenizas.
  - `forja_maldita` (nv.mín 5): Taller Corrompido → Cámara de la Fundición → Trono del Maestro Forjador.
  - `abismo_sin_fondo` (nv.mín 7): Umbral del Abismo → Corredor de las Almas → Cámara del Señor del Abismo.
  - **3 dificultades**: normal (×1 HP/XP), difícil (×1.5), legendario (×2 HP, ×2.5 XP).
  - Salas temporales creadas al entrar y destruidas al completar o a los 60 min (timeout).
  - NPCs spawneados de forma perezosa sala a sala; HP escalado por dificultad; sin respawn en salas temporales.
- **7 nuevos prototipos NPC**: MINERO_MALDITO, SENOR_CENIZAS, MAESTRO_FORJADOR, SENOR_ABISMO, GUARDIAN_PORTAL + uso de ESQUELETO/LICHE_MENOR/CABALLERO_MUERTE/HECHICERO_SOMBRIO/GOLEM_PIEDRA/ARANA_CUEVA ya existentes.
- **3 nuevos ítems de botín** (drops de jefes): RELIQUIA_CENIZA (accesorio), MARTILLO_MALDITO (arma), ESPADA_ABISMO (arma).
- **Zona nueva**: Vestíbulo del Portal (1 sala, conectada al norte de la Plaza, GUARDIAN_PORTAL presente).
- **Comandos**:
  - `mazmorra` / `mazmorras` / `maz` — lista mazmorras, info, entrar, estado, salir.
  - `avanzar` — avanza a la siguiente sala (requiere sala despejada).
- **5 nuevos logros** (categoría "mazmorra"):
  - `cripta_completada`, `forja_completada`, `abismo_completado` (título "el Conquistador"), `todas_mazmorras`, `mazmorra_legendario` (título "el Legendario").
- `db.mazmorras_completadas = {}` y `db.mazmorra_legendario = False` en `Character.at_object_creation`.
- Limpieza de salas de mazmorra huérfanas en `at_server_cold_start`.
- `systems/dungeons/dungeons.py`: catálogo puro + funciones de lógica (41 tests pasando).
- `features/dungeons/dungeon_script.py`: `MazmorraScript` (DefaultScript persistente, timeout 3600s).
- `features/dungeons/commands.py`: `CmdMazmorra`, `CmdAvanzar`, `DungeonCmdSet`.

## [0.37.0] — 2026-06-29

### Añadido
- **Sistema de profesiones de recolección** — tres profesiones con 5 niveles cada una.
  - **Minería** — extraer minerales en las Minas de Hierro Viejo (`boca_mina` nv.1, `galeria_principal` nv.2, `caverna_coloso` nv.3).
  - **Herboristería** — recolectar plantas en bosque y pantano (`bosque_norte`/`claro_bosque`/`senda_fangosa` nv.1, `pantano_cenagoso` nv.2, `guarida_troll` nv.3).
  - **Pesca** — pescar en la nueva Orilla del Río (`orilla_rio` nv.1).
  - **5 niveles** por profesión: Aprendiz → Novato → Artesano → Experto → Maestro. XP acumulada: 0/30/80/160/300.
  - Materiales de nivel superior son más raros (sistema de pesos).
  - Cooldown de 60 s por profesión entre recolecciones.
  - Materiales de minería (mineral de hierro, gema en bruto) compatibles con las recetas de crafteo existentes.
- **15 nuevos prototipos de material**: 5 de minería (mineral de hierro, piedra afilada, mineral de plata, gema en bruto, gema arcana), 5 de herboristería (hierba medicinal, raíz de pantano, flor silvestre, esencia vegetal, extracto raro), 5 de pesca (pez común, pez plateado, pez dorado, perla de río, escama mágica).
- **6 nuevas recetas** que usan materiales de profesión:
  - `cataplasma` (hierba medicinal ×2 → cataplasma curativa, cura 20 HP).
  - `antídoto silvestre` (flor silvestre ×2 → antídoto ×2).
  - `sopa del pescador` (pez dorado + hierba medicinal → poción de vida mayor).
  - `elixir de esencia` (esencia vegetal + flor silvestre → elixir de restauración).
  - `anillo de plata` (mineral de plata ×2 + piedra afilada → accesorio: +2 FUE, +2 DES, +1 CON).
  - `amuleto del bosque` (flor silvestre ×2 + esencia vegetal → accesorio: +3 INT, +2 DES).
- **Zona nueva**: Orilla del Río (1 sala, exterior, conectada al oeste de la Plaza).
- `db.profesiones = {}` inicializado en `Character.at_object_creation`.
- `systems/professions/professions.py`: lógica pura — `PROFESIONES`, `ZONAS_RECURSO`, `nivel_desde_xp`, `xp_para_siguiente`, `elegir_material`, `aprender_profesion`, `ganar_xp`, `zona_a_profesion`, formateo.
- `features/professions/commands.py`: `CmdProfesion` (`profesion`/`profesiones`/`prof`) y `CmdRecolectar` (`recolectar`/`minar`/`cosechar`/`pescar`), `ProfessionCmdSet`.
- 60 tests puros en `tests/test_profesiones_system.py`.

## [0.36.0] — 2026-06-28

### Añadido
- **Sistema de rangos de aventurero**: progresión transversal basada en la actividad acumulada del personaje.
  - `rango` (alias `rank`, `aventurero`) — muestra tu rango actual, puntuación total, barra de progreso al siguiente rango y desglose detallado por fuente.
  - **6 rangos**: Aprendiz (0 pts) → Novicio (50) → Veterano (300) → Héroe (700) → Campeón (1.400) → Leyenda (2.500).
  - **Fórmula de puntuación**: 15 pts × (nivel − 1) + 10 pts × quests entregadas + 20 pts × logros desbloqueados + 1 pt × kills totales.
  - El rango se muestra en el comando `perfil` junto a la clase.
  - Al subir de rango se recibe una notificación inmediata y la sala lo anuncia.
  - El rango nunca baja: si se calcula un rango inferior al almacenado, se mantiene el mayor.
  - Las subidas de rango se comprueban automáticamente cada vez que se llama a `comprobar_y_notificar` (tras kills, quests, logros, crafteo, encantamiento, etc.).
  - `db.rango` inicializado a `"aprendiz"` en `Character.at_object_creation`.
- `systems/ranks/ranks.py`: lógica pura — `RANGOS`, `calcular_puntuacion`, `rango_actual`, `siguiente_rango`, `puntos_para_siguiente`, `formatear_rango`, `desglose_puntuacion`.
- `features/ranks/commands.py`: `CmdRango`, `RankCmdSet`, `verificar_subida_rango()`.
- 44 tests puros en `tests/test_rangos_system.py` + 19 tests de integración en `tests/test_rangos.py`.

## [0.35.0] — 2026-06-25

### Añadido
- **Rareza de loot** — los ítems de equipo que sueltan los NPCs ahora tienen rareza aleatoria:
  - **Común** (70%) — sin modificador, nombre en amarillo.
  - **Raro** (25%) — ×1.2 en todos los bonuses positivos, nombre en cian con sufijo `(Raro)`.
  - **Épico** (5%) — ×1.5 en todos los bonuses positivos, nombre en magenta con sufijo `(Épico)`.
- Los ítems de equipamiento no-prototipo (monedas, materiales, consumibles) nunca tienen rareza.
- `db.rareza` se inicializa a `"comun"` en `Equipo.at_object_creation`.
- El mensaje de loot colorea cada ítem según su rareza; los ítems épicos disparan un anuncio adicional en la sala.
- `look` sobre un ítem de equipo muestra `[Raro]` o `[Épico]` junto al slot.
- `systems/loot/rarity.py` — módulo puro: `tirar_rareza`, `aplicar_rareza_bonuses`, `nombre_con_rareza`, `color_rareza`, `es_notable`, `formatear_drop`.
- 32 tests puros en `tests/test_rarity.py`.

## [0.34.0] — 2026-06-25

### Añadido
- **Buffs de taberna** — 4 ítems consumibles de un solo uso vendidos por el mesonero Gareth:
  - `Cerveza de combate` (30m) — +3 Fuerza durante 20 minutos.
  - `Vino del explorador` (30m) — +3 Destreza durante 20 minutos.
  - `Té arcano` (30m) — +3 Inteligencia durante 20 minutos.
  - `Estofado vigorizante` (35m) — +15 % XP durante 30 minutos.
- `systems/buffs/buffs.py` — módulo puro: `buffs_vigentes`, `aplicar_buff`, `bonus_stat`, `factor_xp`, `hay_buffs`, `formatear_buffs`.
- `db.buffs_activos` (lista) inicializado en `Character.at_object_creation`.
- `Consumible` amplía `EFECTOS_VALIDOS` con `"buff_stat"` y `"buff_xp"`; nuevos atributos `db.stat_buff` y `db.duracion`.
- Los bonuses de stat se aplican en `_get_stats()` del handler de combate (mismo patrón que el evento de Tormenta Mágica).
- El bonus de XP multiplica `xp_real` en `_dar_xp_a_grupo()`; el mensaje al jugador indica el multiplicador cuando está activo.
- Comando `buffs` — lista buffs vigentes con tiempo restante; limpia expirados silenciosamente.
- 25 tests puros en `tests/test_buffs.py`.

## [0.33.0] — 2026-06-25

### Añadido
- **Logros de gremio** — 5 nuevos logros en la categoría **Gremio**:
  - `Fundador` — funda tu propio gremio (sin título).
  - `Líder Unificador` — lidera un gremio con al menos 5 miembros (sin título).
  - `Comandante` — lidera un gremio con el máximo de 20 miembros → título **el Comandante**.
  - `Tesorero` — deposita un total acumulado de 500 monedas en el banco gremial (sin título).
  - `Mecenas` — deposita un total acumulado de 2000 monedas en el banco gremial → título **el Mecenas**.
- `db.gremios_fundados` y `db.gremio_banco_depositado` rastreados por personaje (acumulados).
- `comprobar_y_notificar` se llama automáticamente al fundar un gremio, al aceptar una invitación y al depositar en el banco gremial. Al unirse un nuevo miembro también se comprueba en el Líder (si está conectado).
- `GuildScript.get_lider()` — nuevo helper que devuelve el objeto Character del Líder actual.
- `_extraer_datos_gremio()` en features/achievements: consulta el GuildScript en tiempo real para `es_lider_gremio` y `miembros_gremio`.
- La pantalla `logros` muestra la sección **Gremio** y acepta `logros gremio` como filtro.
- Total logros: 38 (33 anteriores + 5 gremio). Máximo alcanzable por personaje: 31.
- Suite de tests: +20 tests puros (`TestLogrosGremio`) + 8 integración (`TestLogrosGremioIntegracion`).

## [0.32.0] — 2026-06-25

### Añadido
- **Evolución de mascotas**: las mascotas ahora ganan XP con cada enemigo derrotado (XP = nivel del NPC) y evolucionan al acumular suficiente experiencia.
  - **Nivel 1** → base; **Nivel 2** (Mayor, 50 XP): ×1.5 stats; **Nivel 3** (Élite, 150 XP): ×2.5 stats.
  - Al evolucionar: ataque, defensa y HP máx escalan; HP se restaura al máximo; la especie añade el sufijo "Mayor" o "Élite".
  - Notificación inmediata al jugador con el nuevo nombre de especie y nivel.
  - El comando `mascota` muestra ahora **Nivel** y barra de **XP** hacia la siguiente evolución.
- **2 nuevos logros** en categoría **Mascotas**:
  - `Primer Compañero` — lleva tu mascota al nivel 2 (sin título).
  - `Domador` — lleva tu mascota al nivel 3 (Élite) → título **el Domador**.
- `db.mascota_nivel_max` rastreado en el personaje (nivel más alto alcanzado por cualquier mascota).
- `systems/pets/pets.py`: nuevas funciones `xp_para_siguiente_nivel()`, `calcular_evolucion()` y constantes `XP_NIVEL_2`, `XP_NIVEL_3`, `NIVEL_MAX_MASCOTA`.
- `datos_mascota_desde_criatura()` añade campos `nivel`, `xp` y `especie_base` al capturar.
- Suite de tests: +32 tests puros (`TestEvolucion`, `TestXpParaSiguienteNivel`, actualizaciones), +7 integración.

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
