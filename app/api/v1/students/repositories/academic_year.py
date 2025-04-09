from app.api.v1.students.models import AnioAcademico

class AcademicYearRepository:
    """Repositorio para el año académico"""
    def __init__(self, db):
        self.db = db

    def get_academic_year_by_name(self, year: int) -> AnioAcademico:
        """Get objeto de la base de datos del año académico"""
        year = self.db.query(AnioAcademico).filter(AnioAcademico.anio == year).first()
        return year

    def create_academic_year(self, year: int) -> AnioAcademico:
        """Crea un nuevo año académico en la base de datos"""
        year = AnioAcademico(anio=year)
        self.db.add(year)
        self.db.commit()
        return year

    def get_or_create_academic_year(self, year: int) -> AnioAcademico:
        """Obtiene o crea un nuevo año académico en la base de datos"""
        year = self.get_academic_year_by_name(year)
        if not year:
            year = self.create_academic_year(year)
        return year

