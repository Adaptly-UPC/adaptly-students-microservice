from app.api.v1.students.models import NivelEducativo

class AcademicLevelRepository:
    """ Repositorio para el nivel academico (primaria, secundaria) """
    def __init__(self, db):
        self.db = db

    def get_academic_level_by_name(self, level_name: str) -> NivelEducativo:
        """Obtiene el nivel academico (primaria, secundaria) de la base de datos"""

        level = self.db.query(NivelEducativo).filter(NivelEducativo.nombre == level_name).first()
        return level

    def create_academic_level(self, level_name: str) -> NivelEducativo:
        """Crea un nivel academico (primaria, secundaria) en la base de datos"""

        level = NivelEducativo(nombre=level_name)
        self.db.add(level)
        self.db.commit()
        return level

    def get_or_create_academic_level(self, level_name: str) -> NivelEducativo:
        """Obtiene o crea un nivel academico (primaria, secundaria) en la base de datos"""

        level = self.get_academic_level_by_name(level_name)
        if not level:
            level = self.create_academic_level(level_name)
        return level
