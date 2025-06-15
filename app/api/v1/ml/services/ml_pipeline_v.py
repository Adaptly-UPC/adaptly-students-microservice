from app.api.v1.students.services.get_student_data import get_student_data
from app.api.v1.ml.services.data_processing import safe_prepare_data, encode_data, prepare_data_with_missing
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
# import OneHotEncoder
from sklearn.preprocessing import OneHotEncoder
import numpy as np
import pandas as pd
import requests

def full_analysis_pipeline():
    """Pipeline de análisis robusto que maneja datos incompletos"""
    try:
        # 1. Obtener datos con manejo de errores
        try:
            notas_df, encuestas_df = get_student_data()
        except Exception as e:
            print(f"Error al obtener datos: {e}")
            raise

        # 2. Validar datos mínimos
        if notas_df.empty:
            raise ValueError("No hay datos académicos disponibles para análisis")

        # 3. Preparar datos con enfoque resiliente
        full_data = safe_prepare_data(notas_df, encuestas_df)
        print(f"DATA PREPARED: {full_data.shape}")
        # 4. Análisis descriptivo básico
        print("\nResumen de datos:")
        print(f"- Total alumnos: {len(full_data['alumno_id'].unique())}")
        print(f"- Alumnos con encuestas: {full_data.dropna(subset=[col for col in full_data.columns if '¿' in col]).shape[0]}")
        print(f"- Distribución de riesgo inicial: {full_data['riesgo'].value_counts().to_dict()}")

        # 5. Entrenar modelos según datos disponibles
        models = {}
        label_encoder = LabelEncoder()
        full_data['riesgo_encoded'] = label_encoder.fit_transform(full_data['riesgo'])
        models['label_encoder'] = label_encoder

        # Modelo académico básico (siempre disponible)
        academic_cols = [
            c for c in [
                'logro_promedio', 'logro_minimo', 'logro_maximo',
                'logro_std', 'materias_diferentes', 'bimestres_evaluados'
            ] if c in full_data.columns
        ]

        if academic_cols:
            X_academic = full_data[academic_cols].fillna(0)
            y_academic = full_data['riesgo_encoded']

            models['academic_model'] = RandomForestClassifier(
                n_estimators=50,  # Reducido para mayor velocidad
                random_state=42
            )
            models['academic_model'].fit(X_academic, y_academic)

            # Evaluación rápida
            print("\nEvaluación modelo académico:")
            print(pd.crosstab(
                y_academic,
                models['academic_model'].predict(X_academic),
                rownames=['Real'],
                colnames=['Predicho']
            ))

        # Modelo completo solo si hay suficientes encuestas
        survey_cols = [col for col in full_data.columns if '¿' in col]
        if len(survey_cols) > 3 and full_data[survey_cols].notna().sum().min() > 10:
            try:
                # Codificar variables categóricas de encuestas
                encoder = OneHotEncoder(handle_unknown='ignore')
                X_survey = encoder.fit_transform(full_data[survey_cols].fillna('No respondió'))

                # Combinar con características académicas
                if academic_cols:
                    X_full = np.hstack([X_academic.values, X_survey.toarray()])
                else:
                    X_full = X_survey.toarray()

                models['full_model'] = RandomForestClassifier(
                    n_estimators=50,
                    random_state=42
                )
                models['full_model'].fit(X_full, full_data['riesgo_encoded'])
                models['survey_encoder'] = encoder

                print("\nModelo completo con encuestas entrenado exitosamente")
            except Exception as e:
                print(f"\nNo se pudo entrenar modelo completo: {str(e)}")
                models['full_model'] = None
        else:
            models['full_model'] = None
            print("\nInsuficientes datos de encuestas para modelo completo")

        # 6. Generar recomendaciones para cada alumno
        results = []
        for _, student in full_data.iterrows():
            try:
                # Predicción de riesgo
                risk_level = predict_student_risk_v2(models, student)

                # Generar recomendaciones según datos disponibles
                has_survey = any(not pd.isna(student.get(col, np.nan)) for col in survey_cols)
                rec = generate_recommendations_v2(student, risk_level, has_survey)

                results.append({
                    'alumno_id': student['alumno_id'],
                    'nombre_completo': student.get('nombre_completo', 'N/A'),
                    'riesgo_predicho': risk_level,
                    'tiene_encuesta': has_survey,
                    'recomendaciones': rec,
                    'logro_promedio': student.get('logro_promedio', np.nan),
                    'modelo_usado': 'completo' if has_survey and models.get('full_model') else 'académico'
                })
            except Exception as e:
                print(f"Error procesando alumno {student.get('alumno_id')}: {str(e)}")
                continue

        return pd.DataFrame(results)

    except Exception as e:
        print(f"Error crítico en el pipeline: {str(e)}")
        return pd.DataFrame()  # DataFrame vacío para manejo elegante

