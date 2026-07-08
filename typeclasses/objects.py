"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

from evennia.objects.objects import DefaultObject


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).

    Just add any method that exists on `DefaultObject` to this class. If one
    of the derived classes has itself defined that same hook already, that will
    take precedence.

    """


class Object(ObjectParent, DefaultObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    Note: Check the autodocs for complete class members, this may not always
    be up-to date.

    * Base properties defined/available on all Objects

     key (string) - name of object
     name (string)- same as key
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation

     account (Account) - controlling account (if any, only set together with
                       sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                       account above). Use `sessions` handler to get the
                       Sessions directly.
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     has_account (bool, read-only)- will only return *connected* accounts
     contents (list, read only) - returns all objects inside this object
     exits (list of Objects, read-only) - returns all exits from this
                       object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser
     is_connected (bool, read-only) - True if this object is associated with
                            an Account with any connected sessions.
     has_account (bool, read-only) - True is this object has an associated account.
     is_superuser (bool, read-only): True if this object has an account and that
                        account is a superuser.

    * Handlers available

     aliases - alias-handler: use aliases.add/remove/get() to use.
     permissions - permission-handler: use permissions.add/remove() to
                   add/remove new perms.
     locks - lock-handler: use locks.add() to add new lock strings
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().
     sessions - sessions-handler. Get Sessions connected to this
                object with sessions.get()
     attributes - attribute-handler. Use attributes.add/remove/get.
     db - attribute-handler: Shortcut for attribute-handler. Store/retrieve
            database attributes using self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create
            a database entry when storing data

    * Helper methods (see src.objects.objects.py for full headers)

     get_search_query_replacement(searchdata, **kwargs)
     get_search_direct_match(searchdata, **kwargs)
     get_search_candidates(searchdata, **kwargs)
     get_search_result(searchdata, attribute_name=None, typeclass=None,
                       candidates=None, exact=False, use_dbref=None, tags=None, **kwargs)
     get_stacked_result(results, **kwargs)
     handle_search_results(searchdata, results, **kwargs)
     search(searchdata, global_search=False, use_nicks=True, typeclass=None,
            location=None, attribute_name=None, quiet=False, exact=False,
            candidates=None, use_locks=True, nofound_string=None,
            multimatch_string=None, use_dbref=None, tags=None, stacked=0)
     search_account(searchdata, quiet=False)
     execute_cmd(raw_string, session=None, **kwargs))
     msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     for_contents(func, exclude=None, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, mapping=None,
                  raise_funcparse_errors=False, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None, use_destination=True)
     clear_contents()
     create(key, account, caller, method, **kwargs)
     copy(new_key=None)
     at_object_post_copy(new_obj, **kwargs)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False,
            no_superuser_bypass=False, **kwargs)
     filter_visible(obj_list, looker, **kwargs)
     get_default_lockstring()
     get_cmdsets(caller, current, **kwargs)
     check_permstring(permstring)
     get_cmdset_providers()
     get_display_name(looker=None, **kwargs)
     get_extra_display_name_info(looker=None, **kwargs)
     get_numbered_name(count, looker, **kwargs)
     get_display_header(looker, **kwargs)
     get_display_desc(looker, **kwargs)
     get_display_exits(looker, **kwargs)
     get_display_characters(looker, **kwargs)
     get_display_things(looker, **kwargs)
     get_display_footer(looker, **kwargs)
     format_appearance(appearance, looker, **kwargs)
     return_apperance(looker, **kwargs)

    * Hooks (these are class methods, so args should start with self):

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the object
                            has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_delete() - called just before deleting an object. If returning
                            False, deletion is aborted. Note that all objects
                            inside a deleted object are automatically moved
                            to their <home>, they don't need to be removed here.

     at_init()            - called whenever typeclass is cached from memory,
                            at least once every server restart/reload
     at_first_save()
     at_cmdset_get(**kwargs) - this is called just before the command handler
                            requests a cmdset from this object. The kwargs are
                            not normally used unless the cmdset is created
                            dynamically (see e.g. Exits).
     at_pre_puppet(account)- (account-controlled objects only) called just
                            before puppeting
     at_post_puppet()     - (account-controlled objects only) called just
                            after completing connection account<->object
     at_pre_unpuppet()    - (account-controlled objects only) called just
                            before un-puppeting
     at_post_unpuppet(account) - (account-controlled objects only) called just
                            after disconnecting account<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_access(result, accessing_obj, access_type) - called with the result
                            of a lock access check on this object. Return value
                            does not affect check result.

     at_pre_move(destination)             - called just before moving object
                        to the destination. If returns False, move is cancelled.
     announce_move_from(destination)         - called in old location, just
                        before move, if obj.move_to() has quiet=False
     announce_move_to(source_location)       - called in new location, just
                        after move, if obj.move_to() has quiet=False
     at_post_move(source_location)          - always called after a move has
                        been successfully performed.
     at_pre_object_leave(leaving_object, destination, **kwargs)
     at_object_leave(obj, target_location, move_type="move", **kwargs)
     at_object_leave(obj, target_location)   - called when an object leaves
                        this object in any fashion
     at_pre_object_receive(obj, source_location)
     at_object_receive(obj, source_location, move_type="move", **kwargs) - called when this object receives
                        another object
     at_post_move(source_location, move_type="move", **kwargs)

     at_traverse(traversing_object, target_location, **kwargs) - (exit-objects only)
                              handles all moving across the exit, including
                              calling the other exit hooks. Use super() to retain
                              the default functionality.
     at_post_traverse(traversing_object, source_location) - (exit-objects only)
                              called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called if
                       traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, **kwargs) - called when a message
                             (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, **kwargs) - called when this objects
                             sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the
                                 appearance is requested.
     at_pre_get(getter, **kwargs)
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_pre_give(giver, getter, **kwargs)
     at_give(giver, getter, **kwargs)
     at_pre_drop(dropper, **kwargs)
     at_drop(dropper, **kwargs)          - called when this object has been dropped.
     at_pre_say(speaker, message, **kwargs)
     at_say(message, msg_self=None, msg_location=None, receivers=None, msg_receivers=None, **kwargs)

     at_look(target, **kwargs)
     at_desc(looker=None)

    """

    pass


