"""
tests/test_contratos.py

Tests de integración Evennia para el tablón de contratos (v0.27.0).
Cubre: ContractScript (renovar, obtener), CmdTablon (ver, aceptar, estado,
       cancelar, entregar — kill y entrega).

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_contratos
"""
from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from features.contracts.commands import CmdTablon
from features.contracts.contract_script import ContractScript


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


def _crear_script_contratos():
    return create_script(ContractScript, key="tablón_contratos_test",
                         persistent=False)


def _contrato_kill(cantidad=5, kills_al_aceptar=0):
    return {
        "id":              "test_0",
        "tipo":            "kill",
        "descripcion":     f"Elimina {cantidad} enemigos.",
        "objetivo":        "enemigo",
        "cantidad":        cantidad,
        "kills_al_aceptar": kills_al_aceptar,
        "dificultad":      1,
        "etiqueta":        "★☆☆",
        "recompensa":      {"monedas": 60, "xp": 40},
    }


def _contrato_entrega(cantidad=3, objetivo="mineral de hierro"):
    return {
        "id":          "test_1",
        "tipo":        "entrega",
        "descripcion": f"Entrega {cantidad} {objetivo}.",
        "objetivo":    objetivo,
        "cantidad":    cantidad,
        "dificultad":  2,
        "etiqueta":    "★★☆",
        "recompensa":  {"monedas": 120, "xp": 80},
    }


# --------------------------------------------------------------------------- #
#  ContractScript
# --------------------------------------------------------------------------- #

