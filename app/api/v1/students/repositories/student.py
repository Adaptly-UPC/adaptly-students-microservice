from app.api.v1.students.models import Alumno

class StudentRepository:
    def __init__(self, db):
        self.db = db

    def get_student_by_id(self, student_id: int) -> Alumno:
        """Obtiene el alumno de la base de datos"""
        student = self.db.query(Alumno).filter(Alumno.id == student_id).first()
        return student

    def get_student_by_name(self, student_name: str) -> Alumno:
        """Obtiene el alumno de la base de datos"""
        student = self.db.query(Alumno).filter(Alumno.nombre_completo == student_name).first()
        return student

    def create_student(self, student_name: str, student_code="",student_gender='MASCULINO') -> Alumno:
        """Crea un alumno en la base de datos"""

        student = Alumno(nombre_completo=student_name, codigo_alumno=student_code, genero=student_gender)
        self.db.add(student)
        self.db.commit()
        return student

    def get_or_create_student(self, student_name: str, student_code="", student_gender="MASCULINO") -> Alumno:
        """Crea alumno si no puede obtenerlo"""
        student = self.get_student_by_name(student_name)

        if not student:
            student = self.create_student(student_name, student_code, student_gender )

        return student

