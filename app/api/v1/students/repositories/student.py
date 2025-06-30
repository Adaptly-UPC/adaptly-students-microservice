from pydantic import InstanceOf
from app.api.v1.students.models import Alumno, HistorialAcademico, Encuesta, Nota, RespuestaEncuesta, Materia, Bimestre, AnioAcademico, Seccion, NivelEducativo, Grado
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from app.api.v1.students.repositories import achievement_levels

class StudentRepository:
    def __init__(self, db):
        self.db = db

    def get_grades_and_sections(self, nivel_id=None, anio_academico_id=None, grado_id=None, seccion_id=None):
        """
        Obtiene los grados y las secciones asociadas a cada grado, permitiendo filtrar por nivel educativo,
        año académico, grado y sección.
        """
        query = self.db.query(Grado).join(HistorialAcademico).join(Seccion)

        # Aplicar filtros
        if nivel_id:
            query = query.filter(Grado.nivel_id == nivel_id)
        if anio_academico_id:
            query = query.filter(HistorialAcademico.anio_academico_id == anio_academico_id)
        if grado_id:
            query = query.filter(Grado.id == grado_id)
        if seccion_id:
            query = query.filter(HistorialAcademico.seccion_id == seccion_id)

        # Obtener los resultados
        grades = query.distinct().all()

        # Formatear los datos
        formatted_grades = []
        for grade in grades:
            # Obtener secciones únicas para este grado
            unique_sections = set()
            sections_list = []

            for historial in grade.historial_academico:
                # Si hay un seccion_id específico, solo incluir esa sección
                if seccion_id:
                    if historial.seccion and historial.seccion.id == seccion_id and (historial.seccion.id, historial.seccion.nombre) not in unique_sections:
                        unique_sections.add((historial.seccion.id, historial.seccion.nombre))
                        sections_list.append({
                            "seccion_id": historial.seccion.id,
                            "seccion_nombre": historial.seccion.nombre
                        })
                else:
                    # Si no hay seccion_id, incluir todas las secciones únicas
                    if historial.seccion and (historial.seccion.id, historial.seccion.nombre) not in unique_sections:
                        unique_sections.add((historial.seccion.id, historial.seccion.nombre))
                        sections_list.append({
                            "seccion_id": historial.seccion.id,
                            "seccion_nombre": historial.seccion.nombre
                        })

            formatted_grades.append({
                "grado_id": grade.id,
                "grado_nombre": grade.nombre,
                "nivel_id": grade.nivel_id,
                "secciones": sections_list
            })

        return formatted_grades

    def get_students_with_only_notes(self):
        """Obtiene alumnos que tienen solo notas."""
        return self.db.query(Alumno).join(HistorialAcademico).join(Nota).filter(
            ~Alumno.encuestas.any()
        ).distinct(Alumno.id).all()

    def get_students_with_only_surveys(self):
        """Obtiene alumnos que tienen solo encuestas."""
        return self.db.query(Alumno).join(Encuesta).filter(
            ~Alumno.historial_academico.any()
        ).distinct(Alumno.id).all()

    def get_students_with_notes_and_surveys(self):
        """Obtiene alumnos que tienen tanto notas como encuestas."""
        return self.db.query(Alumno).join(HistorialAcademico).join(Nota).join(Encuesta).distinct(Alumno.id).all()

    def get_available_filters(self):
        """
        Obtiene todos los filtros disponibles basados en los datos existentes en la base de datos.

        Returns:
            dict: Diccionario con los filtros disponibles (ID y nombre).
        """
        anios_academicos = self.db.query(AnioAcademico.id, AnioAcademico.anio).distinct().all()
        niveles_educativos = self.db.query(NivelEducativo.id, NivelEducativo.nombre).distinct().all()
        secciones = self.db.query(Seccion.id, Seccion.nombre).distinct().all()
        bimestres = self.db.query(Bimestre.id, Bimestre.nombre).distinct().all()
        materias = self.db.query(Materia.id, Materia.nombre).distinct().all()
        grados = self.db.query(Grado.id, Grado.nombre, Grado.nivel_id).distinct().all()

        return {
            "anios_academicos": [{"id": anio.id, "anio": anio.anio} for anio in anios_academicos],
            "niveles_educativos": [{"id": nivel.id, "nombre": nivel.nombre} for nivel in niveles_educativos],
            "secciones": [{"id": seccion.id, "nombre": seccion.nombre} for seccion in secciones],
            "bimestres": [{"id": bimestre.id, "nombre": bimestre.nombre} for bimestre in bimestres],
            "materias": [{"id": materia.id, "nombre": materia.nombre} for materia in materias],
            "grados": [{"id": grado.id, "nombre": grado.nombre, "nivel_id": grado.nivel_id} for grado in grados]
        }

    def get_students_with_filters(self, anio_academico_id=None, seccion_id=None, nivel_id=None, grado_id=None, bimestre_id=None, materia_id=None, page: int = 1, page_size: int = 10):
        """
        Obtiene alumnos filtrados por los parámetros proporcionados utilizando IDs.

        Args:
            anio_academico_id (int): ID del año académico del historial.
            seccion_id (int): ID de la sección.
            nivel_id (int): ID del nivel educativo.
            grado_id (int): ID del grado.
            bimestre_id (int): ID del bimestre.
            materia_id (int): ID de la materia.
            page (int): Número de página para la paginación.
            page_size (int): Tamaño de la página (cantidad de registros por página).

        Returns:
            dict: Datos paginados de alumnos filtrados.
        """
        query = self.db.query(Alumno).join(HistorialAcademico).join(Nota).join(Materia).join(Bimestre).join(Grado)

        # Aplicar filtros por ID
        if anio_academico_id:
            query = query.filter(HistorialAcademico.anio_academico_id == anio_academico_id)
        if seccion_id:
            query = query.filter(HistorialAcademico.seccion_id == seccion_id)
        if nivel_id:
            query = query.filter(HistorialAcademico.nivel_id == nivel_id)
        if grado_id:
            query = query.filter(HistorialAcademico.grado_id == grado_id)
        if bimestre_id:
            query = query.filter(Nota.bimestre_id == bimestre_id)
        if materia_id:
            query = query.filter(Nota.materia_id == materia_id)

        # Usar distinct para evitar duplicados
        query = query.distinct(Alumno.id)

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
                ]
            })

        return {
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "students": formatted_students
        }
    def get_all_students(self):
        return self.db.query(Alumno).all()

    def get_students_summary(self):
        """Obtiene un resumen del estado de los alumnos."""
        # Contar el total de estudiantes
        total_students = self.db.query(Alumno).count()

        # Contar estudiantes con solo notas
        students_with_only_notes = self.db.query(Alumno).join(HistorialAcademico).join(Nota).filter(
            ~Alumno.encuestas.any()
        ).distinct(Alumno.id).count()

        # Contar estudiantes con solo encuestas
        students_with_only_surveys = self.db.query(Alumno).join(Encuesta).filter(
            ~Alumno.historial_academico.any()
        ).distinct(Alumno.id).count()

        # Contar estudiantes con notas y encuestas
        students_with_notes_and_surveys = self.db.query(Alumno).join(HistorialAcademico).join(Nota).join(Encuesta).distinct(Alumno.id).count()

        return {
            "total_students": total_students,
            "students_with_only_notes": {
                "count": students_with_only_notes,
                "percentage": (students_with_only_notes / total_students) * 100 if total_students > 0 else 0
            },
            "students_with_only_surveys": {
                "count": students_with_only_surveys,
                "percentage": (students_with_only_surveys / total_students) * 100 if total_students > 0 else 0
            },
            "students_with_notes_and_surveys": {
                "count": students_with_notes_and_surveys,
                "percentage": (students_with_notes_and_surveys / total_students) * 100 if total_students > 0 else 0
            }
        }

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


    def get_student_notes(
        self,
        alumno_id: int = None,
        materia_id: int = None,
        grado_id: int = None,
        anio_academico_id: int = None,
        page: int = 1,
        page_size: int = 10
    ):
        """
        Obtiene todas las notas de los alumnos con filtros opcionales.

        Args:
            alumno_id (int): ID del alumno
            materia_id (int): ID de la materia/curso
            grado_id (int): ID del grado
            anio_academico_id (int): ID del año académico
            page (int): Número de página
            page_size (int): Tamaño de página

        Returns:
            dict: Diccionario con las notas y metadata de paginación
        """
        query = self.db.query(Nota).join(HistorialAcademico).join(Alumno).join(Materia)

        # Aplicar filtros
        if alumno_id:
            query = query.filter(HistorialAcademico.alumno_id == alumno_id)
        if materia_id:
            query = query.filter(Nota.materia_id == materia_id)
        if grado_id:
            query = query.filter(HistorialAcademico.grado_id == grado_id)
        if anio_academico_id:
            query = query.filter(HistorialAcademico.anio_academico_id == anio_academico_id)

        # Contar total de registros
        total_records = query.count()

        # Aplicar paginación
        notes = query.offset((page - 1) * page_size).limit(page_size).all()

        # Formatear resultados
        formatted_notes = []
        for note in notes:
            formatted_notes.append({
                "nota_id": note.id,
                "alumno": {
                    "id": note.historial.alumno.id,
                    "nombre": note.historial.alumno.nombre_completo,
                    "codigo": note.historial.alumno.codigo_alumno
                },
                "materia": {
                    "id": note.materia.id,
                    "nombre": note.materia.nombre
                },
                "grado": {
                    "id": note.historial.grado.id,
                    "nombre": note.historial.grado.nombre
                },
                "anio_academico": {
                    "id": note.historial.anio_academico.id,
                    "anio": note.historial.anio_academico.anio
                },
                "bimestre": {
                    "id": note.bimestre.id,
                    "nombre": note.bimestre.nombre
                },
                "criterio_evaluacion": {
                    "id": note.criterio_evaluacion.id,
                    "nombre": note.criterio_evaluacion.nombre
                },
                "valor_criterio": note.valor_criterio_de_evaluacion,
                "nivel_logro": note.nivel_logro.valor if note.nivel_logro else None
            })

        return {
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "notes": formatted_notes
        }


