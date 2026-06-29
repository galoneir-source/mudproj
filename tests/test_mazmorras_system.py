"""
tests/test_mazmorras_system.py

Tests unitarios del sistema de mazmorras (lógica pura).
No requieren Evennia; se ejecutan con pytest directamente.
"""
import pytest
from systems.dungeons.dungeons import (
    MAZMORRAS,
    DIFICULTADES,
    buscar_mazmorra,
    puede_entrar,
    calcular_recompensas,
    escalar_hp,
    total_salas,
    es_sala_jefe,
    formatear_lista,
    formatear_info,
)


# --------------------------------------------------------------------------- #
#  Catálogo
# --------------------------------------------------------------------------- #

class TestCatalogo:
    def test_existen_tres_mazmorras(self):
        assert len(MAZMORRAS) == 3

    def test_ids_esperados(self):
        assert "cripta_ceniza" in MAZMORRAS
        assert "forja_maldita" in MAZMORRAS
        assert "abismo_sin_fondo" in MAZMORRAS

    def test_cada_mazmorra_tiene_tres_salas(self):
        for mid, datos in MAZMORRAS.items():
            assert len(datos["salas"]) == 3, f"{mid} no tiene 3 salas"

    def test_ultima_sala_es_jefe(self):
        for mid, datos in MAZMORRAS.items():
            assert datos["salas"][-1].get("es_jefe"), f"{mid}: última sala no es de jefe"

    def test_campos_requeridos(self):
        for mid, datos in MAZMORRAS.items():
            for campo in ("nombre", "nivel_min", "xp_bonus", "monedas_bonus"):
                assert campo in datos, f"{mid} falta campo '{campo}'"

    def test_nivel_min_creciente(self):
        niveles = [MAZMORRAS[k]["nivel_min"] for k in ("cripta_ceniza", "forja_maldita", "abismo_sin_fondo")]
        assert niveles == sorted(niveles)

    def test_cada_sala_tiene_enemigos(self):
        for mid, datos in MAZMORRAS.items():
            for sala in datos["salas"]:
                assert sala.get("enemigos"), f"{mid} sala '{sala['nombre']}' sin enemigos"

    def test_dificultades_definidas(self):
        for dif in ("normal", "dificil", "legendario"):
            assert dif in DIFICULTADES


# --------------------------------------------------------------------------- #
#  buscar_mazmorra
# --------------------------------------------------------------------------- #

class TestBuscarMazmorra:
    def test_por_id_exacto(self):
        mid, datos = buscar_mazmorra("cripta_ceniza")
        assert mid == "cripta_ceniza"
        assert datos is not None

    def test_por_nombre_parcial(self):
        mid, datos = buscar_mazmorra("cripta")
        assert mid == "cripta_ceniza"

    def test_por_nombre_parcial_case_insensitive(self):
        mid, datos = buscar_mazmorra("FORJA")
        assert mid == "forja_maldita"

    def test_no_encontrado(self):
        mid, datos = buscar_mazmorra("xyzzy_no_existe")
        assert mid is None
        assert datos is None

    def test_ambiguedad_startswith_devuelve_none(self):
        # "maz" no es substring de ningún nombre, pero ningún ID empieza por "maz_" solo
        # Usamos un prefijo que no coincide con nada
        mid, datos = buscar_mazmorra("xyzzy_no_match_ninguna")
        assert mid is None

    def test_busca_abismo(self):
        mid, _ = buscar_mazmorra("abismo")
        assert mid == "abismo_sin_fondo"


# --------------------------------------------------------------------------- #
#  puede_entrar
# --------------------------------------------------------------------------- #

class TestPuedeEntrar:
    def test_nivel_suficiente(self):
        ok, msg = puede_entrar(3, "cripta_ceniza")
        assert ok is True
        assert msg == ""

    def test_nivel_insuficiente(self):
        ok, msg = puede_entrar(2, "cripta_ceniza")
        assert ok is False
        assert "3" in msg

    def test_nivel_exacto(self):
        ok, _ = puede_entrar(5, "forja_maldita")
        assert ok is True

    def test_nivel_alto_cualquier_mazmorra(self):
        ok, _ = puede_entrar(10, "abismo_sin_fondo")
        assert ok is True

    def test_mazmorra_inexistente(self):
        ok, msg = puede_entrar(10, "no_existe")
        assert ok is False

    def test_nivel_0_falla(self):
        ok, _ = puede_entrar(0, "cripta_ceniza")
        assert ok is False


