# app/api/v1/ml/services/recommendation_service.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import logging
from datetime import datetime

from app.api.v1.students.models import (
    Alumno, Nota, Encuesta, RespuestaEncuesta,
     HistorialAcademico, RecommendationResult
)

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.risk_model = None
        self.label_encoder = LabelEncoder()

    def process_all_students(self) -> Dict:
        """Procesa todos los alumnos y genera recomendaciones"""
        try:
            # 1. Obtener todos los alumnos
            all_students = self.db.query(Alumno).all()

            # 2. Preparar datos para análisis
            student_data = self._prepare_student_data(all_students)

            # 3. Entrenar modelo de riesgo
            self._train_risk_model(student_data)

            # 4. Encontrar patrones con Apriori
            patterns = self._find_patterns(student_data)

            # 5. Generar recomendaciones para cada alumno
            results = []
            for student in all_students:
                recommendation = self._generate_student_recommendation(
                    student, patterns
                )
                results.append(recommendation)

            return {
                "status": "success",
                "total_students": len(all_students),
                "recommendations_generated": len(results),
                "patterns_found": len(patterns) if patterns is not None else 0
            }

        except Exception as e:
            logger.error(f"Error processing students: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _prepare_student_data(self, students: List[Alumno]) -> pd.DataFrame:
        """Prepara los datos de todos los estudiantes en un DataFrame"""
        data = []

        for student in students:
            student_info = {
                'student_id': student.id,
                'nombre': student.nombre_completo,
                'edad': student.edad or 0,
                'genero': student.genero,
                'tiene_encuesta': False,
                'tiene_notas': False
            }

            # Obtener datos de notas
            grades_data = self._get_student_grades(student.id)
            student_info.update(grades_data)

            # Obtener datos de encuesta
            survey_data = self._get_student_survey(student.id)
            student_info.update(survey_data)

            # Calcular nivel de riesgo basado en datos disponibles
            student_info['risk_level'] = self._calculate_initial_risk(student_info)

            data.append(student_info)

        return pd.DataFrame(data)

    def _get_student_grades(self, student_id: int) -> Dict:
        """Obtiene y procesa las notas del estudiante"""
        grades_info = {
            'tiene_notas': False,
            'promedio_a': 0,
            'promedio_b': 0,
            'promedio_c': 0,
            'promedio_d': 0,
            'no_calificados': 0,
            'total_notas': 0,
            'materias_criticas': []
        }

        # Obtener historial académico
        historiales = self.db.query(HistorialAcademico).filter(
            HistorialAcademico.alumno_id == student_id
        ).all()

        if not historiales:
            return grades_info

        # Obtener todas las notas
        notas = []
        for historial in historiales:
            historial_notas = self.db.query(Nota).filter(
                Nota.historial_id == historial.id
            ).all()
            notas.extend(historial_notas)

        if not notas:
            return grades_info

        grades_info['tiene_notas'] = True
        grades_info['total_notas'] = len(notas)

        # Contar notas por nivel
        nivel_count = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'No calificado': 0}
        materias_bajas = {}

        for nota in notas:
            if nota.nivel_logro:
                nivel = nota.nivel_logro.valor
                if nivel in nivel_count:
                    nivel_count[nivel] += 1

                # Identificar materias con bajo rendimiento
                if nivel in ['C', 'D']:
                    materia_nombre = nota.materia.nombre
                    if materia_nombre not in materias_bajas:
                        materias_bajas[materia_nombre] = 0
                    materias_bajas[materia_nombre] += 1

        # Calcular promedios
        total = sum(nivel_count.values())
        if total > 0:
            grades_info['promedio_a'] = nivel_count['A'] / total
            grades_info['promedio_b'] = nivel_count['B'] / total
            grades_info['promedio_c'] = nivel_count['C'] / total
            grades_info['promedio_d'] = nivel_count['D'] / total
            grades_info['no_calificados'] = nivel_count['No calificado'] / total

        # Identificar materias críticas (más del 50% de notas C o D)
        for materia, count in materias_bajas.items():
            total_materia = sum(1 for n in notas if n.materia.nombre == materia)
            if count / total_materia > 0.5:
                grades_info['materias_criticas'].append(materia)

        return grades_info

    def _get_student_survey(self, student_id: int) -> Dict:
        """Obtiene y procesa los datos de encuesta del estudiante"""
        survey_info = {
            'tiene_encuesta': False,
            'horas_estudio': 0,
            'participacion_clase': 0,
            'pide_ayuda': 0,
            'gusto_clases': 0,
            'dificultad_percibida': 0,
            'esfuerzo': 0,
            'usa_tecnologia': 0,
            'tiene_internet': 0,
            'actividades_extra': 0,
            'horas_sueno': 0,
            'nivel_estres': 0,
            'recursos_estudio': []
        }

        # Obtener encuesta más reciente
        encuesta = self.db.query(Encuesta).filter(
            Encuesta.alumno_id == student_id
        ).order_by(Encuesta.fecha.desc()).first()

        if not encuesta:
            return survey_info

        survey_info['tiene_encuesta'] = True

        # Procesar respuestas
        respuestas = self.db.query(RespuestaEncuesta).filter(
            RespuestaEncuesta.encuesta_id == encuesta.id
        ).all()

        for respuesta in respuestas:
            pregunta_texto = respuesta.pregunta.pregunta
            opcion_texto = respuesta.opcion.opcion

            # Mapear respuestas a valores numéricos
            if "tiempo dedicas al estudio" in pregunta_texto:
                survey_info['horas_estudio'] = self._map_study_hours(opcion_texto)
            elif "participar en clase" in pregunta_texto:
                survey_info['participacion_clase'] = self._map_frequency(opcion_texto)
            elif "Pides ayuda" in pregunta_texto:
                survey_info['pide_ayuda'] = self._map_frequency(opcion_texto)
            elif "te gustan las clases" in pregunta_texto:
                survey_info['gusto_clases'] = self._map_class_enjoyment(opcion_texto)
            elif "dificultad de las materias" in pregunta_texto:
                survey_info['dificultad_percibida'] = self._map_difficulty(opcion_texto)
            elif "te esfuerzas" in pregunta_texto:
                survey_info['esfuerzo'] = self._map_effort(opcion_texto)
            elif "recursos utilizas" in pregunta_texto:
                survey_info['recursos_estudio'].append(opcion_texto)
            elif "acceso a internet" in pregunta_texto:
                survey_info['tiene_internet'] = 1 if opcion_texto == "Sí" else 0
            elif "utilizas la tecnología" in pregunta_texto:
                survey_info['usa_tecnologia'] = self._map_frequency(opcion_texto)
            elif "actividades extracurriculares" in pregunta_texto:
                survey_info['actividades_extra'] = 1 if opcion_texto == "Sí" else 0
            elif "horas duermes" in pregunta_texto:
                survey_info['horas_sueno'] = self._map_sleep_hours(opcion_texto)
            elif "estrés o ansiedad" in pregunta_texto:
                survey_info['nivel_estres'] = self._map_frequency(opcion_texto)

        return survey_info

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

    def _calculate_initial_risk(self, student_info: Dict) -> str:
        """Calcula el nivel de riesgo inicial basado en datos disponibles"""
        risk_score = 0
        factors_count = 0

        # Factores de notas (si están disponibles)
        if student_info['tiene_notas']:
            factors_count += 1
            if student_info['promedio_d'] > 0.3:
                risk_score += 3
            elif student_info['promedio_c'] > 0.4:
                risk_score += 2
            elif student_info['promedio_b'] > 0.5:
                risk_score += 1

            # Penalización por materias críticas
            if len(student_info['materias_criticas']) > 2:
                risk_score += 2
            elif len(student_info['materias_criticas']) > 0:
                risk_score += 1

        # Factores de encuesta (si están disponibles)
        if student_info['tiene_encuesta']:
            factors_count += 1

            # Horas de estudio
            if student_info['horas_estudio'] < 2:
                risk_score += 1

            # Participación y ayuda
            if student_info['participacion_clase'] < 2:
                risk_score += 1
            if student_info['pide_ayuda'] < 2:
                risk_score += 1

            # Esfuerzo y gusto
            if student_info['esfuerzo'] < 2:
                risk_score += 2
            if student_info['gusto_clases'] < 2:
                risk_score += 1

            # Factores de salud
            if student_info['horas_sueno'] < 2:
                risk_score += 1
            if student_info['nivel_estres'] > 2:
                risk_score += 1

        # Normalizar el puntaje de riesgo
        if factors_count > 0:
            normalized_score = risk_score / (factors_count * 5)  # Max 5 puntos por factor

            if normalized_score > 0.6:
                return "Alto"
            elif normalized_score > 0.3:
                return "Medio"
            else:
                return "Bajo"
        else:
            return "Desconocido"

    def _train_risk_model(self, data: pd.DataFrame):
        """Entrena el modelo de Random Forest para predecir riesgo"""
        # Filtrar solo estudiantes con datos suficientes
        train_data = data[
            (data['tiene_notas'] == True) | (data['tiene_encuesta'] == True)
        ].copy()

        if len(train_data) < 10:
            logger.warning("Insufficient data for training risk model")
            return

        # Preparar características
        feature_columns = [
            'edad', 'promedio_a', 'promedio_b', 'promedio_c', 'promedio_d',
            'horas_estudio', 'participacion_clase', 'pide_ayuda',
            'gusto_clases', 'esfuerzo', 'usa_tecnologia', 'tiene_internet',
            'actividades_extra', 'horas_sueno', 'nivel_estres'
        ]

        # Llenar valores faltantes
        for col in feature_columns:
            if col in train_data.columns:
                train_data[col] = train_data[col].fillna(0)
            else:
                train_data[col] = 0

        X = train_data[feature_columns]
        y = train_data['risk_level']

        # Codificar etiquetas
        y_encoded = self.label_encoder.fit_transform(y)

        # Dividir en entrenamiento y prueba
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )

        # Entrenar modelo
        self.risk_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.risk_model.fit(X_train, y_train)

        # Evaluar modelo
        accuracy = self.risk_model.score(X_test, y_test)
        logger.info(f"Risk model trained with accuracy: {accuracy:.2f}")

    def _find_patterns(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Encuentra patrones de comportamiento usando Apriori"""
        try:
            # Preparar datos para Apriori
            apriori_data = []

            for _, row in data.iterrows():
                student_patterns = []

                # Patrones de rendimiento
                if row['tiene_notas']:
                    if row['promedio_a'] > 0.5:
                        student_patterns.append('Alto_Rendimiento')
                    elif row['promedio_d'] > 0.3:
                        student_patterns.append('Bajo_Rendimiento')
                    else:
                        student_patterns.append('Rendimiento_Medio')

                # Patrones de estudio
                if row['tiene_encuesta']:
                    if row['horas_estudio'] >= 2:
                        student_patterns.append('Estudia_Mucho')
                    else:
                        student_patterns.append('Estudia_Poco')

                    if row['participacion_clase'] >= 2:
                        student_patterns.append('Participa_Activamente')

                    if row['esfuerzo'] >= 2:
                        student_patterns.append('Alto_Esfuerzo')

                    if row['nivel_estres'] >= 2:
                        student_patterns.append('Alto_Estres')

                    if row['horas_sueno'] < 2:
                        student_patterns.append('Poco_Sueno')

                apriori_data.append(student_patterns)

            # Convertir a formato one-hot
            unique_items = set(item for sublist in apriori_data for item in sublist)
            encoded_data = pd.DataFrame(
                [[item in transaction for item in unique_items] for transaction in apriori_data],
                columns=list(unique_items)
            )

            # Aplicar Apriori
            if len(encoded_data) > 5:
                frequent_itemsets = apriori(
                    encoded_data,
                    min_support=0.1,
                    use_colnames=True
                )

                if len(frequent_itemsets) > 0:
                    rules = association_rules(
                        frequent_itemsets,
                        metric="confidence",
                        min_threshold=0.5
                    )
                    return rules

            return None

        except Exception as e:
            logger.error(f"Error finding patterns: {str(e)}")
            return None

    def _generate_student_recommendation(
        self,
        student: Alumno,
        patterns: Optional[pd.DataFrame]
    ) -> Dict:
        """Genera recomendación personalizada para un estudiante"""
        try:
            # Obtener datos del estudiante
            student_data = {
                'student_id': student.id,
                'nombre': student.nombre_completo,
                'edad': student.edad or 0,
                'genero': student.genero
            }

            # Obtener datos académicos y de encuesta
            grades_data = self._get_student_grades(student.id)
            survey_data = self._get_student_survey(student.id)
            student_data.update(grades_data)
            student_data.update(survey_data)

            # Predecir nivel de riesgo
            if self.risk_model and (student_data['tiene_notas'] or student_data['tiene_encuesta']):
                risk_level = self._predict_risk(student_data)
            else:
                risk_level = self._calculate_initial_risk(student_data)

            # Generar recomendaciones basadas en datos disponibles
            recommendations = self._create_recommendations(
                student_data, risk_level, patterns
            )

            # Guardar en base de datos
            result = RecommendationResult(
                alumno_id=student.id,
                riesgo_predicho=risk_level,
                recomendaciones=recommendations
            )
            self.db.add(result)
            self.db.commit()

            return {
                "student_id": student.id,
                "risk_level": risk_level,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"Error generating recommendation for student {student.id}: {str(e)}")
            return {
                "student_id": student.id,
                "risk_level": "Error",
                "recommendations": "No se pudo generar recomendación"
            }

    def _predict_risk(self, student_data: Dict) -> str:
        """Predice el nivel de riesgo usando el modelo entrenado"""
        feature_columns = [
            'edad', 'promedio_a', 'promedio_b', 'promedio_c', 'promedio_d',
            'horas_estudio', 'participacion_clase', 'pide_ayuda',
            'gusto_clases', 'esfuerzo', 'usa_tecnologia', 'tiene_internet',
            'actividades_extra', 'horas_sueno', 'nivel_estres'
        ]

        # Crear un DataFrame con los nombres de las columnas para evitar warnings
        features_dict = {}
        for col in feature_columns:
            features_dict[col] = [student_data.get(col, 0)]

        features_df = pd.DataFrame(features_dict)

        prediction = self.risk_model.predict(features_df)[0]
        return self.label_encoder.inverse_transform([prediction])[0]

    def _create_recommendations(
        self,
        student_data: Dict,
        risk_level: str,
        patterns: Optional[pd.DataFrame]
    ) -> str:
        """Crea recomendaciones personalizadas basadas en los datos del estudiante"""
        recommendations = []

        # Encabezado con nivel de riesgo
        recommendations.append(f"NIVEL DE RIESGO: {risk_level}")
        recommendations.append("\nRECOMENDACIONES PERSONALIZADAS:")

        # Recomendaciones basadas en notas
        if student_data['tiene_notas']:
            if student_data['promedio_d'] > 0.2:
                recommendations.append(
                    "\n📚 RENDIMIENTO ACADÉMICO:\n"
                    "- Se detecta un alto porcentaje de calificaciones D. "
                    "Es urgente implementar un plan de recuperación académica."
                )

            if student_data['materias_criticas']:
                materias = ", ".join(student_data['materias_criticas'])
                recommendations.append(
                    f"- Materias que requieren atención inmediata: {materias}. "
                    "Se recomienda tutorías específicas en estas áreas."
                )

        # Recomendaciones basadas en encuesta
        if student_data['tiene_encuesta']:
            # Hábitos de estudio
            if student_data['horas_estudio'] < 2:
                recommendations.append(
                    "\n⏰ HÁBITOS DE ESTUDIO:\n"
                    "- Aumentar el tiempo de estudio diario a al menos 2 horas. "
                    "Establecer un horario fijo ayudará a crear el hábito."
                )

            # Participación
            if student_data['participacion_clase'] < 2 or student_data['pide_ayuda'] < 2:
                recommendations.append(
                    "\n🙋 PARTICIPACIÓN:\n"
                    "- Fomentar la participación activa en clase. "
                    "No dudar en pedir ayuda cuando algo no se entiende."
                )

            # Salud y bienestar
            if student_data['horas_sueno'] < 2:
                recommendations.append(
                    "\n😴 SALUD:\n"
                    "- Es fundamental dormir al menos 7-8 horas diarias. "
                    "El descanso adecuado mejora significativamente el rendimiento."
                )

            if student_data['nivel_estres'] > 2:
                recommendations.append(
                    "- El alto nivel de estrés detectado puede afectar el aprendizaje. "
                    "Considerar técnicas de relajación o apoyo psicológico."
                )

            # Recursos tecnológicos
            if student_data['usa_tecnologia'] < 2 and student_data['tiene_internet']:
                recommendations.append(
                    "\n💻 TECNOLOGÍA:\n"
                    "- Aprovechar más los recursos tecnológicos disponibles. "
                    "Hay excelentes plataformas educativas gratuitas en línea."
                )

        # Recomendaciones basadas en patrones
        if patterns is not None and len(patterns) > 0:
            relevant_patterns = self._find_relevant_patterns(student_data, patterns)
            if relevant_patterns:
                recommendations.append(
                    "\n🔍 BASADO EN PATRONES SIMILARES:\n" + relevant_patterns
                )

        # Si no hay datos suficientes
        if not student_data['tiene_notas'] and not student_data['tiene_encuesta']:
            recommendations.append(
                "\n⚠️ DATOS INSUFICIENTES:\n"
                "- No se cuenta con suficiente información para una recomendación completa. "
                "Se sugiere completar la evaluación académica y la encuesta de hábitos."
            )

        return "\n".join(recommendations)

    def _find_relevant_patterns(
        self,
        student_data: Dict,
        patterns: pd.DataFrame
    ) -> str:
        """Encuentra patrones relevantes para el estudiante"""
        relevant_recommendations = []

        # Identificar características del estudiante
        student_characteristics = []
        if student_data['promedio_d'] > 0.3:
            student_characteristics.append('Bajo_Rendimiento')
        if student_data['horas_estudio'] < 2:
            student_characteristics.append('Estudia_Poco')
        if student_data['nivel_estres'] >= 2:
            student_characteristics.append('Alto_Estres')

        # Buscar reglas relevantes
        for _, rule in patterns.iterrows():
            antecedents = list(rule['antecedents'])
            consequents = list(rule['consequents'])

            # Si el estudiante tiene las características antecedentes
            if any(char in antecedents for char in student_characteristics):
                # Y las consecuencias son positivas
                if 'Alto_Rendimiento' in consequents:
                    relevant_recommendations.append(
                        f"- Estudiantes con características similares mejoran "
                        f"cuando: {', '.join(antecedents)}"
                    )

        return "\n".join(relevant_recommendations[:3])  # Limitar a 3 patrones