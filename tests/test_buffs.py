"""
tests/test_buffs.py

Tests de integración para el sistema de buffs temporales (v0.34).
Cubre: CmdUsar consumiendo un objeto con efecto buff_stat/buff_xp,
CmdBuffs, y la lectura real de los buffs desde CombatHandler
(_get_stats para bonus de stat, _dar_xp_a_grupo para el factor de XP).

Antes de este archivo, tests/test_buffs.py contenía en realidad los
tests PUROS de systems/buffs/buffs.py (movidos a tests/test_buffs_system.py,
siguiendo la convención de CLAUDE.md) y no existía ningún test de
integración: nada ejercitaba CmdUsar consumiendo un objeto real con
efecto buff_stat/buff_xp, ni la lectura de esos buffs desde
CombatHandler._get_stats()/_dar_xp_a_grupo().

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_buffs
"""
from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.objects import Consumible
from commands.general_commands import CmdUsar
from features.buffs.commands import CmdBuffs


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


def _crear_buff_stat(location, stat="fuerza", potencia=3, duracion=1200):
    obj = create_object(Consumible, key="cerveza de combate", location=location)
    obj.db.efecto = "buff_stat"
    obj.db.stat_buff = stat
    obj.db.potencia = potencia
    obj.db.duracion = duracion
    obj.db.usos = 1
    return obj


def _crear_buff_xp(location, potencia=0.15, duracion=1800):
    obj = create_object(Consumible, key="estofado vigorizante", location=location)
    obj.db.efecto = "buff_xp"
    obj.db.potencia = potencia
    obj.db.duracion = duracion
    obj.db.usos = 1
    return obj


# --------------------------------------------------------------------------- #
#  CmdUsar — consumir un objeto con efecto buff_stat / buff_xp
# --------------------------------------------------------------------------- #

class TestCmdUsarBuff(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.buffs_activos = []
        self.char1.location.msg_contents = lambda m, **kw: None
        self.cap = _MsgCapture(self.char1)

    def _usar(self, args):
        cmd = _make_cmd(CmdUsar, self.char1, args)
        cmd.func()

    def test_usar_buff_stat_lo_registra(self):
        _crear_buff_stat(self.char1, stat="fuerza", potencia=3)
        self._usar("cerveza de combate")
        buffs = list(self.char1.db.buffs_activos or [])
        self.assertEqual(len(buffs), 1)
        self.assertEqual(buffs[0]["tipo"], "buff_stat")
        self.assertEqual(buffs[0]["stat"], "fuerza")
        self.assertEqual(buffs[0]["bonus"], 3)

    def test_usar_buff_stat_confirma_al_jugador(self):
        _crear_buff_stat(self.char1, stat="fuerza", potencia=3)
        self._usar("cerveza de combate")
        self.assertIn("fuerza", self.cap.all().lower())

    def test_usar_buff_xp_lo_registra(self):
        _crear_buff_xp(self.char1, potencia=0.15)
        self._usar("estofado vigorizante")
        buffs = list(self.char1.db.buffs_activos or [])
        self.assertEqual(len(buffs), 1)
        self.assertEqual(buffs[0]["tipo"], "buff_xp")
        self.assertAlmostEqual(buffs[0]["bonus"], 0.15)

    def test_usar_buff_stat_se_agota_tras_un_uso(self):
        poc = _crear_buff_stat(self.char1)
        poc_id = poc.id
        self._usar("cerveza de combate")
        from evennia import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=poc_id).exists())

    def test_dos_buffs_de_stat_distinta_coexisten(self):
        _crear_buff_stat(self.char1, stat="fuerza", potencia=3)
        self._usar("cerveza de combate")
        obj2 = create_object(Consumible, key="vino del explorador", location=self.char1)
        obj2.db.efecto = "buff_stat"
        obj2.db.stat_buff = "destreza"
        obj2.db.potencia = 3
        obj2.db.duracion = 1200
        obj2.db.usos = 1
        self._usar("vino del explorador")
        buffs = list(self.char1.db.buffs_activos or [])
        self.assertEqual(len(buffs), 2)


