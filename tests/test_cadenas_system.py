"""
tests/test_cadenas_system.py

Tests de integración Evennia para el sistema de misiones encadenadas (v0.20.0).
Cubre: aceptar quests con prerrequisito, hablar NPC muestra próximas quests,
entregar quests en cadena desbloquea la siguiente.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_cadenas_system
"""
from evennia.utils.test_resources import EvenniaTest

from features.quests.commands import CmdAceptar, CmdEntregar, CmdMisiones
from systems.quests.quests import QUESTS, quest_disponible


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


def _init_char(char, nivel=10):
    char.db.nivel = nivel
    char.db.quests = {}
    char.db.monedas = 200
    char.db.experiencia = 0
    char.db.reputacion = {}
    char.db.habilidades_desbloqueadas = ["golpe_fuerte", "golpe_rapido"]
    char.db.logros = []
    char.db.titulo_activo = None
    char.db.kills_totales = 0
    char.db.jefes_derrotados = []
    char.db.objetos_crafteados = 0
    char.db.encantamiento_max = 0
    char.db.banco_usado = False


class _MsgCapture:
    def __init__(self, char):
        self.msgs = []
        char.msg = lambda m, **kw: self.msgs.append(str(m))
        if char.location:
            char.location.msg_contents = lambda m, **kw: None

    def all(self):
        return "\n".join(self.msgs)


# ---------------------------------------------------------------------------
# Aceptar quests encadenadas
# ---------------------------------------------------------------------------

