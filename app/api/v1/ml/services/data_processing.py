import pandas as pd
from sklearn.preprocessing import LabelEncoder

import numpy as np

def prepare_data(notas_df, encuestas_df):
    """Prepara los datos para el análisis"""
    # Procesar datos académicos
    # Convertir niveles de logro a valores numéricos
    nivel_logro_map = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'No calificado': 0}
    notas_df['nivel_logro_num'] = notas_df['nivel_logro'].map(nivel_logro_map)

    # Calcular promedio por alumno, materia y bimestre
    academic_performance = notas_df.groupby(
        ['alumno_id', 'nombre_completo', 'edad', 'genero', 'materia', 'bimestre']
    )['nivel_logro_num'].mean().unstack().reset_index()

    # Calcular riesgo académico (ejemplo simple)
    academic_performance['riesgo'] = np.where(
        academic_performance.mean(axis=1) < 2.5, 'Alto',
        np.where(academic_performance.mean(axis=1) < 3, 'Medio', 'Bajo')
    )

    # Procesar datos de encuestas
    # Pivotar las encuestas para tener una fila por alumno
    encuestas_pivot = encuestas_df.pivot_table(
        index='alumno_id',
        columns='pregunta',
        values='opcion',
        aggfunc=lambda x: ', '.join(x)
    ).reset_index()

    # Unir los datos académicos con las encuestas
    full_data = pd.merge(
        academic_performance[['alumno_id', 'nombre_completo', 'edad', 'genero', 'riesgo']],
        encuestas_pivot,
        on='alumno_id',
        how='left'
    )

    return full_data

def encode_data(df):
    """Codifica los datos categóricos para el modelo"""
    # Codificar variables categóricas
    categorical_cols = [
        'genero',
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
    ]

    # One-hot encoding para las variables categóricas
    df_encoded = pd.get_dummies(df, columns=categorical_cols)

    # Codificar la variable objetivo (riesgo)
    label_encoder = LabelEncoder()
    df_encoded['riesgo_encoded'] = label_encoder.fit_transform(df_encoded['riesgo'])

    return df_encoded, label_encoder

def prepare_data_with_missing_alternative(notas_df, encuestas_df):
    """
    Versión alternativa que no depende de nivel_logro_num
    """
    # Convertir valor_criterio_de_evaluacion a numérico si es posible
    notas_df['puntuacion'] = pd.to_numeric(notas_df['valor_criterio_de_evaluacion'], errors='coerce')

    # Si no hay valores numéricos, crear una columna dummy
    if notas_df['puntuacion'].isna().all():
        notas_df['puntuacion'] = 1  # Valor por defecto

    # Calcular métricas académicas
    academic_features = notas_df.groupby('alumno_id').agg({
        'puntuacion': ['mean', 'min', 'max', 'std'],
        'materia': 'nunique',
        'bimestre': 'nunique'
    }).reset_index()

    # Renombrar columnas
    academic_features.columns = [
        'alumno_id',
        'puntuacion_promedio',
        'puntuacion_minima',
        'puntuacion_maxima',
        'puntuacion_std',
        'materias_diferentes',
        'bimestres_evaluados'
    ]

    # Calcular riesgo basado en percentiles
    academic_features['riesgo'] = pd.qcut(
        academic_features['puntuacion_promedio'],
        q=[0, 0.25, 0.75, 1],
        labels=['Alto', 'Medio', 'Bajo']
    )

    academic_features.columns = [
        'alumno_id',
        'logro_promedio',
        'logro_minimo',
        'logro_maximo',
        'logro_std',
        'materias_diferentes',
        'bimestres_evaluados'  # Cambiado de total_evaluaciones
    ]

    # Calcular riesgo basado solo en desempeño académico
    academic_features['riesgo'] = np.where(
        academic_features['logro_promedio'] < 2.5, 'Alto',
        np.where(academic_features['logro_promedio'] < 3, 'Medio', 'Bajo')
    )

    # Procesar encuestas para los que las tienen
    if not encuestas_df.empty:
        encuestas_pivot = encuestas_df.pivot_table(
            index='alumno_id',
            columns='pregunta',
            values='opcion',
            aggfunc=lambda x: ', '.join(x)
        ).reset_index()

        # Unir datos académicos con encuestas (left join para mantener todos los alumnos)
        full_data = pd.merge(
            academic_features,
            encuestas_pivot,
            on='alumno_id',
            how='left'
        )
    else:
        full_data = academic_features

    return full_data