# --------------------------------------------------------------------------- #
#  CmdBuffs — mostrar buffs activos
# --------------------------------------------------------------------------- #

class TestCmdBuffs(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.cap = _MsgCapture(self.char1)

    def test_sin_buffs_informa(self):
        self.char1.db.buffs_activos = []
        cmd = _make_cmd(CmdBuffs, self.char1, "")
        cmd.func()
        self.assertIn("ningún buff", self.cap.all().lower())

    def test_con_buff_activo_lo_muestra(self):
        from systems.buffs.buffs import aplicar_buff
        self.char1.db.buffs_activos = aplicar_buff(
            [], "buff_stat", 3, "Cerveza de Combate", 1200, "fuerza"
        )
        cmd = _make_cmd(CmdBuffs, self.char1, "")
        cmd.func()
        self.assertIn("Cerveza de Combate", self.cap.all())


# --------------------------------------------------------------------------- #
#  CombatHandler — lectura real de buffs (bonus de stat y factor de XP)
# --------------------------------------------------------------------------- #

class TestCombatHandlerLeeBuffs(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.inteligencia = 10
        self.char1.db.fuerza = 10
        self.char1.db.destreza = 10

    def test_get_stats_aplica_bonus_stat_activo(self):
        from systems.buffs.buffs import aplicar_buff
        from features.combat.handler import _get_stats
        self.char1.db.buffs_activos = aplicar_buff(
            [], "buff_stat", 3, "Cerveza de Combate", 1200, "fuerza"
        )
        stats = _get_stats(self.char1)
        self.assertEqual(stats["fuerza"], 13)

    def test_get_stats_ignora_buff_expirado(self):
        import time
        self.char1.db.buffs_activos = [
            {"tipo": "buff_stat", "bonus": 3, "expira": time.time() - 10,
             "nombre": "Vieja Cerveza", "stat": "fuerza"}
        ]
        from features.combat.handler import _get_stats
        stats = _get_stats(self.char1)
        self.assertEqual(stats["fuerza"], 10)

    def test_get_stats_sin_cuenta_no_aplica_buff(self):
        # Un NPC (sin has_account) no debe recibir bonuses de buffs de taberna.
        from systems.buffs.buffs import aplicar_buff
        from features.combat.handler import _get_stats
        npc = create_object("typeclasses.npc.NPC", key="goblin", location=self.room1)
        npc.db.fuerza = 10
        npc.db.buffs_activos = aplicar_buff(
            [], "buff_stat", 3, "Cerveza de Combate", 1200, "fuerza"
        )
        stats = _get_stats(npc)
        self.assertEqual(stats["fuerza"], 10)


class TestGrupoXpAplicaBuffXp(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.char1.db.experiencia = 0
        self.char1.db.nivel = 1
        self.char1.db.monedas = 0
        self.char1.db.buffs_activos = []
        self.char1.msg = lambda text=None, **kw: None

        from features.combat.handler import CombatHandler
        self.handler = create_script(CombatHandler, obj=self.room1, key="combat_handler")
        self.handler.db.activo = True
        self.handler.db.participantes = [self.char1]

    def tearDown(self):
        try:
            self.handler.delete()
        except Exception:
            pass
        super().tearDown()

    def test_dar_xp_a_grupo_aplica_factor_buff_xp(self):
        # xp_base=40 se mantiene por debajo del umbral de subida de nivel
        # 1→2 (100, ver XP_POR_NIVEL en systems/combat/engine.py) incluso
        # con el buff aplicado, para no mezclar la lógica de nivel con la
        # de buffs en esta aserción.
        from systems.buffs.buffs import aplicar_buff
        self.char1.db.buffs_activos = aplicar_buff(
            [], "buff_xp", 0.5, "Estofado Vigorizante", 1800
        )
        self.handler._dar_xp_a_grupo(self.char1, 40)
        self.assertEqual(self.char1.db.experiencia, 60)

    def test_dar_xp_a_grupo_sin_buff_no_altera(self):
        self.handler._dar_xp_a_grupo(self.char1, 40)
        self.assertEqual(self.char1.db.experiencia, 40)


if __name__ == "__main__":
    import unittest
    unittest.main()
