"""
tests/test_bulletin_system.py

Tests puros (pytest, sin Django) para systems/bulletin/bulletin.py.
"""
import time

from systems.bulletin.bulletin import (
    MAX_ANUNCIOS,
    MAX_LONGITUD_TEXTO,
    DURACION_SEGUNDOS,
    crear_anuncio,
    anuncios_vigentes,
    puede_publicar,
    formatear_cartelera,
)


# --------------------------------------------------------------------------- #
#  crear_anuncio
# --------------------------------------------------------------------------- #

def test_crear_anuncio_campos_basicos():
    anuncio = crear_anuncio("Aldric", "#10", "  Se vende espada  ", "1")
    assert anuncio["autor"] == "Aldric"
    assert anuncio["autor_dbref"] == "#10"
    assert anuncio["texto"] == "Se vende espada"
    assert "timestamp" in anuncio
    assert "fecha" in anuncio


def test_crear_anuncio_usa_el_id_recibido():
    # El id lo asigna quien llama (contador de BulletinScript), no se deriva
    # de timestamp+autor: dos anuncios del mismo autor en el mismo segundo
    # ya no colisionan porque cada llamada recibe un id distinto.
    a1 = crear_anuncio("Aldric", "#10", "Uno", "1")
    a2 = crear_anuncio("Aldric", "#10", "Dos", "2")
    assert a1["id"] == "1"
    assert a2["id"] == "2"
    assert a1["id"] != a2["id"]


# --------------------------------------------------------------------------- #
#  anuncios_vigentes
# --------------------------------------------------------------------------- #

def test_anuncios_vigentes_filtra_expirados():
    ahora = 100000.0
    vigente = {"timestamp": ahora - 10}
    expirado = {"timestamp": ahora - DURACION_SEGUNDOS - 10}
    resultado = anuncios_vigentes([vigente, expirado], ahora)
    assert resultado == [vigente]


def test_anuncios_vigentes_justo_en_el_limite():
    ahora = 100000.0
    justo_dentro = {"timestamp": ahora - DURACION_SEGUNDOS + 1}
    justo_fuera = {"timestamp": ahora - DURACION_SEGUNDOS}
    resultado = anuncios_vigentes([justo_dentro, justo_fuera], ahora)
    assert resultado == [justo_dentro]


def test_anuncios_vigentes_lista_vacia():
    assert anuncios_vigentes([], 1000.0) == []


def test_anuncios_vigentes_usa_time_time_por_defecto():
    anuncio = crear_anuncio("Aldric", "#10", "Reciente", "1")
    assert anuncios_vigentes([anuncio]) == [anuncio]


# --------------------------------------------------------------------------- #
#  puede_publicar
# --------------------------------------------------------------------------- #

def test_puede_publicar_ok():
    ok, _ = puede_publicar([], "Se vende espada")
    assert ok


def test_puede_publicar_texto_vacio():
    ok, msg = puede_publicar([], "   ")
    assert not ok
    assert "vacío" in msg.lower()


def test_puede_publicar_texto_demasiado_largo():
    ok, msg = puede_publicar([], "x" * (MAX_LONGITUD_TEXTO + 1))
    assert not ok
    assert "largo" in msg.lower()


def test_puede_publicar_texto_en_el_limite():
    ok, _ = puede_publicar([], "x" * MAX_LONGITUD_TEXTO)
    assert ok


def test_puede_publicar_tablon_lleno():
    llenos = [{"timestamp": time.time()} for _ in range(MAX_ANUNCIOS)]
    ok, msg = puede_publicar(llenos, "Otro más")
    assert not ok
    assert "llena" in msg.lower()


def test_puede_publicar_justo_debajo_del_limite():
    casi_lleno = [{"timestamp": time.time()} for _ in range(MAX_ANUNCIOS - 1)]
    ok, _ = puede_publicar(casi_lleno, "Cabe uno más")
    assert ok


# --------------------------------------------------------------------------- #
#  formatear_cartelera
# --------------------------------------------------------------------------- #

def test_formatear_cartelera_vacia():
    texto = formatear_cartelera([])
    assert "no hay anuncios" in texto.lower()


def test_formatear_cartelera_incluye_autor_y_texto():
    anuncio = crear_anuncio("Aldric", "#10", "Se vende espada del cazador", "1")
    texto = formatear_cartelera([anuncio])
    assert "Aldric" in texto
    assert "Se vende espada del cazador" in texto


def test_formatear_cartelera_ordena_mas_reciente_primero():
    viejo = crear_anuncio("Vex", "#11", "Viejo", "1")
    viejo["timestamp"] = time.time() - 1000
    nuevo = crear_anuncio("Aldric", "#10", "Nuevo", "2")
    texto = formatear_cartelera([viejo, nuevo])
    assert texto.index("Nuevo") < texto.index("Viejo")
