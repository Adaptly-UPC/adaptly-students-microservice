from app.api.v1.students.models import Alumno
import unicodedata
import re
from sqlalchemy import func

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


    def update_student(self, student_id, **kwargs):
        age = kwargs.get("age", None)
        gender = kwargs.get("gender", None)

        if type(age) == int:
            self.db.query(Alumno).filter(Alumno.id == student_id).update({"edad": age})
            self.db.commit()

        if type(gender) == str:
            self.db.query(Alumno).filter(Alumno.id == student_id).update({"genero": gender})
            self.db.commit()

        return self.get_student_by_id(student_id)

    def get_or_create_student(self, student_name: str, student_code="", student_gender="MASCULINO") -> Alumno:
        """Crea alumno si no puede obtenerlo"""
        student = self.get_student_by_name(student_name)

        if not student:
            student = self.create_student(student_name, student_code, student_gender )

        return student

    def normalize_name(self, name: str) -> str:
        """Normaliza un nombre para comparación"""
        if not name:
            return ""
        # Convertir a minúsculas y quitar acentos
        name = unicodedata.normalize('NFKD', name.lower()).encode('ASCII', 'ignore').decode('ASCII')
        # Eliminar caracteres especiales y espacios extras
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def find_student_by_flexible_name(self, partial_name: str) -> Alumno:
        """Busca un alumno por coincidencia flexible de nombre usando SQL"""
        if not partial_name:
            return None

        normalized_partial = self.normalize_name(partial_name)
        search_pattern = f"%{normalized_partial.replace(' ', '%')}%"

        # Buscar coincidencias aproximadas
        possible_matches = self.db.query(Alumno).filter(
            func.lower(func.unaccent(Alumno.nombre_completo)).like(search_pattern)
        ).all()

        if not possible_matches:
            return None

        # Si hay múltiples coincidencias, encontrar la mejor
        if len(possible_matches) > 1:
            partial_parts = normalized_partial.split()
            best_match = None
            best_score = 0

            for student in possible_matches:
                full_name = self.normalize_name(student.nombre_completo)
                parts = [p for p in full_name.split() if p]

                score = sum(1 for part in partial_parts if any(part in p for p in parts))

                if score > best_score:
                    best_score = score
                    best_match = student

            return best_match

        return possible_matches[0]



