from ..repositories.student import StudentRepository
from sqlalchemy.orm import Session
from .base_grades_excel_processor import BaseExcelProcessor as BaseStudent
class Student(BaseStudent):
    def __init__(self, db: Session):
      super().__init__(db)

    def get_available_filters(self):
        """
        Obtiene todos los filtros disponibles basados en los datos existentes en la base de datos.

        Returns:
            dict: Diccionario con los filtros disponibles.
        """
        student_repo = StudentRepository(self.db)
        return student_repo.get_available_filters()

    def get_students(self, page: int, page_size: int):
        student_repo = StudentRepository(self.db)
        return student_repo.get_all_students_with_associated_data(page, page_size)

    def get_student_by_id(self, student_id: int):
        student_repo = StudentRepository(self.db)
        return student_repo.get_student_by_id(student_id)

    def get_students_with_filters(self,
        anio_academico_id: int = None,
        seccion_id: int = None,
        nivel_id: int = None,
        bimestre_id: int = None,
        materia_id: int = None,
        grado_id: int = None,
        page: int = 1,
        page_size: int = 10
    ):
        student_repo = StudentRepository(self.db)
        return student_repo.get_students_with_filters(
        anio_academico_id=anio_academico_id,
        seccion_id=seccion_id,
        grado_id=grado_id,
        nivel_id=nivel_id,
        bimestre_id=bimestre_id,
        materia_id=materia_id,
        page=page,
        page_size=page_size
        )

    def get_students_with_only_notes(self):
        """Obtiene alumnos que tienen solo notas."""
        student_repo = StudentRepository(self.db)
        return student_repo.get_students_with_only_notes()

    def get_students_with_only_surveys(self):
        """Obtiene alumnos que tienen solo encuestas."""
        student_repo = StudentRepository(self.db)
        return student_repo.get_students_with_only_surveys()

    def get_students_with_notes_and_surveys(self):
        """Obtiene alumnos que tienen tanto notas como encuestas."""
        student_repo = StudentRepository(self.db)
        return student_repo.get_students_with_notes_and_surveys()

    def get_students_summary(self):
        """Obtiene un resumen del estado de los alumnos."""
        student_repo = StudentRepository(self.db)
        return student_repo.get_students_summary()

    def get_grades_and_sections(self, nivel_id=None, anio_academico_id=None, grado_id=None, seccion_id=None):
        student_repo = StudentRepository(self.db)
        return student_repo.get_grades_and_sections(nivel_id, anio_academico_id, grado_id, seccion_id)

    def get_student_notes(
        self,
        alumno_id: int = None,
        materia_id: int = None,
        grado_id: int = None,
        anio_academico_id: int = None,
        page: int = 1,
        page_size: int = 10
    ):
        student_repo = StudentRepository(self.db)
        return student_repo.get_student_notes(
            alumno_id=alumno_id,
            materia_id=materia_id,
            grado_id=grado_id,
            anio_academico_id=anio_academico_id,
            page=page,
            page_size=page_size
    )


    def get_student_performance_data(self, include_surveys: bool = False):
        student_repo = StudentRepository(self.db)
        return student_repo.get_student_performance_data(include_surveys)


    def get_student_behavior_patterns(self, min_survey_responses: int, min_academic_periods: int):
        student_repo = StudentRepository(self.db)
        return student_repo.get_student_behavior_patterns(min_survey_responses, min_academic_periods)

    def get_complete_student_profile(self, analysis_type: str = "all"):
        student_repo = StudentRepository(self.db)
        return student_repo.get_complete_student_profile(analysis_type)


