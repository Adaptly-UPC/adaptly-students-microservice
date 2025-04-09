from dataclasses import dataclass
from app.api.v1.students.models import Nota


@dataclass
class CalificationParams:
    history_id: int
    course_id: int
    bimester_id: int
    evaluation_criteria_id: int
    criteria_value: int
    achievement_level_id: int

class CalificationRepository:
    """Repositorio para manejo de calificaciones"""
    def __init__(self, db):
        self.db = db

    def create_calification(self, calification_params: CalificationParams) -> Nota:
        """Crea una nueva calificación en la base de datos."""
        criteria_value = calification_params.get("criteria_value")
        if criteria_value is None:
            criteria_value = ""

        calification = Nota(
            historial_id=calification_params.get("history_id"),
            materia_id=calification_params.get("course_id"),
            bimestre_id=calification_params.get("bimester_id"),
            criterio_evaluacion_id=calification_params.get("evaluation_criteria_id"),
            valor_criterio_de_evaluacion=criteria_value,
            nivel_logro_id=calification_params.get("achievement_level_id"),
        )
        self.db.add(calification)
        self.db.commit()
        self.db.refresh(calification)

        return calification
