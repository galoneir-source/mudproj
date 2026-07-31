"""
features/bulletin/bulletin_script.py

Script persistente de la cartelera de anuncios global.
"""
from evennia import DefaultScript


class BulletinScript(DefaultScript):

    def at_script_creation(self):
        self.key = "cartelera_global"
        self.desc = "Cartelera de anuncios de la ciudad"
        self.persistent = True
        self.db.anuncios = []

    # ------------------------------------------------------------------ #
    #  API pública
    # ------------------------------------------------------------------ #

    def publicar(self, autor, texto: str) -> tuple[bool, str]:
        """
        Publica un anuncio. Devuelve (True, "") o (False, msg_error).
        """
        from systems.bulletin.bulletin import (
            crear_anuncio, anuncios_vigentes, puede_publicar,
        )
        vigentes = anuncios_vigentes(list(self.db.anuncios or []))

        ok, msg = puede_publicar(vigentes, texto)
        if not ok:
            return False, msg

        anuncio = crear_anuncio(autor.key, autor.dbref, texto)
        self.db.anuncios = vigentes + [anuncio]
        return True, ""

    def retirar(self, anuncio_id: str, solicitante) -> tuple[bool, str]:
        """
        Retira un anuncio. Solo su autor puede hacerlo.
        Devuelve (True, "") o (False, msg_error).
        """
        from systems.bulletin.bulletin import anuncios_vigentes
        vigentes = anuncios_vigentes(list(self.db.anuncios or []))

        anuncio = next((a for a in vigentes if a["id"] == anuncio_id), None)
        if not anuncio:
            self.db.anuncios = vigentes
            return False, "No existe ese anuncio."

        if anuncio["autor_dbref"] != solicitante.dbref:
            return False, "No eres el autor de ese anuncio."

        self.db.anuncios = [a for a in vigentes if a["id"] != anuncio_id]
        return True, ""

    def obtener_anuncios(self) -> list:
        """Devuelve los anuncios vigentes, purgando los expirados."""
        from systems.bulletin.bulletin import anuncios_vigentes
        vigentes = anuncios_vigentes(list(self.db.anuncios or []))
        self.db.anuncios = vigentes
        return vigentes


def obtener_cartelera_script() -> BulletinScript:
    """Devuelve el script de la cartelera global, creándolo si no existe."""
    from evennia.scripts.models import ScriptDB
    from evennia.utils import create

    script = ScriptDB.objects.filter(db_key="cartelera_global").first()
    if script:
        return script
    return create.create_script(BulletinScript, key="cartelera_global", persistent=True)
