from app.api.v1.students.models import Alumno, HistorialAcademico, Encuesta, Nota, RespuestaEncuesta
from sqlalchemy.orm import joinedload
from sqlalchemy import func

class StudentRepository:
    def __init__(self, db):
        self.db = db

    def get_all_students(self):
        return self.db.query(Alumno).all()

    def get_all_students_with_associated_data(self, page: int = 1, page_size: int = 10, search: str = None):
        """
        Obtiene todos los estudiantes con sus datos asociados, respetando parámetros de calidad como paginación y búsqueda.

        Args:
            page (int): Número de página para la paginación.
            page_size (int): Tamaño de la página (cantidad de registros por página).
            search (str): Cadena para buscar estudiantes por nombre.

        Returns:
            dict: Datos paginados de estudiantes con todas sus relaciones.
        """
        query = self.db.query(Alumno).options(
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.anio_academico),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.nivel),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.grado),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.seccion),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.materia),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.bimestre),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.criterio_evaluacion),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.nivel_logro),
            joinedload(Alumno.encuestas).joinedload(Encuesta.respuestas).joinedload(RespuestaEncuesta.opcion),
            joinedload(Alumno.encuestas).joinedload(Encuesta.respuestas_texto)
        )

        # Aplicar búsqueda por nombre si se proporciona
        if search:
            query = query.filter(func.lower(Alumno.nombre_completo).like(f"%{search.lower()}%"))

        # Contar el total de registros para la paginación
        total_records = query.count()

        # Aplicar paginación
        students = query.offset((page - 1) * page_size).limit(page_size).all()

        # Formatear los datos para incluir todas las relaciones
        formatted_students = []
        for student in students:
            formatted_students.append({
                "id": student.id,
                "codigo_alumno": student.codigo_alumno,
                "nombre_completo": student.nombre_completo,
                "edad": student.edad,
                "genero": student.genero,
                "historial_academico": [
                    {
                        "anio_academico": record.anio_academico.anio,
                        "nivel_educativo": record.nivel.nombre,
                        "grado": record.grado.nombre,
                        "seccion": record.seccion.nombre,
                        "notas": [
                            {
                                "materia": nota.materia.nombre,
                                "bimestre": nota.bimestre.nombre,
                                "criterio_evaluacion": nota.criterio_evaluacion.nombre,
                                "valor_criterio_de_evaluacion": nota.valor_criterio_de_evaluacion,
                                "nivel_logro": nota.nivel_logro.valor if nota.nivel_logro else None
                            }
                            for nota in record.notas
                        ]
                    }
                    for record in student.historial_academico
                ],
                "encuestas": [
                    {
                        "anio": encuesta.anio,
                        "fecha": encuesta.fecha,
                        "respuestas": [
                            {
                                "pregunta": respuesta.pregunta.pregunta,
                                "opcion": respuesta.opcion.opcion
                            }
                            for respuesta in encuesta.respuestas
                        ],
                        "respuestas_texto": [
                            {
                                "pregunta": respuesta_texto.pregunta.pregunta,
                                "texto": respuesta_texto.texto
                            }
                            for respuesta_texto in encuesta.respuestas_texto
                        ]
                    }
                    for encuesta in student.encuestas
                ]
            })

        return {
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "students": formatted_students
        }

    def get_student_by_id(self, student_id: int) -> Alumno:
        """Obtiene el alumno de la base de datos"""
        student = self.db.query(Alumno).filter(Alumno.id == student_id).options(
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.anio_academico),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.nivel),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.grado),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.seccion),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.materia),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.bimestre),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.criterio_evaluacion),
            joinedload(Alumno.historial_academico).joinedload(HistorialAcademico.notas).joinedload(Nota.nivel_logro),
            joinedload(Alumno.encuestas).joinedload(Encuesta.respuestas).joinedload(RespuestaEncuesta.opcion),
            joinedload(Alumno.encuestas).joinedload(Encuesta.respuestas_texto)
        ).first()

        return student

    def get_student_by_name(self, student_name: str) -> Alumno:
        """Obtiene el alumno de la base de datos"""
        student = self.db.query(Alumno).filter(Alumno.nombre_completo == student_name).first()
        return student

    def create_student(self, student_name: str, student_code="",student_gender='MASCULINO') -> Alumno:
        """Crea un alumno en la base de datos"""

        student = Alumno(nombre_completo=student_name, codigo_alumno=student_code, genero=student_gender)
        self.db.add(student)
        self.db.commit()
        return student


    def update_student(self, student_id, **kwargs):
        age = kwargs.get("age", None)
        gender = kwargs.get("gender", None)

        if type(age) == int:
            self.db.query(Alumno).filter(Alumno.id == student_id).update({"edad": age})
            self.db.commit()

        if type(gender) == str:
            self.db.query(Alumno).filter(Alumno.id == student_id).update({"genero": gender})
            self.db.commit()

        return self.get_student_by_id(student_id)

    def get_or_create_student(self, student_name: str, student_code="", student_gender="MASCULINO") -> Alumno:
        """Crea alumno si no puede obtenerlo"""
        student = self.get_student_by_name(student_name)

        if not student:
            student = self.create_student(student_name, student_code, student_gender )

        return student

