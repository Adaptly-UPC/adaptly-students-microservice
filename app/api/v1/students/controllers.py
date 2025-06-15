from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.v1.students.services.excel_inspect import inspect_excel
from sqlalchemy import func, and_, exists
from typing import List, Optional

from app.api.v1.students.services.excel_proccessor_high_level import ExcelProcessor as ExcelProcessorHighSchool
from app.api.v1.students.services.excel_processor_primary_level import ExcelProcessor as ExcelProcessorPrimary

from app.api.v1.students.models import (
    Alumno, HistorialAcademico, Nota, Encuesta,
    RespuestaEncuesta, AnioAcademico, RecommendationResult
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    responses={404: {"description": "Not found"}}
)

def get_student_data_status(student_id: int, db: Session):
    """Obtiene información sobre qué datos tiene un estudiante"""

    # Verificar si tiene notas
    has_grades = db.query(
        exists().where(
            and_(
                HistorialAcademico.alumno_id == student_id,
                Nota.historial_id == HistorialAcademico.id
            )
        )
    ).scalar()

    # Contar total de notas si las tiene
    grades_count = 0
    if has_grades:
        grades_count = (
            db.query(Nota)
            .join(HistorialAcademico)
            .filter(HistorialAcademico.alumno_id == student_id)
            .count()
        )

    # Verificar si tiene encuestas
    has_surveys = db.query(
        exists().where(Encuesta.alumno_id == student_id)
    ).scalar()

    # Contar encuestas si las tiene
    surveys_count = 0
    last_survey_date = None
    if has_surveys:
        surveys_count = db.query(Encuesta).filter(Encuesta.alumno_id == student_id).count()
        last_survey = (
            db.query(Encuesta)
            .filter(Encuesta.alumno_id == student_id)
            .order_by(Encuesta.fecha.desc())
            .first()
        )
        if last_survey and last_survey.fecha:
            last_survey_date = last_survey.fecha.isoformat()

    # Verificar si tiene recomendaciones
    has_recommendations = db.query(
        exists().where(RecommendationResult.alumno_id == student_id)
    ).scalar()

    # Obtener última recomendación si existe
    last_recommendation = None
    if has_recommendations:
        rec = (
            db.query(RecommendationResult)
            .filter(RecommendationResult.alumno_id == student_id)
            .order_by(RecommendationResult.id.desc())
            .first()
        )
        if rec:
            last_recommendation = {
                "risk_level": rec.riesgo_predicho,
                "generated_at": rec.id  # Usando ID como proxy de timestamp
            }

    return {
        "has_grades": has_grades,
        "grades_count": grades_count,
        "has_surveys": has_surveys,
        "surveys_count": surveys_count,
        "last_survey_date": last_survey_date,
        "has_recommendations": has_recommendations,
        "last_recommendation": last_recommendation,
        "data_completeness": "complete" if has_grades and has_surveys else
                           ("partial" if has_grades or has_surveys else "empty")
    }



@router.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    rows_inserted = inspect_excel(content)
    return {"message": "Datos insertados correctamente", "rows_inserted": rows_inserted}


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


