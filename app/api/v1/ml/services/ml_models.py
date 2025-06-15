from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from mlxtend.frequent_patterns import apriori, association_rules
import random
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

def train_risk_model(df_encoded):
    """Entrena un modelo Random Forest para predecir riesgo académico"""
    # Separar características y objetivo
    X = df_encoded.drop(['alumno_id', 'nombre_completo', 'riesgo', 'riesgo_encoded'], axis=1, errors='ignore')
    y = df_encoded['riesgo_encoded']

    # Dividir en entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Entrenar el modelo
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluar el modelo
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=['Bajo', 'Medio', 'Alto']))

    return model

def predict_risk(model, label_encoder, new_student_data):
    """Predice el riesgo para un nuevo alumno"""
    prediction = model.predict(new_student_data)
    return label_encoder.inverse_transform(prediction)



def find_behavior_patterns(df):
    """Encuentra patrones de comportamiento usando Apriori"""
    # Preparar datos para Apriori (solo respuestas de encuestas)
    survey_data = df[[
        '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?',
        '¿Sueles participar en clase respondiendo preguntas o haciendo comentarios?',
        '¿Pides ayuda cuando no entiendes un tema?',
        'En general, ¿te gustan las clases?',
        '¿Cómo calificas la dificultad de las materias en general?',
        '¿Cuánto te esfuerzas en las tareas y exámenes?',
        '¿Tienes acceso a internet en casa?',
        '¿Cuánto utilizas la tecnología para aprender?',
        '¿Participas en actividades extracurriculares (deporte, arte, clubes)?',
        '¿Cuántas horas duermes en promedio por noche?',
        '¿Sientes estrés o ansiedad cuando tienes exámenes o tareas importantes?'
    ]]

    # Convertir a formato one-hot
    survey_encoded = pd.get_dummies(survey_data.astype(str))

    # Aplicar Apriori
    frequent_itemsets = apriori(survey_encoded, min_support=0.1, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)

    # Filtrar reglas interesantes
    interesting_rules = rules[
        (rules['lift'] > 1.2) &
        (rules['confidence'] > 0.6)
    ].sort_values('confidence', ascending=False)

    return interesting_rules


def train_hybrid_model(df):
    """Entrena un modelo que puede funcionar con o sin datos de encuestas"""
    # Separar alumnos con y sin encuestas
    alumnos_con_encuestas = df.dropna(subset=[
        '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?'
    ])

    alumnos_sin_encuestas = df[df.isna()[
        '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?'
    ]].copy()

    # Codificar riesgo
    label_encoder = LabelEncoder()
    df['riesgo_encoded'] = label_encoder.fit_transform(df['riesgo'])

    if not alumnos_con_encuestas.empty:
        # Entrenar modelo completo (con características de encuestas)
        X_full = alumnos_con_encuestas.drop([
            'alumno_id', 'riesgo', 'riesgo_encoded'
        ], axis=1)

        # One-hot encoding para variables categóricas
        categorical_cols = X_full.select_dtypes(include=['object']).columns
        X_full_encoded = pd.get_dummies(X_full, columns=categorical_cols)

        y_full = alumnos_con_encuestas['riesgo_encoded']

        # Dividir solo si tenemos suficientes muestras
        if len(X_full_encoded) > 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X_full_encoded, y_full, test_size=0.2, random_state=42
            )

            full_model = RandomForestClassifier(n_estimators=100, random_state=42)
            full_model.fit(X_train, y_train)

            # Evaluar
            y_pred = full_model.predict(X_test)
            print("Evaluación del modelo completo (con encuestas):")
            print(classification_report(y_test, y_pred,
                                      target_names=label_encoder.classes_))
        else:
            full_model = None
            print("No hay suficientes alumnos con encuestas para entrenar el modelo completo")
    else:
        full_model = None

    # Entrenar modelo básico (solo con características académicas)
    academic_cols = [
        'logro_promedio', 'logro_minimo', 'logro_maximo',
        'logro_std', 'materias_diferentes', 'total_evaluaciones'
    ]

    X_academic = df[academic_cols]
    y_academic = df['riesgo_encoded']

    academic_model = RandomForestClassifier(n_estimators=100, random_state=42)
    academic_model.fit(X_academic, y_academic)

    print("\nEvaluación del modelo académico (todos los alumnos):")
    # Evaluación cruzada para el modelo académico
    # from sklearn.model_selection import cross_val_score
    # scores = cross_val_score(academic_model, X_academic, y_academic, cv=5)
    # print(f"Precisión promedio: {scores.mean():.2f} (+/- {scores.std():.2f})")

    return {
        'full_model': full_model,
        'academic_model': academic_model,
        'label_encoder': label_encoder
    }

# def predict_student_risk(models, student_data):
#     """Predice el riesgo usando el mejor modelo disponible para cada alumno"""
#     # Determinar si tenemos datos de encuestas para este alumno
#     has_survey = not pd.isna(student_data.get(
#         '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?', np.nan
#     ))

#     # Preparar características académicas
#     academic_features = student_data[[
#         'logro_promedio', 'logro_minimo', 'logro_maximo',
#         'logro_std', 'materias_diferentes', 'total_evaluaciones'
#     ]].values.reshape(1, -1)

#     if has_survey and models['full_model'] is not None:
#         # Usar modelo completo
#         categorical_cols = student_data.select_dtypes(include=['object']).index
#         student_data_encoded = pd.get_dummies(
#             student_data.to_frame().T,
#             columns=categorical_cols
#         )

#         # Asegurar que tenemos todas las columnas esperadas
#         expected_columns = models['full_model'].feature_names_in_
#         for col in expected_columns:
#             if col not in student_data_encoded.columns:
#                 student_data_encoded[col] = 0

#         student_data_encoded = student_data_encoded[expected_columns]
#         prediction = models['full_model'].predict(student_data_encoded)
#     else:
#         # Usar modelo académico básico
#         prediction = models['academic_model'].predict(academic_features)

#     return models['label_encoder'].inverse_transform(prediction)[0]


def predict_student_risk(models, student_data):
    """Predice el riesgo usando el mejor modelo disponible para cada alumno"""
    # Determinar si tenemos datos de encuestas para este alumno
    has_survey = not pd.isna(student_data.get(
        '¿Cuánto tiempo dedicas al estudio fuera del horario escolar?', np.nan
    ))

    # Preparar características académicas
    academic_features = student_data[[
        'logro_promedio', 'logro_minimo', 'logro_maximo',
        'logro_std', 'materias_diferentes', 'total_evaluaciones'
    ]].values.reshape(1, -1)

    if has_survey and models['full_model'] is not None:
        # Usar modelo completo
        categorical_cols = student_data.select_dtypes(include=['object']).index
        student_data_encoded = pd.get_dummies(
            student_data.to_frame().T,
            columns=categorical_cols
        )

        # Asegurar que tenemos todas las columnas esperadas
        expected_columns = models['full_model'].feature_names_in_
        for col in expected_columns:
            if col not in student_data_encoded.columns:
                student_data_encoded[col] = 0

        student_data_encoded = student_data_encoded[expected_columns]
        prediction = models['full_model'].predict(student_data_encoded)
    else:
        # Usar modelo académico básico
        prediction = models['academic_model'].predict(academic_features)

    return models['label_encoder'].inverse_transform(prediction)[0]