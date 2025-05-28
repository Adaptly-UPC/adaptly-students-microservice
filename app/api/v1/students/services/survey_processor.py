from app.api.v1.students.services.base_grades_excel_processor import BaseProcessor

class SurveyProcessor(BaseProcessor):
    def __init__(self, db):
        self.db = db

    def process_survey(self, file_content: bytes):



