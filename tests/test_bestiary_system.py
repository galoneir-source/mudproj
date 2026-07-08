"""
tests/test_bestiary_system.py

Tests puros del sistema de bestiario (sin dependencias de Evennia/Django).
"""
import time
import pytest
from systems.bestiary.bestiary import (
    CATALOGO, TIPOS, _TOTAL_CATALOGO,
    registrar_kill,
    criaturas_registradas,
    bestiary_completo,
    buscar_en_catalogo,
    formatear_lista,
    formatear_entrada,
    _tiempo_transcurrido,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:

    def test_catalogo_no_vacio(self):
        assert len(CATALOGO) > 0

    def test_todos_los_tipos_validos(self):
        for key, info in CATALOGO.items():
            assert info["tipo"] in TIPOS, f"{key} tiene tipo desconocido: {info['tipo']}"

    def test_todos_tienen_campos_obligatorios(self):
        campos = ("nombre", "tipo", "zona", "nivel", "es_jefe", "descripcion")
        for key, info in CATALOGO.items():
            for campo in campos:
                assert campo in info, f"{key} le falta el campo '{campo}'"

    def test_niveles_son_enteros_positivos(self):
        for key, info in CATALOGO.items():
            assert isinstance(info["nivel"], int) and info["nivel"] >= 1

    def test_total_catalogo_coincide_con_len(self):
        assert _TOTAL_CATALOGO == len(CATALOGO)


# --------------------------------------------------------------------------- #
#  registrar_kill
# --------------------------------------------------------------------------- #

class TestRegistrarKill:

    def test_primera_baja(self):
        resultado = registrar_kill({}, "GOBLIN")
        assert resultado["GOBLIN"]["kills"] == 1
        assert "primera_vez" in resultado["GOBLIN"]

    def test_baja_acumulada(self):
        b = registrar_kill({}, "GOBLIN")
        b = registrar_kill(b, "GOBLIN")
        assert b["GOBLIN"]["kills"] == 2

    def test_primera_vez_no_se_sobreescribe(self):
        b = registrar_kill({}, "GOBLIN")
        ts_original = b["GOBLIN"]["primera_vez"]
        b = registrar_kill(b, "GOBLIN")
        assert b["GOBLIN"]["primera_vez"] == ts_original

    def test_prototipo_fuera_de_catalogo_ignorado(self):
        resultado = registrar_kill({}, "NPC_INEXISTENTE")
        assert "NPC_INEXISTENTE" not in resultado

    def test_no_modifica_dict_original(self):
        original = {}
        resultado = registrar_kill(original, "GOBLIN")
        assert original == {}
        assert "GOBLIN" in resultado

    def test_multiples_criaturas_independientes(self):
        b = registrar_kill({}, "GOBLIN")
        b = registrar_kill(b, "TROLL")
        assert b["GOBLIN"]["kills"] == 1
        assert b["TROLL"]["kills"] == 1


# --------------------------------------------------------------------------- #
#  criaturas_registradas
# --------------------------------------------------------------------------- #

class TestCriaturasRegistradas:

    def test_vacio(self):
        assert criaturas_registradas({}) == 0

    def test_una_criatura(self):
        b = registrar_kill({}, "GOBLIN")
        assert criaturas_registradas(b) == 1

    def test_varias_criaturas(self):
        b = registrar_kill({}, "GOBLIN")
        b = registrar_kill(b, "TROLL")
        b = registrar_kill(b, "ESQUELETO")
        assert criaturas_registradas(b) == 3

    def test_kills_multiples_cuentan_como_uno(self):
        b = registrar_kill({}, "GOBLIN")
        b = registrar_kill(b, "GOBLIN")
        assert criaturas_registradas(b) == 1

    def test_clave_fuera_de_catalogo_no_cuenta(self):
        b = {"CRIATURA_FALSA": {"kills": 5}}
        assert criaturas_registradas(b) == 0


# --------------------------------------------------------------------------- #
#  bestiary_completo
# --------------------------------------------------------------------------- #

class TestBestiaryCompleto:

    def test_vacio_no_es_completo(self):
        assert not bestiary_completo({})

    def test_parcial_no_es_completo(self):
        b = registrar_kill({}, "GOBLIN")
        assert not bestiary_completo(b)

    def test_completo_cuando_todas_registradas(self):
        b = {}
        for proto in CATALOGO:
            b = registrar_kill(b, proto)
        assert bestiary_completo(b)

    def test_falta_una_no_es_completo(self):
        b = {}
        claves = list(CATALOGO.keys())
        for proto in claves[:-1]:   # todas menos la última
            b = registrar_kill(b, proto)
        assert not bestiary_completo(b)


# --------------------------------------------------------------------------- #
#  buscar_en_catalogo
# --------------------------------------------------------------------------- #

class TestBuscarEnCatalogo:

    def test_busqueda_exacta(self):
        resultado = buscar_en_catalogo("Goblin")
        assert "GOBLIN" in resultado

    def test_busqueda_parcial(self):
        resultado = buscar_en_catalogo("liche")
        assert len(resultado) >= 2  # Liche Menor y Liche Inmortal

    def test_busqueda_insensible_mayusculas(self):
        r1 = buscar_en_catalogo("troll")
        r2 = buscar_en_catalogo("TROLL")
        assert set(r1) == set(r2)

    def test_busqueda_sin_resultados(self):
        assert buscar_en_catalogo("xyzxyz") == []

    def test_busqueda_por_tipo_en_nombre(self):
        resultado = buscar_en_catalogo("araña")
        assert "ARANA_CUEVA" in resultado


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:

    def test_formatear_lista_incluye_totales(self):
        txt = formatear_lista({})
        assert f"0/{_TOTAL_CATALOGO}" in txt

    def test_formatear_lista_criatura_registrada_muestra_kills(self):
        b = registrar_kill({}, "GOBLIN")
        b = registrar_kill(b, "GOBLIN")
        txt = formatear_lista(b)
        assert "2 bajas" in txt

    def test_formatear_lista_criatura_sin_registrar_muestra_x(self):
        txt = formatear_lista({})
        assert "✗" in txt

    def test_formatear_entrada_conocida(self):
        txt = formatear_entrada("GOBLIN", {})
        assert "Goblin" in txt
        assert "Humanoides" in txt

    def test_formatear_entrada_con_kills(self):
        b = registrar_kill({}, "GOBLIN")
        txt = formatear_entrada("GOBLIN", b)
        assert "1 baja" in txt

    def test_formatear_entrada_sin_kills(self):
        txt = formatear_entrada("GOBLIN", {})
        assert "no has derrotado" in txt

    def test_formatear_entrada_inexistente(self):
        txt = formatear_entrada("NADA", {})
        assert "no encontrada" in txt

    def test_formatear_lista_muestra_jefes_con_etiqueta(self):
        txt = formatear_lista({})
        assert "[Jefe]" in txt


# --------------------------------------------------------------------------- #
#  _tiempo_transcurrido
# --------------------------------------------------------------------------- #

class TestTiempoTranscurrido:

    def test_hace_un_momento(self):
        ts = int(time.time()) - 30
        assert "momento" in _tiempo_transcurrido(ts)

    def test_hace_minutos(self):
        ts = int(time.time()) - 600
        txt = _tiempo_transcurrido(ts)
        assert "min" in txt

    def test_hace_horas(self):
        ts = int(time.time()) - 7200
        txt = _tiempo_transcurrido(ts)
        assert "h" in txt

    def test_hace_dias(self):
        ts = int(time.time()) - 172800  # 2 días
        txt = _tiempo_transcurrido(ts)
        assert "día" in txt
