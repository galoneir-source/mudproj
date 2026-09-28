"""
tests/test_cmd_atacar.py

Tests de integración para CmdAtacar (features/combat/commands.py).
Ejecutar con:
  cd /opt/evennia/mudproj/mygame && evennia test --settings settings.py tests.test_cmd_atacar
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from features.combat.commands import CmdAtacar


def _atacar(caller, args):
    cmd = CmdAtacar()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = f"{cmd.key} {args}"
    cmd.func()


def _handlers(sala):
    return [s for s in sala.scripts.all() if s.key == "combat_handler"]


class TestCmdAtacar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.en_combate = False
        self.msgs = []
        self.char1.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def tearDown(self):
        for sala in (self.room1, self.room2):
            for h in _handlers(sala):
                h.delete()
        super().tearDown()

    def test_atacar_npc_inicia_combate(self):
        npc = create_object("typeclasses.npc.NPC", key="lobo", location=self.room1)
        _atacar(self.char1, "lobo")
        handlers = _handlers(self.room1)
        self.assertEqual(len(handlers), 1)
        self.assertIn(npc, handlers[0].db.participantes)

    def test_no_se_puede_atacar_un_objeto(self):
        # Regresión: el objeto entraba al combate y al "morir" se borraba.
        _atacar(self.char1, "Obj")
        self.assertEqual(_handlers(self.room1), [])
        self.assertFalse(self.obj1.db.en_combate)
        self.assertIn("No puedes atacar", "\n".join(self.msgs))

    def test_no_se_puede_atacar_una_salida(self):
        # Regresión: "atacar <salida>" acababa borrando la salida del mundo.
        _atacar(self.char1, self.exit.key)
        self.assertEqual(_handlers(self.room1), [])
        self.assertTrue(self.exit.pk)

    def test_en_combate_en_otra_sala_no_inicia_un_segundo_combate(self):
        # Regresión: el atacante quedaba en dos CombatHandler a la vez.
        create_object("typeclasses.npc.NPC", key="lobo", location=self.room2)
        create_object("typeclasses.npc.NPC", key="rata", location=self.room1)
        self.char1.move_to(self.room2, quiet=True)
        _atacar(self.char1, "lobo")
        self.assertEqual(len(_handlers(self.room2)), 1)

        self.char1.move_to(self.room1, quiet=True)
        _atacar(self.char1, "rata")
        self.assertEqual(_handlers(self.room1), [])

    def test_objetivo_en_combate_en_otra_sala_no_se_arrastra(self):
        self.char2.move_to(self.room1, quiet=True)
        self.char2.db.en_combate = True
        _atacar(self.char1, "Char2")
        self.assertEqual(_handlers(self.room1), [])
        self.assertIn("ya está en combate", "\n".join(self.msgs))
