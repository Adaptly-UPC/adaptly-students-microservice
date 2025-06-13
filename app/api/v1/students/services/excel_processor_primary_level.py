import io
from dataclasses import dataclass
import pandas as pd
from app.api.v1.students.services.base_grades_excel_processor import BaseExcelProcessor
from app.utils.retrieve_dregree import get_degree_by_number

@dataclass
class GenericData:
    """Clase para tipar almacenar datos generales"""
    level: dict
    bimester: dict
    degree: dict
    section: dict
    school: str
    academic_year: dict
    modular_code: str

class ExcelProcessor(BaseExcelProcessor):
    """Procesa el archivo Excel y guarda los datos de estudiantes de Primaria en la base de datos."""
    def load_excel(self, file_content: bytes) -> pd.ExcelFile:
        """Carga el contenido del archivo Excel en un objeto pd.ExcelFile."""
        excel_data = pd.ExcelFile(io.BytesIO(file_content))
        return excel_data


    def get_generic_data(self, excel_data: pd.DataFrame):
        """Extrae los datos generales del archivo Excel."""
        sheet_names = excel_data.sheet_names
        if not sheet_names:
            raise ValueError("El archivo Excel no contiene hojas.")

        first_sheet = excel_data.parse(sheet_names[0], header=None)
        base_data = {
            "ugel": {
                "code": None,
                "name": ""
            },
            "school":{
                "code": None,
                "name": ""
            },
            "modular_code": None
        }
        generic_data = first_sheet.iloc[1:10, 1: 3].T

        school = generic_data.iloc[1, 2].split()
        base_data["ugel"]["code"] = generic_data.iloc[1, 0]
        base_data["ugel"]["name"] = generic_data.iloc[1, 1]
        base_data["school"]["code"] = school[0]
        base_data["school"]["name"] = generic_data.iloc[1, 2]
        base_data["modular_code"] = generic_data.iloc[1, 3]

        degree=get_degree_by_number(generic_data.iloc[1, 4])
        section=generic_data.iloc[1, 5]

        level_obj = self.level_repo.get_or_create_academic_level("PRIMARIA")
        bimester_obj = self.bimester_repo.get_or_create_bimester("NO APLICA")
        degree_obj = self.grade_repo.get_or_create_degree(degree, level_obj.id)
        section_obj = self.section_repo.get_or_create_section(section)
        academic_year_obj = self.year_repo.get_or_create_academic_year(2024)
        return {
            "level":level_obj,
            "bimester":bimester_obj,
            "degree":degree_obj,
            "section":section_obj,
            "school":base_data["school"]["name"],
            "academic_year":academic_year_obj,
            "modular_code":base_data["modular_code"]
        }


    def pesonal_social_calification(self, row: pd.Series):
        """Procesa las calificaciones de Personal Social."""
        personal_social_califications = [
            {
                "criteria": "Construye su identidad",
                "calification": str(row.iloc[4]),
            },
            {
                "criteria": "Convive y participa democráticamente en la búsqueda del bien común",
                "calification": str(row.iloc[5]),
            },
            {
                "criteria": "Construye interpretaciones históricas",
                "calification": str(row.iloc[6]),
            },
            {
                "criteria": "Gestiona responsablemente el espacio y el ambiente",
                "calification": str(row.iloc[7]),
            },
            {
                "criteria": "Gestiona responsablemente los recursos económicos",
                "calification": str(row.iloc[8]),
            }
        ]

        return personal_social_califications

    def educacion_fisica_calification(self, row: pd.Series):
        """Procesa las calificaciones de Educación Física."""
        educacion_fisica_califications = [
            {
                "criteria": "Se desenvuelve de manera autónoma a través de su motricidad",
                "calification": str(row.iloc[9]),
            },
            {
                "criteria": "Asume una vida saludable",
                "calification": str(row.iloc[10]),
            },
            {
                "criteria": "Interactúa a través de sus habilidades sociomotrices",
                "calification": str(row.iloc[11]),
            }
        ]

        return educacion_fisica_califications

    def comunicacion_calification(self, row: pd.Series):
        """Procesa las calificaciones de Comunicación."""
        comunicacion_califications = [
            {
                "criteria": "Se comunica oralmente en su lengua materna",
                "calification": str(row.iloc[12]),
            },
            {
                "criteria": "Lee diversos tipos de textos escritos en su lengua materna",
                "calification": str(row.iloc[13]),
            },
            {
                "criteria": "Escribe diversos tipos de textos en su lengua materna",
                "calification": str(row.iloc[14]),
            }
        ]

        return comunicacion_califications

    def arte_y_cultura_calification(self, row: pd.Series):
        """Procesa las calificaciones de Arte y Cultura."""
        arte_y_cultura_califications = [
            {
                "criteria": "Aprecia de manera crítica manifestaciones artístico- culturales",
                "calification": str(row.iloc[15]),
            },
            {
                "criteria": "Crea proyectos desde los lenguajes artísticos",
                "calification": str(row.iloc[16]),
            }
        ]

        return arte_y_cultura_califications

    def matematica_calification(self, row: pd.Series):
        """Procesa las calificaciones de Matemática."""
        matematica_califications = [
            {
                "criteria": "Resuelve problemas de cantidad",
                "calification": str(row.iloc[24]),
            },
            {
                "criteria": "Resuelve problemas de regularidad, equivalencia y cambio",
                "calification": str(row.iloc[25]),
            },
            {
                "criteria": "Resuelve problemas de forma, movimiento y localización",
                "calification": str(row.iloc[26]),
            },
            {
                "criteria": "Resuelve problemas de gestión de datos e incertidumbre",
                "calification": str(row.iloc[27]),
            }
        ]

        return matematica_califications

    def ciencia_y_tecnologia_calification(self, row: pd.Series):
        """Procesa las calificaciones de Ciencia y Tecnología."""
        ciencia_califications = [
            {
                "criteria": "Indaga mediante métodos científicos para construir sus conocimientos",
                "calification": str(row.iloc[28]),
            },
            {
                "criteria": "Explica el mundo físico basándose en conocimientos sobre los seres vivos; materia y energía; biodiversidad, Tierra y Universo",
                "calification": str(row.iloc[29]),
            },
            {
                "criteria": "Diseña y construye soluciones tecnológicas para resolver problemas de su entorno",
                "calification": str(row.iloc[30]),
            }
        ]

        return ciencia_califications


    def educacion_religiosa_calification(self, row: pd.Series):
        """Procesa las calificaciones de Educación Religiosa."""
        educacion_religiosa_califications = [
            {
                "criteria": "Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas",
                "calification": str(row.iloc[31]),
            },
            {
                "criteria": "Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida en coherencia con su creencia religiosa",
                "calification": str(row.iloc[32]),
            },
        ]

        return educacion_religiosa_califications


    def save_student_califications(self, academic_histori_id, course_id, bimester_id, califications_per_criteria: list[dict[str, str]]):
        """Guarda las calificaciones de un alumno en la base de datos."""
        for criteria_and_calification in califications_per_criteria:
            criteria = criteria_and_calification.get("criteria")
            achievement_level = criteria_and_calification.get("calification")

            criteria_obj = self.criteria_repo.get_or_create_evaluation_criteria(criteria, course_id)
            achievement_level_obj = self.achievement_repo.get_or_create_achievement_level(achievement_level)

            calification_params = {
                "history_id": academic_histori_id,
                "course_id": course_id,
                "bimester_id": bimester_id,
                "evaluation_criteria_id": criteria_obj.id,
                "criteria_value": "",
                "achievement_level_id": achievement_level_obj.id
            }

            self.calification_repo.create_calification(calification_params)



    def process_student_califications(self, csv_content: bytes):
        """Procesa las calificaciones de los estudiantes de Primaria."""
        csv_df = pd.ExcelFile(io.BytesIO(csv_content))

        # csv_df = self.load_excel(csv_content)
        generic_data = self.get_generic_data(csv_df)
        bimesters = ["PRIMER BIMESTRE", "SEGUNDO BIMESTRE", "TERCER BIMESTRE", "CUARTO BIMESTRE"]

        sheet_names = csv_df.sheet_names

        for sheet_name in sheet_names:
            current_sheet_df = csv_df.parse(sheet_name, header=None)
            students_grades = current_sheet_df.iloc[9:, 1:]
            students_grade_df = pd.DataFrame(students_grades)

            if students_grade_df.empty:
                continue

            for index, row in students_grade_df.iterrows():
                if index == 9 or index == 10:
                    print(f"Skipping header rows {index} in sheet {sheet_name}.")
                    continue

                # Student data
                student_code = str(row.iloc[0])
                student_name = str(row.iloc[1])
                student_gender = "MASCULINO" if row.iloc[2] == "H" else "FEMENINO"

                if not student_code:
                    print(f"Skipping row {index} due to missing student code. - {row.iloc[1]}")
                    continue

                student = self.student_repo.get_or_create_student(
                    student_code=student_code,
                    student_name=student_name,
                    student_gender=student_gender
                )

                academic_history = self.academic_repo.get_or_create_academic_history(
                    academic_year_id= generic_data.get("academic_year").id,
                    level_id=generic_data.get("level").id,
                    degree_id=generic_data.get("degree").id,
                    section_id=generic_data.get("section").id,
                    student_id=student.id
                )


                # """Al no tener bimestres en primaria, se replica las notas para todos los bimestres"""

                ## Curso PERSONAL SOCIAL
                course = self.course_repo.get_or_create_primary_course("PERSONAL SOCIAL")
                personal_social_califications_per_criteria = self.pesonal_social_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, personal_social_califications_per_criteria)


                ## Curso EDUCACIÓN FÍSICA
                course = self.course_repo.get_or_create_primary_course("EDUCACIÓN FÍSICA")
                fisica_califications_per_criteria = self.educacion_fisica_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, fisica_califications_per_criteria)

                ## Curso COMUNICACIÓN
                course = self.course_repo.get_or_create_primary_course("COMUNICACIÓN")
                comunicacion_califications_per_criteria = self.comunicacion_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, comunicacion_califications_per_criteria)

                ### ARTE Y CULTURA
                course = self.course_repo.get_or_create_primary_course("ARTE Y CULTURA")
                arte_y_cultura_califications_per_criteria = self.arte_y_cultura_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, arte_y_cultura_califications_per_criteria)

                ### MATEMÁTICA
                course = self.course_repo.get_or_create_primary_course("MATEMÁTICA")
                matematica_califications_per_criteria = self.matematica_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, matematica_califications_per_criteria)

                ### CIENCIA Y TECNOLOGÍA
                course = self.course_repo.get_or_create_primary_course("CIENCIA Y TECNOLOGÍA")
                ciencia_y_tecnologia_califications_per_criteria = self.ciencia_y_tecnologia_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, ciencia_y_tecnologia_califications_per_criteria)

                ### EDUCACIÓN RELIGIOSA
                course = self.course_repo.get_or_create_primary_course("EDUCACIÓN RELIGIOSA")
                educacion_religiosa_califications_per_criteria = self.educacion_religiosa_calification(row)

                for bimester in bimesters:
                    current_bimester_obj = self.bimester_repo.get_or_create_bimester(bimester)

                    self.save_student_califications(academic_history.id, course.id, current_bimester_obj.id, educacion_religiosa_califications_per_criteria)

                ### OTRAS COMPETENCIAS
                # TODO: Implement this section if needed





















