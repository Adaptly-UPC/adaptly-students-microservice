from app.api.v1.students.models import Materia

class CourseRepository:
    """Repositorio para manejo de materias"""
    def __init__(self, db):
        self.db = db

    def get_course_by_name(self, course_name: str, course_code: str) -> Materia:
        """Obtiene una materia de la base de datos"""
        course = self.db.query(Materia).filter(Materia.nombre == course_name, Materia.codigo == course_code).first()
        return course

    def get_course_by_code(self, course_code: str) -> Materia:
        """Obtiene una materia de la base de datos"""
        course = self.db.query(Materia).filter(Materia.codigo == course_code).first()
        return course

    def create_course(self, course_name: str, course_code: str) -> Materia:
        """Crea una materia en la base de datos"""
        course = Materia(nombre=course_name, codigo=course_code)
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def get_or_create_course(self, course_name: str, course_code: str) -> Materia:
        """Obtiene o crea una materia en la base de datos"""
        course = self.get_course_by_name(course_name, course_code)
        if not course:
            course = self.create_course(course_name, course_code)
        return course
