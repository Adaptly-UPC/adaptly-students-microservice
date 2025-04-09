import io
import pandas as pd
import json
import os
import string
from typing import Dict, List
from sqlalchemy.orm import Session
from app.api.v1.students.repositories.student import StudentRepository
from app.api.v1.students.repositories.course import CourseRepository
from app.api.v1.students.repositories.academic_history import AcademicHistoryRepository
from app.api.v1.students.repositories.degree import DegreeRepository
from app.api.v1.students.repositories.evaluation_criteria import EvaluationCriteriaRepository
from app.api.v1.students.repositories.academic_level import AcademicLevelRepository
from app.api.v1.students.repositories.academic_year import AcademicYearRepository
from app.api.v1.students.repositories.section import SectionRepository
from app.api.v1.students.repositories.bimester import BimesterRepository
from app.api.v1.students.repositories.achievement_levels import AchievementLevelsRepository
from app.api.v1.students.repositories.calification import CalificationRepository
from dataclasses import dataclass

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

class ExcelProcessor:
    """Process the Excel file and save the data to the database."""
    def __init__(self, db: Session):
        self.db = db
        self.student_repo = StudentRepository(db)
        self.course_repo = CourseRepository(db)
        self.academic_repo = AcademicHistoryRepository(db)
        self.grade_repo = DegreeRepository(db)
        self.criteria_repo = EvaluationCriteriaRepository(db)
        self.level_repo = AcademicLevelRepository(db)
        self.year_repo = AcademicYearRepository(db)
        self.section_repo = SectionRepository(db)
        self.bimester_repo = BimesterRepository(db)
        self.achievement_repo = AchievementLevelsRepository(db)
        self.calification_repo = CalificationRepository(db)


    def get_column_letter(self, col_idx):
        """Convierte índice de columna (0=A, 1=B, 2=C, ...) en formato de Excel"""
        result = ""
        while col_idx >= 0:
            result = string.ascii_uppercase[col_idx % 26] + result
            col_idx = col_idx // 26 - 1
        return result

    def organize_data(self, excel_data) -> Dict:
        """Organiza los datos en una estructura para obtener datos generales"""
        structured_data = {}

        for sheet_name in excel_data.sheet_names:
            df = excel_data.parse(sheet_name, header=None)
            df.fillna(value="No Definido", inplace=True)

            formatted_data = []
            for row_idx, row in df.iterrows():
                formatted_row = {}
                for col_idx, value in enumerate(row):
                    cell_ref = f"{self.get_column_letter(col_idx)}{row_idx + 1}"
                    formatted_row[cell_ref] = value
                formatted_data.append(formatted_row)

            structured_data[sheet_name] = {
                "sample_data": formatted_data
            }

        return {"structure": structured_data}

    def get_course_name(self, course_code):
        json_route = os.path.join(os.path.dirname(__file__), '.',  'courses.json')
        with open(json_route, 'r', encoding='utf-8') as file:
            courses_dic = json.load(file)
            course_name = courses_dic.get(course_code)
            return course_name

    def extract_generic_data(self, excel_data) -> GenericData:
        """Extrae datos generales del Excel (grado, sección, año académico)"""
        data_structured = self.organize_data(excel_data)["structure"]

        level_obj = self.level_repo.get_or_create_academic_level(data_structured["Generalidades"]["sample_data"][4]["H5"])
        bimester_obj = self.bimester_repo.get_or_create_bimester(data_structured["Generalidades"]["sample_data"][9]["D10"])
        degree_obj = self.grade_repo.get_or_create_degree(data_structured["Generalidades"]["sample_data"][9]["H10"], level_obj.id)
        section_obj = self.section_repo.get_or_create_section(data_structured["Generalidades"]["sample_data"][9]["J10"])
        # TODO: add for colegio
        academic_year_obj = self.year_repo.get_or_create_academic_year(int(data_structured["Parametros"]["sample_data"][3]["B4"]))
        # TODO: add for modular code

        return {
            "level": level_obj,
            "bimester": bimester_obj,
            "degree": degree_obj,
            "section": section_obj,
            "school": data_structured["Parametros"]["sample_data"][0]["C1"],
            "academic_year": academic_year_obj,
            "modular_code": data_structured["Parametros"]["sample_data"][0]["B1"]
        }

    def sheet_validator(self, sheet_data: pd.DataFrame) -> bool:
        """Valida la hoja de excel"""
        if sheet_data.shape[0] < 3:
            print("La hoja tiene menos de 3 filas, no se puede procesar.")
            return False
        sheet_data.fillna("No Definido", inplace=True)
        try:
            column_names = sheet_data.iloc[1, 1:].astype(str).tolist()
            df = sheet_data.iloc[2:]
            df.columns = ["indice"] + column_names
        except Exception as e:
            print(f"Error en hoja: {str(e)}")
            return False

        return True


    def should_skip_row(self, row_data: pd.Series) -> bool:
        return row_data.iloc[1] == "LEYENDA" or str(row_data.iloc[1]).startswith(("01 =", "02 =", "03 =", "04 ="))

    def process_student_califications(self, row_data, generic_data: GenericData, critera_list: List[int], course_id: int) -> int:
        """Procesa el archivo completo de excel y lo guarda en la base de datos de forma organizada"""
        student = self.student_repo.get_or_create_student(str(row_data.iloc[2]), str(row_data.iloc[1]))

        academic_year_id = generic_data.get("academic_year").id
        level_id = generic_data.get("level").id
        degree_id = generic_data.get("degree").id
        section_id = generic_data.get("section").id

        academic_historic = self.academic_repo.get_or_create_academic_history(
            student.id, academic_year_id, level_id, degree_id, section_id)

        index_criteria = 4
        index_calification = 3

        for i in critera_list:
            try:
                criteria_value = str(row_data.iloc[index_criteria])
                if(criteria_value == "No Definido"):
                    criteria_value = None
                calification_value = str(row_data.iloc[index_calification])
                if(calification_value == "No Definido" or calification_value == "EXO"):
                    calification_value = "No calificado"
                achievement_level_id = self.achievement_repo.get_or_create_achievement_level(calification_value).id
                calification_list = []

                calification_params = {
                    "history_id": academic_historic.id,
                    "course_id": course_id,
                    "bimester_id": generic_data.get('bimester').id,
                    "evaluation_criteria_id": i,
                    "criteria_value": criteria_value,
                    "achievement_level_id": achievement_level_id
                }

                print(f"LLEGA: {calification_params}")

                calification = self.calification_repo.create_calification(calification_params)
                print(f"CALIFICATION CREADA: {calification}")
                calification_list.append(calification)

                index_criteria += 2
                index_calification += 2
            except Exception as e:
                return {"error": f"Error al procesar fila {row_data}: {str(e)}"}

        return len(calification_list)

    def process_excel(self, file_content: bytes):
        """Procesa el archivo completo de excel y lo guarda en la base de datos de forma organizada"""
        excel_data = pd.ExcelFile(io.BytesIO(file_content))
        base_data = self.extract_generic_data(excel_data)
        sheet_names = excel_data.sheet_names[1:]
        total_alumnos = 0

        for sheet_name in sheet_names:
            df = excel_data.parse(sheet_name, header=None)

            if df.shape[0] < 3:
                return {"error": f"La hoja '{sheet_name}' tiene menos de 3 filas, no se puede procesar."}

            df.fillna("No Definido", inplace=True)

            try:
                column_names = df.iloc[1, 1:].astype(str).tolist()
                df = df.iloc[2:]
                df.columns = ["indice"] + column_names
            except Exception as e:
                print(f"Error en hoja {sheet_name}, fila {row.name}: {str(e)}")
                continue

            course = self.course_repo.get_course_by_code(sheet_name)

            if sheet_name == "Parametros" or sheet_name == "Generalidades":
                continue

            if not course:
                course_name = self.get_course_name(sheet_name)
                course = self.course_repo.create_course(sheet_name, course_name)

            evaluation_criteria_list = self.criteria_repo.get_evaluation_criteria_list(df, course.id)

            for _, row in df.iterrows():
                try:
                    if self.should_skip_row(row) or row[1] == "Cód. Estudiante":
                        continue

                    if row.iloc[1] == "LEYENDA":
                        continue

                    if (row.iloc[1].startswith("01 =") or
                        row.iloc[1].startswith("02 =") or
                        row.iloc[1].startswith("04 =") or
                            row.iloc[1].startswith("03 =")):
                        continue

                    self.process_student_califications(row, base_data, evaluation_criteria_list, course.id)

                except Exception as e:
                    return {"error": f"Error al procesar fila {row[1]}: {str(e)}"}

        return {"total_alumnos": total_alumnos}
