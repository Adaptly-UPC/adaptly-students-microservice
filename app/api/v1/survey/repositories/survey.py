from app.api.v1.students.models import PreguntaEncuesta
from app.api.v1.students.models import OpcionEncuesta
from app.api.v1.students.models import Encuesta
from app.api.v1.students.models import RespuestaEncuesta
from app.api.v1.students.models import RespuestaTextoEncuesta
from sqlalchemy.orm import class_mapper

class SurveyRepository:
    def __init__(self, db):
        self.db = db

    def as_dict(self, obj):
        return {c.key: getattr(obj, c.key) for c in class_mapper(obj.__class__).columns}

    def create_question(self, question_text, is_multiple_choice, question_type):
        """Crea una pregunta en la base de datos"""

        question = self.db.query(PreguntaEncuesta).filter_by(pregunta=question_text).first()

        if question:
            return question

        question = PreguntaEncuesta(
          pregunta=question_text,
          es_multiple= 1 if is_multiple_choice else 0,
          tipo=question_type
        )
        self.db.add(question)

        self.db.commit()
        self.db.refresh(question)

        return question

    def get_question_by_text(self, question_text):
        """Obtiene pregunta de la base de datos"""
        question = self.db.query(PreguntaEncuesta).filter_by(pregunta=question_text).first()

        if not question:
            return

        dictionary = {**self.as_dict(question), "id": question.id}
        return dictionary

    def create_options(self, option_text, question_id):
        """Crea opciones en la base de datos"""
        option = self.db.query(OpcionEncuesta).filter_by(opcion=option_text,
        pregunta_id=question_id).first()

        if option:
            return option

        option = OpcionEncuesta(
          opcion=option_text,
          pregunta_id=question_id
        )
        self.db.add(option)
        self.db.commit()
        self.db.refresh(option)
        return option

    def get_options_by_question_id(self, question_id):
        """Obtiene opciones de la base de datos"""
        options_list = self.db.query(OpcionEncuesta).filter_by(pregunta_id=question_id).all()
        options = [{**self.as_dict(option), "id": option.id} for option in options_list]
        print(f"OPCIONES THREEEE: {options}")

        return options

    def get_option_by_id_and_question_id(self, option_id, question_id):
        """Obtiene opciones de la base de datos"""
        option = self.db.query(OpcionEncuesta).filter_by(id=option_id, pregunta_id=question_id).first()
        return option

    def create_survey(self,  academic_year_id, student_id):
        """Crea una encuesta en la base de datos"""
        survey = Encuesta(
          anio=academic_year_id,
          alumno_id=student_id
        )
        self.db.add(survey)
        self.db.commit()
        self.db.refresh(survey)

        return survey


    def create_answer_choice(self, survey_id, question_id, option_id):
        """Crea una respuesta en la base de datos"""

        answer = RespuestaEncuesta(
          encuesta_id=survey_id,
          pregunta_id=question_id,
          opcion_id=option_id
        )
        self.db.add(answer)
        self.db.commit()
        self.db.refresh(answer)
        return answer


    def create_answer_text(self, survey_id, question_id, answer):
        """Crea una respuesta en la base de datos"""

        answer = RespuestaTextoEncuesta(
          encuesta_id=survey_id,
          pregunta_id=question_id,
          texto=answer
        )
        self.db.add(answer)
        self.db.commit()
        self.db.refresh(answer)

        return answer
