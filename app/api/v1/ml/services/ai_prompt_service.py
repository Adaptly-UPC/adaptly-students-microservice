# app/api/v1/ml/services/ai_prompt_service.py

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging
from datetime import datetime

from app.api.v1.students.models import (
    Alumno, Nota, Encuesta, RespuestaEncuesta,
    RespuestaTextoEncuesta, HistorialAcademico,
)

logger = logging.getLogger(__name__)

class AIPromptService:
    """Servicio para generar prompts detallados para APIs de IA generativa"""

    def __init__(self, db: Session):
        self.db = db

    def generate_student_prompt(self, student_id: int) -> Dict:
        """Genera un prompt completo para la IA con todos los datos del estudiante"""
        try:
            student = self.db.query(Alumno).filter(Alumno.id == student_id).first()

            if not student:
                return {
                    "has_data": False,
                    "error": "Estudiante no encontrado"
                }

            # Recopilar todos los datos disponibles
            academic_data = self._get_academic_data(student_id)
            survey_data = self._get_survey_data(student_id)
            behavioral_patterns = self._analyze_patterns(academic_data, survey_data)
            comparative_data = self._get_comparative_analysis(student_id, academic_data)

            # Construir prompt estructurado
            prompt = self._build_prompt(
                student,
                academic_data,
                survey_data,
                behavioral_patterns,
                comparative_data
            )

            # Metadatos sobre los datos disponibles
            data_summary = {
                "has_data": True,
                "prompt": prompt,
                "data_sources": {
                    "has_grades": academic_data["has_data"],
                    "has_survey": survey_data["has_data"],
                    "total_grades": academic_data.get("total_grades", 0),
                    "survey_responses": len(survey_data.get("responses", [])),
                    "subjects_analyzed": len(academic_data.get("grades_by_subject", {})),
                    "periods_covered": len(academic_data.get("grades_by_period", {}))
                }
            }

            return data_summary

        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            return {
                "has_data": False,
                "error": str(e)
            }

    def _get_academic_data(self, student_id: int) -> Dict:
        """Obtiene y estructura todos los datos académicos del estudiante"""
        data = {
            "has_data": False,
            "grades_by_subject": {},
            "grades_by_period": {},
            "grades_by_criteria": {},
            "performance_trend": "stable",
            "critical_subjects": [],
            "strengths": [],
            "total_grades": 0,
            "grade_evolution": [],
            "attendance_issues": [],
            "academic_level": None,
            "current_grade": None
        }

        # Obtener historial académico
        historiales = self.db.query(HistorialAcademico).filter(
            HistorialAcademico.alumno_id == student_id
        ).order_by(HistorialAcademico.anio_academico_id).all()

        if not historiales:
            return data

        # Obtener información del nivel y grado actual
        latest_historial = historiales[-1]
        if latest_historial.nivel:
            data["academic_level"] = latest_historial.nivel.nombre
        if latest_historial.grado:
            data["current_grade"] = f"{latest_historial.grado.nombre} {latest_historial.seccion.nombre if latest_historial.seccion else ''}"

        # Analizar todas las notas
        all_grades = []
        subject_performance = {}
        period_performance = {}
        criteria_performance = {}

        for historial in historiales:
            year = historial.anio_academico.anio

            notas = self.db.query(Nota).filter(
                Nota.historial_id == historial.id
            ).all()

            for nota in notas:
                if nota.nivel_logro and nota.nivel_logro.valor:
                    grade_value = nota.nivel_logro.valor
                    subject_name = nota.materia.nombre
                    period = nota.bimestre.nombre
                    criteria = nota.criterio_evaluacion.nombre

                    # Datos completos de la nota
                    grade_info = {
                        'subject': subject_name,
                        'period': period,
                        'grade': grade_value,
                        'criteria': criteria,
                        'year': year,
                        'criteria_value': nota.valor_criterio_de_evaluacion
                    }
                    all_grades.append(grade_info)

                    # Acumular por materia
                    if subject_name not in subject_performance:
                        subject_performance[subject_name] = {
                            'grades': [],
                            'criteria_details': {}
                        }
                    subject_performance[subject_name]['grades'].append(grade_value)

                    # Acumular por criterio dentro de la materia
                    if criteria not in subject_performance[subject_name]['criteria_details']:
                        subject_performance[subject_name]['criteria_details'][criteria] = []
                    subject_performance[subject_name]['criteria_details'][criteria].append({
                        'grade': grade_value,
                        'period': period,
                        'year': year
                    })

                    # Acumular por período
                    period_key = f"{year} - {period}"
                    if period_key not in period_performance:
                        period_performance[period_key] = []
                    period_performance[period_key].append(grade_value)

                    # Acumular por criterio general
                    if criteria not in criteria_performance:
                        criteria_performance[criteria] = []
                    criteria_performance[criteria].append(grade_value)

        if all_grades:
            data["has_data"] = True
            data["total_grades"] = len(all_grades)

            # Analizar rendimiento por materia
            for subject, info in subject_performance.items():
                grades = info['grades']
                grade_counts = {g: grades.count(g) for g in set(grades)}

                data["grades_by_subject"][subject] = {
                    'distribution': grade_counts,
                    'total': len(grades),
                    'average_performance': self._calculate_grade_average(grades),
                    'criteria_analysis': info['criteria_details']
                }

                # Identificar materias críticas y fortalezas
                d_percentage = grades.count('D') / len(grades) if len(grades) > 0 else 0
                a_percentage = grades.count('A') / len(grades) if len(grades) > 0 else 0

                if d_percentage > 0.3:
                    data["critical_subjects"].append({
                        'subject': subject,
                        'd_percentage': d_percentage,
                        'total_grades': len(grades)
                    })
                elif a_percentage > 0.5:
                    data["strengths"].append({
                        'subject': subject,
                        'a_percentage': a_percentage,
                        'total_grades': len(grades)
                    })

            # Analizar rendimiento por período
            data["grades_by_period"] = period_performance

            # Analizar rendimiento por criterio
            for criteria, grades in criteria_performance.items():
                grade_counts = {g: grades.count(g) for g in set(grades)}
                data["grades_by_criteria"][criteria] = {
                    'distribution': grade_counts,
                    'average_performance': self._calculate_grade_average(grades)
                }

            # Analizar tendencia de rendimiento
            data["performance_trend"] = self._analyze_performance_trend(all_grades)

            # Evolución temporal del rendimiento
            data["grade_evolution"] = self._analyze_grade_evolution(all_grades)

        return data

    def _get_survey_data(self, student_id: int) -> Dict:
        """Obtiene y estructura todos los datos de encuesta del estudiante"""
        data = {
            "has_data": False,
            "responses": [],
            "study_habits": {},
            "challenges": [],
            "resources": [],
            "wellness_indicators": {},
            "learning_preferences": {},
            "self_perception": {},
            "support_needs": [],
            "survey_date": None
        }

        # Obtener encuesta más reciente
        encuesta = self.db.query(Encuesta).filter(
            Encuesta.alumno_id == student_id
        ).order_by(Encuesta.fecha.desc()).first()

        if not encuesta:
            return data

        data["has_data"] = True
        data["survey_date"] = encuesta.fecha.isoformat() if encuesta.fecha else None

        # Obtener todas las respuestas de opción múltiple
        respuestas = self.db.query(RespuestaEncuesta).filter(
            RespuestaEncuesta.encuesta_id == encuesta.id
        ).all()

        # Obtener respuestas de texto
        respuestas_texto = self.db.query(RespuestaTextoEncuesta).filter(
            RespuestaTextoEncuesta.encuesta_id == encuesta.id
        ).all()

        # Procesar respuestas estructuradas
        for respuesta in respuestas:
            question = respuesta.pregunta.pregunta
            answer = respuesta.opcion.opcion

            # Guardar respuesta completa
            data["responses"].append({
                "question": question,
                "answer": answer,
                "question_type": respuesta.pregunta.tipo
            })

            # Categorizar respuestas para análisis
            self._categorize_survey_response(question, answer, data)

        # Procesar respuestas de texto
        for respuesta in respuestas_texto:
            question = respuesta.pregunta.pregunta
            answer = respuesta.texto

            if answer and len(answer.strip()) > 0:
                data["responses"].append({
                    "question": question,
                    "answer": answer,
                    "question_type": "texto"
                })

                # Categorizar respuestas de texto
                if "mejorarías" in question.lower():
                    data["challenges"].append({
                        "type": "improvement_suggestion",
                        "description": answer
                    })
                elif "apoyo adicional" in question.lower():
                    data["support_needs"].append({
                        "type": "additional_support",
                        "description": answer
                    })

        # Calcular índices compuestos
        data["engagement_index"] = self._calculate_engagement_index(data)
        data["wellness_index"] = self._calculate_wellness_index(data)
        data["resource_utilization_index"] = self._calculate_resource_index(data)

        return data

    def _categorize_survey_response(self, question: str, answer: str, data: Dict):
        """Categoriza las respuestas de encuesta en diferentes dimensiones"""
        question_lower = question.lower()

        # Hábitos de estudio
        if "tiempo dedicas al estudio" in question_lower:
            data["study_habits"]["study_time"] = answer
            data["study_habits"]["study_time_numeric"] = self._map_study_hours(answer)

        elif "participar en clase" in question_lower:
            data["study_habits"]["class_participation"] = answer
            data["study_habits"]["participation_level"] = self._map_frequency(answer)

        elif "pides ayuda" in question_lower:
            data["study_habits"]["help_seeking"] = answer
            data["study_habits"]["help_seeking_level"] = self._map_frequency(answer)

        elif "te esfuerzas" in question_lower:
            data["study_habits"]["effort_level"] = answer
            data["study_habits"]["effort_numeric"] = self._map_effort(answer)

        # Percepciones y actitudes
        elif "te gustan las clases" in question_lower:
            data["self_perception"]["class_enjoyment"] = answer
            data["self_perception"]["enjoyment_level"] = self._map_class_enjoyment(answer)

        elif "dificultad de las materias" in question_lower:
            data["self_perception"]["perceived_difficulty"] = answer
            data["self_perception"]["difficulty_level"] = self._map_difficulty(answer)

        # Bienestar
        elif "estrés o ansiedad" in question_lower:
            data["wellness_indicators"]["stress_level"] = answer
            data["wellness_indicators"]["stress_numeric"] = self._map_frequency(answer)

        elif "horas duermes" in question_lower:
            data["wellness_indicators"]["sleep_hours"] = answer
            data["wellness_indicators"]["sleep_quality"] = self._map_sleep_hours(answer)

        # Recursos y tecnología
        elif "recursos utilizas" in question_lower:
            if answer not in data["resources"]:
                data["resources"].append(answer)

        elif "acceso a internet" in question_lower:
            data["learning_preferences"]["has_internet"] = answer == "Sí"

        elif "utilizas la tecnología" in question_lower:
            data["learning_preferences"]["technology_use"] = answer
            data["learning_preferences"]["tech_level"] = self._map_frequency(answer)

        # Actividades extracurriculares
        elif "actividades extracurriculares" in question_lower:
            data["wellness_indicators"]["has_extracurricular"] = answer == "Sí"

    def _analyze_patterns(self, academic_data: Dict, survey_data: Dict) -> Dict:
        """Analiza patrones complejos entre datos académicos y de encuesta"""
        patterns = {
            "risk_factors": [],
            "protective_factors": [],
            "correlations": [],
            "recommendations_priority": [],
            "intervention_areas": []
        }

        # Análisis de factores de riesgo académico
        if academic_data["has_data"]:
            # Riesgo por bajo rendimiento general
            total_grades = academic_data["total_grades"]
            if total_grades > 0:
                d_count = sum(1 for g in self._flatten_grades(academic_data) if g == 'D')
                d_percentage = d_count / total_grades

                if d_percentage > 0.3:
                    patterns["risk_factors"].append({
                        "factor": "high_failure_rate",
                        "severity": "high",
                        "details": f"{d_percentage*100:.1f}% de calificaciones D"
                    })
                    patterns["recommendations_priority"].append("academic_recovery")

            # Riesgo por materias críticas múltiples
            if len(academic_data["critical_subjects"]) > 2:
                patterns["risk_factors"].append({
                    "factor": "multiple_failing_subjects",
                    "severity": "high",
                    "details": f"{len(academic_data['critical_subjects'])} materias críticas"
                })
                patterns["recommendations_priority"].append("subject_specific_support")

            # Riesgo por tendencia negativa
            if academic_data["performance_trend"] == "declining":
                patterns["risk_factors"].append({
                    "factor": "declining_performance",
                    "severity": "medium",
                    "details": "Rendimiento en declive en últimos períodos"
                })
                patterns["recommendations_priority"].append("early_intervention")

        # Análisis de factores de encuesta
        if survey_data["has_data"]:
            # Factores de hábitos de estudio
            study_time = survey_data["study_habits"].get("study_time_numeric", 0)
            if study_time < 2:
                patterns["risk_factors"].append({
                    "factor": "insufficient_study_time",
                    "severity": "medium",
                    "details": survey_data["study_habits"].get("study_time", "No especificado")
                })
                patterns["intervention_areas"].append("study_habits")

            # Factores de participación
            participation = survey_data["study_habits"].get("participation_level", 0)
            help_seeking = survey_data["study_habits"].get("help_seeking_level", 0)

            if participation < 2 and help_seeking < 2:
                patterns["risk_factors"].append({
                    "factor": "low_engagement",
                    "severity": "medium",
                    "details": "Baja participación y poca búsqueda de ayuda"
                })
                patterns["intervention_areas"].append("engagement")

            # Factores de bienestar
            stress = survey_data["wellness_indicators"].get("stress_numeric", 0)
            sleep = survey_data["wellness_indicators"].get("sleep_quality", 0)

            if stress >= 3:
                patterns["risk_factors"].append({
                    "factor": "high_stress",
                    "severity": "high",
                    "details": survey_data["wellness_indicators"].get("stress_level", "Alto")
                })
                patterns["intervention_areas"].append("emotional_support")

            if sleep < 2:
                patterns["risk_factors"].append({
                    "factor": "sleep_deprivation",
                    "severity": "medium",
                    "details": survey_data["wellness_indicators"].get("sleep_hours", "Pocas")
                })
                patterns["intervention_areas"].append("health_habits")

        # Identificar factores protectores
        if academic_data.get("strengths"):
            patterns["protective_factors"].append({
                "factor": "academic_strengths",
                "impact": "positive",
                "details": f"Fortalezas en {len(academic_data['strengths'])} materias"
            })

        if survey_data.get("resources"):
            patterns["protective_factors"].append({
                "factor": "diverse_learning_resources",
                "impact": "positive",
                "details": f"Utiliza {len(survey_data['resources'])} recursos diferentes"
            })

        if survey_data.get("wellness_indicators", {}).get("has_extracurricular"):
            patterns["protective_factors"].append({
                "factor": "extracurricular_engagement",
                "impact": "positive",
                "details": "Participa en actividades extracurriculares"
            })

        # Análisis de correlaciones
        if academic_data["has_data"] and survey_data["has_data"]:
            # Correlación entre horas de estudio y rendimiento
            if study_time < 2 and len(academic_data["critical_subjects"]) > 0:
                patterns["correlations"].append({
                    "type": "study_time_performance",
                    "finding": "Bajo tiempo de estudio correlacionado con materias críticas",
                    "strength": "strong"
                })

            # Correlación entre estrés y rendimiento
            if stress >= 3 and academic_data["performance_trend"] == "declining":
                patterns["correlations"].append({
                    "type": "stress_performance",
                    "finding": "Alto estrés asociado con declive en rendimiento",
                    "strength": "moderate"
                })

        # Priorizar recomendaciones basadas en severidad
        patterns["recommendations_priority"] = self._prioritize_recommendations(patterns)

        return patterns

    def _get_comparative_analysis(self, student_id: int, academic_data: Dict) -> Dict:
        """Compara el rendimiento del estudiante con sus pares"""
        comparative = {
            "peer_comparison": {},
            "grade_level_stats": {},
            "percentile_rank": None,
            "comparison_available": False
        }

        if not academic_data["has_data"]:
            return comparative

        try:
            # Obtener información del estudiante actual
            student = self.db.query(Alumno).filter(Alumno.id == student_id).first()
            historial = self.db.query(HistorialAcademico).filter(
                HistorialAcademico.alumno_id == student_id
            ).order_by(HistorialAcademico.id.desc()).first()

            if not historial:
                return comparative

            # Obtener estudiantes del mismo grado y nivel
            peer_historiales = self.db.query(HistorialAcademico).filter(
                HistorialAcademico.grado_id == historial.grado_id,
                HistorialAcademico.nivel_id == historial.nivel_id,
                HistorialAcademico.anio_academico_id == historial.anio_academico_id,
                HistorialAcademico.alumno_id != student_id
            ).all()

            if not peer_historiales:
                return comparative

            comparative["comparison_available"] = True

            # Calcular estadísticas de pares
            peer_grades = []
            for peer_hist in peer_historiales:
                peer_notas = self.db.query(Nota).filter(
                    Nota.historial_id == peer_hist.id
                ).all()

                for nota in peer_notas:
                    if nota.nivel_logro and nota.nivel_logro.valor:
                        peer_grades.append(nota.nivel_logro.valor)

            if peer_grades:
                # Calcular distribución de notas del grupo
                grade_distribution = {g: peer_grades.count(g) / len(peer_grades) for g in set(peer_grades)}
                comparative["grade_level_stats"] = {
                    "total_peers": len(peer_historiales),
                    "grade_distribution": grade_distribution,
                    "average_performance": self._calculate_grade_average(peer_grades)
                }

                # Calcular percentil del estudiante
                student_avg = self._calculate_student_average(academic_data)
                peer_averages = [self._calculate_grade_average(peer_grades)]

                if student_avg is not None:
                    percentile = sum(1 for avg in peer_averages if avg < student_avg) / len(peer_averages) * 100
                    comparative["percentile_rank"] = round(percentile, 1)

                    # Comparación cualitativa
                    if percentile >= 75:
                        comparative["peer_comparison"]["status"] = "above_average"
                        comparative["peer_comparison"]["description"] = "Rendimiento superior al promedio"
                    elif percentile >= 25:
                        comparative["peer_comparison"]["status"] = "average"
                        comparative["peer_comparison"]["description"] = "Rendimiento promedio"
                    else:
                        comparative["peer_comparison"]["status"] = "below_average"
                        comparative["peer_comparison"]["description"] = "Rendimiento por debajo del promedio"

        except Exception as e:
            logger.error(f"Error in comparative analysis: {str(e)}")

        return comparative

    def _build_prompt(
        self,
        student: Alumno,
        academic_data: Dict,
        survey_data: Dict,
        patterns: Dict,
        comparative_data: Dict
    ) -> str:
        """Construye el prompt final estructurado para la IA"""
        prompt_parts = []

        # 1. Contexto e instrucciones iniciales
        prompt_parts.append(
            "Eres un experto en educación y psicología educativa con amplia experiencia "
            "en el desarrollo de planes de aprendizaje personalizados. Tu tarea es analizar "
            "los datos de un estudiante y generar recomendaciones específicas, accionables "
            "y basadas en evidencia para mejorar su rendimiento académico y bienestar."
        )

        # 2. Información básica del estudiante
        prompt_parts.append(f"\n\n{'='*50}")
        prompt_parts.append("INFORMACIÓN DEL ESTUDIANTE")
        prompt_parts.append(f"{'='*50}")
        prompt_parts.append(f"Nombre: {student.nombre_completo}")
        if student.edad:
            prompt_parts.append(f"Edad: {student.edad} años")
        prompt_parts.append(f"Género: {student.genero}")

        if academic_data.get("academic_level"):
            prompt_parts.append(f"Nivel educativo: {academic_data['academic_level']}")
        if academic_data.get("current_grade"):
            prompt_parts.append(f"Grado actual: {academic_data['current_grade']}")

        # 3. Rendimiento académico detallado
        if academic_data["has_data"]:
            prompt_parts.append(f"\n\n{'='*50}")
            prompt_parts.append("ANÁLISIS DE RENDIMIENTO ACADÉMICO")
            prompt_parts.append(f"{'='*50}")

            prompt_parts.append(f"\nTotal de calificaciones analizadas: {academic_data['total_grades']}")
            prompt_parts.append(f"Tendencia general: {academic_data['performance_trend']}")

            # Materias críticas
            if academic_data["critical_subjects"]:
                prompt_parts.append("\n### Materias que requieren atención urgente:")
                for subject_info in academic_data["critical_subjects"]:
                    subject = subject_info['subject']
                    d_percent = subject_info['d_percentage'] * 100
                    grades_info = academic_data["grades_by_subject"].get(subject, {})

                    prompt_parts.append(f"\n- **{subject}**:")
                    prompt_parts.append(f"  - {d_percent:.1f}% de calificaciones D")
                    prompt_parts.append(f"  - Distribución: {grades_info.get('distribution', {})}")

                    # Análisis por criterio si está disponible
                    if grades_info.get('criteria_analysis'):
                        prompt_parts.append("  - Análisis por criterio:")
                        for criteria, details in grades_info['criteria_analysis'].items():
                            grades = [d['grade'] for d in details]
                            grade_counts = {g: grades.count(g) for g in set(grades)}
                            prompt_parts.append(f"    * {criteria}: {grade_counts}")

            # Fortalezas
            if academic_data["strengths"]:
                prompt_parts.append("\n### Materias donde el estudiante destaca:")
                for strength_info in academic_data["strengths"]:
                    subject = strength_info['subject']
                    a_percent = strength_info['a_percentage'] * 100
                    prompt_parts.append(f"- {subject}: {a_percent:.1f}% de calificaciones A")

            # Rendimiento por período
            if academic_data["grades_by_period"]:
                prompt_parts.append("\n### Evolución temporal del rendimiento:")
                sorted_periods = sorted(academic_data["grades_by_period"].items())
                for period, grades in sorted_periods[-3:]:  # Últimos 3 períodos
                    grade_counts = {g: grades.count(g) for g in set(grades)}
                    prompt_parts.append(f"- {period}: {grade_counts}")

            # Análisis por criterios de evaluación
            if academic_data["grades_by_criteria"]:
                prompt_parts.append("\n### Rendimiento por criterios de evaluación:")
                for criteria, info in list(academic_data["grades_by_criteria"].items())[:5]:
                    avg = info['average_performance']
                    prompt_parts.append(f"- {criteria}: Promedio {avg:.2f}")

        # 4. Datos de encuesta y hábitos
        if survey_data["has_data"]:
            prompt_parts.append(f"\n\n{'='*50}")
            prompt_parts.append("HÁBITOS DE ESTUDIO Y BIENESTAR")
            prompt_parts.append(f"{'='*50}")

            if survey_data["survey_date"]:
                prompt_parts.append(f"Fecha de encuesta: {survey_data['survey_date']}")

            # Hábitos de estudio
            if survey_data["study_habits"]:
                prompt_parts.append("\n### Hábitos de estudio:")
                for habit, value in survey_data["study_habits"].items():
                    if not habit.endswith('_numeric') and not habit.endswith('_level'):
                        prompt_parts.append(f"- {habit.replace('_', ' ').title()}: {value}")

            # Indicadores de bienestar
            if survey_data["wellness_indicators"]:
                prompt_parts.append("\n### Indicadores de bienestar:")
                for indicator, value in survey_data["wellness_indicators"].items():
                    if not indicator.endswith('_numeric') and not indicator.endswith('_quality'):
                        prompt_parts.append(f"- {indicator.replace('_', ' ').title()}: {value}")

            # Autopercepción
            if survey_data["self_perception"]:
                prompt_parts.append("\n### Autopercepción del estudiante:")
                for perception, value in survey_data["self_perception"].items():
                    if not perception.endswith('_level'):
                        prompt_parts.append(f"- {perception.replace('_', ' ').title()}: {value}")

            # Recursos utilizados
            if survey_data["resources"]:
                prompt_parts.append("\n### Recursos de aprendizaje que utiliza:")
                for resource in survey_data["resources"]:
                    prompt_parts.append(f"- {resource}")

            # Preferencias de aprendizaje
            if survey_data["learning_preferences"]:
                prompt_parts.append("\n### Preferencias de aprendizaje:")
                for pref, value in survey_data["learning_preferences"].items():
                    if pref == "has_internet":
                        prompt_parts.append(f"- Acceso a internet: {'Sí' if value else 'No'}")
                    else:
                        prompt_parts.append(f"- {pref.replace('_', ' ').title()}: {value}")

            # Necesidades expresadas
            if survey_data["challenges"]:
                prompt_parts.append("\n### Desafíos identificados por el estudiante:")
                for challenge in survey_data["challenges"]:
                    prompt_parts.append(f"- {challenge['description']}")

            if survey_data["support_needs"]:
                prompt_parts.append("\n### Apoyo solicitado:")
                for need in survey_data["support_needs"]:
                    prompt_parts.append(f"- {need['description']}")

            # Índices calculados
            prompt_parts.append("\n### Índices de evaluación:")
            prompt_parts.append(f"- Índice de compromiso: {survey_data.get('engagement_index', 'N/A')}")
            prompt_parts.append(f"- Índice de bienestar: {survey_data.get('wellness_index', 'N/A')}")
            prompt_parts.append(f"- Índice de uso de recursos: {survey_data.get('resource_utilization_index', 'N/A')}")

        # 5. Análisis comparativo con pares
        if comparative_data.get("comparison_available"):
            prompt_parts.append(f"\n\n{'='*50}")
            prompt_parts.append("ANÁLISIS COMPARATIVO")
            prompt_parts.append(f"{'='*50}")

            if comparative_data.get("percentile_rank") is not None:
                prompt_parts.append(f"\nPercentil en su grupo: {comparative_data['percentile_rank']}%")
                prompt_parts.append(f"Estado comparativo: {comparative_data['peer_comparison']['description']}")

            if comparative_data.get("grade_level_stats"):
                stats = comparative_data["grade_level_stats"]
                prompt_parts.append(f"\nEstadísticas del grupo (n={stats['total_peers']}):")
                prompt_parts.append(f"- Distribución de notas: {stats['grade_distribution']}")

        # 6. Análisis de patrones y factores
        prompt_parts.append(f"\n\n{'='*50}")
        prompt_parts.append("ANÁLISIS DE FACTORES Y PATRONES")
        prompt_parts.append(f"{'='*50}")

        # Factores de riesgo
        if patterns["risk_factors"]:
            prompt_parts.append("\n### Factores de riesgo identificados:")
            for factor in patterns["risk_factors"]:
                severity_emoji = "🔴" if factor["severity"] == "high" else "🟡"
                prompt_parts.append(f"{severity_emoji} {factor['details']}")
                prompt_parts.append(f"   Tipo: {factor['factor'].replace('_', ' ').title()}")
                prompt_parts.append(f"   Severidad: {factor['severity']}")

        # Factores protectores
        if patterns["protective_factors"]:
            prompt_parts.append("\n### Factores protectores:")
            for factor in patterns["protective_factors"]:
                prompt_parts.append(f"✅ {factor['details']}")
                prompt_parts.append(f"   Tipo: {factor['factor'].replace('_', ' ').title()}")

        # Correlaciones encontradas
        if patterns["correlations"]:
            prompt_parts.append("\n### Correlaciones identificadas:")
            for correlation in patterns["correlations"]:
                prompt_parts.append(f"- {correlation['finding']}")
                prompt_parts.append(f"  Fuerza de la correlación: {correlation['strength']}")

        # Áreas prioritarias de intervención
        if patterns["intervention_areas"]:
            prompt_parts.append("\n### Áreas prioritarias para intervención:")
            for area in patterns["intervention_areas"]:
                prompt_parts.append(f"- {area.replace('_', ' ').title()}")

        # 7. Casos especiales y consideraciones
        prompt_parts.append(f"\n\n{'='*50}")
        prompt_parts.append("CONSIDERACIONES ESPECIALES")
        prompt_parts.append(f"{'='*50}")

        # Datos faltantes
        if not academic_data["has_data"] and not survey_data["has_data"]:
            prompt_parts.append(
                "\n⚠️ ALERTA: Este estudiante no tiene datos académicos ni de encuesta registrados. "
                "Las recomendaciones deben enfocarse en establecer una línea base y crear un sistema "
                "de seguimiento inicial."
            )
        elif not academic_data["has_data"]:
            prompt_parts.append(
                "\n⚠️ No hay datos académicos disponibles. Las recomendaciones se basan únicamente "
                "en los hábitos y percepciones reportadas por el estudiante."
            )
        elif not survey_data["has_data"]:
            prompt_parts.append(
                "\n⚠️ No hay datos de encuesta disponibles. Las recomendaciones se basan únicamente "
                "en el rendimiento académico observado."
            )

        # Casos críticos
        critical_indicators = []
        if academic_data.get("critical_subjects") and len(academic_data["critical_subjects"]) > 3:
            critical_indicators.append("Múltiples materias en situación crítica")
        if survey_data.get("wellness_indicators", {}).get("stress_numeric", 0) >= 3:
            critical_indicators.append("Niveles altos de estrés reportados")
        if survey_data.get("wellness_indicators", {}).get("sleep_quality", 0) < 2:
            critical_indicators.append("Privación de sueño severa")

        if critical_indicators:
            prompt_parts.append("\n🚨 INDICADORES CRÍTICOS:")
            for indicator in critical_indicators:
                prompt_parts.append(f"- {indicator}")

        # 8. Instrucciones específicas para la generación de recomendaciones
        prompt_parts.append(f"\n\n{'='*50}")
        prompt_parts.append("INSTRUCCIONES PARA GENERAR RECOMENDACIONES")
        prompt_parts.append(f"{'='*50}")

        prompt_parts.append(
            "\nBasándote en TODA la información anterior, genera un plan de recomendaciones "
            "integral que debe incluir:"
        )

        prompt_parts.append("\n### 1. EVALUACIÓN GENERAL (2-3 párrafos)")
        prompt_parts.append(
            "- Resumen del estado actual del estudiante\n"
            "- Principales fortalezas identificadas\n"
            "- Áreas críticas que requieren atención inmediata"
        )

        prompt_parts.append("\n### 2. PLAN DE ACCIÓN INMEDIATA (próximas 2 semanas)")
        prompt_parts.append(
            "- 3-5 acciones específicas y realizables\n"
            "- Cada acción debe incluir: qué hacer, cómo hacerlo, frecuencia\n"
            "- Priorizar basándose en los factores de riesgo identificados"
        )

        prompt_parts.append("\n### 3. ESTRATEGIAS A MEDIANO PLAZO (próximo mes)")
        prompt_parts.append(
            "- Establecimiento de rutinas y hábitos\n"
            "- Plan de mejora para materias críticas\n"
            "- Estrategias de bienestar emocional si aplica"
        )

        prompt_parts.append("\n### 4. OBJETIVOS A LARGO PLAZO (próximo trimestre)")
        prompt_parts.append(
            "- Metas académicas medibles y alcanzables\n"
            "- Desarrollo de habilidades de aprendizaje\n"
            "- Mejora continua del bienestar integral"
        )

        prompt_parts.append("\n### 5. RECURSOS Y HERRAMIENTAS ESPECÍFICAS")
        prompt_parts.append(
            "- Recursos digitales apropiados para el nivel del estudiante\n"
            "- Técnicas de estudio adaptadas a su estilo de aprendizaje\n"
            "- Herramientas para las materias críticas identificadas"
        )

        prompt_parts.append("\n### 6. APOYO REQUERIDO")
        prompt_parts.append(
            "- De los profesores (acciones específicas por materia)\n"
            "- De la familia (cómo pueden apoyar en casa)\n"
            "- De la institución (servicios o programas recomendados)"
        )

        prompt_parts.append("\n### 7. SISTEMA DE SEGUIMIENTO")
        prompt_parts.append(
            "- Indicadores clave para monitorear progreso\n"
            "- Frecuencia de evaluación recomendada\n"
            "- Señales de alerta a observar"
        )

        # Consideraciones finales
        prompt_parts.append("\n\n### CRITERIOS IMPORTANTES:")
        prompt_parts.append(
            "- Las recomendaciones deben ser ESPECÍFICAS para este estudiante\n"
            "- Deben ser REALISTAS considerando los recursos disponibles\n"
            "- Deben ser MEDIBLES para evaluar progreso\n"
            "- Deben considerar el CONTEXTO (edad, nivel educativo, circunstancias)\n"
            "- Deben ser POSITIVAS y enfocadas en soluciones\n"
            "- Deben promover la AUTONOMÍA del estudiante"
        )

        # Recordatorio sobre datos faltantes
        if not academic_data["has_data"] or not survey_data["has_data"]:
            prompt_parts.append(
                "\n\n⚠️ IMPORTANTE: Dado que hay datos limitados, incluye en las recomendaciones "
                "la necesidad de completar evaluaciones para tener un panorama más completo."
            )

        return "\n".join(prompt_parts)

    # Métodos auxiliares de mapeo
    def _map_study_hours(self, option: str) -> int:
        """Mapea opciones de horas de estudio a valores numéricos"""
        mapping = {
            "Menos de 1 hora al día": 1,
            "Entre 1 y 2 horas al día": 2,
            "Más de 2 horas al día": 3
        }
        return mapping.get(option, 0)

    def _map_frequency(self, option: str) -> int:
        """Mapea frecuencias a valores numéricos"""
        mapping = {
            "Nunca": 0,
            "A veces": 1,
            "Casi siempre": 2,
            "Siempre": 3
        }
        return mapping.get(option, 0)

    def _map_class_enjoyment(self, option: str) -> int:
        """Mapea gusto por las clases a valores numéricos"""
        mapping = {
            "No me gustan": 0,
            "No mucho": 1,
            "A veces": 2,
            "Sí, mucho": 3
        }
        return mapping.get(option, 0)

    def _map_difficulty(self, option: str) -> int:
        """Mapea dificultad percibida a valores numéricos"""
        mapping = {
            "Muy fáciles": 0,
            "Normales": 1,
            "Difíciles": 2,
            "Muy difíciles": 3
        }
        return mapping.get(option, 0)

    def _map_effort(self, option: str) -> int:
        """Mapea nivel de esfuerzo a valores numéricos"""
        mapping = {
            "Casi nada": 0,
            "Poco": 1,
            "Lo necesario": 2,
            "Mucho": 3
        }
        return mapping.get(option, 0)

    def _map_sleep_hours(self, option: str) -> int:
        """Mapea horas de sueño a valores numéricos"""
        mapping = {
            "Menos de 5 horas": 1,
            "Entre 5 y 7 horas": 2,
            "Más de 7 horas": 3
        }
        return mapping.get(option, 0)

    # Métodos de cálculo auxiliares
    def _calculate_grade_average(self, grades: List[str]) -> float:
        """Calcula el promedio numérico de las calificaciones"""
        if not grades:
            return 0.0

        grade_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'No calificado': 0}
        total = sum(grade_values.get(g, 0) for g in grades)
        return total / len(grades) if grades else 0.0

    def _calculate_student_average(self, academic_data: Dict) -> Optional[float]:
        """Calcula el promedio general del estudiante"""
        all_grades = self._flatten_grades(academic_data)
        if all_grades:
            return self._calculate_grade_average(all_grades)
        return None

    def _flatten_grades(self, academic_data: Dict) -> List[str]:
        """Aplana todas las calificaciones en una lista"""
        grades = []
        for subject_data in academic_data.get("grades_by_subject", {}).values():
            if isinstance(subject_data, dict) and "distribution" in subject_data:
                for grade, count in subject_data["distribution"].items():
                    grades.extend([grade] * count)
        return grades

    def _analyze_performance_trend(self, all_grades: List[Dict]) -> str:
        """Analiza la tendencia del rendimiento académico"""
        if len(all_grades) < 10:
            return "insufficient_data"

        # Dividir en períodos antiguos y recientes
        mid_point = len(all_grades) // 2
        old_grades = all_grades[:mid_point]
        recent_grades = all_grades[mid_point:]

        # Calcular promedios
        old_avg = self._calculate_grade_average([g['grade'] for g in old_grades])
        recent_avg = self._calculate_grade_average([g['grade'] for g in recent_grades])

        # Determinar tendencia
        difference = recent_avg - old_avg
        if difference > 0.3:
            return "improving"
        elif difference < -0.3:
            return "declining"
        else:
            return "stable"

    def _analyze_grade_evolution(self, all_grades: List[Dict]) -> List[Dict]:
        """Analiza la evolución temporal de las calificaciones"""
        evolution = []

        # Agrupar por año y período
        grades_by_time = {}
        for grade in all_grades:
            key = f"{grade['year']} - {grade['period']}"
            if key not in grades_by_time:
                grades_by_time[key] = []
            grades_by_time[key].append(grade['grade'])

        # Calcular estadísticas por período
        for period, grades in sorted(grades_by_time.items()):
            grade_counts = {g: grades.count(g) for g in set(grades)}
            evolution.append({
                'period': period,
                'distribution': grade_counts,
                'average': self._calculate_grade_average(grades),
                'total_grades': len(grades)
            })

        return evolution

    def _calculate_engagement_index(self, survey_data: Dict) -> float:
        """Calcula un índice de compromiso del estudiante"""
        factors = []

        # Participación en clase
        participation = survey_data.get("study_habits", {}).get("participation_level", 0)
        factors.append(participation / 3.0)

        # Búsqueda de ayuda
        help_seeking = survey_data.get("study_habits", {}).get("help_seeking_level", 0)
        factors.append(help_seeking / 3.0)

        # Esfuerzo
        effort = survey_data.get("study_habits", {}).get("effort_numeric", 0)
        factors.append(effort / 3.0)

        # Gusto por las clases
        enjoyment = survey_data.get("self_perception", {}).get("enjoyment_level", 0)
        factors.append(enjoyment / 3.0)

        if factors:
            return round(sum(factors) / len(factors), 2)
        return 0.0

    def _calculate_wellness_index(self, survey_data: Dict) -> float:
        """Calcula un índice de bienestar del estudiante"""
        factors = []

        # Sueño (invertir escala)
        sleep = survey_data.get("wellness_indicators", {}).get("sleep_quality", 0)
        factors.append(sleep / 3.0)

        # Estrés (invertir escala)
        stress = survey_data.get("wellness_indicators", {}).get("stress_numeric", 0)
        factors.append((3 - stress) / 3.0)

        # Actividades extracurriculares
        extracurricular = 1.0 if survey_data.get("wellness_indicators", {}).get("has_extracurricular") else 0.5
        factors.append(extracurricular)

        if factors:
            return round(sum(factors) / len(factors), 2)
        return 0.0

    def _calculate_resource_index(self, survey_data: Dict) -> float:
        """Calcula un índice de utilización de recursos"""
        factors = []

        # Cantidad de recursos utilizados
        resource_count = len(survey_data.get("resources", []))
        factors.append(min(resource_count / 5.0, 1.0))  # Normalizar a máximo 5 recursos

        # Uso de tecnología
        tech_use = survey_data.get("learning_preferences", {}).get("tech_level", 0)
        factors.append(tech_use / 3.0)

        # Acceso a internet
        internet = 1.0 if survey_data.get("learning_preferences", {}).get("has_internet") else 0.0
        factors.append(internet)

        if factors:
            return round(sum(factors) / len(factors), 2)
        return 0.0

    def _prioritize_recommendations(self, patterns: Dict) -> List[str]:
        """Prioriza las recomendaciones basándose en los patrones encontrados"""
        priorities = []

        # Alta prioridad: factores de riesgo severos
        high_risk_factors = [f for f in patterns["risk_factors"] if f["severity"] == "high"]
        if high_risk_factors:
            if any("high_failure_rate" in f["factor"] for f in high_risk_factors):
                priorities.append("academic_recovery")
            if any("high_stress" in f["factor"] for f in high_risk_factors):
                priorities.append("emotional_support")

        # Media prioridad: factores de riesgo moderados
        medium_risk_factors = [f for f in patterns["risk_factors"] if f["severity"] == "medium"]
        if medium_risk_factors:
            if any("insufficient_study_time" in f["factor"] for f in medium_risk_factors):
                priorities.append("study_habits")
            if any("low_engagement" in f["factor"] for f in medium_risk_factors):
                priorities.append("engagement_strategies")

        # Agregar áreas de intervención
        for area in patterns["intervention_areas"]:
            if area not in priorities:
                priorities.append(area)

        return priorities[:5]  # Limitar a 5 prioridades principales