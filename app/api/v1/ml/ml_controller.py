from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging
from sqlalchemy.sql import func


from app.db.database import get_db
from app.api.v1.ml.services.recommendation_service import RecommendationService
from app.api.v1.ml.services.ai_prompt_service import AIPromptService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"],
    responses={404: {"description": "Not found"}}
)

@router.post("/generate-recommendations")
async def generate_all_recommendations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Genera recomendaciones para todos los estudiantes"""
    try:
        # Ejecutar en background para no bloquear
        background_tasks.add_task(
            process_recommendations_background,
            db
        )

        return {
            "status": "processing",
            "message": "Generación de recomendaciones iniciada en segundo plano"
        }

    except Exception as e:
        logger.error(f"Error iniciando generación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/{student_id}")
async def get_student_recommendation(
    student_id: int,
    regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """Obtiene o regenera la recomendación para un estudiante específico"""
    try:
        from app.api.v1.students.models import RecommendationResult, Alumno

        # Verificar que el estudiante existe
        student = db.query(Alumno).filter(Alumno.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")

        # Buscar recomendación existente
        if not regenerate:
            existing = db.query(RecommendationResult).filter(
                RecommendationResult.alumno_id == student_id
            ).order_by(RecommendationResult.id.desc()).first()

            if existing:
                return {
                    "student_id": student_id,
                    "student_name": student.nombre_completo,
                    "risk_level": existing.riesgo_predicho,
                    "recommendations": existing.recomendaciones,
                    "generated_at": existing.id  # Usar ID como timestamp proxy
                }

        # Generar nueva recomendación
        service = RecommendationService(db)
        result = service._generate_student_recommendation(student, None)

        return {
            "student_id": student_id,
            "student_name": student.nombre_completo,
            "risk_level": result["risk_level"],
            "recommendations": result["recommendations"],
            "generated_at": "now"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo recomendación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-ai-recommendation/{student_id}")
async def generate_ai_recommendation(
    student_id: int,
    use_gpt4: bool = False,
    db: Session = Depends(get_db)
):
    """Genera una recomendación usando IA generativa"""
    try:
        ai_service = AIPromptService(db)

        # Generar prompt
        prompt_data = ai_service.generate_student_prompt(student_id)

        if not prompt_data["has_data"]:
            raise HTTPException(
                status_code=400,
                detail="No hay suficientes datos para generar recomendación"
            )

        # Aquí llamarías a tu API de IA preferida
        # Por ejemplo: OpenAI, Anthropic, etc.

        return {
            "student_id": student_id,
            "prompt": prompt_data["prompt"],
            "data_sources": prompt_data["data_sources"],
            "recommendation": "Aquí iría la respuesta de la IA"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando recomendación IA: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/summary")
async def get_analytics_summary(db: Session = Depends(get_db)):
    """Obtiene un resumen analítico de todos los estudiantes"""
    try:
        from app.api.v1.students.models import Alumno, RecommendationResult

        # Estadísticas generales
        total_students = db.query(Alumno).count()
        total_recommendations = db.query(RecommendationResult).count()

        # Distribución de riesgo
        risk_distribution = db.query(
            RecommendationResult.riesgo_predicho,
            func.count(RecommendationResult.id)
        ).group_by(RecommendationResult.riesgo_predicho).all()

        return {
            "total_students": total_students,
            "total_recommendations": total_recommendations,
            "risk_distribution": {
                risk: count for risk, count in risk_distribution
            },
            "coverage": f"{(total_recommendations/total_students)*100:.1f}%" if total_students > 0 else "0%"
        }

    except Exception as e:
        logger.error(f"Error obteniendo analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_recommendations_background(db: Session):
    """Procesa recomendaciones en segundo plano"""
    try:
        service = RecommendationService(db)
        result = service.process_all_students()
        logger.info(f"Proceso completado: {result}")
    except Exception as e:
        logger.error(f"Error en proceso background: {str(e)}")
    finally:
        db.close()


# # ===== SERVICIO DE PROMPTS PARA IA =====
# # app/api/v1/ml/services/ai_prompt_service.py

# from typing import Dict, List, Optional
# from sqlalchemy.orm import Session
# import json

# from app.api.v1.students.models import (
#     Alumno, Nota, Encuesta, RespuestaEncuesta,
#     RespuestaTextoEncuesta, HistorialAcademico
# )

# class AIPromptService:
#     def __init__(self, db: Session):
#         self.db = db

#     def generate_student_prompt(self, student_id: int) -> Dict:
#         """Genera un prompt completo para la IA con todos los datos del estudiante"""
#         student = self.db.query(Alumno).filter(Alumno.id == student_id).first()

#         if not student:
#             return {"has_data": False, "error": "Estudiante no encontrado"}

#         # Recopilar todos los datos
#         academic_data = self._get_academic_data(student_id)
#         survey_data = self._get_survey_data(student_id)
#         behavioral_patterns = self._analyze_patterns(academic_data, survey_data)

#         # Construir prompt
#         prompt = self._build_prompt(
#             student,
#             academic_data,
#             survey_data,
#             behavioral_patterns
#         )

#         return {
#             "has_data": True,
#             "prompt": prompt,
#             "data_sources": {
#                 "has_grades": academic_data["has_data"],
#                 "has_survey": survey_data["has_data"],
#                 "total_grades": academic_data.get("total_grades", 0),
#                 "survey_responses": len(survey_data.get("responses", []))
#             }
#         }

#     def _get_academic_data(self, student_id: int) -> Dict:
#         """Obtiene datos académicos estructurados"""
#         data = {
#             "has_data": False,
#             "grades_by_subject": {},
#             "grades_by_period": {},
#             "performance_trend": "stable",
#             "critical_subjects": [],
#             "strengths": [],
#             "total_grades": 0
#         }

#         # Obtener historial
#         historiales = self.db.query(HistorialAcademico).filter(
#             HistorialAcademico.alumno_id == student_id
#         ).all()

#         if not historiales:
#             return data

#         # Analizar notas
#         all_grades = []
#         subject_performance = {}

#         for historial in historiales:
#             notas = self.db.query(Nota).filter(
#                 Nota.historial_id == historial.id
#             ).all()

#             for nota in notas:
#                 if nota.nivel_logro and nota.nivel_logro.valor:
#                     grade_value = nota.nivel_logro.valor
#                     subject_name = nota.materia.nombre
#                     period = nota.bimestre.nombre

#                     # Agregar a la lista general
#                     all_grades.append({
#                         'subject': subject_name,
#                         'period': period,
#                         'grade': grade_value,
#                         'criteria': nota.criterio_evaluacion.nombre,
#                         'year': historial.anio_academico.anio
#                     })

#                     # Acumular por materia
#                     if subject_name not in subject_performance:
#                         subject_performance[subject_name] = []
#                     subject_performance[subject_name].append(grade_value)

#         if all_grades:
#             data["has_data"] = True
#             data["total_grades"] = len(all_grades)

#             # Analizar por materia
#             for subject, grades in subject_performance.items():
#                 grade_counts = {g: grades.count(g) for g in set(grades)}
#                 data["grades_by_subject"][subject] = grade_counts

#                 # Identificar materias críticas y fortalezas
#                 if grades.count('D') > len(grades) * 0.3:
#                     data["critical_subjects"].append(subject)
#                 elif grades.count('A') > len(grades) * 0.5:
#                     data["strengths"].append(subject)

#             # Analizar tendencia (simplificado)
#             if len(all_grades) > 10:
#                 recent_grades = all_grades[-5:]
#                 old_grades = all_grades[:5]

#                 recent_d_count = sum(1 for g in recent_grades if g['grade'] == 'D')
#                 old_d_count = sum(1 for g in old_grades if g['grade'] == 'D')

#                 if recent_d_count > old_d_count:
#                     data["performance_trend"] = "declining"
#                 elif recent_d_count < old_d_count:
#                     data["performance_trend"] = "improving"

#         return data

#     def _get_survey_data(self, student_id: int) -> Dict:
#         """Obtiene datos de encuesta estructurados"""
#         data = {
#             "has_data": False,
#             "responses": [],
#             "study_habits": {},
#             "challenges": [],
#             "resources": [],
#             "wellness_indicators": {}
#         }

#         # Obtener encuesta más reciente
#         encuesta = self.db.query(Encuesta).filter(
#             Encuesta.alumno_id == student_id
#         ).order_by(Encuesta.fecha.desc()).first()

#         if not encuesta:
#             return data

#         data["has_data"] = True

#         # Obtener respuestas
#         respuestas = self.db.query(RespuestaEncuesta).filter(
#             RespuestaEncuesta.encuesta_id == encuesta.id
#         ).all()

#         respuestas_texto = self.db.query(RespuestaTextoEncuesta).filter(
#             RespuestaTextoEncuesta.encuesta_id == encuesta.id
#         ).all()

#         # Procesar respuestas estructuradas
#         for respuesta in respuestas:
#             question = respuesta.pregunta.pregunta
#             answer = respuesta.opcion.opcion

#             data["responses"].append({
#                 "question": question,
#                 "answer": answer
#             })

#             # Categorizar respuestas
#             if "tiempo dedicas al estudio" in question:
#                 data["study_habits"]["study_time"] = answer
#             elif "participar en clase" in question:
#                 data["study_habits"]["class_participation"] = answer
#             elif "estrés o ansiedad" in question:
#                 data["wellness_indicators"]["stress_level"] = answer
#             elif "horas duermes" in question:
#                 data["wellness_indicators"]["sleep_hours"] = answer
#             elif "recursos utilizas" in question:
#                 data["resources"].append(answer)

#         # Procesar respuestas de texto
#         for respuesta in respuestas_texto:
#             question = respuesta.pregunta.pregunta
#             answer = respuesta.texto

#             if answer and len(answer.strip()) > 0:
#                 if "mejorarías" in question:
#                     data["challenges"].append(answer)
#                 elif "apoyo adicional" in question:
#                     data["challenges"].append(f"Necesita: {answer}")

#         return data

#     def _analyze_patterns(self, academic_data: Dict, survey_data: Dict) -> Dict:
#         """Analiza patrones entre datos académicos y de encuesta"""
#         patterns = {
#             "risk_factors": [],
#             "positive_factors": [],
#             "recommendations_priority": []
#         }

#         # Factores de riesgo académico
#         if academic_data["has_data"]:
#             if len(academic_data["critical_subjects"]) > 2:
#                 patterns["risk_factors"].append("Múltiples materias con bajo rendimiento")
#                 patterns["recommendations_priority"].append("tutorías_especializadas")

#             if academic_data["performance_trend"] == "declining":
#                 patterns["risk_factors"].append("Tendencia de rendimiento decreciente")
#                 patterns["recommendations_priority"].append("intervención_temprana")

#         # Factores de encuesta
#         if survey_data["has_data"]:
#             # Analizar hábitos de estudio
#             study_time = survey_data["study_habits"].get("study_time", "")
#             if "Menos de 1 hora" in study_time:
#                 patterns["risk_factors"].append("Tiempo de estudio insuficiente")
#                 patterns["recommendations_priority"].append("plan_estudio")

#             # Analizar bienestar
#             stress = survey_data["wellness_indicators"].get("stress_level", "")
#             if "Siempre" in stress or "Casi siempre" in stress:
#                 patterns["risk_factors"].append("Alto nivel de estrés reportado")
#                 patterns["recommendations_priority"].append("apoyo_emocional")

#             sleep = survey_data["wellness_indicators"].get("sleep_hours", "")
#             if "Menos de 5 horas" in sleep:
#                 patterns["risk_factors"].append("Privación de sueño")
#                 patterns["recommendations_priority"].append("higiene_sueño")

#         # Factores positivos
#         if academic_data.get("strengths"):
#             patterns["positive_factors"].append(
#                 f"Fortalezas en: {', '.join(academic_data['strengths'])}"
#             )

#         if survey_data["study_habits"].get("class_participation") in ["Siempre", "Casi siempre"]:
#             patterns["positive_factors"].append("Alta participación en clase")

#         return patterns

#     def _build_prompt(
#         self,
#         student: Alumno,
#         academic_data: Dict,
#         survey_data: Dict,
#         patterns: Dict
#     ) -> str:
#         """Construye el prompt final para la IA"""
#         prompt_parts = []

#         # Contexto
#         prompt_parts.append(
#             "Eres un experto en educación y psicología educativa. "
#             "Analiza los siguientes datos de un estudiante y genera recomendaciones "
#             "personalizadas, específicas y accionables para mejorar su rendimiento académico."
#         )

#         # Información del estudiante
#         prompt_parts.append(f"\n\n=== INFORMACIÓN DEL ESTUDIANTE ===")
#         prompt_parts.append(f"Nombre: {student.nombre_completo}")
#         if student.edad:
#             prompt_parts.append(f"Edad: {student.edad} años")
#         prompt_parts.append(f"Género: {student.genero}")

#         # Datos académicos
#         if academic_data["has_data"]:
#             prompt_parts.append(f"\n\n=== RENDIMIENTO ACADÉMICO ===")
#             prompt_parts.append(f"Total de calificaciones analizadas: {academic_data['total_grades']}")
#             prompt_parts.append(f"Tendencia de rendimiento: {academic_data['performance_trend']}")

#             if academic_data["critical_subjects"]:
#                 prompt_parts.append(f"\nMaterias que requieren atención urgente:")
#                 for subject in academic_data["critical_subjects"]:
#                     grades = academic_data["grades_by_subject"].get(subject, {})
#                     prompt_parts.append(f"- {subject}: {grades}")

#             if academic_data["strengths"]:
#                 prompt_parts.append(f"\nMaterias donde destaca:")
#                 for subject in academic_data["strengths"]:
#                     prompt_parts.append(f"- {subject}")

#             # Distribución general de notas
#             prompt_parts.append(f"\nDistribución de calificaciones por materia:")
#             for subject, grades in academic_data["grades_by_subject"].items():
#                 if subject not in academic_data["critical_subjects"] and subject not in academic_data["strengths"]:
#                     prompt_parts.append(f"- {subject}: {grades}")

#         # Datos de encuesta
#         if survey_data["has_data"]:
#             prompt_parts.append(f"\n\n=== HÁBITOS Y BIENESTAR ===")

#             # Hábitos de estudio
#             if survey_data["study_habits"]:
#                 prompt_parts.append(f"\nHábitos de estudio:")
#                 for habit, value in survey_data["study_habits"].items():
#                     prompt_parts.append(f"- {habit.replace('_', ' ').title()}: {value}")

#             # Indicadores de bienestar
#             if survey_data["wellness_indicators"]:
#                 prompt_parts.append(f"\nIndicadores de bienestar:")
#                 for indicator, value in survey_data["wellness_indicators"].items():
#                     prompt_parts.append(f"- {indicator.replace('_', ' ').title()}: {value}")

#             # Recursos que utiliza
#             if survey_data["resources"]:
#                 prompt_parts.append(f"\nRecursos de estudio que utiliza:")
#                 for resource in survey_data["resources"]:
#                     prompt_parts.append(f"- {resource}")

#             # Desafíos expresados
#             if survey_data["challenges"]:
#                 prompt_parts.append(f"\nDesafíos y necesidades expresadas por el estudiante:")
#                 for challenge in survey_data["challenges"]:
#                     prompt_parts.append(f"- {challenge}")

#         # Análisis de patrones
#         prompt_parts.append(f"\n\n=== ANÁLISIS DE PATRONES ===")

#         if patterns["risk_factors"]:
#             prompt_parts.append(f"\nFactores de riesgo identificados:")
#             for factor in patterns["risk_factors"]:
#                 prompt_parts.append(f"- {factor}")

#         if patterns["positive_factors"]:
#             prompt_parts.append(f"\nFactores positivos:")
#             for factor in patterns["positive_factors"]:
#                 prompt_parts.append(f"- {factor}")

#         if patterns["recommendations_priority"]:
#             prompt_parts.append(f"\nÁreas prioritarias para intervención:")
#             for priority in patterns["recommendations_priority"]:
#                 prompt_parts.append(f"- {priority.replace('_', ' ').title()}")

#         # Instrucciones para la IA
#         prompt_parts.append(f"\n\n=== INSTRUCCIONES PARA GENERAR RECOMENDACIONES ===")
#         prompt_parts.append(
#             "Basándote en toda la información anterior, genera recomendaciones que sean:\n"
#             "1. ESPECÍFICAS: Adaptadas a las necesidades exactas de este estudiante\n"
#             "2. ACCIONABLES: Con pasos concretos que el estudiante pueda seguir\n"
#             "3. REALISTAS: Considerando los recursos y limitaciones mencionados\n"
#             "4. MEDIBLES: Que permitan evaluar el progreso\n"
#             "5. TEMPORALES: Con sugerencias de plazos o frecuencias\n"
#             "\nOrganiza las recomendaciones en las siguientes categorías:\n"
#             "- ACCIONES INMEDIATAS (para implementar esta semana)\n"
#             "- PLAN A MEDIANO PLAZO (próximo mes)\n"
#             "- ESTRATEGIAS A LARGO PLAZO (próximo trimestre)\n"
#             "- RECURSOS RECOMENDADOS (específicos y accesibles)\n"
#             "- APOYO NECESARIO (de profesores, familia o institución)"
#         )

#         # Consideraciones especiales basadas en los datos
#         if not academic_data["has_data"] and not survey_data["has_data"]:
#             prompt_parts.append(
#                 "\n\nNOTA IMPORTANTE: Este estudiante no tiene datos académicos ni de encuesta. "
#                 "Las recomendaciones deben enfocarse en:\n"
#                 "1. La importancia de completar evaluaciones\n"
#                 "2. Establecer una línea base de rendimiento\n"
#                 "3. Crear un plan de seguimiento inicial"
#             )
#         elif not academic_data["has_data"]:
#             prompt_parts.append(
#                 "\n\nNOTA: No hay datos académicos disponibles. "
#                 "Basa las recomendaciones principalmente en los hábitos y necesidades expresadas."
#             )
#         elif not survey_data["has_data"]:
#             prompt_parts.append(
#                 "\n\nNOTA: No hay datos de encuesta disponibles. "
#                 "Basa las recomendaciones principalmente en el rendimiento académico observado."
#             )

#         return "\n".join(prompt_parts)