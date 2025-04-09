from app.api.v1.students.models import Grado

class DegreeRepository:
    """Repositorio para manejo de grados de primero a quinto de secundaria"""
    def __init__(self, db):
        self.db = db

    def get_degree_by_name_and_level(self, degree_name: str, level_id: int) -> Grado:
        """Obtiene el grado de la base de datos"""

        degree = self.db.query(Grado).filter(Grado.nombre == degree_name, Grado.nivel_id == level_id).first()
        return degree

    def create_degree(self, degree_name: str, level_id: int) -> Grado:
        """Crea un grado en la base de datos"""

        degree = Grado(nombre=degree_name, nivel_id=level_id)
        self.db.add(degree)
        self.db.commit()
        return degree

    def get_or_create_degree(self, degree_name: str, level_id: int) -> Grado:
        """Obtiene o crea un grado en la base de datos"""

        degree = self.get_degree_by_name_and_level(degree_name, level_id)
        if not degree:
            degree = self.create_degree(degree_name, level_id)
        return degree
