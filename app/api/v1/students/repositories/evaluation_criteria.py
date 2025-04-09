from app.api.v1.students.models import CriterioEvaluacion

class EvaluationCriteriaRepository:
    """Repositorio para manejo de criterios de evaluación"""
    def __init__(self, db):
        self.db = db

    def get_evaluation_criteria(self, criteria_name: str, course_id: int) ->     CriterioEvaluacion:
        """Obtiene el criterio de evaluación de la base de datos"""

        criterio_obj = self.db.query(CriterioEvaluacion).filter(
            CriterioEvaluacion.nombre == criteria_name,
            CriterioEvaluacion.materia_id == course_id
        ).first()

        return criterio_obj

    def create_evaluation_criteria(self, criteria_name: str, course_id: int) -> CriterioEvaluacion:
        """Crea un criterio de evaluación en la base de datos"""

        criterio_obj = CriterioEvaluacion(
            nombre=criteria_name,
            materia_id=course_id
        )
        self.db.add(criterio_obj)
        self.db.commit()
        self.db.refresh(criterio_obj)  # Esto es crucial

        return criterio_obj

    def get_or_create_evaluation_criteria(self, criteria_name: str, course_id: int) -> CriterioEvaluacion:
        """Obtiene o crea un criterio de evaluación en la base de datos"""

        criterio_obj = self.get_evaluation_criteria(criteria_name, course_id)

        if not criterio_obj:
            criterio_obj = self.create_evaluation_criteria(criteria_name, course_id)

        return criterio_obj

    def get_evaluation_criteria_list(self, df, course_id: int) -> list[CriterioEvaluacion]:
        """Obtiene la lista de criterios de evaluación por curso de la base de datos"""
        criteria_ids = []

        for _, row in df.iterrows():
            criteria_description_with_order = row.iloc[1]

            if (criteria_description_with_order.startswith("01 =") or
                criteria_description_with_order.startswith("02 =") or
                criteria_description_with_order.startswith("04 =") or
                criteria_description_with_order.startswith("03 =")):

                criteria_description = criteria_description_with_order.split("=", 1)[1].strip()

                criteria_obj = self.get_or_create_evaluation_criteria(criteria_description, course_id)

                criteria_ids.append(criteria_obj.id)

        return criteria_ids
