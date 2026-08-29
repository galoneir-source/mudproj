"""
tests/test_bounty.py

Tests de integración Evennia para el sistema de cazarrecompensas:
CmdRecompensa (poner/cancelar/tablon/mias), CmdCazar y el gancho real de
pago en features/bounty/bounty_script.py::cobrar_recompensa_por_duelo,
llamado desde CombatHandler._fin_duelo().

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_bounty
"""
from evennia.utils import create
from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest

from features.bounty.commands import CmdRecompensa, CmdCazar
from features.bounty.bounty_script import RecompensasScript, obtener_recompensas_script
from systems.bounty.bounty import MIN_RECOMPENSA
from typeclasses.characters import Character
from typeclasses.rooms import Room


class JugadorDePrueba(Character):
    """has_account real requiere sesión conectada; para simular un jugador
    presente sin montar una sesión real, se sobreescribe la propiedad --
    mismo truco usado en test_arena.py / test_guild_wars.py. Solo se usa
    para el OBJETIVO, que nunca necesita llamar a caller.search() (eso
    exige un account real, que este typeclass no tiene)."""

    @property
    def has_account(self):
        return True


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
        char.msg = lambda text=None, **kw: self.msgs.append(str(text))

    def all(self):
        return "\n".join(self.msgs)


class TestCazaRecompensaCancelacion(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.script = create_script(RecompensasScript, key="recompensas_script", persistent=True)
        self.sala = create.create_object(Room, key="Plaza de prueba")

        # char1 = emisor, char2 = cazador (ambos con account real, necesario
        # para caller.search()); objetivo es un personaje aparte que nunca
        # llama a ningún comando, así que no necesita account real.
        self.emisor = self.char1
        self.cazador = self.char2
        self.objetivo = create.create_object(JugadorDePrueba, key="Objetivo", location=self.sala)

        for char in (self.emisor, self.cazador, self.objetivo):
            char.db.monedas = 1000
            char.msg = lambda text=None, **kw: None
            char.move_to(self.sala, quiet=True)

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def _poner_bounty(self):
        _make_cmd(CmdRecompensa, self.emisor, f"poner Objetivo {MIN_RECOMPENSA}").func()

    def test_cancelar_normalmente_funciona(self):
        self._poner_bounty()
        _make_cmd(CmdRecompensa, self.emisor, "cancelar Objetivo").func()
        self.assertEqual(self.emisor.db.monedas, 1000)

    def test_no_se_puede_cancelar_mientras_hay_una_caza_en_curso(self):
        """
        Regresión: recompensa cancelar no comprobaba si el objetivo estaba
        en ese mismo instante en un combate de caza de recompensa activo.
        cazar() solo lee el total de recompensas al FINAL del combate
        (_fin_duelo -> cobrar_recompensa_por_duelo), no al empezarlo, así
        que el emisor podía ver que su objetivo estaba perdiendo y
        cancelar su recompensa a mitad del combate para no pagarla,
        dejando al cazador con menos premio del anunciado -- o ninguno,
        si era la única recompensa activa -- pese a ganar limpiamente.
        """
        self._poner_bounty()
        cap = _MsgCapture(self.emisor)

        _make_cmd(CmdCazar, self.cazador, "Objetivo").func()

        _make_cmd(CmdRecompensa, self.emisor, "cancelar Objetivo").func()

        self.assertEqual(self.emisor.db.monedas, 1000 - MIN_RECOMPENSA)
        self.assertIn("caza en curso", cap.all().lower())

        script = obtener_recompensas_script()
        self.assertEqual(len(list(script.db.bounties or [])), 1)

    def test_cancelar_funciona_de_nuevo_tras_terminar_la_caza(self):
        self._poner_bounty()
        _make_cmd(CmdCazar, self.cazador, "Objetivo").func()

        handler = None
        for s in self.sala.scripts.all():
            if s.key == "combat_handler":
                handler = s
                break
        self.assertIsNotNone(handler)
        handler._fin_duelo(ganador=self.objetivo, perdedor=self.cazador)

        _make_cmd(CmdRecompensa, self.emisor, "cancelar Objetivo").func()
        self.assertEqual(self.emisor.db.monedas, 1000)
