from sqlalchemy.orm import Session
from app.api.v1.students.repositories.course import CourseRepository
from app.api.v1.students.repositories.degree import DegreeRepository
from app.api.v1.students.repositories.academic_year import AcademicYearRepository
from app.api.v1.students.repositories.section import SectionRepository
from app.api.v1.students.repositories.bimester import BimesterRepository
from app.api.v1.students.repositories.achievement_levels import AchievementLevelsRepository
from app.api.v1.students.repositories.academic_level import AcademicLevelRepository

class InsertBaseData:
    """Clase para insertar datos generales en la base de datos"""
    def __init__(self, db: Session):
        self.db = db
        self.bimester_repo = BimesterRepository(db)
        self.year_repo = AcademicYearRepository(db)
        self.academic_level_repo = AcademicLevelRepository(db)
        self.degree_repo = DegreeRepository(db)
        self.course_repo = CourseRepository(db)
        self.section_repo = SectionRepository(db)
        self.achievement_repo = AchievementLevelsRepository(db)

    def insert_base_data(self):
        """Inserta datos generales en la base de datos"""
        self.insert_bimesters()
        self.insert_years()
        self.insert_academic_levels()
        self.insert_degrees()
        self.insert_courses()
        self.insert_sections()
        self.insert_achievement_levels()

    def insert_bimesters(self):
        """Inserta bimestres en la base de datos"""
        bimesters_to_insert = [
            'PRIMER BIMESTRE',
            'SEGUNDO BIMESTRE',
            'TERCER BIMESTRE',
            'CUARTO BIMESTRE'
        ]

        for bimester in bimesters_to_insert:
            self.bimester_repo.get_or_create_bimester(bimester)

    def insert_years(self):
        """Inserta years en la base de datos"""
        years_to_insert = [
            2021,
            2022,
            2023,
            2024,
            2025
        ]

        for year in years_to_insert:
            self.year_repo.get_or_create_academic_year(year)

    def insert_academic_levels(self):
        """Inserta academic levels en la base de datos"""
        academic_levels_to_insert = [
            'PRIMARIA',
            'SECUNDARIA'
        ]

        for academic_level in academic_levels_to_insert:
            self.academic_level_repo.get_or_create_academic_level(academic_level)

    def insert_degrees(self):
        """Inserta degrees en la base de datos"""
        degrees_to_insert = [
            'PRIMERO',
            'SEGUNDO',
            'TERCERO',
            'CUARTO',
            'QUINTO'
        ]

        secundary_id = self.academic_level_repo.get_or_create_academic_level('SECUNDARIA').id

        primary_id = self.academic_level_repo.get_or_create_academic_level('PRIMARIA').id

        for degree in degrees_to_insert:
            self.degree_repo.get_or_create_degree(degree, secundary_id)

        for degree in degrees_to_insert:
            self.degree_repo.get_or_create_degree(degree, primary_id)

        self.degree_repo.get_or_create_degree('SEXTO', primary_id)

    def insert_courses(self):
        """Inserta cursos en la base de datos"""
        courses_to_insert = [
            {"code":'0001-ART Y CULT', "name":'ARTE Y CULTURA'},
            {"code":'0002-CAST SEGNL', "name":'CASTELLANO COMO SEGUNDA LENGUA'},
            {"code":'0004-CIENC TEC', "name":'CIENCIA Y TECNOLOGÍA'},
            {"code":'0010-DESARR PCC', "name":'DESARROLLO PERSONAL, CIUDADANÍA Y CÍVICA'},
            {"code":'014-CCSS', "name":'CIENCIAS SOCIALES'},
            {"code":'017-COMU', "name":'COMUNICACIÓN'},
            {"code":'031-EFIS', "name":'EDUCACIÓN FÍSICA'},
            {"code":'032-ETRA', "name":'EDUCACIÓN PARA EL TRABAJO'},
            {"code":'035-EREL', "name":'EDUCACIÓN RELIGIOSA'},
            {"code":'057-INGL', "name":'INGLÉS'},
            {"code":'063-MATE', "name":'MATEMÁTICA'},
            {"code":'0006-DESEN TIC', "name":'SE DESENVUELVE EN ENTORNOS VIRTUALES GENERADOS POR LAS TIC'},
            {"code":'0007-GEST AUTO', "name":'GESTIONA SU APRENDIZAJE DE MANERA AUTÓNOMA'}
        ]

        for course in courses_to_insert:
            self.course_repo.get_or_create_course(course['name'], course['code'])


    def insert_sections(self):
        """Inserta secciones en la base de datos"""
        sections_to_insert = [
            'A',
            'B',
            'C',
            'D',
            'E',
            'F'
        ]

        for section in sections_to_insert:
            self.section_repo.get_or_create_section(section)

    def insert_achievement_levels(self):
        """Inserta niveles de logros en la base de datos"""
        achievement_levels_to_insert = [
            'A',
            'B',
            'C',
            'D',
            'No calificado'
        ]

        for achievement_level in achievement_levels_to_insert:
            self.achievement_repo.get_or_create_achievement_level(achievement_level)


