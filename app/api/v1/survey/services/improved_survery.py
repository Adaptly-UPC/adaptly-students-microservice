# app/api/v1/students/services/improved_survey_processor.py

import pandas as pd
import io
import unicodedata
import re
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import logging
from app.api.v1.students.models import Alumno


from app.api.v1.students.services.base_grades_excel_processor import BaseExcelProcessor

logger = logging.getLogger(__name__)

class ImprovedSurveyProcessor(BaseExcelProcessor):
    def __init__(self, db):
        super().__init__(db)
        self.matching_threshold = 0.85  # Umbral de similitud para matching
        self.unmatched_students = []
        self.matched_students = []

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

    def _extract_student_name(self, row) -> str:
        """Extrae el nombre del estudiante de la fila"""
        try:
            # Asumiendo formato: apellidos, nombres
            if pd.notna(row[0]) and pd.notna(row[1]) and row[0] != row[1]:
                return f"{row[1]}, {row[0]}".upper()
            elif pd.notna(row[0]):
                return str(row[0]).upper()
            return ""
        except:
            return ""

    def _extract_age(self, row) -> Optional[int]:
        """Extrae la edad del estudiante"""
        try:
            age = row[3]
            if pd.notna(age) and isinstance(age, (int, float)):
                return int(age)
        except:
            pass
        return None

    def _extract_gender(self, row) -> str:
        """Extrae el género del estudiante"""
        try:
            if pd.notna(row[4]) and str(row[4]).lower() == "x":
                return "MASCULINO"
            elif pd.notna(row[5]) and str(row[5]).lower() == "x":
                return "FEMENINO"
            elif pd.notna(row[6]) and str(row[6]).lower() == "x":
                return "OTRO"
        except:
            pass
        return "NO_ESPECIFICADO"

    def _student_has_grades(self, student_id: int) -> bool:
        """Verifica si el estudiante tiene notas registradas"""
        from app.api.v1.students.models import HistorialAcademico, Nota

        historial = self.db.query(HistorialAcademico).filter(
            HistorialAcademico.alumno_id == student_id
        ).first()

        if historial:
            notas = self.db.query(Nota).filter(
                Nota.historial_id == historial.id
            ).first()
            return notas is not None

        return False

    def _process_study_hours(self, row, survey):
        """Procesa pregunta de horas de estudio"""
        study_hours = next(
            (i + 1 for i in range(3) if pd.notna(row[7 + i]) and str(row[7 + i]).lower() == "x"),
            0
        )

        if study_hours > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cuánto tiempo dedicas al estudio fuera del horario escolar?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                option_map = {
                    1: "Menos de 1 hora al día",
                    2: "Entre 1 y 2 horas al día",
                    3: "Más de 2 horas al día"
                }

                target_option = option_map.get(study_hours)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def _process_class_participation(self, row, survey):
        """Procesa pregunta de participación en clase"""
        participation = next(
            (i + 1 for i in range(4) if pd.notna(row[10 + i]) and str(row[10 + i]).lower() == "x"),
            0
        )

        if participation > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?"
            )
            if question:
                self._save_frequency_answer(survey, question, participation)

    def _process_help_seeking(self, row, survey):
        """Procesa pregunta sobre pedir ayuda"""
        help_seeking = next(
            (i + 1 for i in range(4) if pd.notna(row[14 + i]) and str(row[14 + i]).lower() == "x"),
            0
        )

        if help_seeking > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Pides ayuda cuando no entiendes un tema?"
            )
            if question:
                self._save_frequency_answer(survey, question, help_seeking)

    def _save_frequency_answer(self, survey, question, level):
        """Guarda respuestas de tipo frecuencia (Nunca, A veces, etc.)"""
        options = self.survey_repo.get_options_by_question_id(question.get("id"))
        frequency_map = {
            1: "Nunca",
            2: "A veces",
            3: "Casi siempre",
            4: "Siempre"
        }

        target_option = frequency_map.get(level)
        for option in options:
            if option.get("opcion") == target_option:
                self.create_answer_choice(
                    survey.id,
                    question.get("id"),
                    option.get("id")
                )
                break

    def _process_text_responses(self, row, survey):
        """Procesa respuestas de texto"""
        # Pregunta 13: Mejoras en clases
        if pd.notna(row[50]):
            question = self.survey_repo.get_question_by_text(
                "¿Qué mejorarías en las clases para aprender mejor?"
            )
            if question:
                self.create_answer_text(
                    survey.id,
                    question.get("id"),
                    str(row[50])
                )

        # Pregunta 14: Apoyo adicional
        if pd.notna(row[51]):
            question = self.survey_repo.get_question_by_text(
                "¿Qué tipo de apoyo adicional te gustaría recibir para mejorar tu aprendizaje?"
            )
            if question:
                self.create_answer_text(
                    survey.id,
                    question.get("id"),
                    str(row[51])
                )

    def _generate_matching_report(self, stats: Dict) -> str:
        """Genera un reporte detallado del proceso de matching"""
        report = []
        report.append("=== REPORTE DE PROCESAMIENTO DE ENCUESTAS ===\n")
        report.append(f"Total de registros procesados: {stats['total_processed']}")
        report.append(f"Estudiantes emparejados con notas: {stats['matched_with_grades']}")
        report.append(f"Estudiantes emparejados sin notas: {stats['matched_without_grades']}")
        report.append(f"Nuevos estudiantes creados: {stats['created_new']}")
        report.append(f"Errores encontrados: {stats['errors']}\n")

        if stats['matching_details']:
            report.append("=== DETALLES DE EMPAREJAMIENTO ===")
            for detail in stats['matching_details'][:10]:  # Mostrar primeros 10
                report.append(
                    f"- '{detail['survey_name']}' → '{detail['matched_to']}' "
                    f"(similitud: {detail['score']:.2%}, tiene notas: {'Sí' if detail['has_grades'] else 'No'})"
                )

        return "\n".join(report)

    # Métodos restantes para procesar otras preguntas...
    def _process_class_enjoyment(self, row, survey):
        """Procesa pregunta sobre gusto por las clases"""
        enjoyment = next(
            (i + 1 for i in range(4) if pd.notna(row[18 + i]) and str(row[18 + i]).lower() == "x"),
            0
        )

        if enjoyment > 0:
            question = self.survey_repo.get_question_by_text(
                "En general, ¿te gustan las clases?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                enjoyment_map = {
                    1: "Sí, mucho",
                    2: "A veces",
                    3: "No mucho",
                    4: "No me gustan"
                }

                target_option = enjoyment_map.get(enjoyment)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break


    def normalize_text(self, texto: str) -> str:
        """Normaliza texto para comparación mejorada"""
        if not texto:
            return ""

        # Convertir a string si no lo es
        texto = str(texto).strip()

        # Normalizar unicode
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

        # Convertir a minúsculas
        texto = texto.lower()

        # Eliminar caracteres especiales pero mantener espacios
        texto = re.sub(r'[^\w\s]', '', texto)

        # Normalizar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto).strip()

        return texto


    def find_best_match(self, name: str, existing_students: List) -> Tuple[Optional[object], float]:
        """Encuentra el mejor match para un nombre usando similitud difusa"""
        if not name:
            return None, 0.0

        normalized_name = self.normalize_text(name)
        best_match = None
        best_score = 0.0

        for student in existing_students:
            if not student.nombre_completo:
                continue

            normalized_existing = self.normalize_text(student.nombre_completo)

            # Calcular similitud
            score = SequenceMatcher(None, normalized_name, normalized_existing).ratio()

            # También verificar si uno contiene al otro
            if normalized_name in normalized_existing or normalized_existing in normalized_name:
                score = max(score, 0.9)

            # Verificar coincidencia de palabras clave (apellidos)
            words_name = set(normalized_name.split())
            words_existing = set(normalized_existing.split())

            # Si comparten al menos 2 palabras (probablemente apellidos)
            common_words = words_name.intersection(words_existing)
            if len(common_words) >= 2:
                score = max(score, 0.85)

            if score > best_score:
                best_score = score
                best_match = student

        return best_match, best_score

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


    def process_student_survey_improved(self, file_content: bytes) -> Dict:
        """Procesa las encuestas con mejor manejo de matching de estudiantes"""
        try:
            # Crear preguntas si no existen
            self.create_question_and_options()

            # Obtener todos los estudiantes existentes
            all_students = self.student_repo.db.query(self.student_repo.db.query(Alumno).all())

            # Estadísticas de procesamiento
            stats = {
                'total_processed': 0,
                'matched_with_grades': 0,
                'matched_without_grades': 0,
                'created_new': 0,
                'errors': 0,
                'matching_details': []
            }

            excel_file = pd.ExcelFile(io.BytesIO(file_content))

            for sheet in excel_file.sheet_names:
                df = excel_file.parse(sheet_name=sheet)
                df = df.iloc[3:, 1:]  # Saltar headers

                for index, row in df.iterrows():
                    try:
                        stats['total_processed'] += 1

                        # Procesar nombre
                        student_name = self._extract_student_name(row)
                        if not student_name:
                            logger.warning(f"Fila {index}: Nombre vacío, saltando")
                            continue

                        # Buscar mejor coincidencia
                        matched_student, match_score = self.find_best_match(
                            student_name,
                            all_students
                        )

                        # Decidir si usar el match o crear nuevo
                        if matched_student and match_score >= self.matching_threshold:
                            # Verificar si tiene notas
                            has_grades = self._student_has_grades(matched_student.id)

                            if has_grades:
                                stats['matched_with_grades'] += 1
                            else:
                                stats['matched_without_grades'] += 1

                            stats['matching_details'].append({
                                'survey_name': student_name,
                                'matched_to': matched_student.nombre_completo,
                                'score': match_score,
                                'has_grades': has_grades
                            })

                            student_registered = matched_student

                        else:
                            # Crear nuevo estudiante
                            gender = self._extract_gender(row)
                            student_registered = self.student_repo.create_student(
                                student_name,
                                None,
                                gender
                            )
                            stats['created_new'] += 1
                            all_students.append(student_registered)  # Agregar a la lista

                        # Actualizar edad si está disponible
                        age = self._extract_age(row)
                        if age:
                            self.student_repo.update_student(
                                student_registered.id,
                                age=age
                            )

                        # Procesar encuesta
                        self._process_survey_responses(row, student_registered)

                    except Exception as e:
                        logger.error(f"Error procesando fila {index}: {str(e)}")
                        stats['errors'] += 1
                        continue

            # Generar reporte de matching
            stats['matching_report'] = self._generate_matching_report(stats)

            return stats

        except Exception as e:
            logger.error(f"Error general en procesamiento: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _extract_student_name(self, row) -> str:
        """Extrae el nombre del estudiante de la fila"""
        try:
            # Asumiendo formato: apellidos, nombres
            if pd.notna(row[0]) and pd.notna(row[1]) and row[0] != row[1]:
                return f"{row[1]}, {row[0]}".upper()
            elif pd.notna(row[0]):
                return str(row[0]).upper()
            return ""
        except:
            return ""

    def _extract_age(self, row) -> Optional[int]:
        """Extrae la edad del estudiante"""
        try:
            age = row[3]
            if pd.notna(age) and isinstance(age, (int, float)):
                return int(age)
        except:
            pass
        return None

    def _extract_gender(self, row) -> str:
        """Extrae el género del estudiante"""
        try:
            if pd.notna(row[4]) and str(row[4]).lower() == "x":
                return "MASCULINO"
            elif pd.notna(row[5]) and str(row[5]).lower() == "x":
                return "FEMENINO"
            elif pd.notna(row[6]) and str(row[6]).lower() == "x":
                return "OTRO"
        except:
            pass
        return "NO_ESPECIFICADO"

    def _student_has_grades(self, student_id: int) -> bool:
        """Verifica si el estudiante tiene notas registradas"""
        from app.api.v1.students.models import HistorialAcademico, Nota

        historial = self.db.query(HistorialAcademico).filter(
            HistorialAcademico.alumno_id == student_id
        ).first()

        if historial:
            notas = self.db.query(Nota).filter(
                Nota.historial_id == historial.id
            ).first()
            return notas is not None

        return False

    def create_survey(self, academic_year_id, student_id):
        """Crea una encuesta en la base de datos"""
        survey = self.survey_repo.create_survey(academic_year_id, student_id)
        return survey
    def _process_effort_level(self, row, survey):
        """Procesa pregunta sobre nivel de esfuerzo"""
        effort = next(
            (i + 1 for i in range(4) if pd.notna(row[26 + i]) and str(row[26 + i]).lower() == "x"),
            0
        )

        if effort > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cuánto te esfuerzas en las tareas y exámenes?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                effort_map = {
                    1: "Mucho",
                    2: "Lo necesario",
                    3: "Poco",
                    4: "Casi nada"
                }

                target_option = effort_map.get(effort)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def _process_study_resources(self, row, survey):
        """Procesa pregunta sobre recursos de estudio (respuesta múltiple)"""
        # Mapeo de columnas a recursos
        resource_columns = {
            30: "Aplicaciones o plataformas digitales",
            31: "Videos educativos",
            32: "Libros físicos",
            33: "Apuntes de clase",
            34: "Tutorías o asesorías"
        }

        question = self.survey_repo.get_question_by_text(
            "¿Qué recursos utilizas para estudiar?"
        )

        if question:
            options = self.survey_repo.get_options_by_question_id(question.get("id"))

            # Verificar cada columna de recursos
            for col_index, resource_name in resource_columns.items():
                if pd.notna(row[col_index]) and str(row[col_index]).lower() == "x":
                    # Buscar la opción correspondiente
                    for option in options:
                        if option.get("opcion") == resource_name:
                            self.create_answer_choice(
                                survey.id,
                                question.get("id"),
                                option.get("id")
                            )
                            break

    def _process_internet_access(self, row, survey):
        """Procesa pregunta sobre acceso a internet"""
        has_internet = None

        if pd.notna(row[35]) and str(row[35]).lower() == "x":
            has_internet = "Sí"
        elif pd.notna(row[36]) and str(row[36]).lower() == "x":
            has_internet = "No"

        if has_internet:
            question = self.survey_repo.get_question_by_text(
                "¿Tienes acceso a internet en casa?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                for option in options:
                    if option.get("opcion") == has_internet:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def _process_technology_use(self, row, survey):
        """Procesa pregunta sobre uso de tecnología"""
        tech_use = next(
            (i + 1 for i in range(4) if pd.notna(row[37 + i]) and str(row[37 + i]).lower() == "x"),
            0
        )

        if tech_use > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cuánto utilizas la tecnología para aprender?"
            )
            if question:
                self._save_frequency_answer(survey, question, tech_use)

    def _process_extracurricular(self, row, survey):
        """Procesa pregunta sobre actividades extracurriculares"""
        extracurricular = None

        if pd.notna(row[41]) and str(row[41]).lower() == "x":
            extracurricular = "Sí"
        elif pd.notna(row[42]) and str(row[42]).lower() == "x":
            extracurricular = "No"

        if extracurricular:
            question = self.survey_repo.get_question_by_text(
                "¿Participas en actividades extracurriculares (deporte, arte, clubes)?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                for option in options:
                    if option.get("opcion") == extracurricular:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def _process_sleep_hours(self, row, survey):
        """Procesa pregunta sobre horas de sueño"""
        sleep = next(
            (i + 1 for i in range(3) if pd.notna(row[43 + i]) and str(row[43 + i]).lower() == "x"),
            0
        )

        if sleep > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cuántas horas duermes en promedio por noche?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                sleep_map = {
                    1: "Menos de 5 horas",
                    2: "Entre 5 y 7 horas",
                    3: "Más de 7 horas"
                }

                target_option = sleep_map.get(sleep)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def _process_stress_level(self, row, survey):
        """Procesa pregunta sobre nivel de estrés"""
        stress = next(
            (i + 1 for i in range(4) if pd.notna(row[46 + i]) and str(row[46 + i]).lower() == "x"),
            0
        )

        if stress > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?"
            )
            if question:
                self._save_frequency_answer(survey, question, stress)

    def _process_class_participation(self, row, survey):
        """Procesa pregunta de participación en clase"""
        participation = next(
            (i + 1 for i in range(4) if pd.notna(row[10 + i]) and str(row[10 + i]).lower() == "x"),
            0
        )

        if participation > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?"
            )
            if question:
                self._save_frequency_answer(survey, question, participation)

    def _process_survey_responses(self, row, student):
        """Procesa todas las respuestas de la encuesta para un estudiante"""
        # Crear encuesta
        current_year = 2025
        academic_year = self.year_repo.get_or_create_academic_year(current_year)
        survey = self.create_survey(academic_year.id, student.id)

        # Procesar cada pregunta
        self._process_study_hours(row, survey)
        self._process_class_participation(row, survey)
        self._process_help_seeking(row, survey)
        self._process_class_enjoyment(row, survey)
        self._process_difficulty_perception(row, survey)
        self._process_effort_level(row, survey)
        self._process_study_resources(row, survey)
        self._process_internet_access(row, survey)
        self._process_technology_use(row, survey)
        self._process_extracurricular(row, survey)
        self._process_sleep_hours(row, survey)
        self._process_stress_level(row, survey)
        self._process_text_responses(row, survey)



    def _process_difficulty_perception(self, row, survey):
        """Procesa pregunta sobre percepción de dificultad"""
        difficulty = next(
            (i + 1 for i in range(4) if pd.notna(row[22 + i]) and str(row[22 + i]).lower() == "x"),
            0
        )

        if difficulty > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cómo calificas la dificultad de las materias en general?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                difficulty_map = {
                    1: "Muy fáciles",
                    2: "Normales",
                    3: "Difíciles",
                    4: "Muy difíciles"
                }

                target_option = difficulty_map.get(difficulty)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break





    def _process_study_hours(self, row, survey):
        """Procesa pregunta de horas de estudio"""
        study_hours = next(
            (i + 1 for i in range(3) if pd.notna(row[7 + i]) and str(row[7 + i]).lower() == "x"),
            0
        )

        if study_hours > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Cuánto tiempo dedicas al estudio fuera del horario escolar?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                option_map = {
                    1: "Menos de 1 hora al día",
                    2: "Entre 1 y 2 horas al día",
                    3: "Más de 2 horas al día"
                }

                target_option = option_map.get(study_hours)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break

    def create_answer_choice(self, survey_id, question_id, option_id):
        """Crea una respuesta en la base de datos"""
        answer = self.survey_repo.create_answer_choice(survey_id, question_id, option_id)
        return answer

    def _process_class_participation(self, row, survey):
        """Procesa pregunta de participación en clase"""
        participation = next(
            (i + 1 for i in range(4) if pd.notna(row[10 + i]) and str(row[10 + i]).lower() == "x"),
            0
        )

        if participation > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?"
            )
            if question:
                self._save_frequency_answer(survey, question, participation)

    def _process_help_seeking(self, row, survey):
        """Procesa pregunta sobre pedir ayuda"""
        help_seeking = next(
            (i + 1 for i in range(4) if pd.notna(row[14 + i]) and str(row[14 + i]).lower() == "x"),
            0
        )

        if help_seeking > 0:
            question = self.survey_repo.get_question_by_text(
                "¿Pides ayuda cuando no entiendes un tema?"
            )
            if question:
                self._save_frequency_answer(survey, question, help_seeking)

    def _save_frequency_answer(self, survey, question, level):
        """Guarda respuestas de tipo frecuencia (Nunca, A veces, etc.)"""
        options = self.survey_repo.get_options_by_question_id(question.get("id"))
        frequency_map = {
            1: "Nunca",
            2: "A veces",
            3: "Casi siempre",
            4: "Siempre"
        }

        target_option = frequency_map.get(level)
        for option in options:
            if option.get("opcion") == target_option:
                self.create_answer_choice(
                    survey.id,
                    question.get("id"),
                    option.get("id")
                )
                break

    def _process_text_responses(self, row, survey):
        """Procesa respuestas de texto"""
        # Pregunta 13: Mejoras en clases
        if pd.notna(row[50]):
            question = self.survey_repo.get_question_by_text(
                "¿Qué mejorarías en las clases para aprender mejor?"
            )
            if question:
                self.create_answer_text(
                    survey.id,
                    question.get("id"),
                    str(row[50])
                )

        # Pregunta 14: Apoyo adicional
        if pd.notna(row[51]):
            question = self.survey_repo.get_question_by_text(
                "¿Qué tipo de apoyo adicional te gustaría recibir para mejorar tu aprendizaje?"
            )
            if question:
                self.create_answer_text(
                    survey.id,
                    question.get("id"),
                    str(row[51])
                )

    def create_answer_text(self, survey_id, question_id, answer):
        """Crea una respuesta en la base de datos"""
        answer = self.survey_repo.create_answer_text(survey_id, question_id, answer)
        return answer

    def _generate_matching_report(self, stats: Dict) -> str:
        """Genera un reporte detallado del proceso de matching"""
        report = []
        report.append("=== REPORTE DE PROCESAMIENTO DE ENCUESTAS ===\n")
        report.append(f"Total de registros procesados: {stats['total_processed']}")
        report.append(f"Estudiantes emparejados con notas: {stats['matched_with_grades']}")
        report.append(f"Estudiantes emparejados sin notas: {stats['matched_without_grades']}")
        report.append(f"Nuevos estudiantes creados: {stats['created_new']}")
        report.append(f"Errores encontrados: {stats['errors']}\n")

        if stats['matching_details']:
            report.append("=== DETALLES DE EMPAREJAMIENTO ===")
            for detail in stats['matching_details'][:10]:  # Mostrar primeros 10
                report.append(
                    f"- '{detail['survey_name']}' → '{detail['matched_to']}' "
                    f"(similitud: {detail['score']:.2%}, tiene notas: {'Sí' if detail['has_grades'] else 'No'})"
                )

        return "\n".join(report)

    # Métodos restantes para procesar otras preguntas...
    def _process_class_enjoyment(self, row, survey):
        """Procesa pregunta sobre gusto por las clases"""
        enjoyment = next(
            (i + 1 for i in range(4) if pd.notna(row[18 + i]) and str(row[18 + i]).lower() == "x"),
            0
        )

        if enjoyment > 0:
            question = self.survey_repo.get_question_by_text(
                "En general, ¿te gustan las clases?"
            )
            if question:
                options = self.survey_repo.get_options_by_question_id(question.get("id"))
                enjoyment_map = {
                    1: "Sí, mucho",
                    2: "A veces",
                    3: "No mucho",
                    4: "No me gustan"
                }

                target_option = enjoyment_map.get(enjoyment)
                for option in options:
                    if option.get("opcion") == target_option:
                        self.create_answer_choice(
                            survey.id,
                            question.get("id"),
                            option.get("id")
                        )
                        break