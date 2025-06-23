from ..repositories.student import StudentRepository
from sqlalchemy.orm import Session
from .base_grades_excel_processor import BaseExcelProcessor as BaseStudent
class Student(BaseStudent):
    def __init__(self, db: Session):
      super().__init__(db)


    def get_students(self, page: int, page_size: int):
        student_repo = StudentRepository(self.db)
        return student_repo.get_all_students_with_associated_data(page, page_size)

    def get_student_by_id(self, student_id: int):
        student_repo = StudentRepository(self.db)
        return student_repo.get_student_by_id(student_id)