class Equipo(DefaultObject):
    """
    Objeto equipable: arma, armadura o accesorio.

    Atributos:
      db.slot    — slot que ocupa: "arma" | "armadura" | "accesorio"
      db.bonuses — dict de bonificaciones a stats, ej: {"fuerza": 3, "defensa": 2}
    """

    SLOTS_VALIDOS = ("arma", "armadura", "accesorio")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.slot = "accesorio"
        self.db.bonuses = {}
        self.db.rareza = "comun"

    def return_appearance(self, looker, **kwargs):
        desc = self.db.desc or "Un objeto sin descripción especial."
        slot = self.db.slot or "accesorio"
        bonuses = self.db.bonuses or {}
        rareza = self.db.rareza or "comun"

        if bonuses:
            bonus_txt = ", ".join(f"|w{k}|n +{v}" for k, v in sorted(bonuses.items()))
        else:
            bonus_txt = "ninguna"

        rareza_txt = ""
        if rareza == "raro":
            rareza_txt = " |c[Raro]|n"
        elif rareza == "epico":
            rareza_txt = " |m[Épico]|n"

        return (
            f"|w{self.key}|n |c[{slot}]|n{rareza_txt}\n"
            f"{desc}\n"
            f"Bonificaciones: {bonus_txt}"
        )


