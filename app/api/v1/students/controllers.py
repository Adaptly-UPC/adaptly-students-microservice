from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.v1.students.services.excel_inspect import inspect_excel
from .services.students import Student

from app.api.v1.students.services.excel_proccessor_high_level import ExcelProcessor as ExcelProcessorHighSchool
from app.api.v1.students.services.excel_processor_primary_level import ExcelProcessor as ExcelProcessorPrimary

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    responses={404: {"description": "Not found"}}
)


# @router.post("/upload-excel/")
# async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     content = await file.read()
#     rows_inserted = inspect_excel(content)
#     return {"message": "Datos insertados correctamente", "rows_inserted": rows_inserted}



@router.get("/")
async def get_students(page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    students_service = Student(db)
    print(f"page: {page}, page_size: {page_size}")
    return students_service.get_students(page, page_size)

@router.get("/filters")
def get_available_filters(db: Session = Depends(get_db)):
    """
    Endpoint para obtener todos los filtros disponibles con ID y nombre.
    """
    students_service = Student(db)
    return students_service.get_available_filters()

@router.get("/by-filters/")
async def get_students_by_filters(
    anio_academico_id: int = None,
    seccion_id: int = None,
    nivel_id: int = None,
    grado_id: int = None,
    bimestre_id: int = None,
    materia_id: int = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener alumnos filtrados por los parámetros proporcionados utilizando IDs.
    """
    students_service = Student(db)
    return students_service.get_students_with_filters(
        anio_academico_id=anio_academico_id,
        seccion_id=seccion_id,
        nivel_id=nivel_id,
        grado_id=grado_id,
        bimestre_id=bimestre_id,
        materia_id=materia_id,
        page=page,
        page_size=page_size
    )

@router.post("/save-high-school-grades/")
async def parse_save_data(file: UploadFile = File(...), db: Session = Depends
(get_db)):
    processor = ExcelProcessorHighSchool(db)
    excel_content = await file.read()
    return processor.process_excel(excel_content)


@router.post("/save-primary-grades/")
async def parse_save_primary_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    processor = ExcelProcessorPrimary(db)
    excel_content = await file.read()
    return processor.process_student_califications(excel_content)

@router.get("/{student_id}")
async def get_student_by_id(student_id: int, db: Session = Depends(get_db)):
    student_repo = Student(db)
    return student_repo.get_student_by_id(student_id)

@router.get("/only-notes")
def get_students_with_only_notes(db: Session = Depends(get_db)):
    student_service = Student(db)
    return student_service.get_students_with_only_notes()

@router.get("/only-surveys")
def get_students_with_only_surveys(db: Session = Depends(get_db)):
    student_service = Student(db)
    return student_service.get_students_with_only_surveys()

@router.get("/notes-and-surveys")
def get_students_with_notes_and_surveys(db: Session = Depends(get_db)):
    student_service = Student(db)
    return student_service.get_students_with_notes_and_surveys()

@router.get("/summary/all")
def get_students_summary(db: Session = Depends(get_db)):
    student_service = Student(db)
    return student_service.get_students_summary()

@router.get("/grades-and-sections/")
def get_grades_and_sections(
    nivel_id: int = None,
    anio_academico_id: int = None,
    grado_id: int = None,
    seccion_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener grados y secciones asociadas, con filtros opcionales.
    """
    student_service = Student(db)
    return student_service.get_grades_and_sections(nivel_id, anio_academico_id, grado_id, seccion_id)



@router.get("/notes/get-all")
async def get_student_notes(
    alumno_id: int = None,
    materia_id: int = None,
    grado_id: int = None,
    anio_academico_id: int = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener todas las notas de los alumnos con filtros opcionales.

    - **alumno_id**: ID del alumno (opcional)
    - **materia_id**: ID de la materia/curso (opcional)
    - **grado_id**: ID del grado (opcional)
    - **anio_academico_id**: ID del año académico (opcional)
    - **page**: Número de página (default: 1)
    - **page_size**: Tamaño de página (default: 10)
    """
    student_service = Student(db)
    return student_service.get_student_notes(
        alumno_id=alumno_id,
        materia_id=materia_id,
        grado_id=grado_id,
        anio_academico_id=anio_academico_id,
        page=page,
        page_size=page_size
    )



# RUTAS PARA ANALISIS -----------------------

@router.get("/analytics/student-performance/")
async def get_student_performance_data(
    include_surveys: bool = False,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos estructurados para análisis de rendimiento académico.
    Optimizado para Random Forest (predicción de riesgo académico).

    - include_surveys: Si es True, solo incluye estudiantes que tienen tanto notas como encuestas
    """
    student_service = Student(db)

    return student_service.get_student_performance_data(include_surveys)

@router.get("/analytics/behavior-patterns/")
async def get_student_behavior_patterns(
    min_survey_responses: int = 1,
    min_academic_periods: int = 1,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos estructurados para análisis de patrones de comportamiento.
    Optimizado para algoritmo Apriori.

    - min_survey_responses: Número mínimo de encuestas respondidas
    - min_academic_periods: Número mínimo de períodos académicos con notas
    """
    student_service = Student(db)
    return student_service.get_student_behavior_patterns(
        min_survey_responses,
        min_academic_periods
    )

@router.get("/analytics/complete-student-profile/")
async def get_complete_student_profile(
    analysis_type: str = "all",
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener el perfil completo de estudiantes con diferentes niveles de detalle.

    - analysis_type:
        - "all": Todos los estudiantes con datos disponibles
        - "complete": Solo estudiantes con notas y encuestas
        - "academic": Solo estudiantes con notas
        - "behavioral": Solo estudiantes con encuestas
    """
    student_service = Student(db)
    return student_service.get_complete_student_profile(analysis_type)
