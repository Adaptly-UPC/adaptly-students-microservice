from app.api.v1.students.models import HistorialAcademico

class AcademicHistoryRepository:
    """Repositorio para el historial académico"""
    def __init__(self, db):
        self.db = db

    def get_academic_history_by_id(self, academic_history_id: int):
        """Obtiene el historial académico de la base de datos"""
        return self.db.query(HistorialAcademico).filter(HistorialAcademico.id == academic_history_id).first()

    def get_academic_history_by_entrie_attributes(self, student_id: int, academic_year_id: int, level_id: int, degree_id: int, section_id: int):
        """Obtiene el historial académico con usando todos los atributos"""
        academic_history = self.db.query(HistorialAcademico).filter(
            HistorialAcademico.alumno_id==student_id, HistorialAcademico.anio_academico_id==academic_year_id, HistorialAcademico.nivel_id==level_id, HistorialAcademico.grado_id==degree_id, HistorialAcademico.seccion_id==section_id).first()
        return academic_history

    def get_academic_history_by_student_id(self, student_id: int):
        """Obtiene el historial académico de la base de datos"""
        return self.db.query(HistorialAcademico).filter(HistorialAcademico.alumno_id == student_id).all()

    def create_academic_history(self, student_id: int, academic_year_id: int, level_id: int, degree_id: int, section_id: int):
        """Crea un nuevo historial académico en la base de datos"""
        academic_history = HistorialAcademico(alumno_id=student_id, anio_academico_id=academic_year_id, nivel_id=level_id, grado_id=degree_id, seccion_id=section_id)
        self.db.add(academic_history)
        self.db.commit()
        return academic_history

    def get_or_create_academic_history(self, student_id: int, academic_year_id: int, level_id: int, degree_id: int, section_id: int):
        """Crea un nuevo historial academico en caso no encuentre alguno con los paramentros"""
        academic_history = self.get_academic_history_by_entrie_attributes(
            student_id,
            academic_year_id,
            level_id,
            degree_id,
            section_id
        )

        if not academic_history:
            academic_history = self.create_academic_history(
                student_id,
                academic_year_id,
                level_id,
                degree_id,
                section_id
            )

        return academic_history
