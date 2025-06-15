from app.api.v1.students.services.get_student_data import get_student_data
from app.api.v1.ml.services.data_processing import prepare_data, encode_data, prepare_data_with_missing
from app.api.v1.ml.services.ml_models import train_risk_model, find_behavior_patterns, train_hybrid_model, predict_student_risk
from app.api.v1.ml.services.recommendation import generate_recommendations_based_on_risk
import pandas as pd
import numpy as np

# def full_analysis_pipeline():
#     """Pipeline completo de análisis"""
#     # 1. Obtener datos
#     notas_df, encuestas_df = get_student_data()

#     # 2. Preparar datos
#     full_data = prepare_data(notas_df, encuestas_df)
#     df_encoded, label_encoder = encode_data(full_data)

#     # 3. Entrenar modelo de riesgo
#     risk_model = train_risk_model(df_encoded)

#     # 4. Encontrar patrones de comportamiento
#     behavior_patterns = find_behavior_patterns(full_data)

#     # 5. Generar recomendaciones para cada alumno
#     results = []
#     for _, student in full_data.iterrows():
#         # Predecir riesgo
#         student_data = student.drop(['riesgo']).to_frame().T
#         student_encoded, _ = encode_data(student_data)
#         features = student_encoded.drop(['alumno_id', 'nombre_completo', 'riesgo', 'riesgo_encoded'], axis=1, errors='ignore')
#         risk_level = predict_risk(risk_model, label_encoder, features)[0]

#         # Generar recomendaciones
#         recommendations = generate_personalized_recommendations(student, risk_level, behavior_patterns)

#         results.append({
#             'alumno_id': student['alumno_id'],
#             'nombre_completo': student['nombre_completo'],
#             'riesgo_predicho': risk_level,
#             'recomendaciones': recommendations
#             # Agregar otras id del alumno asociado
#         })

#     return pd.DataFrame(results)

# Ejecutar el análisis completo
# results_df = full_analysis_pipeline()
# print(results_sdf)


def full_analysis_pipeline():
    """Pipeline de análisis robusto que maneja datos incompletos"""
    # 1. Obtener datos
    notas_df, encuestas_df = get_student_data()

    # 2. Preparar datos manejando valores faltantes
    full_data = prepare_data_with_missing(notas_df, encuestas_df)

    # 3. Entrenar modelos híbridos
    models = train_hybrid_model(full_data)

    # 4. Generar recomendaciones para cada alumno
    results = []
    for _, student in full_data.iterrows():
        # Predecir riesgo
        risk_level = predict_student_risk(models, student)

        # Generar recomendaciones basadas en el riesgo y datos disponibles
        recommendations = generate_recommendations_based_on_risk(
            student,
            risk_level,
            has_survey=not pd.isna(student.get(
                '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?', np.nan
            ))
        )

        results.append({
            'alumno_id': student['alumno_id'],
            'nombre_completo': next((n for n in [student.get('nombre_completo')] if n is not None), 'Desconocido'),
            'riesgo_predicho': risk_level,
            'tiene_encuesta': not pd.isna(student.get(
                '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?', np.nan
            )),
            'recomendaciones': recommendations
        })

    return pd.DataFrame(results)

def generate_recommendations_based_on_risk_2(student, risk_level, has_survey):
    """Genera recomendaciones apropiadas según los datos disponibles"""
    if has_survey:
        # Recomendaciones detalladas basadas en encuesta
        return (
            f"Recomendaciones para {student.get('nombre_completo', 'el estudiante')}:\n"
            f"- Nivel de riesgo: {risk_level}\n"
            f"- Basado en su desempeño académico y hábitos de estudio reportados:\n"
            f"  1. Considere {'aumentar' if risk_level in ['Alto', 'Medio'] else 'mantener'} "
            "el tiempo de estudio fuera del aula\n"
            f"  2. {'Busque ayuda docente con mayor frecuencia' if risk_level == 'Alto' else 'Continúe con su actual nivel de apoyo'}\n"
            f"  3. {'Participe más en clase' if student.get('¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?') in ['Nunca', 'A veces'] else 'Mantenga su participación activa'}"
        )
    else:
        # Recomendaciones genéricas basadas solo en riesgo académico
        return (
            f"Recomendaciones generales para {student.get('nombre_completo', 'el estudiante')}:\n"
            f"- Nivel de riesgo: {risk_level}\n"
            f"- Basado en su desempeño académico:\n"
            f"  1. {'Necesita intervención urgente' if risk_level == 'Alto' else 'Beneficiaría de apoyo adicional' if risk_level == 'Medio' else 'Continúe con buen trabajo'}\n"
            "  2. Recomendamos completar la encuesta de hábitos de estudio para recomendaciones personalizadas"
        )