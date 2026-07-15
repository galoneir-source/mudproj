"""
tests/test_doors.py

Tests de integración para el sistema de Puertas (features/doors): DoorExit
(abrir/cerrar/bloquear/desbloquear, sincronización con el par, bloqueo de
tránsito), find_door_exit_in_room (resolución por nombre/índice/prefijo),
CmdDoor (creación de puertas emparejadas) y CmdKeyMake (creación de llaves).

No existía ningún test para este sistema — ni siquiera parcial — pese a
ser el patrón (sistema sin ningún test de integración) que más bugs
reales ha escondido durante esta sesión de revisiones.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_doors
"""
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from features.doors.typeclasses import DoorExit, _find_key_by_id
from features.doors.utils import find_door_exit_in_room, list_doors_in_room
from features.doors.commands import (
    CmdOpenDoor, CmdCloseDoor, CmdLockDoor, CmdUnlockDoor, CmdDoorStatus,
)
from features.doors.builder import CmdDoor, CmdKeyMake
from typeclasses.objects import Key


def _make_cmd(CmdClass, caller, args="", switches=None, lhs=None, rhs=None):
    cmd = CmdClass()
    cmd.caller = caller
    cmd.args = args
    cmd.cmdstring = cmd.key
    cmd.session = None
    cmd.obj = caller
    cmd.raw_string = cmd.key + (" " + args if args else "")
    cmd.switches = switches or []
    cmd.lhs = lhs if lhs is not None else args
    cmd.rhs = rhs if rhs is not None else ""
    cmd.key_id = None
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


def _crear_puerta_par(room_a, room_b, key_a="norte", key_b="sur"):
    """Crea dos DoorExit emparejados entre dos salas, cerrados y desbloqueados."""
    exit_out = create_object(DoorExit, key=key_a, location=room_a, destination=room_b)
    exit_back = create_object(DoorExit, key=key_b, location=room_b, destination=room_a)
    exit_out.db.paired_exit = exit_back
    exit_back.db.paired_exit = exit_out
    return exit_out, exit_back


