from app.api.v1.students.models import Bimestre

class BimesterRepository:
    """Repositorio para el bimestre"""
    def __init__(self, db):
        self.db = db

    def get_bimester_by_name(self, bimester_name: str) -> Bimestre:
        """Obtiene el bimestre de la base de datos"""
        bimester = self.db.query(Bimestre).filter(Bimestre.nombre == bimester_name).first()
        return bimester

    def create_bimester(self, bimester_name: str) -> Bimestre:
        """Crea un bimestre en la base de datos"""
        bimester = Bimestre(nombre=bimester_name)
        self.db.add(bimester)
        self.db.commit()
        return bimester

    def get_or_create_bimester(self, bimester_name: str) -> Bimestre:
        """Obtiene o crea un bimestre en la base de datos"""
        bimester = self.get_bimester_by_name(bimester_name)
        if not bimester:
            bimester = self.create_bimester(bimester_name)
        return bimester