class TestAceptarCadenadas(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _aceptar(self, args):
        cmd = _make_cmd(CmdAceptar, self.char1, args)
        cmd.func()

    def test_ecos_bloqueada_sin_prereq(self):
        self._aceptar("Los Ecos del Barón")
        self.assertNotIn("ecos_del_baron", dict(self.char1.db.quests or {}))
        self.assertIn("Primero debes completar", self.cap.all())

    def test_secretos_bloqueada_sin_prereq(self):
        self._aceptar("secretos de la torre")
        self.assertNotIn("secretos_de_la_torre", dict(self.char1.db.quests or {}))
        self.assertIn("Primero debes completar", self.cap.all())

    def test_ecos_disponible_con_prereq(self):
        self.char1.db.quests = {"caballero_sombras": {"estado": "entregada"}}
        # Necesitamos un NPC dador en la sala
        npc = self.char2
        npc.key = "Hermano Aldric el sacerdote"
        npc.db.dialogo = {}
        npc.move_to(self.room1, quiet=True)
        self._aceptar("Los Ecos del Barón")
        quests = dict(self.char1.db.quests or {})
        self.assertIn("ecos_del_baron", quests)
        self.assertEqual(quests["ecos_del_baron"]["estado"], "activa")

    def test_legion_bloqueada_sin_ecos(self):
        self.char1.db.quests = {"caballero_sombras": {"estado": "entregada"}}
        self._aceptar("La Legión en Marcha")
        self.assertNotIn("legion_en_marcha", dict(self.char1.db.quests or {}))
        self.assertIn("Primero debes completar", self.cap.all())

    def test_cadena_1_completa_funciona(self):
        # Completar toda la cadena 1 hasta poder aceptar filo_del_abismo
        self.char1.db.quests = {
            "caballero_sombras": {"estado": "entregada"},
            "ecos_del_baron": {"estado": "entregada"},
            "legion_en_marcha": {"estado": "entregada"},
        }
        ok, _ = quest_disponible("filo_del_abismo", nivel=10, quests_personaje=self.char1.db.quests)
        self.assertTrue(ok)


# ---------------------------------------------------------------------------
# CmdMisiones muestra quests encadenadas
# ---------------------------------------------------------------------------

class TestMisionesConCadenas(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _misiones(self, args=""):
        cmd = _make_cmd(CmdMisiones, self.char1, args)
        cmd.func()

    def test_misiones_muestra_activas(self):
        self.char1.db.quests = {
            "ecos_del_baron": {"estado": "activa", "progreso": {}}
        }
        self._misiones()
        self.assertIn("Los Ecos del Barón", self.cap.all())

    def test_misiones_detalle_ecos(self):
        self.char1.db.quests = {
            "ecos_del_baron": {"estado": "activa", "progreso": {}}
        }
        self._misiones("Los Ecos del Barón")
        texto = self.cap.all().lower()
        self.assertIn("fragmento", texto)
        self.assertIn("alma oscura", texto)

    def test_misiones_detalle_esencia(self):
        self.char1.db.quests = {
            "esencia_del_poder": {"estado": "activa", "progreso": {}}
        }
        self._misiones("La Esencia del Poder")
        texto = self.cap.all()
        self.assertIn("esencia del liche", texto.lower())


# ---------------------------------------------------------------------------
# hablar NPC muestra misiones próximas (bloqueadas por prereq)
# ---------------------------------------------------------------------------

class TestHablarNpcMisionesProximas(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        # Crear NPC falso tipo Aldric
        self.npc_aldric = self.char2
        self.npc_aldric.key = "Hermano Aldric el sacerdote"
        self.npc_aldric.db.dialogo = {"hola": "Que los dioses te guíen."}
        self.npc_aldric.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _mostrar_misiones(self):
        from commands.general_commands import CmdHablar
        cmd = _make_cmd(CmdHablar, self.char1, f"{self.npc_aldric.key} = misión")
        cmd.func()

    def test_sin_prereq_no_muestra_proximas(self):
        self._mostrar_misiones()
        self.assertNotIn("Próximamente", self.cap.all())

    def test_con_prereq_en_log_muestra_proxima(self):
        # Si el jugador tiene caballero_sombras en su log (cualquier estado),
        # debería ver ecos_del_baron como "próxima"
        self.char1.db.quests = {"caballero_sombras": {"estado": "activa"}}
        self._mostrar_misiones()
        texto = self.cap.all()
        self.assertIn("Próximamente", texto)
        self.assertIn("Los Ecos del Barón", texto)

    def test_con_prereq_entregado_muestra_como_disponible(self):
        # Con prereq entregado, la quest aparece como disponible, no bloqueada
        self.char1.db.quests = {"caballero_sombras": {"estado": "entregada"}}
        self._mostrar_misiones()
        texto = self.cap.all()
        self.assertIn("Los Ecos del Barón", texto)
        self.assertNotIn("Próximamente disponibles:\n    |x·|n Los Ecos", texto)

    def test_segunda_de_cadena_aparece_proxima_si_primera_conocida(self):
        # Si ecos_del_baron está activa, legion_en_marcha debería aparecer como próxima
        self.char1.db.quests = {
            "caballero_sombras": {"estado": "entregada"},
            "ecos_del_baron": {"estado": "activa"},
        }
        self._mostrar_misiones()
        texto = self.cap.all()
        self.assertIn("La Legión en Marcha", texto)


# ---------------------------------------------------------------------------
# Progreso y entrega en cadena
# ---------------------------------------------------------------------------

class TestProgresoEnCadena(EvenniaTest):

    def setUp(self):
        super().setUp()
        _init_char(self.char1)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_kill_progresa_legion_en_marcha(self):
        from systems.quests.quests import registrar_kill
        quests = {"legion_en_marcha": {"estado": "activa", "progreso": {}}}
        resultado = registrar_kill("legion_en_marcha", quests)
        self.assertEqual(resultado["legion_en_marcha"]["progreso"]["kills"], 1)
        self.assertEqual(resultado["legion_en_marcha"]["estado"], "activa")

    def test_tres_kills_completan_legion(self):
        from systems.quests.quests import registrar_kill
        quests = {"legion_en_marcha": {"estado": "activa", "progreso": {"kills": 2}}}
        resultado = registrar_kill("legion_en_marcha", quests)
        self.assertEqual(resultado["legion_en_marcha"]["estado"], "completada")

    def test_entregar_ecos_requiere_items(self):
        self.char1.db.quests = {
            "caballero_sombras": {"estado": "entregada"},
            "ecos_del_baron": {"estado": "activa", "progreso": {}},
        }
        cmd = _make_cmd(CmdEntregar, self.char1, "Los Ecos del Barón")
        cmd.func()
        # Sin items, debería fallar con mensaje de falta
        texto = self.cap.all()
        self.assertIn("faltan", texto.lower())

    def test_entregar_ecos_con_items_da_xp(self):
        self.char1.db.quests = {
            "caballero_sombras": {"estado": "entregada"},
            "ecos_del_baron": {"estado": "activa", "progreso": {}},
        }
        # Crear NPC receptor en sala
        npc = self.char2
        npc.key = "Hermano Aldric el sacerdote"
        npc.db.dialogo = {}
        npc.move_to(self.room1, quiet=True)
        # Añadir items al inventario
        import evennia
        for _ in range(2):
            item = evennia.create_object("typeclasses.objects.Object",
                                         key="fragmento de alma oscura",
                                         location=self.char1)
        xp_antes = self.char1.db.experiencia or 0
        cmd = _make_cmd(CmdEntregar, self.char1, "Los Ecos del Barón")
        cmd.func()
        xp_despues = self.char1.db.experiencia or 0
        self.assertGreater(xp_despues, xp_antes)

    def test_entregar_ecos_desbloquea_legion(self):
        # Después de entregar ecos_del_baron, legion_en_marcha debe estar disponible
        quests = {
            "caballero_sombras": {"estado": "entregada"},
            "ecos_del_baron": {"estado": "entregada"},
        }
        ok, _ = quest_disponible("legion_en_marcha", nivel=10, quests_personaje=quests)
        self.assertTrue(ok)


if __name__ == "__main__":
    import unittest
    unittest.main()