class TestContractScript(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.script = _crear_script_contratos()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_renovar_genera_contratos(self):
        self.script.renovar()
        contratos = self.script.obtener_contratos()
        self.assertEqual(len(contratos), 5)

    def test_contratos_son_dicts(self):
        self.script.renovar()
        for c in self.script.obtener_contratos():
            self.assertIsInstance(c, dict)

    def test_obtener_contrato_valido(self):
        self.script.renovar()
        c = self.script.obtener_contrato(1)
        self.assertIsNotNone(c)

    def test_obtener_contrato_fuera_de_rango(self):
        self.script.renovar()
        self.assertIsNone(self.script.obtener_contrato(0))
        self.assertIsNone(self.script.obtener_contrato(10))

    def test_obtener_contrato_5(self):
        self.script.renovar()
        c = self.script.obtener_contrato(5)
        self.assertIsNotNone(c)

    def test_renovar_misma_seed_no_cambia(self):
        self.script.renovar()
        contratos_antes = list(self.script.obtener_contratos())
        self.script.renovar()
        contratos_despues = list(self.script.obtener_contratos())
        self.assertEqual(contratos_antes, contratos_despues)


# --------------------------------------------------------------------------- #
#  CmdTablon — mostrar tablón
# --------------------------------------------------------------------------- #

class TestCmdTablonMostrar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.contrato_activo = None
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)
        self.script = _crear_script_contratos()
        self.script.renovar()

    def tearDown(self):
        try:
            self.script.delete()
        except Exception:
            pass
        super().tearDown()

    def test_muestra_cabecera(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.func()
        self.assertIn("Tablón", self.cap.all())

    def test_muestra_contratos(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.func()
        self.assertIn("[1]", self.cap.all())

    def test_muestra_cinco_contratos(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.func()
        texto = self.cap.all()
        for i in range(1, 6):
            self.assertIn(f"[{i}]", texto)

    def test_consejo_aceptar(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.func()
        self.assertIn("aceptar", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdTablon — aceptar contrato
# --------------------------------------------------------------------------- #

class TestCmdTablonAceptar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.contrato_activo = None
        self.char1.db.kills_totales = 10
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_aceptar_asigna_contrato(self):
        script = _crear_script_contratos()
        script.renovar()
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar 1")
        cmd.func()
        script.delete()
        self.assertIsNotNone(self.char1.db.contrato_activo)

    def test_aceptar_confirma_con_mensaje(self):
        script = _crear_script_contratos()
        script.renovar()
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar 1")
        cmd.func()
        script.delete()
        self.assertIn("aceptado", self.cap.all().lower())

    def test_aceptar_con_activo_falla(self):
        self.char1.db.contrato_activo = _contrato_kill()
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar 1")
        cmd.func()
        self.assertIn("ya tienes", self.cap.all().lower())

    def test_aceptar_numero_invalido_falla(self):
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar 99")
        cmd.func()
        self.assertIn("ningún contrato", self.cap.all().lower())

    def test_aceptar_kill_guarda_kills_al_aceptar(self):
        self.char1.db.kills_totales = 42
        script = _crear_script_contratos()
        script.renovar()
        # Forzar un contrato kill en posición 1
        contratos = list(script.db.contratos)
        contratos[0] = _contrato_kill(5)
        script.db.contratos = contratos
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar 1")
        cmd.func()
        script.delete()
        activo = dict(self.char1.db.contrato_activo or {})
        if activo.get("tipo") == "kill":
            self.assertEqual(activo.get("kills_al_aceptar"), 42)

    def test_aceptar_sin_numero_falla(self):
        cmd = _make_cmd(CmdTablon, self.char1, "aceptar abc")
        cmd.func()
        self.assertIn("uso", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdTablon — estado
# --------------------------------------------------------------------------- #

class TestCmdTablonEstado(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.kills_totales = 0
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_contrato_informa(self):
        self.char1.db.contrato_activo = None
        cmd = _make_cmd(CmdTablon, self.char1, "estado")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_con_kill_muestra_progreso(self):
        self.char1.db.kills_totales = 3
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "estado")
        cmd.func()
        self.assertIn("3/5", self.cap.all())

    def test_con_entrega_muestra_material(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        cmd = _make_cmd(CmdTablon, self.char1, "estado")
        cmd.func()
        self.assertIn("mineral de hierro", self.cap.all().lower())

    def test_listo_para_entregar_si_completado(self):
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "estado")
        cmd.func()
        self.assertIn("listo", self.cap.all().lower())

    def test_en_progreso_si_no_completado(self):
        self.char1.db.kills_totales = 2
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "estado")
        cmd.func()
        self.assertIn("progreso", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdTablon — cancelar
# --------------------------------------------------------------------------- #

class TestCmdTablonCancelar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_cancelar_limpia_contrato(self):
        self.char1.db.contrato_activo = _contrato_kill()
        cmd = _make_cmd(CmdTablon, self.char1, "cancelar")
        cmd.func()
        self.assertIsNone(self.char1.db.contrato_activo)

    def test_cancelar_confirma(self):
        self.char1.db.contrato_activo = _contrato_kill()
        cmd = _make_cmd(CmdTablon, self.char1, "cancelar")
        cmd.func()
        self.assertIn("abandonado", self.cap.all().lower())

    def test_cancelar_sin_contrato_informa(self):
        self.char1.db.contrato_activo = None
        cmd = _make_cmd(CmdTablon, self.char1, "cancelar")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdTablon — entregar kill
# --------------------------------------------------------------------------- #

class TestCmdTablonEntregarKill(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.kills_totales = 0
        self.char1.db.monedas = 50
        self.char1.db.experiencia = 0
        self.char1.db.nivel = 1
        self.char1.db.hp = 30
        self.char1.db.hp_max = 30
        self.char1.db.ataque = 5
        self.char1.db.defensa = 3
        self.char1.db.quests = {}
        self.char1.db.jefes_derrotados = []
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_sin_contrato_activo_falla(self):
        self.char1.db.contrato_activo = None
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("no tienes", self.cap.all().lower())

    def test_kill_insuficiente_falla(self):
        self.char1.db.kills_totales = 3
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("faltan", self.cap.all().lower())
        self.assertIsNotNone(self.char1.db.contrato_activo)

    def test_kill_completado_da_recompensa_monedas(self):
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertEqual(self.char1.db.monedas, 50 + 60)

    def test_kill_completado_da_xp(self):
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertEqual(self.char1.db.experiencia, 40)

    def test_kill_completado_aplica_buff_de_xp(self):
        """
        Regresión: factor_xp() (buffs_activos, p.ej. Estofado Vigorizante)
        solo se aplicaba en _dar_xp_a_grupo() (kills de combate normal)
        desde que se introdujo este buff en v0.34.0 -- contratos nunca
        retomó esta integración, así que el mismo buff que promete "+N%
        XP" sin excepción de alcance no tenía ningún efecto al entregar
        un contrato.
        """
        import time

        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        self.char1.db.buffs_activos = [{
            "tipo": "buff_xp", "bonus": 0.5, "nombre": "Estofado Vigorizante",
            "expira": time.time() + 1800,
        }]
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertEqual(self.char1.db.experiencia, int(40 * 1.5))

    def test_kill_completado_limpia_contrato(self):
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIsNone(self.char1.db.contrato_activo)

    def test_kill_completado_mensaje_exito(self):
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("completado", self.cap.all().lower())

    def test_kill_completado_comprueba_logros(self):
        """
        Regresión: _dar_recompensa() importaba
        'features.achievements.hooks.comprobar_y_notificar' — ese módulo no
        existe (el real es 'features.achievements.commands'). El
        ImportError quedaba silenciado por un except Exception genérico,
        así que completar un contrato nunca disparaba la comprobación de
        logros (p.ej. subir de nivel o cruzar un umbral de monedas vía la
        recompensa del contrato no se notificaba hasta la siguiente acción
        no relacionada que sí llamara a comprobar_y_notificar).
        """
        from unittest.mock import patch

        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        with patch(
            "features.achievements.commands.comprobar_y_notificar"
        ) as mock_comprobar:
            cmd = _make_cmd(CmdTablon, self.char1, "entregar")
            cmd.func()
            mock_comprobar.assert_called_once_with(self.char1)

    def test_kill_faltan_indica_cuantos(self):
        self.char1.db.kills_totales = 2
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("3", self.cap.all())  # faltan 3

    def test_kill_completado_con_subida_de_nivel_no_crashea(self):
        """
        Regresión: el mensaje de subida de nivel en _dar_recompensa()
        (features/contracts/commands.py) leía nuevos_stats['ataque'], una
        clave que no existe en el dict que devuelve procesar_subida_de_nivel()
        (systems/combat/engine.py) -- STAT_DEFAULTS no tiene ningún stat
        "ataque" en todo el proyecto. Completar un contrato con recompensa de
        XP suficiente para subir de nivel lanzaba un KeyError sin capturar,
        que interrumpía _entregar() a medias: la recompensa (monedas, XP, y
        los materiales consumidos en un contrato de entrega) ya se había
        aplicado, pero contrato_activo nunca se limpiaba -- el jugador se
        quedaba con "ya tienes un contrato activo" para siempre, sin poder
        aceptar otro ni ver ningún mensaje de éxito.
        """
        self.char1.db.experiencia = 70  # + 40 de recompensa = 110 >= 100 (nivel 2)
        self.char1.db.kills_totales = 10
        self.char1.db.contrato_activo = _contrato_kill(5, kills_al_aceptar=0)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()  # no debe lanzar KeyError

        self.assertIsNone(self.char1.db.contrato_activo)
        self.assertEqual(self.char1.db.nivel, 2)
        self.assertIn("completado", self.cap.all().lower())


# --------------------------------------------------------------------------- #
#  CmdTablon — entregar materiales
# --------------------------------------------------------------------------- #

class TestCmdTablonEntregarMateriales(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.monedas = 50
        self.char1.db.experiencia = 0
        self.char1.db.nivel = 1
        self.char1.db.hp = 30
        self.char1.db.hp_max = 30
        self.char1.db.ataque = 5
        self.char1.db.defensa = 3
        self.char1.db.quests = {}
        self.char1.db.jefes_derrotados = []
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def _crear_materiales(self, nombre, cantidad):
        for _ in range(cantidad):
            obj = create_object(
                "typeclasses.objects.Object",
                key=nombre,
                location=self.char1,
            )
        return obj

    def test_entrega_insuficiente_falla(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 2)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("necesitas", self.cap.all().lower())
        self.assertIsNotNone(self.char1.db.contrato_activo)

    def test_entrega_sin_materiales_falla(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("necesitas", self.cap.all().lower())

    def test_entrega_exitosa_da_recompensa(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertEqual(self.char1.db.monedas, 50 + 120)

    def test_entrega_exitosa_da_xp(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertEqual(self.char1.db.experiencia, 80)

    def test_entrega_exitosa_consume_materiales(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        restantes = sum(
            1 for o in self.char1.contents
            if o.key.lower() == "mineral de hierro"
        )
        self.assertEqual(restantes, 0)

    def test_entrega_exitosa_consume_solo_necesarios(self):
        self.char1.db.contrato_activo = _contrato_entrega(2, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 4)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        restantes = sum(
            1 for o in self.char1.contents
            if o.key.lower() == "mineral de hierro"
        )
        self.assertEqual(restantes, 2)

    def test_entrega_exitosa_limpia_contrato(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIsNone(self.char1.db.contrato_activo)

    def test_entrega_exitosa_muestra_completado(self):
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()
        self.assertIn("completado", self.cap.all().lower())

    def test_entrega_con_subida_de_nivel_no_crashea(self):
        """
        Mismo bug que en TestCmdTablonEntregarKill, verificado en la ruta de
        entrega: _dar_recompensa() es la misma función para ambos tipos de
        contrato, así que un KeyError('ataque') a mitad de la entrega
        dejaba los materiales ya consumidos y contrato_activo sin limpiar.
        """
        self.char1.db.experiencia = 20  # + 80 de recompensa = 100 >= 100 (nivel 2)
        self.char1.db.contrato_activo = _contrato_entrega(3, "mineral de hierro")
        self._crear_materiales("mineral de hierro", 3)
        cmd = _make_cmd(CmdTablon, self.char1, "entregar")
        cmd.func()  # no debe lanzar KeyError

        self.assertIsNone(self.char1.db.contrato_activo)
        self.assertEqual(self.char1.db.nivel, 2)


# --------------------------------------------------------------------------- #
#  Alias del comando
# --------------------------------------------------------------------------- #

class TestCmdTablonAliases(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.db.contrato_activo = None
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_alias_tablon_sin_tilde(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.cmdstring = "tablon"
        cmd.func()
        self.assertIn("Tablón", self.cap.all())

    def test_alias_contratos(self):
        cmd = _make_cmd(CmdTablon, self.char1, "")
        cmd.cmdstring = "contratos"
        cmd.func()
        self.assertIn("Tablón", self.cap.all())


if __name__ == "__main__":
    import unittest
    unittest.main()
