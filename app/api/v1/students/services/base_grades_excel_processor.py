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

class BaseExcelProcessor:
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