def predict_student_risk_v2(models, student_data):
    """Versión mejorada de predicción de riesgo"""
    # Datos académicos siempre disponibles
    academic_features = [
        student_data.get(col, 0) for col in [
            'logro_promedio', 'logro_minimo', 'logro_maximo',
            'logro_std', 'materias_diferentes', 'bimestres_evaluados'
        ]
    ]

    # Intentar usar modelo completo si está disponible y el alumno tiene encuesta
    survey_cols = [col for col in student_data.index if '¿' in str(col)]
    has_survey = any(not pd.isna(student_data.get(col, np.nan)) for col in survey_cols)

    if has_survey and models.get('full_model'):
        try:
            # Codificar datos de encuesta
            survey_data = [student_data.get(col, 'No respondió') for col in models['survey_encoder'].feature_names_in_]
            survey_encoded = models['survey_encoder'].transform([survey_data])

            # Combinar características
            X = np.hstack([[academic_features], survey_encoded.toarray()])

            # Predecir
            pred = models['full_model'].predict(X)
            return models['label_encoder'].inverse_transform(pred)[0]
        except:
            pass  # Si falla, continuar con modelo académico

    # Usar modelo académico como respaldo
    if models.get('academic_model'):
        pred = models['academic_model'].predict([academic_features])
        return models['label_encoder'].inverse_transform(pred)[0]

    # Respaldo final: usar el riesgo calculado directamente
    return student_data.get('riesgo', 'Medio')  # Valor por defecto

# def generate_recommendations_v2(student, risk_level, has_survey):
#     """Genera recomendaciones adaptativas"""
#     base_rec = [
#         f"Alumno: {student.get('nombre_completo', 'N/A')}",
#         f"Nivel de riesgo: {risk_level}",
#         f"Puntaje promedio: {student.get('logro_promedio', 'ND'):.2f}"
#     ]

#     risk_specific = {
#         'Alto': [
#             "Recomendación prioritaria: necesita intervención inmediata",
#             "Sugerencia: programar reunión con el equipo docente",
#             "Acción: evaluar necesidades de apoyo adicional"
#         ],
#         'Medio': [
#             "Recomendación: monitoreo continuo",
#             "Sugerencia: reforzar áreas con bajo desempeño",
#             "Acción: asignar tutorías focalizadas"
#         ],
#         'Bajo': [
#             "Recomendación: mantener buen desempeño",
#             "Sugerencia: ofrecer actividades de enriquecimiento",
#             "Acción: reconocer logros académicos"
#         ]
#     }

#     if has_survey:
#         # Agregar recomendaciones basadas en encuesta
#         survey_based = []
#         if student.get('¿Cuánto tiempo dedicas al estudio fuera del horario escolar?') == 'Menos de 1 hora al día':
#             survey_based.append("Incrementar tiempo de estudio fuera del aula")
#         if student.get('¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?') in ['Casi siempre', 'Siempre']:
#             survey_based.append("Implementar técnicas de manejo de estrés")

#         if survey_based:
#             base_rec.append("\nRecomendaciones basadas en encuesta:")
#             base_rec.extend(survey_based)

#     base_rec.append("\nRecomendaciones generales:")
#     base_rec.extend(risk_specific.get(risk_level, []))

#     return "\n- ".join(base_rec)


def generate_recommendation(context):
    """Genera una recomendación personalizada usando la API de DeepSeek"""
    prompt = f"""
    Eres un experto en educación con amplia experiencia en análisis de desempeño estudiantil.
    Genera recomendaciones personalizadas basadas en los siguientes datos del alumno:

    Contexto:
    {context}

    Instrucciones:
    1. Analiza el perfil académico y conductual del alumno
    2. Identifica 3 áreas clave de oportunidad
    3. Propone recomendaciones específicas y accionables
    4. Usa un tono motivador y constructivo
    5. Limita la respuesta a 250 palabras máximo
    6. Estructura la respuesta en: diagnóstico, recomendaciones y recursos sugeridos

    Respuesta:
    """
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un tutor educativo experto que genera recomendaciones personalizadas para estudiantes."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    api_key = "sk-f74854c412394337b01533c09eb03fd8"

    base_url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(base_url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

def generate_recommendations_v2(student, risk_level, has_survey):
    """Genera recomendaciones personalizadas usando IA generativa"""
    # Construir contexto estructurado para la IA
    context = f"""
    ## Información Básica:
    - Nombre: {student.get('nombre_completo', 'N/A')}
    - Edad: {student.get('edad', 'No especificada')}
    - Género: {student.get('genero', 'No especificado')}

    ## Desempeño Académico:
    - Nivel de riesgo: {risk_level}
    - Puntaje promedio: {student.get('logro_promedio', 'ND'):.2f}
    - Materias con mejor desempeño: {student.get('mejores_materias', 'No disponible')}
    - Materias con mayor dificultad: {student.get('materias_dificiles', 'No disponible')}

    ## Hábitos de Estudio:"""

    # Agregar datos de encuesta si están disponibles
    if has_survey:
        context += f"""
        - Tiempo de estudio fuera de clase: {student.get('¿Cuánto tiempo dedicas al estudio fuera del horario escolar?', 'No reportado')}
        - Participación en clase: {student.get('¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?', 'No reportado')}
        - Solicitud de ayuda: {student.get('¿Pides ayuda cuando no entiendes un tema?', 'No reportado')}
        - Uso de tecnología: {student.get('¿Cuánto utilizas la tecnología para aprender?', 'No reportado')}
        - Horas de sueño: {student.get('¿Cuántas horas duermes en promedio por noche?', 'No reportado')}
        - Nivel de estrés: {student.get('¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?', 'No reportado')}"""
    else:
        context += "\n    - No se cuenta con datos de hábitos de estudio (encuesta no disponible)"

    # Generar recomendación con DeepSeek
    try:
        recommendation = generate_recommendation(context)
        return recommendation
    except Exception as e:
        print(f"Error al generar recomendación con IA: {str(e)}")
        # Recomendación de respaldo
        return f"""Recomendaciones para {student.get('nombre_completo', 'el estudiante')}:
        - Nivel de riesgo: {risk_level}
        - Acciones sugeridas: Consulte con el departamento de orientación educativa
        para obtener recomendaciones personalizadas."""