class TestDoorExitEstadoBasico(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.puerta, self.puerta_vuelta = _crear_puerta_par(self.room1, self.room2)

    def tearDown(self):
        self.puerta.delete()
        self.puerta_vuelta.delete()
        super().tearDown()

    def test_puerta_empieza_cerrada_y_desbloqueada(self):
        self.assertFalse(self.puerta.db.is_open)
        self.assertFalse(self.puerta.db.is_locked)

    def test_abrir_puerta_cambia_estado(self):
        ok, msg = self.puerta.open(self.char1)
        self.assertTrue(ok)
        self.assertTrue(self.puerta.db.is_open)

    def test_abrir_dos_veces_falla(self):
        self.puerta.open(self.char1)
        ok, msg = self.puerta.open(self.char1)
        self.assertFalse(ok)

    def test_cerrar_puerta_abierta(self):
        self.puerta.open(self.char1)
        ok, msg = self.puerta.close()
        self.assertTrue(ok)
        self.assertFalse(self.puerta.db.is_open)

    def test_cerrar_ya_cerrada_falla(self):
        ok, msg = self.puerta.close()
        self.assertFalse(ok)

    def test_bloquear_sin_key_id_requiere_builder(self):
        # EvenniaTest da permiso "Developer" a char1 por defecto (superior a
        # Builder en la jerarquía de Evennia), así que hay que simular
        # explícitamente un personaje sin permiso para probar el rechazo.
        self.char1.check_permstring = lambda perm: False
        ok, msg = self.puerta.lock(self.char1)
        self.assertFalse(ok)
        self.assertIn("permiso", msg)

    def test_bloquear_sin_key_id_con_builder_funciona(self):
        self.char1.check_permstring = lambda perm: perm == "Builder"
        ok, msg = self.puerta.lock(self.char1)
        self.assertTrue(ok)
        self.assertTrue(self.puerta.db.is_locked)

    def test_bloquear_puerta_abierta_falla(self):
        self.puerta.open(self.char1)
        self.char1.check_permstring = lambda perm: perm == "Builder"
        ok, msg = self.puerta.lock(self.char1)
        self.assertFalse(ok)
        self.assertIn("Ciérrala", msg)


class TestDoorExitSincronizacionConPar(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.puerta, self.puerta_vuelta = _crear_puerta_par(self.room1, self.room2)
        self.char1.check_permstring = lambda perm: perm == "Builder"

    def tearDown(self):
        self.puerta.delete()
        self.puerta_vuelta.delete()
        super().tearDown()

    def test_abrir_un_lado_abre_el_par(self):
        self.puerta.open(self.char1)
        self.assertTrue(self.puerta_vuelta.db.is_open)

    def test_cerrar_un_lado_cierra_el_par(self):
        self.puerta.open(self.char1)
        self.puerta.close()
        self.assertFalse(self.puerta_vuelta.db.is_open)

    def test_bloquear_un_lado_bloquea_el_par(self):
        self.puerta.lock(self.char1)
        self.assertTrue(self.puerta_vuelta.db.is_locked)

    def test_desbloquear_un_lado_desbloquea_el_par(self):
        self.puerta.lock(self.char1)
        self.puerta.unlock(self.char1)
        self.assertFalse(self.puerta_vuelta.db.is_locked)

    def test_key_id_se_propaga_al_par(self):
        self.puerta.db.key_id = "cobre_01"
        self.puerta.open(self.char1)  # cualquier acción dispara _sync_to_pair
        self.puerta.close()
        self.assertEqual(self.puerta_vuelta.db.key_id, "cobre_01")

    def test_borrar_una_puerta_limpia_el_enlace_del_par(self):
        self.puerta.delete()
        self.assertIsNone(self.puerta_vuelta.db.paired_exit)


class TestDoorExitConLlave(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.puerta, self.puerta_vuelta = _crear_puerta_par(self.room1, self.room2)
        self.puerta.db.key_id = "bronce_01"
        self.puerta_vuelta.db.key_id = "bronce_01"

    def tearDown(self):
        self.puerta.delete()
        self.puerta_vuelta.delete()
        super().tearDown()

    def test_bloquear_sin_llave_falla(self):
        ok, msg = self.puerta.lock(self.char1)
        self.assertFalse(ok)
        self.assertIn("llave", msg.lower())

    def test_bloquear_con_llave_correcta(self):
        llave = create_object(Key, key="llave de bronce", location=self.char1)
        llave.db.keycode = "bronce_01"
        ok, msg = self.puerta.lock(self.char1)
        self.assertTrue(ok)

    def test_desbloquear_con_llave_incorrecta_falla(self):
        llave = create_object(Key, key="llave equivocada", location=self.char1)
        llave.db.keycode = "otra_cosa"
        self.puerta.db.is_locked = True
        ok, msg = self.puerta.unlock(self.char1)
        self.assertFalse(ok)
        self.assertTrue(self.puerta.db.is_locked)

    def test_llave_maestra_abre_cualquier_key_id(self):
        maestra = create_object(Key, key="llave maestra", location=self.char1)
        maestra.db.is_master = True
        ok, msg = self.puerta.lock(self.char1)
        self.assertTrue(ok)
        ok, msg = self.puerta.unlock(self.char1)
        self.assertTrue(ok)

    def test_llave_por_prefijo(self):
        llave = create_object(Key, key="llave de zona", location=self.char1)
        llave.db.keyprefixes = ["bronce_"]
        ok, msg = self.puerta.lock(self.char1)
        self.assertTrue(ok)

    def test_llave_por_lista_de_codigos(self):
        llave = create_object(Key, key="llavero", location=self.char1)
        llave.db.keycodes = ["bronce_01", "plata_02"]
        ok, msg = self.puerta.lock(self.char1)
        self.assertTrue(ok)


class TestAtTraverseBloqueaTransito(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.puerta, self.puerta_vuelta = _crear_puerta_par(self.room1, self.room2)
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        self.puerta.delete()
        self.puerta_vuelta.delete()
        super().tearDown()

    def test_puerta_cerrada_bloquea_transito(self):
        self.puerta.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)
        self.assertIn("cerrada", self.cap.all().lower())

    def test_puerta_bloqueada_impide_transito_aunque_este_abierta_antes(self):
        self.puerta.db.is_open = True
        self.puerta.db.is_locked = True
        self.puerta.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)
        self.assertIn("llave", self.cap.all().lower())

    def test_puerta_abierta_permite_transito(self):
        self.puerta.db.is_open = True
        self.puerta.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)


class TestFindDoorExitInRoom(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)

    def tearDown(self):
        for ex in list_doors_in_room(self.room1):
            ex.delete()
        super().tearDown()

    def test_sin_puertas_informa(self):
        door, err = find_door_exit_in_room(self.char1, None)
        self.assertIsNone(door)
        self.assertIn("ninguna puerta", err)

    def test_una_puerta_sin_nombre_la_resuelve_sola(self):
        p, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        door, err = find_door_exit_in_room(self.char1, None)
        self.assertEqual(door, p)
        p.delete()

    def test_varias_puertas_sin_nombre_pide_especificar(self):
        p1, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        p2, _ = _crear_puerta_par(self.room1, self.room2, "este", "oeste")
        door, err = find_door_exit_in_room(self.char1, None)
        self.assertIsNone(door)
        self.assertIn("varias puertas", err.lower())
        p1.delete()
        p2.delete()

    def test_busqueda_por_nombre_exacto(self):
        p1, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        p2, _ = _crear_puerta_par(self.room1, self.room2, "este", "oeste")
        door, err = find_door_exit_in_room(self.char1, "norte")
        self.assertEqual(door, p1)
        p1.delete()
        p2.delete()

    def test_busqueda_por_indice(self):
        p1, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        p2, _ = _crear_puerta_par(self.room1, self.room2, "este", "oeste")
        door, err = find_door_exit_in_room(self.char1, "2")
        self.assertIn(door, (p1, p2))
        p1.delete()
        p2.delete()

    def test_prefijo_unico_resuelve(self):
        p1, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        door, err = find_door_exit_in_room(self.char1, "nor")
        self.assertEqual(door, p1)
        p1.delete()

    def test_prefijo_ambiguo_pide_especificar(self):
        p1, _ = _crear_puerta_par(self.room1, self.room2, "norte", "sur")
        p2, _ = _crear_puerta_par(self.room1, self.room2, "noreste", "suroeste")
        door, err = find_door_exit_in_room(self.char1, "nor")
        self.assertIsNone(door)
        self.assertIn("varias puertas", err.lower())
        p1.delete()
        p2.delete()


class TestComandosDePuerta(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.puerta, self.puerta_vuelta = _crear_puerta_par(self.room1, self.room2)
        self.char1.move_to(self.room1, quiet=True)
        self.char1.check_permstring = lambda perm: perm == "Builder"
        self.cap = _MsgCapture(self.char1)

    def tearDown(self):
        self.puerta.delete()
        self.puerta_vuelta.delete()
        super().tearDown()

    def test_cmd_abrir(self):
        cmd = _make_cmd(CmdOpenDoor, self.char1, "")
        cmd.func()
        self.assertTrue(self.puerta.db.is_open)

    def test_cmd_cerrar(self):
        self.puerta.db.is_open = True
        cmd = _make_cmd(CmdCloseDoor, self.char1, "")
        cmd.func()
        self.assertFalse(self.puerta.db.is_open)

    def test_cmd_bloquear(self):
        cmd = _make_cmd(CmdLockDoor, self.char1, "")
        cmd.func()
        self.assertTrue(self.puerta.db.is_locked)

    def test_cmd_desbloquear(self):
        self.puerta.db.is_locked = True
        cmd = _make_cmd(CmdUnlockDoor, self.char1, "")
        cmd.func()
        self.assertFalse(self.puerta.db.is_locked)

    def test_cmd_estado(self):
        cmd = _make_cmd(CmdDoorStatus, self.char1, "")
        cmd.func()
        self.assertIn("cerrada", self.cap.all())


class TestCmdDoorCrea(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)
        self.cap = _MsgCapture(self.char1)

    def test_crea_par_de_puertas(self):
        rhs = f"#{self.room2.id} ; sur"
        cmd = _make_cmd(CmdDoor, self.char1, lhs="norte", rhs=rhs)
        cmd.func()

        salida = next(
            (ex for ex in self.room1.exits if ex.key == "norte"), None
        )
        self.assertIsNotNone(salida)
        self.assertTrue(salida.db.door)
        self.assertEqual(salida.destination, self.room2)

        vuelta = next(
            (ex for ex in self.room2.exits if ex.key == "sur"), None
        )
        self.assertIsNotNone(vuelta)
        self.assertEqual(vuelta.db.paired_exit, salida)
        salida.delete()
        vuelta.delete()

    def test_falta_dir_vuelta_no_crea_nada(self):
        cmd = _make_cmd(CmdDoor, self.char1, lhs="norte", rhs=f"#{self.room2.id}")
        cmd.func()
        salida = next((ex for ex in self.room1.exits if ex.key == "norte"), None)
        self.assertIsNone(salida)

    def test_open_y_locked_a_la_vez_rechazado(self):
        rhs = f"#{self.room2.id} ; sur"
        cmd = _make_cmd(CmdDoor, self.char1, lhs="norte", rhs=rhs, switches=["open", "locked"])
        cmd.func()
        salida = next((ex for ex in self.room1.exits if ex.key == "norte"), None)
        self.assertIsNone(salida)


class TestCmdKeyMake(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.char1.move_to(self.room1, quiet=True)

    def test_keymake_normal(self):
        cmd = _make_cmd(CmdKeyMake, self.char1, lhs="Llave Bronce", rhs="bronce_01")
        cmd.func()
        llave = next((o for o in self.char1.contents if o.key == "Llave Bronce"), None)
        self.assertIsNotNone(llave)
        self.assertEqual(llave.db.keycode, "bronce_01")

    def test_keymake_master(self):
        cmd = _make_cmd(CmdKeyMake, self.char1, lhs="Llave Maestra", switches=["master"])
        cmd.func()
        llave = next((o for o in self.char1.contents if o.key == "Llave Maestra"), None)
        self.assertTrue(llave.db.is_master)

    def test_keymake_list(self):
        cmd = _make_cmd(
            CmdKeyMake, self.char1, lhs="Llave Lista",
            rhs='["ciudad-01","ciudad-02"]', switches=["list"],
        )
        cmd.func()
        llave = next((o for o in self.char1.contents if o.key == "Llave Lista"), None)
        self.assertEqual(llave.db.keycodes, ["ciudad-01", "ciudad-02"])

    def test_keymake_formato_invalido_borra_el_objeto_parcial(self):
        cmd = _make_cmd(
            CmdKeyMake, self.char1, lhs="Llave Rota",
            rhs="esto no es una lista", switches=["list"],
        )
        cmd.func()
        llave = next((o for o in self.char1.contents if o.key == "Llave Rota"), None)
        self.assertIsNone(llave)


if __name__ == "__main__":
    import unittest
    unittest.main()