@router.get("/with-both-data")
async def get_students_with_grades_and_surveys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Obtiene estudiantes que tienen TANTO notas COMO encuestas.

    - **skip**: Número de registros a saltar (paginación)
    - **limit**: Número máximo de registros a devolver
    """
    try:
        # Subquery para estudiantes con notas
        has_grades_subquery = (
            db.query(Alumno.id)
            .join(HistorialAcademico)
            .join(Nota)
            .group_by(Alumno.id)
            .subquery()
        )

        # Subquery para estudiantes con encuestas
        has_survey_subquery = (
            db.query(Alumno.id)
            .join(Encuesta)
            .group_by(Alumno.id)
            .subquery()
        )

        # Query principal: estudiantes que aparecen en ambas subqueries
        students = (
            db.query(Alumno)
            .filter(
                and_(
                    Alumno.id.in_(has_grades_subquery),
                    Alumno.id.in_(has_survey_subquery)
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Contar total para paginación
        total = (
            db.query(Alumno)
            .filter(
                and_(
                    Alumno.id.in_(has_grades_subquery),
                    Alumno.id.in_(has_survey_subquery)
                )
            )
            .count()
        )

        # Obtener estadísticas adicionales para cada estudiante
        result = []
        for student in students:
            # Contar notas
            grades_count = (
                db.query(Nota)
                .join(HistorialAcademico)
                .filter(HistorialAcademico.alumno_id == student.id)
                .count()
            )

            # Contar encuestas
            surveys_count = (
                db.query(Encuesta)
                .filter(Encuesta.alumno_id == student.id)
                .count()
            )

            result.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "total_notas": grades_count,
                "total_encuestas": surveys_count
            })

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error getting students with both data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/only-surveys")
async def get_students_only_surveys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Obtiene estudiantes que SOLO tienen encuestas (NO tienen notas).

    - **skip**: Número de registros a saltar (paginación)
    - **limit**: Número máximo de registros a devolver
    """
    try:
        # Subquery para estudiantes con notas
        has_grades_subquery = (
            db.query(HistorialAcademico.alumno_id)
            .join(Nota)
            .distinct()
            .subquery()
        )

        # Query principal: estudiantes con encuestas pero NO en la subquery de notas
        students = (
            db.query(Alumno)
            .join(Encuesta)
            .filter(~Alumno.id.in_(has_grades_subquery))
            .distinct()
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Contar total
        total = (
            db.query(Alumno)
            .join(Encuesta)
            .filter(~Alumno.id.in_(has_grades_subquery))
            .distinct()
            .count()
        )

        # Preparar resultado con información adicional
        result = []
        for student in students:
            # Obtener última encuesta
            last_survey = (
                db.query(Encuesta)
                .filter(Encuesta.alumno_id == student.id)
                .order_by(Encuesta.fecha.desc())
                .first()
            )

            # Contar total de respuestas en encuestas
            total_responses = (
                db.query(RespuestaEncuesta)
                .join(Encuesta)
                .filter(Encuesta.alumno_id == student.id)
                .count()
            )

            result.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "total_encuestas": db.query(Encuesta).filter(Encuesta.alumno_id == student.id).count(),
                "ultima_encuesta": last_survey.fecha.isoformat() if last_survey and last_survey.fecha else None,
                "total_respuestas": total_responses
            })

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error getting students with only surveys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/only-grades")
async def get_students_only_grades(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    min_grades: Optional[int] = Query(None, ge=1, description="Mínimo número de notas"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estudiantes que SOLO tienen notas (NO tienen encuestas).

    - **skip**: Número de registros a saltar (paginación)
    - **limit**: Número máximo de registros a devolver
    - **min_grades**: Filtrar estudiantes con al menos esta cantidad de notas
    """
    try:
        # Subquery para estudiantes con encuestas
        has_survey_subquery = (
            db.query(Encuesta.alumno_id)
            .distinct()
            .subquery()
        )

        # Query principal: estudiantes con notas pero NO en la subquery de encuestas
        query = (
            db.query(Alumno)
            .join(HistorialAcademico)
            .join(Nota)
            .filter(~Alumno.id.in_(has_survey_subquery))
            .group_by(Alumno.id)
        )

        # Aplicar filtro de mínimo de notas si se especifica
        if min_grades:
            query = query.having(func.count(Nota.id) >= min_grades)

        students = query.offset(skip).limit(limit).all()
        total = query.count()

        # Preparar resultado con estadísticas
        result = []
        for student in students:
            # Obtener todas las notas del estudiante
            student_grades = (
                db.query(Nota)
                .join(HistorialAcademico)
                .filter(HistorialAcademico.alumno_id == student.id)
                .all()
            )

            # Calcular distribución de notas
            grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "No calificado": 0}
            subjects = set()

            for grade in student_grades:
                if grade.nivel_logro and grade.nivel_logro.valor:
                    grade_distribution[grade.nivel_logro.valor] += 1
                subjects.add(grade.materia.nombre)

            # Obtener año académico más reciente
            latest_year = (
                db.query(AnioAcademico.anio)
                .join(HistorialAcademico)
                .filter(HistorialAcademico.alumno_id == student.id)
                .order_by(AnioAcademico.anio.desc())
                .first()
            )

            result.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "total_notas": len(student_grades),
                "materias_evaluadas": len(subjects),
                "distribucion_notas": grade_distribution,
                "ultimo_año_academico": latest_year[0] if latest_year else None
            })

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error getting students with only grades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# BONUS: API de resumen general
@router.get("/data-summary")
async def get_students_data_summary(db: Session = Depends(get_db)):
    """
    Obtiene un resumen de la distribución de datos de los estudiantes.
    """
    try:
        # Total de estudiantes
        total_students = db.query(Alumno).count()

        # Estudiantes con notas
        students_with_grades = (
            db.query(Alumno.id)
            .join(HistorialAcademico)
            .join(Nota)
            .distinct()
            .count()
        )

        # Estudiantes con encuestas
        students_with_surveys = (
            db.query(Alumno.id)
            .join(Encuesta)
            .distinct()
            .count()
        )

        # Calcular intersecciones
        has_grades_subquery = (
            db.query(Alumno.id)
            .join(HistorialAcademico)
            .join(Nota)
            .distinct()
            .subquery()
        )

        has_survey_subquery = (
            db.query(Alumno.id)
            .join(Encuesta)
            .distinct()
            .subquery()
        )

        # Estudiantes con ambos
        students_with_both = (
            db.query(Alumno)
            .filter(
                and_(
                    Alumno.id.in_(has_grades_subquery),
                    Alumno.id.in_(has_survey_subquery)
                )
            )
            .count()
        )

        # Calcular los que solo tienen uno u otro
        only_grades = students_with_grades - students_with_both
        only_surveys = students_with_surveys - students_with_both
        no_data = total_students - students_with_grades - students_with_surveys + students_with_both

        return {
            "total_students": total_students,
            "with_both_data": students_with_both,
            "only_grades": only_grades,
            "only_surveys": only_surveys,
            "no_data": no_data,
            "percentages": {
                "with_both": round((students_with_both / total_students * 100), 2) if total_students > 0 else 0,
                "only_grades": round((only_grades / total_students * 100), 2) if total_students > 0 else 0,
                "only_surveys": round((only_surveys / total_students * 100), 2) if total_students > 0 else 0,
                "no_data": round((no_data / total_students * 100), 2) if total_students > 0 else 0
            }
        }

    except Exception as e:
        logger.error(f"Error getting data summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-id/{student_id}")
async def get_student_by_id(
    student_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtiene un estudiante por su ID con información sobre sus datos.

    - **student_id**: ID único del estudiante
    """
    try:
        # Buscar estudiante
        student = db.query(Alumno).filter(Alumno.id == student_id).first()

        if not student:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        # Obtener estado de datos
        data_status = get_student_data_status(student.id, db)

        # Obtener información académica adicional si tiene notas
        academic_info = None
        if data_status["has_grades"]:
            # Obtener última información académica
            latest_academic = (
                db.query(HistorialAcademico)
                .filter(HistorialAcademico.alumno_id == student.id)
                .order_by(HistorialAcademico.id.desc())
                .first()
            )
            if latest_academic:
                academic_info = {
                    "nivel": latest_academic.nivel.nombre if latest_academic.nivel else None,
                    "grado": latest_academic.grado.nombre if latest_academic.grado else None,
                    "seccion": latest_academic.seccion.nombre if latest_academic.seccion else None,
                    "año": latest_academic.anio_academico.anio if latest_academic.anio_academico else None
                }

        return {
            "id": student.id,
            "codigo_alumno": student.codigo_alumno,
            "nombre_completo": student.nombre_completo,
            "edad": student.edad,
            "genero": student.genero,
            "data_status": data_status,
            "academic_info": academic_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student by ID: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/student/by-code/{codigo_alumno}")
async def get_student_by_code(
    codigo_alumno: str = Path(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    Obtiene un estudiante por su código único con información sobre sus datos.

    - **codigo_alumno**: Código único del estudiante
    """
    try:
        # Buscar estudiante
        student = db.query(Alumno).filter(Alumno.codigo_alumno == codigo_alumno).first()

        if not student:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        # Obtener estado de datos
        data_status = get_student_data_status(student.id, db)

        return {
            "id": student.id,
            "codigo_alumno": student.codigo_alumno,
            "nombre_completo": student.nombre_completo,
            "edad": student.edad,
            "genero": student.genero,
            "data_status": data_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student by code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/search")
async def search_students_by_name(
    search_term: str = Query(..., min_length=2, description="Nombre completo o parcial"),
    exact_match: bool = Query(False, description="Buscar coincidencia exacta"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Busca estudiantes por nombre completo o parcial.

    - **search_term**: Término de búsqueda (mínimo 2 caracteres)
    - **exact_match**: Si es True, busca coincidencia exacta. Si es False, busca coincidencias parciales
    - **skip**: Número de registros a saltar
    - **limit**: Número máximo de resultados

    Ejemplos:
    - "PEREZ GARCIA, JUAN" → Coincidencia exacta si exact_match=True
    - "PEREZ" → Todos los estudiantes con apellido PEREZ
    - "JUAN" → Todos los estudiantes con nombre JUAN
    - "PER GAR" → Coincidencias flexibles
    """
    try:
        # Normalizar término de búsqueda
        search_normalized = search_term.strip().upper()

        if exact_match:
            # Búsqueda exacta
            query = db.query(Alumno).filter(
                func.upper(Alumno.nombre_completo) == search_normalized
            )
        else:
            # Búsqueda flexible
            # Dividir el término en palabras
            search_words = search_normalized.split()

            if len(search_words) == 1:
                # Una sola palabra: buscar en cualquier parte del nombre
                query = db.query(Alumno).filter(
                    func.upper(Alumno.nombre_completo).contains(search_normalized)
                )
            else:
                # Múltiples palabras: todas deben estar presentes
                conditions = []
                for word in search_words:
                    conditions.append(func.upper(Alumno.nombre_completo).contains(word))

                query = db.query(Alumno).filter(and_(*conditions))

        # Aplicar paginación
        total = query.count()
        students = query.offset(skip).limit(limit).all()

        # Preparar resultados con estado de datos
        results = []
        for student in students:
            data_status = get_student_data_status(student.id, db)

            # Calcular score de relevancia para ordenar mejor los resultados
            relevance_score = 0
            student_name_upper = student.nombre_completo.upper()

            if exact_match:
                relevance_score = 100 if student_name_upper == search_normalized else 0
            else:
                # Dar mayor score a coincidencias más exactas
                if search_normalized in student_name_upper:
                    relevance_score = 90
                else:
                    # Contar cuántas palabras coinciden
                    for word in search_words:
                        if word in student_name_upper:
                            relevance_score += 10

                # Bonus si el término aparece al inicio
                if student_name_upper.startswith(search_normalized):
                    relevance_score += 20

            results.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "data_status": data_status,
                "relevance_score": relevance_score
            })

        # Ordenar por relevancia (mayor a menor)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Remover el score de relevancia del resultado final
        for result in results:
            result.pop("relevance_score", None)

        return {
            "search_term": search_term,
            "exact_match": exact_match,
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error searching students: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/advanced-search")
async def advanced_search_students(
    nombre: Optional[str] = Query(None, min_length=2),
    codigo: Optional[str] = Query(None, min_length=1),
    edad_min: Optional[int] = Query(None, ge=1),
    edad_max: Optional[int] = Query(None, le=100),
    genero: Optional[str] = Query(None, regex="^(MASCULINO|FEMENINO|OTRO|NO_ESPECIFICADO)$"),
    has_grades: Optional[bool] = Query(None),
    has_surveys: Optional[bool] = Query(None),
    risk_level: Optional[str] = Query(None, regex="^(Alto|Medio|Bajo|Desconocido)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada de estudiantes con múltiples filtros.

    Todos los parámetros son opcionales y se pueden combinar:
    - **nombre**: Búsqueda parcial en nombre
    - **codigo**: Código del alumno
    - **edad_min/edad_max**: Rango de edad
    - **genero**: MASCULINO, FEMENINO, OTRO, NO_ESPECIFICADO
    - **has_grades**: True = con notas, False = sin notas
    - **has_surveys**: True = con encuestas, False = sin encuestas
    - **risk_level**: Alto, Medio, Bajo, Desconocido
    """
    print(f"NOMBRE:, {nombre}")
    try:
        # Query base
        query = db.query(Alumno)

        # Aplicar filtros básicos
        if nombre:
            query = query.filter(func.upper(Alumno.nombre_completo).contains(nombre.upper()))

        if codigo:
            query = query.filter(Alumno.codigo_alumno == codigo)

        if edad_min is not None:
            query = query.filter(Alumno.edad >= edad_min)

        if edad_max is not None:
            query = query.filter(Alumno.edad <= edad_max)

        if genero:
            query = query.filter(Alumno.genero == genero)

        # Filtros de datos académicos
        if has_grades is not None:
            grades_subquery = (
                db.query(HistorialAcademico.alumno_id)
                .join(Nota)
                .distinct()
                .subquery()
            )
            if has_grades:
                query = query.filter(Alumno.id.in_(grades_subquery))
            else:
                query = query.filter(~Alumno.id.in_(grades_subquery))

        # Filtros de encuestas
        if has_surveys is not None:
            surveys_subquery = (
                db.query(Encuesta.alumno_id)
                .distinct()
                .subquery()
            )
            if has_surveys:
                query = query.filter(Alumno.id.in_(surveys_subquery))
            else:
                query = query.filter(~Alumno.id.in_(surveys_subquery))

        # Filtro de nivel de riesgo
        if risk_level:
            risk_subquery = (
                db.query(RecommendationResult.alumno_id)
                .filter(RecommendationResult.riesgo_predicho == risk_level)
                .distinct()
                .subquery()
            )
            query = query.filter(Alumno.id.in_(risk_subquery))

        # Contar total antes de paginar
        total = query.count()

        # Aplicar paginación
        students = query.offset(skip).limit(limit).all()

        # Preparar resultados
        results = []
        for student in students:
            data_status = get_student_data_status(student.id, db)

            results.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "data_status": data_status
            })

        return {
            "filters_applied": {
                "nombre": nombre,
                "codigo": codigo,
                "edad_range": f"{edad_min or 'any'}-{edad_max or 'any'}",
                "genero": genero,
                "has_grades": has_grades,
                "has_surveys": has_surveys,
                "risk_level": risk_level
            },
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))