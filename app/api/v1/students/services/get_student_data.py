from app.api.v1.students.models import Alumno, HistorialAcademico, AnioAcademico, NivelEducativo, Grado, Seccion, Nota, Materia, Bimestre, CriterioEvaluacion, NivelLogro, PreguntaEncuesta, OpcionEncuesta, RespuestaEncuesta, Encuesta
from app.db.database import get_db
import pandas as pd
from sqlalchemy import create_engine, func, case, and_, or_

def get_student_data():
    """Consulta corregida para obtener todos los datos relevantes"""
    # Configurar la sesión
    session = next(get_db())

    try:
        # Definir el mapeo de niveles de logro a valores numéricos
        # FORMA CORRECTA para SQLAlchemy 2.x:
        nivel_logro_case = case(
            (NivelLogro.valor == 'A', 4),
            (NivelLogro.valor == 'B', 3),
            (NivelLogro.valor == 'C', 2),
            (NivelLogro.valor == 'D', 1),
            (NivelLogro.valor == 'No calificado', 0),
            else_=0
        ).label("nivel_logro_num")

        # Consulta para obtener las notas con el valor numérico calculado
        notas_query = (
            session.query(
                Alumno.id.label("alumno_id"),
                Alumno.nombre_completo,
                Alumno.edad,
                Alumno.genero,
                HistorialAcademico.anio_academico_id,
                AnioAcademico.anio.label("anio"),
                NivelEducativo.nombre.label("nivel_educativo"),
                Grado.nombre.label("grado"),
                Seccion.nombre.label("seccion"),
                Materia.nombre.label("materia"),
                Bimestre.nombre.label("bimestre"),
                CriterioEvaluacion.nombre.label("criterio_evaluacion"),
                NivelLogro.valor.label("nivel_logro"),
                nivel_logro_case,
                func.count().label("total_evaluaciones")
            )
            .join(HistorialAcademico, Alumno.id == HistorialAcademico.alumno_id)
            .join(AnioAcademico, HistorialAcademico.anio_academico_id == AnioAcademico.id)
            .join(NivelEducativo, HistorialAcademico.nivel_id == NivelEducativo.id)
            .join(Grado, HistorialAcademico.grado_id == Grado.id)
            .join(Seccion, HistorialAcademico.seccion_id == Seccion.id)
            .join(Nota, HistorialAcademico.id == Nota.historial_id)
            .join(Materia, Nota.materia_id == Materia.id)
            .join(Bimestre, Nota.bimestre_id == Bimestre.id)
            .join(CriterioEvaluacion, Nota.criterio_evaluacion_id == CriterioEvaluacion.id)
            .join(NivelLogro, Nota.nivel_logro_id == NivelLogro.id)
            .group_by(
                Alumno.id, Alumno.nombre_completo, Alumno.edad, Alumno.genero,
                HistorialAcademico.anio_academico_id, AnioAcademico.anio,
                NivelEducativo.nombre, Grado.nombre, Seccion.nombre,
                Materia.nombre, Bimestre.nombre, CriterioEvaluacion.nombre,
                NivelLogro.valor
            )
        )

        # Consulta para obtener las respuestas de las encuestas
        encuestas_query = (
            session.query(
                Alumno.id.label("alumno_id"),
                PreguntaEncuesta.pregunta,
                OpcionEncuesta.opcion,
                func.count().label("respuesta_count")
            )
            .join(Encuesta, Alumno.id == Encuesta.alumno_id)
            .join(RespuestaEncuesta, Encuesta.id == RespuestaEncuesta.encuesta_id)
            .join(PreguntaEncuesta, RespuestaEncuesta.pregunta_id == PreguntaEncuesta.id)
            .join(OpcionEncuesta, RespuestaEncuesta.opcion_id == OpcionEncuesta.id)
            .group_by(Alumno.id, PreguntaEncuesta.pregunta, OpcionEncuesta.opcion)
        )

        # Convertir a DataFrames
        notas_df = pd.read_sql(notas_query.statement, session.bind)
        encuestas_df = pd.read_sql(encuestas_query.statement, session.bind)

        print(f"Datos académicos obtenidos: {len(notas_df)} registros")
        print(f"Datos de encuestas obtenidos: {len(encuestas_df)} registros")

        return notas_df, encuestas_df

    except Exception as e:
        print(f"Error al obtener datos: {str(e)}")
        raise
    finally:
        session.close()