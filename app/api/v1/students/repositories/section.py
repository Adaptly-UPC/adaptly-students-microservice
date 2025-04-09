from app.api.v1.students.models import Seccion

class SectionRepository:
    """Repositorio para la sección (A, B, C, D, etc)"""
    def __init__(self, db):
        self.db = db

    def get_section_by_name(self, section_letter: str) -> Seccion:
        """Obtiene la sección de la base de datos (A, B, C, D, etc)"""

        section = self.db.query(Seccion).filter(Seccion.nombre == section_letter).first()
        return section

    def create_section(self, section_letter: str) -> Seccion:
        """Crea una sección en la base de datos (A, B, C, D, etc)"""

        section = Seccion(nombre=section_letter)
        self.db.add(section)
        self.db.commit()
        return section

    def get_or_create_section(self, section_letter: str) -> Seccion:
        """Obtiene o crea una sección en la base de datos (A, B, C, D, etc)"""

        section = self.get_section_by_name(section_letter)
        if not section:
            section = self.create_section(section_letter)
        return section

