"""
tests/test_jefes_mundo.py

Tests de integración Evennia para el sistema de jefes de mundo (v0.41.0).
Cubre: distribuir_recompensas_jefe_mundo() y el límite de reparto total
cuando participan muchos jugadores.

Ejecutar con:
  cd /opt/evennia/mudproj/mygame && ../venv/bin/evennia test tests.test_jefes_mundo
"""
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from features.world_bosses.world_boss_script import distribuir_recompensas_jefe_mundo
from systems.world_bosses.world_bosses import JEFES_MUNDO
from typeclasses.characters import Character


class JugadorDePrueba(Character):
    """
    has_account en Evennia cuenta sesiones conectadas (self.sessions.count()),
    no la mera asignación de account — EvenniaTest solo conecta una sesión
    real por defecto (a self.account, normalmente char1). Este typeclass de
    prueba simula "hay un jugador real detrás" sin montar N sesiones reales.
    """

    @property
    def has_account(self):
        return True


class TestDistribuirRecompensas(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        self.sala = create.create_object("typeclasses.rooms.Room", key="Sala de prueba jefe")
        self.char2 = create.create_object(JugadorDePrueba, key="Char2Jugador")
        for char in (self.char1, self.char2):
            char.msg = lambda text=None, **kw: None
            char.db.experiencia = 0
            char.db.monedas = 0

    def test_dos_participantes_50_50_no_supera_el_pool(self):
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        tracker = {self.char1.dbref: 500, self.char2.dbref: 500}

        distribuir_recompensas_jefe_mundo(None, tracker, self.sala, "TITAN_PANTANO")

        self.assertEqual(
            self.char1.db.experiencia + self.char2.db.experiencia, datos["xp_total"]
        )
        self.assertLessEqual(self.char1.db.monedas + self.char2.db.monedas, datos["monedas_total"])

    def test_muchos_participantes_no_inflan_el_pool_total(self):
        """
        Regresión: calcular_recompensas_participante() garantiza un mínimo
        del 10% del pool a cada participante (por diseño, para no dejar a
        nadie sin recompensa en un grupo pequeño), pero sin normalizar eso
        significa que con muchos participantes de bajo daño cada uno cobra
        su 10% igualmente y el total repartido supera el 100% del pool
        nominal sin límite — cuantos más "personajes-alfiler" se sumen al
        combate, más XP/monedas totales se generan de la nada. Verificado
        que con 20 participantes al 5% de daño cada uno (que sin el fix
        repartían el 200% del pool) el total ahora queda acotado.
        """
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        personajes = [self.char1, self.char2]
        for i in range(18):
            c = create.create_object(JugadorDePrueba, key=f"Extra{i}")
            c.msg = lambda text=None, **kw: None
            c.db.experiencia = 0
            c.db.monedas = 0
            personajes.append(c)

        tracker = {c.dbref: 50 for c in personajes}  # 20 × 50 = 1000 daño total, 5% cada uno

        distribuir_recompensas_jefe_mundo(None, tracker, self.sala, "TITAN_PANTANO")

        xp_repartido = sum(c.db.experiencia for c in personajes)
        mon_repartido = sum(c.db.monedas for c in personajes)

        self.assertLessEqual(xp_repartido, datos["xp_total"])
        self.assertLessEqual(mon_repartido, datos["monedas_total"])

    def test_un_solo_participante_recibe_el_pool_completo(self):
        datos = JEFES_MUNDO["TITAN_PANTANO"]
        tracker = {self.char1.dbref: 1000}

        distribuir_recompensas_jefe_mundo(None, tracker, self.sala, "TITAN_PANTANO")

        self.assertEqual(self.char1.db.experiencia, datos["xp_total"])
        self.assertEqual(self.char1.db.monedas, datos["monedas_total"])