def prepare_data_with_missing(notas_df, encuestas_df):
    """
    Prepara los datos manejando casos donde faltan encuestas
    y crea características alternativas basadas solo en notas
    """
    # Primero verificar y crear la columna nivel_logro_num si no existe
    if 'nivel_logro_num' not in notas_df.columns:
        # Mapear los niveles de logro a valores numéricos
        nivel_logro_map = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'No calificado': 0}
        notas_df['nivel_logro_num'] = notas_df['nivel_logro'].map(nivel_logro_map)

    # Verificar que la columna se creó correctamente
    if 'nivel_logro_num' not in notas_df.columns:
        raise ValueError("No se pudo crear la columna nivel_logro_num. Verifique los datos de entrada.")

    # Calcular métricas académicas
    academic_features = notas_df.groupby('alumno_id').agg({
        'nivel_logro_num': ['mean', 'min', 'max', 'std'],
        'materia': 'nunique',
        'bimestre': 'nunique'  # Usamos bimestre como proxy de evaluaciones si total_evaluaciones no existe
    }).reset_index()

    # Renombrar columnas multi-nivel
    academic_features.columns = [
        'alumno_id',
        'logro_promedio',
        'logro_minimo',
        'logro_maximo',
        'logro_std',
        'materias_diferentes',
        'bimestres_evaluados'  # Cambiado de total_evaluaciones
    ]

    # Calcular riesgo basado solo en desempeño académico
    academic_features['riesgo'] = np.where(
        academic_features['logro_promedio'] < 2.5, 'Alto',
        np.where(academic_features['logro_promedio'] < 3, 'Medio', 'Bajo')
    )

    # Procesar encuestas para los que las tienen
    if not encuestas_df.empty:
        encuestas_pivot = encuestas_df.pivot_table(
            index='alumno_id',
            columns='pregunta',
            values='opcion',
            aggfunc=lambda x: ', '.join(x)
        ).reset_index()

        # Unir datos académicos con encuestas (left join para mantener todos los alumnos)
        full_data = pd.merge(
            academic_features,
            encuestas_pivot,
            on='alumno_id',
            how='left'
        )
    else:
        full_data = academic_features

    return full_data

def validate_input_data(notas_df):
    """Valida que los datos de entrada tengan las columnas necesarias"""
    required_columns = {'alumno_id', 'materia', 'bimestre'}

    # Verificar columnas mínimas
    if not required_columns.issubset(notas_df.columns):
        missing = required_columns - set(notas_df.columns)
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    # Verificar al menos una columna de evaluación
    evaluation_cols = {'nivel_logro', 'valor_criterio_de_evaluacion', 'nivel_logro_num'}
    if not evaluation_cols.intersection(notas_df.columns):
        raise ValueError("Se necesita al menos una columna de evaluación: nivel_logro, valor_criterio_de_evaluacion o nivel_logro_num")

    return True


def safe_prepare_data(notas_df, encuestas_df):
    """Versión final que maneja múltiples escenarios"""
    try:
        # Intentar con nivel_logro primero
        if 'nivel_logro' in notas_df.columns:
            notas_df['nivel_logro_num'] = notas_df['nivel_logro'].map(
                {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'No calificado': 0}
            )
            metric_col = 'nivel_logro_num'
        elif 'valor_criterio_de_evaluacion' in notas_df.columns:
            notas_df['puntuacion'] = pd.to_numeric(
                notas_df['valor_criterio_de_evaluacion'],
                errors='coerce'
            ).fillna(0)
            metric_col = 'puntuacion'
        else:
            raise ValueError("No hay columnas de evaluación disponibles")

        # Calcular métricas
        features = notas_df.groupby('alumno_id').agg({
            metric_col: ['mean', 'min', 'max', 'std'],
            'materia': 'nunique',
            'bimestre': 'nunique'
        }).reset_index()

        features.columns = [
            'alumno_id', 'logro_promedio', 'logro_minimo',
            'logro_maximo', 'logro_std', 'materias_diferentes',
            'bimestres_evaluados'
        ]

        # Calcular riesgo
        features['riesgo'] = pd.qcut(
            features['logro_promedio'],
            q=[0, 0.25, 0.75, 1],
            labels=['Alto', 'Medio', 'Bajo']
        )

        # Unir con encuestas si existen
        if not encuestas_df.empty:
            encuestas_pivot = encuestas_df.pivot_table(
                index='alumno_id',
                columns='pregunta',
                values='opcion',
                aggfunc='first'  # Usar first en lugar de join para mantener valores únicos
            ).reset_index()

            full_data = pd.merge(
                features,
                encuestas_pivot,
                on='alumno_id',
                how='left'
            )
        else:
            full_data = features

        return full_data

    except Exception as e:
        print(f"Error al preparar datos: {e}")
        # Intentar recuperación mínima
        minimal_features = notas_df.groupby('alumno_id').agg({
            'materia': 'nunique',
            'bimestre': 'nunique'
        }).reset_index()
        minimal_features['riesgo'] = 'Medio'  # Valor por defecto
        return minimal_features