# ANALISIS DE DATOS DE ESTUDIANTES

    def get_student_performance_data(self, include_surveys: bool = False):
        """
        Obtiene datos estructurados para análisis de rendimiento académico.
        """
        query = self.db.query(Alumno)

        if include_surveys:
            query = query.join(HistorialAcademico).join(Nota).join(Encuesta)
        else:
            query = query.join(HistorialAcademico).join(Nota)

        students = query.distinct(Alumno.id).all()

        performance_data = []
        for student in students:
            student_data = {
                "student_id": student.id,
                "demographic_features": {
                    "gender": student.genero,
                    "age": student.edad
                },
                "academic_performance": [],
                "risk_indicators": {
                    "failed_subjects_count": 0,
                    "low_performance_count": 0,
                    "missing_assignments": 0
                }
            }

            for record in student.historial_academico:
                period_data = {
                    "academic_year": record.anio_academico.anio,
                    "grade": record.grado.nombre,
                    "subjects": []
                }

                for nota in record.notas:
                    if nota.nivel_logro.valor == "No calificado" or nota.nivel_logro.valor is None:
                        continue

                    subject_data = {
                        "subject": nota.materia.nombre,
                        "achievement_level": nota.nivel_logro.valor if nota.nivel_logro else None,
                        "evaluation_criteria": nota.valor_criterio_de_evaluacion
                    }
                    period_data["subjects"].append(subject_data)

                    # Actualizar indicadores de riesgo
                    if nota.nivel_logro and nota.nivel_logro.valor in ['C', 'D']:
                        student_data["risk_indicators"]["low_performance_count"] += 1

                student_data["academic_performance"].append(period_data)

            performance_data.append(student_data)

        return {
            "total_records": len(performance_data),
            "performance_data": performance_data
        }

    def get_student_behavior_patterns(self, min_survey_responses: int, min_academic_periods: int):
        """
        Obtiene datos estructurados para análisis de patrones de comportamiento.
        """
        students = self.db.query(Alumno).join(Encuesta).join(HistorialAcademico).distinct(Alumno.id).all()

        behavior_data = []
        for student in students:
            if len(student.encuestas) >= min_survey_responses and \
            len(student.historial_academico) >= min_academic_periods:

                student_data = {
                    "student_id": student.id,
                    "survey_responses": [],
                    # TODO: Implementar
                    # "academic_indicators": {
                    #     "attendance": [],
                    #     "participation": [],
                    #     "homework_completion": []
                    # }
                }

                # Procesar encuestas
                for encuesta in student.encuestas:
                    survey_data = {
                        "year": encuesta.anio,
                        "responses": [
                            {
                                "question": resp.pregunta.pregunta,
                                "answer": resp.opcion.opcion
                            }
                            for resp in encuesta.respuestas
                        ]
                    }
                    student_data["survey_responses"].append(survey_data)

                behavior_data.append(student_data)

        return {
            "total_records": len(behavior_data),
            "behavior_data": behavior_data
        }
    
    def materia_exist(self, materia_list: list, current_materia_id: int) -> int: 
        value: int = -1
        for index, materia in enumerate(materia_list):
            if materia.get("materia_id") == current_materia_id:
                value = index
        print(f"VALUEEEERRRRR: {value}")
        return value

    def get_complete_student_profile(self, analysis_type: str = "all"):
        """
        Obtiene el perfil completo de estudiantes con diferentes niveles de detalle,
        organizando el historial académico por año, grado y bimestre.
        """
        query = self.db.query(Alumno)

        if analysis_type == "complete":
            query = query.join(HistorialAcademico).join(Nota).join(Encuesta)
        elif analysis_type == "academic":
            query = query.join(HistorialAcademico).join(Nota)
        elif analysis_type == "behavioral":
            query = query.join(Encuesta)

        students = query.distinct(Alumno.id).all()

        profiles = []
        for student in students:
            profile = {
                "student_info": {
                    "id": student.id,
                    "code": student.codigo_alumno,
                    "name": student.nombre_completo,
                    "age": student.edad,
                    "gender": student.genero
                },
                "academic_history": [],
                "survey_data": [],
                # "performance_metrics": {
                #     "average_achievement": None,
                #     "risk_level": None,
                #     "improvement_areas": []
                # }
            }

            # Procesar historial académico
            if hasattr(student, 'historial_academico'):
                for record in student.historial_academico:
                    # Organizar notas por bimestre
                    bimestres = {}
                    for nota in record.notas:
                        bimestre_id = nota.bimestre.id
                        if bimestre_id not in bimestres:
                            bimestres[bimestre_id] = {
                                "bimestre_id": bimestre_id,
                                "bimestre_nombre": nota.bimestre.nombre,
                                "materias": []
                            }
                        if nota.nivel_logro.valor == "No calificado" or nota.nivel_logro.valor is None:
                            # TODO: Limpiar base de datos si alumno no cuenta con notas de algún curso
                            continue

                        materia_index = self.materia_exist(bimestres[bimestre_id]["materias"], nota.materia.id)
                        if materia_index >=0:
                            bimestres[bimestre_id]["materias"][materia_index]["grades"].append({        
                                "achievement": nota.nivel_logro.valor if nota.nivel_logro else None,
                                "evaluation_criteria": nota.criterio_evaluacion.nombre,
                                "valor_criterio": nota.valor_criterio_de_evaluacion})  
                            # })
                        else:
                            bimestres[bimestre_id]["materias"].append({
                                "name": nota.materia.nombre,
                                "materia_id": nota.materia.id,
                                "grades": [{        
                                    "achievement": nota.nivel_logro.valor if nota.nivel_logro else None,
                                    "evaluation_criteria": nota.criterio_evaluacion.nombre,
                                    "valor_criterio": nota.valor_criterio_de_evaluacion}]
                            })


                    academic_period = {
                        "year": record.anio_academico.anio,
                        "anio_academico_id": record.anio_academico_id,
                        "grade": record.grado.nombre,
                        "grado_id": record.grado_id,
                        "section": record.seccion.nombre,
                        "seccion_id": record.seccion_id,
                        "bimestres": list(bimestres.values())
                    }
                    profile["academic_history"].append(academic_period)

                # Calcular métricas de rendimiento
                # total_grades = 0
                # count_grades = 0
                # risk_count = 0
                # improvement_areas = set()

                # for period in profile["academic_history"]:
                #     for bimestre in period["bimestres"]:
                #         for materia in bimestre["materias"]:
                #             if materia["achievement"]:
                #                 if materia["achievement"] in ['C', 'D']:
                #                     risk_count += 1
                #                     improvement_areas.add(materia["name"])
                #                 # Convertir nivel de logro a valor numérico
                #                 grade_value = {
                #                     'AD': 4,
                #                     'A': 3,
                #                     'B': 2,
                #                     'C': 1,
                #                     'D': 0
                #                 }.get(materia["achievement"], 0)
                #                 total_grades += grade_value
                #                 count_grades += 1

                # Actualizar métricas de rendimiento
                # if count_grades > 0:
                #     profile["performance_metrics"]["average_achievement"] = round(total_grades / count_grades, 2)
                #     profile["performance_metrics"]["risk_level"] = "Alto" if risk_count > count_grades * 0.3 else "Medio" if risk_count > 0 else "Bajo"
                #     profile["performance_metrics"]["improvement_areas"] = list(improvement_areas)

            # Procesar encuestas
            if hasattr(student, 'encuestas'):
                for encuesta in student.encuestas:
                    survey_data = {
                        "year": encuesta.anio,
                        "date": encuesta.fecha,
                        "responses": [
                            {
                                "question": resp.pregunta.pregunta,
                                "answer": resp.opcion.opcion
                            }
                            for resp in encuesta.respuestas
                        ]
                    }
                    profile["survey_data"].append(survey_data)

            profiles.append(profile)

        return {
            "total_records": len(profiles),
            "analysis_type": analysis_type,
            "profiles": profiles
        }
