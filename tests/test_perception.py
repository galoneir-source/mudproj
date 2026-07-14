"""
tests/test_perception.py

Tests de integración para CmdPercibir (commands/general_commands.py).

Antes de este archivo, tests/test_perception.py contenía en realidad los
tests puros de systems/perception/perception_manager.py (movidos a
tests/test_perception_system.py, siguiendo la convención de CLAUDE.md).
Ningún test en el proyecto instanciaba CmdPercibir directamente — los
tests de clima/hora (test_weather.py::TestWeatherPercepcion,
test_time.py::TestPercepcionNocturna) llaman a PerceptionManager
directamente, saltándose el comando real por completo.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_perception
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.general_commands import CmdPercibir


def _make_cmd(CmdClass, caller, args=""):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = []
    cmd.lhs = args
    cmd.rhs = ""
    return cmd


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        cap = self

        def _capture(m=None, **kw):
            text = m
            if text is None:
                text = kw.get("text", "")
            if isinstance(text, tuple):
                text = text[0]
            cap.msgs.append(str(text or ""))

        char.msg = _capture

    def all(self):
        return "\n".join(self.msgs)


class TestCmdPercibirDetallesOcultos(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.inteligencia = 20
        self.char1.db.nivel = 10
        self.room1.db.exterior = False  # evitar acoplar con clima/hora reales
        self.room1.msg_contents = lambda m, **kw: None
        self.cap = _MsgCapture(self.char1)

    def _percibir(self):
        cmd = _make_cmd(CmdPercibir, self.char1, "")
        cmd.func()

    def test_revela_detalle_al_alcance(self):
        self.room1.db.detalles_ocultos = [
            {"texto": "Hay una grieta sospechosa en la pared.", "req_percepcion": 5}
        ]
        self._percibir()
        self.assertIn("grieta sospechosa", self.cap.all())

    def test_no_revela_detalle_fuera_de_alcance(self):
        self.char1.db.inteligencia = 1
        self.char1.db.nivel = 1
        self.room1.db.detalles_ocultos = [
            {"texto": "Secreto muy difícil de notar.", "req_percepcion": 99}
        ]
        self._percibir()
        self.assertNotIn("Secreto muy difícil", self.cap.all())

    def test_sin_detalles_no_falla(self):
        self.room1.db.detalles_ocultos = []
        self._percibir()
        self.assertIn("Percepción", self.cap.all())


class TestCmdPercibirEntidadesOcultas(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.inteligencia = 20
        self.char1.db.nivel = 10
        self.room1.db.exterior = False
        self.room1.msg_contents = lambda m, **kw: None
        self.cap = _MsgCapture(self.char1)

    def _percibir(self):
        cmd = _make_cmd(CmdPercibir, self.char1, "")
        cmd.func()

    def test_detecta_npc_oculto_alcanzable(self):
        npc = create_object("typeclasses.npc.NPC", key="asesino sombrío", location=self.room1)
        npc.db.oculto = True
        npc.db.nivel_sigilo = 5
        npc.db.nivel = 3
        self._percibir()
        self.assertIn("asesino sombrío", self.cap.all())

    def test_no_detecta_npc_oculto_fuera_de_alcance(self):
        self.char1.db.inteligencia = 1
        self.char1.db.nivel = 1
        npc = create_object("typeclasses.npc.NPC", key="asesino invisible", location=self.room1)
        npc.db.oculto = True
        npc.db.nivel_sigilo = 99
        self._percibir()
        self.assertNotIn("asesino invisible", self.cap.all())

    def test_objeto_no_oculto_no_aparece_como_hallazgo(self):
        from typeclasses.objects import Object
        create_object(Object, key="piedra normal", location=self.room1)
        self._percibir()
        self.assertNotIn("Descubres", self.cap.all())

    def test_sin_sala_informa(self):
        self.char1.location = None
        self._percibir()
        self.assertIn("ningún lugar", self.cap.all().lower())


if __name__ == "__main__":
    import unittest
    unittest.main()
