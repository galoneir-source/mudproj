"""
tests/conftest.py

Bajo pytest directo (sin Django configurado) hay que evitar colectar los
tests de integración, que heredan de EvenniaTest y requieren
`evennia test` para correr. La convención de nombre (`test_*_system.py`
= puro) no siempre se respeta, así que se detecta por contenido: si el
archivo importa EvenniaTest, se ignora en esta colección.
"""
from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):
    if collection_path.suffix != ".py" or not collection_path.name.startswith("test_"):
        return None
    try:
        texto = collection_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if "EvenniaTest" in texto:
        return True
    return None
