from sqlalchemy.orm import Session

class Database:
    def __init__(self, db: Session):
        self.db = db

    def delete_all(self, model):
        """Delete all records from the given model."""
        self.db.query(model).delete()
        self.db.commit()
        self.db.flush()
        self.db.refresh(model)
        self.db.close()
        return model

    def delete_all_db(self):
        """Delete all records from all models."""
        models = [
            "NivelLogro",
            "CriterioEvaluacion",
            "Materia",
            "Alumno",
            "Bimestre",
            "AnioAcademico",
            "Seccion",
            "Grado",
            "NivelEducativo"
        ]
        for model in models:
            self.delete_all(model)
        return models

    def create_all_tables(self):
        """Create all tables in the database."""
        self.db.create_all()
        return "All tables created successfully"