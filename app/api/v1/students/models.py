from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Alumno(Base):
    __tablename__ = "alumnos"
    id = Column(Integer, primary_key=True, index=True)
    codigo_alumno = Column(String, unique=True, index=True, nullable=True)
    nombre_completo = Column(String, index=True)
    edad = Column(Integer, nullable=True)
    genero = Column(String(10), nullable=False)  # 'masculino', 'femenino'


class NivelEducativo(Base):
    __tablename__ = "niveles_educativos"
    id = Column(Integer, primary_key=True, index=True)
    # "Primaria", "Secundaria"
    nombre = Column(String(50), unique=True, nullable=False)


class AnioAcademico(Base):
    __tablename__ = "anios_academicos"
    id = Column(Integer, primary_key=True, index=True)
    anio = Column(Integer, unique=True, nullable=False)
    # "2022", "2023", "2024" ...


class HistorialAcademico(Base):
    __tablename__ = "historial_academico"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"), nullable=False)
    anio_academico_id = Column(Integer, ForeignKey(
        "anios_academicos.id"), nullable=False)
    nivel_id = Column(Integer, ForeignKey(
        "niveles_educativos.id"), nullable=False)
    grado_id = Column(Integer, ForeignKey("grados.id"), nullable=False)
    seccion_id = Column(Integer, ForeignKey("secciones.id"), nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())

    # Relaciones
    alumno = relationship("Alumno")
    anio_academico = relationship("AnioAcademico")
    nivel = relationship("NivelEducativo")
    grado = relationship("Grado")
    seccion = relationship("Seccion")


class Grado(Base):
    __tablename__ = "grados"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    nivel_id = Column(Integer, ForeignKey(
        "niveles_educativos.id"), nullable=False)
    nivel = relationship("NivelEducativo")


class Seccion(Base):
    __tablename__ = "secciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)

class Materia(Base):
    __tablename__ = "materias"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(100), nullable=False)
    nombre = Column(String(100), nullable=False)


class CriterioEvaluacion(Base):
    __tablename__ = "criterios_evaluacion"
    id = Column(Integer, primary_key=True, index=True)
    materia_id = Column(Integer, ForeignKey("materias.id"), nullable=False)
    nombre = Column(String(), nullable=False)

class NivelLogro(Base):
    __tablename__ = "niveles_logro"
    id = Column(Integer, primary_key=True, index=True)
    valor = Column(String(20), nullable=True)  # 'A', 'B', 'C', 'D', 'No calificado'


class Bimestre(Base):
    __tablename__ = "bimestres"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)


class Nota(Base):
    __tablename__ = "notas"
    id = Column(Integer, primary_key=True, index=True)
    historial_id = Column(Integer, ForeignKey(
        "historial_academico.id"), nullable=False)
    materia_id = Column(Integer, ForeignKey("materias.id"), nullable=False)
    bimestre_id = Column(Integer, ForeignKey("bimestres.id"), nullable=False)
    criterio_evaluacion_id = Column(Integer, ForeignKey(
        "criterios_evaluacion.id", onupdate="CASCADE"), nullable=False)
    valor_criterio_de_evaluacion = Column(String(1000), nullable=False)
    nivel_logro_id = Column(Integer, ForeignKey(
        "niveles_logro.id"), nullable=True)

    # Relaciones
    historial = relationship("HistorialAcademico", lazy='joined')
    materia = relationship("Materia", lazy='joined')
    bimestre = relationship("Bimestre", lazy='joined')
    criterio_evaluacion = relationship("CriterioEvaluacion", lazy='joined')
    nivel_logro = relationship("NivelLogro", lazy='joined')

class PreguntaEncuesta(Base):
    __tablename__ = "preguntas_encuesta"
    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(String, nullable=False)
    tipo = Column(String, default="cerrada")  # 'cerrada' o 'abierta'
    es_multiple = Column(Integer, default=0)  # 1 = sí, 0 = no

    opciones = relationship("OpcionEncuesta", back_populates="pregunta", cascade="all, delete-orphan")
    respuestas = relationship("RespuestaEncuesta", back_populates="pregunta", cascade="all, delete-orphan")



class OpcionEncuesta(Base):
    __tablename__ = "opciones_encuesta"
    id = Column(Integer, primary_key=True, index=True)
    pregunta_id = Column(Integer, ForeignKey("preguntas_encuesta.id"), nullable=False)
    opcion = Column(String, nullable=False)

    pregunta = relationship("PreguntaEncuesta", back_populates="opciones")
    respuestas = relationship("RespuestaEncuesta", back_populates="opcion")


class Encuesta(Base):
    __tablename__ = "encuestas"
    id = Column(Integer, primary_key=True, index=True)
    anio = Column(Integer)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"), nullable=False)
    fecha = Column(TIMESTAMP, server_default=func.now())

    alumno = relationship("Alumno")
    respuestas = relationship("RespuestaEncuesta", back_populates="encuesta", cascade="all, delete-orphan")
    respuestas_texto = relationship("RespuestaTextoEncuesta", back_populates="encuesta", cascade="all, delete-orphan")



class RespuestaEncuesta(Base):
    __tablename__ = "respuestas_encuesta"
    id = Column(Integer, primary_key=True, index=True)
    encuesta_id = Column(Integer, ForeignKey("encuestas.id"), nullable=False)
    pregunta_id = Column(Integer, ForeignKey("preguntas_encuesta.id"), nullable=False)
    opcion_id = Column(Integer, ForeignKey("opciones_encuesta.id"), nullable=False)

    encuesta = relationship("Encuesta", back_populates="respuestas")
    pregunta = relationship("PreguntaEncuesta", back_populates="respuestas")
    opcion = relationship("OpcionEncuesta", back_populates="respuestas")


class RespuestaTextoEncuesta(Base):
    __tablename__ = "respuestas_texto_encuesta"
    id = Column(Integer, primary_key=True, index=True)
    encuesta_id = Column(Integer, ForeignKey("encuestas.id"), nullable=False)
    pregunta_id = Column(Integer, ForeignKey("preguntas_encuesta.id"), nullable=False)
    texto = Column(Text, nullable=False)

    encuesta = relationship("Encuesta", back_populates="respuestas_texto")
    pregunta = relationship("PreguntaEncuesta")

class RecommendationResult(Base):
    __tablename__ = "recommendation_results"

    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"), nullable=True)
    riesgo_predicho = Column(String, nullable=False)
    recomendaciones = Column(Text, nullable=False)