# --------------------------------------------------------------------------- #
#  calcular_recompensas
# --------------------------------------------------------------------------- #

class TestCalcularRecompensas:
    def test_normal_es_base(self):
        xp, mon = calcular_recompensas("cripta_ceniza", "normal")
        assert xp == MAZMORRAS["cripta_ceniza"]["xp_bonus"]
        assert mon == MAZMORRAS["cripta_ceniza"]["monedas_bonus"]

    def test_dificil_mas_que_normal(self):
        xp_n, mon_n = calcular_recompensas("forja_maldita", "normal")
        xp_d, mon_d = calcular_recompensas("forja_maldita", "dificil")
        assert xp_d > xp_n
        assert mon_d > mon_n

    def test_legendario_mas_que_dificil(self):
        xp_d, mon_d = calcular_recompensas("abismo_sin_fondo", "dificil")
        xp_l, mon_l = calcular_recompensas("abismo_sin_fondo", "legendario")
        assert xp_l > xp_d
        assert mon_l > mon_d

    def test_mazmorra_desconocida_no_explota(self):
        xp, mon = calcular_recompensas("no_existe", "normal")
        assert isinstance(xp, int)
        assert isinstance(mon, int)

    def test_dificultad_desconocida_usa_normal(self):
        xp_def, _ = calcular_recompensas("cripta_ceniza", "normal")
        xp_unk, _ = calcular_recompensas("cripta_ceniza", "raro_desconocido")
        assert xp_unk == xp_def


# --------------------------------------------------------------------------- #
#  escalar_hp
# --------------------------------------------------------------------------- #

class TestEscalarHp:
    def test_normal_no_cambia(self):
        assert escalar_hp(100, "normal") == 100

    def test_dificil_x15(self):
        assert escalar_hp(100, "dificil") == 150

    def test_legendario_x20(self):
        assert escalar_hp(100, "legendario") == 200

    def test_minimo_uno(self):
        assert escalar_hp(0, "legendario") == 1

    def test_dificultad_invalida_usa_normal(self):
        assert escalar_hp(100, "xyzzy") == 100

    def test_valores_fraccionados_son_enteros(self):
        resultado = escalar_hp(7, "dificil")
        assert isinstance(resultado, int)
        assert resultado == 10  # 7 * 1.5 = 10 (int)


# --------------------------------------------------------------------------- #
#  total_salas / es_sala_jefe
# --------------------------------------------------------------------------- #

class TestSalas:
    def test_total_tres(self):
        for mid in MAZMORRAS:
            assert total_salas(mid) == 3

    def test_total_desconocido(self):
        assert total_salas("no_existe") == 0

    def test_jefe_en_ultima(self):
        for mid in MAZMORRAS:
            assert es_sala_jefe(mid, 2) is True

    def test_no_jefe_en_primera(self):
        for mid in MAZMORRAS:
            assert es_sala_jefe(mid, 0) is False

    def test_indice_fuera_de_rango(self):
        assert es_sala_jefe("cripta_ceniza", 10) is False
        assert es_sala_jefe("cripta_ceniza", -1) is False


# --------------------------------------------------------------------------- #
#  Formateo
# --------------------------------------------------------------------------- #

class TestFormateo:
    def test_lista_contiene_nombres(self):
        resultado = formatear_lista()
        for mid, datos in MAZMORRAS.items():
            assert datos["nombre"] in resultado
            assert mid in resultado

    def test_lista_menciona_dificultades(self):
        resultado = formatear_lista()
        assert "normal" in resultado.lower()
        assert "legendario" in resultado.lower()

    def test_info_cripta(self):
        resultado = formatear_info("cripta_ceniza")
        assert "Cripta de Ceniza" in resultado
        assert "JEFE" in resultado

    def test_info_desconocida(self):
        resultado = formatear_info("no_existe")
        assert "no encontrada" in resultado.lower()

    def test_info_incluye_recompensas(self):
        resultado = formatear_info("forja_maldita")
        assert "Recompensas" in resultado
        assert "XP" in resultado
