from app.api.v1.students.services.base_grades_excel_processor import BaseExcelProcessor
import pandas as pd
import io
import unicodedata

class SurveyProcessor(BaseExcelProcessor):

    def get_questions(self):
        return  [
            # {
            #     "pregunta": "nombre_completo",
            #     "tipo": "texto"
            # },
            # {
            #     "pregunta": "Grado",
            #     "tipo": "texto"
            # },
            # {
            #     "pregunta": "Edad",
            #     "tipo": "número"
            # },
            # {
            #     "pregunta": "Género",
            #     "tipo": "selección",
            #     "opciones": [
            #     "Masculino",
            #     "Femenino",
            #     "Prefiero no decirlo"
            #     ]
            # },
            {
                "pregunta": "¿Cuánto tiempo dedicas al estudio fuera del horario escolar?",
                "tipo": "selección",
                "opciones": [
                "Menos de 1 hora al día",
                "Entre 1 y 2 horas al día",
                "Más de 2 horas al día"
                ]
            },
            {
                "pregunta": "¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?",
                "tipo": "selección",
                "opciones": [
                "Nunca",
                "A veces",
                "Casi siempre",
                "Siempre"
                ]
            },
            {
                "pregunta": "¿Pides ayuda cuando no entiendes un tema?",
                "tipo": "selección",
                "opciones": [
                "Nunca",
                "A veces",
                "Casi siempre",
                "Siempre"
                ]
            },
            {
                "pregunta": "En general, ¿te gustan las clases?",
                "tipo": "selección",
                "opciones": [
                "Sí, mucho",
                "A veces",
                "No mucho",
                "No me gustan"
                ]
            },
            {
                "pregunta": "¿Cómo calificas la dificultad de las materias en general?",
                "tipo": "selección",
                "opciones": [
                "Muy fáciles",
                "Normales",
                "Difíciles",
                "Muy difíciles"
                ]
            },
            {
                "pregunta": "¿Cuánto te esfuerzas en las tareas y exámenes?",
                "tipo": "selección",
                "opciones": [
                "Mucho",
                "Lo necesario",
                "Poco",
                "Casi nada"
                ]
            },
            {
                "pregunta": "¿Qué recursos utilizas para estudiar?",
                "tipo": "selección múltiple",
                "opciones": [
                "Videos educativos",
                "Libros físicos",
                "Apuntes de clase",
                "Tutorías o asesorías",
                "Aplicaciones o plataformas digitales"
                ]
            },
            {
                "pregunta": "¿Tienes acceso a internet en casa?",
                "tipo": "selección",
                "opciones": [
                "Sí",
                "No"
                ]
            },
            {
                "pregunta": "¿Cuánto utilizas la tecnología para aprender?",
                "tipo": "selección",
                "opciones": [
                "Nunca",
                "A veces",
                "Casi siempre",
                "Siempre"
                ]
            },
            {
                "pregunta": "¿Participas en actividades extracurriculares (deporte, arte, clubes)?",
                "tipo": "selección",
                "opciones": [
                "Sí",
                "No"
                ]
            },
            {
                "pregunta": "¿Cuántas horas duermes en promedio por noche?",
                "tipo": "selección",
                "opciones": [
                "Menos de 5 horas",
                "Entre 5 y 7 horas",
                "Más de 7 horas"
                ]
            },
            {
                "pregunta": "¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?",
                "tipo": "selección",
                "opciones": [
                "Nunca",
                "A veces",
                "Casi siempre",
                "Siempre"
                ]
            },
            {
                "pregunta": "¿Qué mejorarías en las clases para aprender mejor?",
                "tipo": "texto"
            },
            {
                "pregunta": "¿Qué tipo de apoyo adicional te gustaría recibir para mejorar tu aprendizaje?",
                "tipo": "texto"
            }
        ]

    def normalizar_texto(self,texto: str) -> str:
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

        # Reemplazar espacios por guión bajo y convertir a minúsculas
        texto = texto.replace(' ', '_').lower()

        return texto

    def create_question_and_options(self):
        """Crea las preguntas en la base de datos"""
        questions_list = self.get_questions()

        for question_data in questions_list:
            question_text = question_data["pregunta"]
            is_multiple_choice = True if question_data["tipo"] == "selección múltiple" else False
            question_type = "abierta" if question_data["tipo"] == "texto" else "cerrada"


            question = self.survey_repo.create_question(question_text, is_multiple_choice, question_type)

            if question_type == "cerrada":
                options = question_data["opciones"]
                for option in options:
                    self.survey_repo.create_options(option, question.id)

        print("preguntas creadas")


    def create_survey(self, academic_year_id, student_id):
        """Crea una encuesta en la base de datos"""
        survey = self.survey_repo.create_survey(academic_year_id, student_id)
        return survey

    def create_answer_choice(self, survey_id, question_id, option_id):
        """Crea una respuesta en la base de datos"""
        answer = self.survey_repo.create_answer_choice(survey_id, question_id, option_id)
        return answer

    def create_answer_text(self, survey_id, question_id, answer):
        """Crea una respuesta en la base de datos"""
        answer = self.survey_repo.create_answer_text(survey_id, question_id, answer)
        return answer

    def get_dic_id(self, diccionario):
        return diccionario.get("id")

    def get_option_dic(self, diccionario):
        return diccionario.get("opcion")

    def process_student_survey(self, file_content: bytes):
        """Procesa las encuestas de los estudiantes de Secundaria."""
        self.create_question_and_options()
        excel_file = pd.ExcelFile(io.BytesIO(file_content))

        csv_names = excel_file.sheet_names

        for sheet in csv_names:
            df = excel_file.parse(sheet_name=sheet)
            df = df.iloc[3:, 1:]

            for _, row in df.iterrows():
                student_name = f"{row[1]}, {row[0]}".upper() if row[0] != row[1] else f"{row[0]}".upper()
                age = row[3]

                student_registered = self.student_repo.get_student_by_name(student_name)

                if not student_registered:
                    flexible_name = self.student_repo.find_student_by_flexible_name(student_name)

                    if flexible_name:
                        student_registered = flexible_name
                    else:
                        student_registered = self.student_repo.create_student(student_name, None)

                    if isinstance(age, int) == int:
                        self.student_repo.update_student(student_registered.id, age=age)


                current_academic_year = 2025
                academic_year = self.year_repo.get_or_create_academic_year(current_academic_year)

                survey = self.create_survey(academic_year.id, student_registered.id)


                # Grado y sección
                # degree_section = str(row[2]).split()
                # degree = degree_section[0].replace("°", "") if len(degree_section) > 0 else ""
                # section = degree_section[1] if len(degree_section) > 1 else ""

                # Género
                gender = "MASCULINO" if str(row[4]).lower() == "x" else (
                        "FEMENINO" if str(row[5]).lower() == "x" else (
                        "OTRO" if str(row[6]).lower() == "x" else None))

                self.student_repo.update_student(student_registered.id, gender=gender)

                # Pregunta 1: ¿Cuánto tiempo dedicas al estudio fuera del horario escolar?
                # 1 -> Menos de 1 hora al día
                # 2 -> Entre 1 y 2 horas al día
                # 3 -> Más de 2 horas al día
                study_hours_out_of_class = next(
                    (i + 1 for i in range(3) if str(row[7 + i]).lower() == "x"),
                    0
                )

                question_one = self.survey_repo.get_question_by_text("¿Cuánto tiempo dedicas al estudio fuera del horario escolar?")

                if(not question_one):
                    return "Error en la primera pregunta"

                options_one = self.survey_repo.get_options_by_question_id(question_one.get("id"))
                match study_hours_out_of_class:
                    case 1:

                        for option in options_one:
                            if option.get("opcion") == "Menos de 1 hora al día":
                                self.create_answer_choice(survey.id, question_one.get("id"), option.get("id"))
                    case 2:
                        for option in options_one:
                            if option.get("opcion") == "Entre 1 y 2 horas al día":
                                self.create_answer_choice(survey.id, question_one.get("id"), option.get("id"))
                    case 3:
                        for option in options_one:
                            if option.get("opcion") == "Más de 2 horas al día":
                                self.create_answer_choice(survey.id, question_one.get("id"), option.get("id"))

                # Pregunta 2: ¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?
                # 1 -> Nunca
                # 2 -> A veces
                # 3 -> Casi siempre
                # 4 -> Siempre
                participate_in_class = next(
                    (i + 1 for i in range(4) if str(row[10 + i]).lower() == "x"),
                    0
                )

                question_two = self.survey_repo.get_question_by_text("¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?")
                question_two_id = self.get_dic_id(question_two)
                options_two = self.survey_repo.get_options_by_question_id(question_two_id)

                match participate_in_class:
                    case 1:
                        for option in options_two:
                            if self.get_option_dic(option) == "Nunca":
                                self.create_answer_choice(survey.id, question_two_id, self.get_dic_id(option))
                    case 2:
                        for option in options_two:
                            if self.get_option_dic(option) == "A veces":
                                self.create_answer_choice(survey.id,question_two_id, self.get_dic_id(option))
                    case 3:
                        for option in options_two:
                            if self.get_option_dic(option) == "Casi siempre":
                                self.create_answer_choice(survey.id,question_two_id, self.get_dic_id(option))
                    case 4:
                        for option in options_two:
                            if self.get_option_dic(option) == "Siempre":
                                self.create_answer_choice(survey.id,question_two_id, self.get_dic_id(option))

                # Pregunta 3: ¿Pides ayuda cuando no entiendes un tema?
                # 1 -> Nunca
                # 2 -> A veces
                # 3 -> Casi siempre
                # 4 -> Siempre
                ask_for_help = next(
                    (i + 1 for i in range(4) if str(row[14 + i]).lower() == "x"),
                    0
                )

                question_three = self.survey_repo.get_question_by_text("¿Pides ayuda cuando no entiendes un tema?")

                question_three_id = self.get_dic_id(question_three)
                options_three = self.survey_repo.get_options_by_question_id(question_three_id)

                match ask_for_help:
                    case 1:
                        for option in options_three:
                            if self.get_option_dic(option) == "Nunca":
                                self.create_answer_choice(survey.id, question_three_id, self.get_dic_id(option))
                    case 2:
                        for option in options_three:
                            if self.get_option_dic(option) == "A veces":
                                self.create_answer_choice(survey.id, question_three_id,  self.get_dic_id(option))
                    case 3:
                        for option in options_three:
                            if self.get_option_dic(option) == "Casi siempre":
                                self.create_answer_choice(survey.id, question_three_id,  self.get_dic_id(option))
                    case 4:
                        for option in options_three:
                            if self.get_option_dic(option) == "Siempre":
                                self.create_answer_choice(survey.id, question_three_id,  self.get_dic_id(option))

                # Pregunta 4: En general, ¿te gustan las clases?
                # 1 -> Sí, mucho
                # 2 -> A veces
                # 3 -> No mucho
                # 4 -> No me gustan

                general_class_likes = next(
                    (i + 1 for i in range(4) if str(row[18 + i]).lower() == "x"),
                    0
                )

                question_four = self.survey_repo.get_question_by_text("En general, ¿te gustan las clases?")
                question_four_id = self.get_dic_id(question_four)
                options_four = self.survey_repo.get_options_by_question_id(question_four_id)

                match general_class_likes:
                    case 1:
                        for option in options_four:
                            if self.get_option_dic(option) == "Sí, mucho":
                                self.create_answer_choice(survey.id, question_four_id, self.get_dic_id(option))
                    case 2:
                        for option in options_four:
                            if self.get_option_dic(option) == "A veces":
                                self.create_answer_choice(survey.id, question_four_id, self.get_dic_id(option))
                    case 3:
                        for option in options_four:
                            if self.get_option_dic(option) == "No mucho":
                                self.create_answer_choice(survey.id, question_four_id, self.get_dic_id(option))
                    case 4:
                        for option in options_four:
                            if self.get_option_dic(option) == "No me gustan":
                                self.create_answer_choice(survey.id, question_four_id, self.get_dic_id(option))

                # Pregunta 5: ¿Cómo calificas la dificultad de las materias en general?
                # 1 -> Muy fáciles
                # 2 -> Normales
                # 3 -> Difíciles
                # 4 -> Muy difficiles

                materia_level = next(
                    (i + 1 for i in range(4) if str(row[22 + i]).lower() == "x"),
                    0
                )

                question_five = self.survey_repo.get_question_by_text("¿Cómo calificas la dificultad de las materias en general?")
                question_five_id = self.get_dic_id(question_five)
                options_five = self.survey_repo.get_options_by_question_id(question_five_id)

                match materia_level:
                    case 1:
                        for option in options_five:
                            if self.get_option_dic(option) == "Muy fáciles":
                                self.create_answer_choice(survey.id, question_five_id, self.get_dic_id(option))
                    case 2:
                        for option in options_five:
                            if self.get_option_dic(option) == "Normales":
                                self.create_answer_choice(survey.id, question_five_id, self.get_dic_id(option))
                    case 3:
                        for option in options_five:
                            if self.get_option_dic(option) == "Difíciles":
                                self.create_answer_choice(survey.id, question_five_id, self.get_dic_id(option))
                    case 4:
                        for option in options_five:
                            if self.get_option_dic(option) == "Muy difficiles":
                                self.create_answer_choice(survey.id, question_five_id, self.get_dic_id(option))

                # Pregunta 6: ¿Cuánto te esfuerzas en las tareas y exámenes?
                # 1 -> Mucho
                # 2 -> Lo necesario
                # 3 -> Poco
                # 4 -> Casi nada
                effort = next(
                    (i + 1 for i in range(4) if str(row[26 + i]).lower() == "x"),
                    0
                )

                question_six = self.survey_repo.get_question_by_text("¿Cuánto te esfuerzas en las tareas y exámenes?")
                question_six_id = self.get_dic_id(question_six)

                options_six = self.survey_repo.get_options_by_question_id(question_six_id)

                match effort:
                    case 1:
                        for option in options_six:
                            if self.get_option_dic(option) == "Mucho":
                                self.create_answer_choice(survey.id, question_six_id, self.get_dic_id(option))
                    case 2:
                        for option in options_six:
                            if self.get_option_dic(option) == "Lo necesario":
                                self.create_answer_choice(survey.id, question_six_id, self.get_dic_id(option))
                    case 3:
                        for option in options_six:
                            if self.get_option_dic(option) == "Poco":
                                self.create_answer_choice(survey.id, question_six_id, self.get_dic_id(option))
                    case 4:
                        for option in options_six:
                            if self.get_option_dic(option) == "Casi nada":
                                self.create_answer_choice(survey.id, question_six_id, self.get_dic_id(option))


                # Pregunta 7: ¿Qué recursos utilizas para estudiar? (puedes marcar más de uno)
                # Multiples respuestas posibles
                # Videos educativos	Libros físicos	Apuntes de clase	Tutorías o asesorías
                # 1 - Aplicaciones o plataformas digitales
                # 2 - Videos educativos
                # 3 - Libros físicos
                # 4 - Apuntes de clase
                # 5 - Tutorías o asesorías

                study_resources = {
                    "aplicaciones_o_plataformas_digitales":  True if isinstance(row[30], str) and row[30].lower() == "x" else False,
                    "videos_educativos": True if isinstance(row[31], str) and str(row[31]).lower() == "x" else False,
                    "libros_fisicos":   True if isinstance(row[32], str) and str(row[32]).lower() == "x" else False,
                    "apuntes_de_clase":  True if isinstance(row[33], str) and str(row[33]).lower() == "x" else False,
                    "tutorias_o_asesorias":  True if isinstance(row[34], str) and str(row[34]).lower() == "x" else False,
                }

                question_seven = self.survey_repo.get_question_by_text("¿Qué recursos utilizas para estudiar?")
                question_seven_id = self.get_dic_id(question_seven)
                options_seven = self.survey_repo.get_options_by_question_id(question_seven_id)


                for option in options_seven: # TODO: Revisar
                    if study_resources[self.normalizar_texto(self.get_option_dic(option))]:
                        self.create_answer_choice(survey.id, question_seven_id, self.get_dic_id(option))

                # Pregunt 8: ¿Tienes acceso a internet en casa?
                # 1 - Sí
                # 2 - No
                has_internet_at_home = True if str(row[35]).lower() == "x" else (
                    False if str(row[36]).lower() == "x" else False)

                question_eight = self.survey_repo.get_question_by_text("¿Tienes acceso a internet en casa?")

                question_eight_id = self.get_dic_id(question_eight)

                options_eight = self.survey_repo.get_options_by_question_id(question_eight_id)

                match has_internet_at_home:
                    case True:
                        for option in options_eight:
                            if  self.get_option_dic(option) == "Sí":
                                self.create_answer_choice(survey.id, question_eight_id, self.get_dic_id(option))
                    case False:
                        for option in options_eight:
                            if  self.get_option_dic(option) == "No":
                                self.create_answer_choice(survey.id, question_eight_id, self.get_dic_id(option))

                # Pregunta 9: ¿Cuánto utilizas la tecnología para aprender?
                # 1 - Nunca
                # 2 - A veces
                # 3 - Casi siempre
                # 4 - Siempre
                technology_used_to_learn = next(
                    (i + 1 for i in range(4) if str(row[37 + i]).lower() == "x"),
                    0
                )

                question_nine = self.survey_repo.get_question_by_text("¿Cuánto utilizas la tecnología para aprender?")
                question_nine_id = self.get_dic_id(question_nine)

                options_nine = self.survey_repo.get_options_by_question_id(question_nine_id)

                match technology_used_to_learn:
                    case 1:
                        for option in options_nine:
                            if self.get_option_dic(option) == "Nunca":
                                self.create_answer_choice(survey.id, question_nine_id, self.get_dic_id(option))
                    case 2:
                        for option in options_nine:
                            if self.get_option_dic(option) == "A veces":
                                self.create_answer_choice(survey.id, question_nine_id, self.get_dic_id(option))
                    case 3:
                        for option in options_nine:
                            if self.get_option_dic(option) == "Casi siempre":
                                self.create_answer_choice(survey.id, question_nine_id, self.get_dic_id(option))
                    case 4:
                        for option in options_nine:
                            if self.get_option_dic(option) == "Siempre":
                                self.create_answer_choice(survey.id, question_nine_id, self.get_dic_id(option))


                # Pregunta 10: ¿Participas en actividades extracurriculares (deporte, arte, clubes)?
                # 1 - Sí
                # 2 - No
                extra_curricular_activities = True if str(row[41]).lower() == "x" else (
                    False if str(row[42]).lower() == "x" else False)

                question_ten = self.survey_repo.get_question_by_text("¿Participas en actividades extracurriculares (deporte, arte, clubes)?")
                question_ten_id = self.get_dic_id(question_ten)
                options_ten = self.survey_repo.get_options_by_question_id(question_ten_id)

                match extra_curricular_activities:
                    case True:
                        for option in options_ten:
                            if self.get_option_dic(option) == "Sí":
                                self.create_answer_choice(survey.id, question_ten_id, self.get_dic_id(option))
                    case False:
                        for option in options_ten:
                            if self.get_option_dic(option) == "No":
                                self.create_answer_choice(survey.id, question_ten_id, self.get_dic_id(option))

                # Pregunta 11: ¿Cuántas horas duermes en promedio por noche?
                # Menos de 5 horas	Entre 5 y 7 horas	Más de 7 horas
                # 1 - Menos de 5 horas
                # 2 - Entre 5 y 7 horas
                # 3 - Más de 7 horas

                sleep_hours = next(
                    (i + 1 for i in range(3) if str(row[43 + i]).lower() == "x"),
                    0
                )

                question_eleven = self.survey_repo.get_question_by_text("¿Cuántas horas duermes en promedio por noche?")

                question_eleven_id = self.get_dic_id(question_eleven)

                options_eleven = self.survey_repo.get_options_by_question_id(question_eleven_id)

                match sleep_hours:
                    case 1:
                        for option in options_eleven:
                            if self.get_option_dic(option) == "Menos de 5 horas":
                                self.create_answer_choice(survey.id, question_eleven_id, self.get_dic_id(option))
                    case 2:
                        for option in options_eleven:
                            if self.get_option_dic(option) == "Entre 5 y 7 horas":
                                self.create_answer_choice(survey.id, question_eleven_id, self.get_dic_id(option))
                    case 3:
                        for option in options_eleven:
                            if self.get_option_dic(option) == "Más de 7 horas":
                                self.create_answer_choice(survey.id, question_eleven_id, self.get_dic_id(option))


                # Pregunta 12: ¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?
                # Nunca	A veces	Casi siempre	Siempre
                # 1 - Nunca
                # 2 - A veces
                # 3 - Casi siempre
                # 4 - Siempre

                level_anxiety = next(
                    (i + 1 for i in range(4) if str(row[46 + i]).lower() == "x"),
                    0
                )

                question_twelve = self.survey_repo.get_question_by_text("¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?")

                question_twelve_id = self.get_dic_id(question_twelve)
                options_twelve = self.survey_repo.get_options_by_question_id(question_twelve_id)

                match level_anxiety:
                    case 1:
                        for option in options_twelve:
                            if self.get_option_dic(option) == "Nunca":
                                self.create_answer_choice(survey.id, question_twelve_id, self.get_dic_id(option))
                    case 2:
                        for option in options_twelve:
                            if self.get_option_dic(option) == "A veces":
                                self.create_answer_choice(survey.id, question_twelve_id, self.get_dic_id(option))
                    case 3:
                        for option in options_twelve:
                            if self.get_option_dic(option) == "Casi siempre":
                                self.create_answer_choice(survey.id, question_twelve_id, self.get_dic_id(option))
                    case 4:
                        for option in options_twelve:
                            if self.get_option_dic(option) == "Siempre":
                                self.create_answer_choice(survey.id, question_twelve_id, self.get_dic_id(option))


                # Pregunta 13: ¿Qué mejorarías en las clases para aprender mejor?

                improvement_request = row[50] if type(row[50]) == str and row[50] is not None else ""

                question_thirteen = self.survey_repo.get_question_by_text("¿Qué mejorarías en las clases para aprender mejor?")
                question_thirteen_id = self.get_dic_id(question_thirteen)
                self.survey_repo.create_answer_text(survey.id, question_thirteen_id, improvement_request)


                # Pregunta 14: ¿Qué tipo de apoyo adicional te gustaría recibir para mejorar tu aprendizaje?
                additional_support =  row[51] if type(row[51]) == str and row[51] is not None else ""

                question_fourteen = self.survey_repo.get_question_by_text("¿Qué tipo de apoyo adicional te gustaría recibir para mejorar tu aprendizaje?")
                question_fourteen_id = self.get_dic_id(question_fourteen)
                self.survey_repo.create_answer_text(survey.id, question_fourteen_id, additional_support)