class Consumible(DefaultObject):
    """
    Objeto consumible: pociones, antídotos, elixires, etc.

    Atributos:
      db.efecto   — tipo de efecto: "curar_hp" | "curar_maximo" | "curar_veneno"
      db.potencia — magnitud del efecto (HP recuperados, etc.)
      db.usos     — usos restantes; -1 = ilimitado
      db.valor    — precio base de venta al 50%
    """

    EFECTOS_VALIDOS = ("curar_hp", "curar_maximo", "curar_veneno",
                        "buff_stat", "buff_xp",
                        "sigilo", "curar_veneno_protegido")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.efecto = "curar_hp"
        self.db.potencia = 30
        self.db.usos = 1
        self.db.valor = 15
        self.db.stat_buff = ""    # estadística afectada (sólo en buff_stat)
        self.db.duracion = 1200   # segundos que dura el buff

    def aplicar(self, caller) -> str:
        efecto = self.db.efecto or "curar_hp"
        potencia = self.db.potencia or 0

        if efecto == "curar_hp":
            hp = getattr(caller.db, "hp", None)
            hp_max = getattr(caller.db, "hp_max", None)
            if hp is None or hp_max is None:
                return "No tiene efecto en ti."
            if hp >= hp_max:
                return "Ya estás en perfectas condiciones. No necesitas esto ahora."
            recuperado = min(potencia, hp_max - hp)
            caller.db.hp = hp + recuperado
            return (
                f"|gRecuperas {recuperado} puntos de vida.|n "
                f"HP: |w{caller.db.hp}/{hp_max}|n"
            )

        if efecto == "curar_maximo":
            hp_max = getattr(caller.db, "hp_max", None)
            if hp_max is None:
                return "No tiene efecto en ti."
            hp = getattr(caller.db, "hp", hp_max)
            if hp >= hp_max:
                return "Ya estás en perfectas condiciones. No necesitas esto ahora."
            recuperado = hp_max - hp
            caller.db.hp = hp_max
            return (
                f"|gRecuperas {recuperado} puntos de vida. ¡HP al máximo!|n "
                f"HP: |w{hp_max}/{hp_max}|n"
            )

        if efecto == "curar_veneno":
            from systems.combat.states import limpiar_estado
            estados = dict(getattr(caller.db, "estados", {}) or {})
            caller.db.estados = limpiar_estado(estados, "veneno")
            return "|gSientes cómo el veneno se disuelve en tu sangre.|n"

        if efecto in ("buff_stat", "buff_xp"):
            from systems.buffs.buffs import aplicar_buff
            buffs = list(getattr(caller.db, "buffs_activos", None) or [])
            stat = self.db.stat_buff or ""
            duracion = int(self.db.duracion or 1200)
            caller.db.buffs_activos = aplicar_buff(
                buffs, efecto, potencia, self.key, duracion, stat
            )
            if efecto == "buff_stat":
                return f"|Y¡{self.key}! Ganas +{potencia} {stat} durante {duracion // 60} minutos.|n"
            pct = int(potencia * 100)
            return f"|Y¡{self.key}! Ganas +{pct}% XP durante {duracion // 60} minutos.|n"

        if efecto == "sigilo":
            dur = int(potencia or 180)
            caller.db.oculto = True
            caller.db.nivel_sigilo = 25
            from evennia.utils import delay as _delay
            def _quitar_sigilo(char=caller):
                try:
                    if char and char.db:
                        char.db.oculto = False
                        char.msg("|xEl efecto de sigilo ha expirado.|n")
                except Exception:
                    pass
            _delay(dur, _quitar_sigilo)
            mins = dur // 60
            segs = dur % 60
            dur_txt = f"{mins} min" if not segs else (f"{mins} min {segs} s" if mins else f"{segs} s")
            return f"|cTe mueves en las sombras.|n  Duración: |w{dur_txt}|n."

        if efecto == "curar_veneno_protegido":
            from systems.combat.states import limpiar_estado
            estados = dict(getattr(caller.db, "estados", {}) or {})
            caller.db.estados = limpiar_estado(estados, "veneno")
            caller.db.inmune_veneno = True
            return "|gEl antídoto purifica tu sangre y te protege del veneno.|n"

        return "No tiene ningún efecto aparente."

    def consumir(self, caller) -> bool:
        """Aplica el efecto y descuenta un uso. Devuelve True si debe eliminarse."""
        msg = self.aplicar(caller)
        caller.msg(msg)
        usos = self.db.usos
        if usos == -1:
            return False
        usos -= 1
        if usos <= 0:
            return True
        self.db.usos = usos
        return False

    def return_appearance(self, looker, **kwargs):
        desc = self.db.desc or "Un objeto consumible sin descripción."
        efecto = self.db.efecto or "curar_hp"
        potencia = self.db.potencia or 0
        usos = self.db.usos

        if efecto == "buff_stat":
            stat = self.db.stat_buff or "?"
            dur = int(self.db.duracion or 0) // 60
            efecto_txt = f"+{potencia} {stat} durante {dur} min"
        elif efecto == "buff_xp":
            pct = int(potencia * 100)
            dur = int(self.db.duracion or 0) // 60
            efecto_txt = f"+{pct}% XP durante {dur} min"
        else:
            efecto_txt = {
                "curar_hp":               f"Restaura {potencia} HP",
                "curar_maximo":           "Restaura HP al máximo",
                "curar_veneno":           "Cura el envenenamiento",
                "sigilo":                 f"Sigilo {potencia // 60} min",
                "curar_veneno_protegido": "Cura veneno + Inmunidad (1 combate)",
            }.get(efecto, efecto)

        usos_txt = "ilimitados" if usos == -1 else f"{usos} uso{'s' if usos != 1 else ''}"

        return (
            f"|w{self.key}|n |c[consumible]|n\n"
            f"{desc}\n"
            f"Efecto: {efecto_txt}  —  Usos: {usos_txt}"
        )


class Key(DefaultObject):
    """
    Llave con varias formas de autorización:
      - db.keycode: código exacto
      - db.keycodes: lista de códigos exactos (master por lista)
      - db.keyprefixes: lista de prefijos (master por prefijo)
      - db.is_master: True => abre todo
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.keycode = None          # ej: "bronce-01"
        self.db.keycodes = []           # ej: ["bronce-01", "bronce-02"]
        self.db.keyprefixes = []        # ej: ["bronce-", "ciudad-"]
        self.db.is_master = False       # ej: True
