from sqlalchemy.orm import Session
from app.api.v1.students.models import Grado
from app.api.v1.students.models import NivelEducativo
from app.api.v1.students.models import Seccion
from app.api.v1.students.models import AnioAcademico
from app.api.v1.students.models import Bimestre
from app.api.v1.students.models import Alumno
from app.api.v1.students.models import CriterioEvaluacion
from app.api.v1.students.models import Materia
from app.api.v1.students.models import NivelLogro

#handle nivel (PRIMARIA, SECUNDARIA)
def get_nivel(nivel: str, db: Session) -> int:
    """Get the ID of the given nivel or create it if it doesn't exist."""

    nivel_obj = db.query(NivelEducativo).filter_by(nombre=nivel).first()

    if not nivel_obj:
        nivel_obj = NivelEducativo(nombre=nivel)
        db.add(nivel_obj)
        db.commit()

    return nivel_obj.id


# handle grado
def get_grado(grado: str, nivelId: int, db: Session):
    """Get the ID of the given grado or create it if it doesn't exist."""

    grado_obj = db.query(Grado).filter(Grado.nombre == grado, Grado.nivel_id == nivelId).first()

    if not grado_obj:
        grado_obj = Grado(grado=grado, nivel_id=nivelId)
        db.add(grado_obj)
        db.commit()

    return grado_obj.id

def get_seccion(seccion: str, db: Session):
    """Get the ID of the given seccion or create it if it doesn't exist."""

    seccion_obj = db.query(Seccion).filter(Seccion.nombre == seccion).first()

    if not seccion_obj:
        seccion_obj = Seccion(nombre=seccion)
        db.add(seccion_obj)
        db.commit()

    return seccion_obj.id

def get_anio_academico(anio: int, db: Session):
    """Get the ID of the given anio academico or create it if it doesn't exist."""

    anio_academico_obj = db.query(AnioAcademico).filter(AnioAcademico.anio == anio).first()

    if not anio_academico_obj:
        anio_academico_obj = AnioAcademico(anio=anio)
        db.add(anio_academico_obj)
        db.commit()

    return anio_academico_obj.id


def get_bimestre(bimestre: str, db: Session):
    """Get the ID of the given bimestre or create it if it doesn't exist."""

    bimestre_obj = db.query(Bimestre).filter(Bimestre.nombre == bimestre).first()

    if not bimestre_obj:
        bimestre_obj = Bimestre(nombre=bimestre)
        db.add(bimestre_obj)
        db.commit()

    return bimestre_obj.id


def get_alumno(nombre_completo: str, db: Session):
    """Get the ID of the given alumno or create it if it doesn't exist."""

    alumno = db.query(Alumno).filter(Alumno.nombre_completo == nombre_completo).first()

    if not alumno_id:
        alumno_id = Alumno(nombre_completo=nombre_completo)
        db.add(alumno_id)
        db.commit()

    return alumno.id


def get_criterio_de_evaluacion(criterio: str, curso_id: int, db: Session):
    """Get the ID of the given criterio específico para una materia"""
    # Buscar EXACTAMENTE por nombre Y materia_id
    criterio_obj = db.query(CriterioEvaluacion).filter(
        CriterioEvaluacion.nombre == criterio,
        CriterioEvaluacion.materia_id == curso_id
    ).first()

    if not criterio_obj:
        # Crear nuevo criterio con relación explícita
        criterio_obj = CriterioEvaluacion(
            nombre=criterio,
            materia_id=curso_id
        )
        db.add(criterio_obj)
        db.commit()
        db.refresh(criterio_obj)  # Esto es crucial

    return criterio_obj.id

def get_course_id(courseCode: str, course_name: str, db: Session):
    """Get the ID of the given course or create it if it doesn't exist."""
    # Limpiar la caché primero
    db.expire_all()

    # Buscar por código exacto con sincronización explícita
    course = db.query(Materia).filter(
        Materia.codigo == courseCode
    ).with_for_update().first()

    if not course:
        # Buscar por nombre exacto con sincronización
        course = db.query(Materia).filter(
            Materia.nombre == course_name
        ).with_for_update().first()

    if not course:
        # Crear nueva materia con refresco inmediato
        course = Materia(codigo=courseCode, nombre=course_name)
        db.add(course)
        db.flush()  # Usar flush en lugar de commit para mantener la transacción
        db.refresh(course)  # Refrescar el objeto inmediatamente

    return course.id

def get_niveles_de_logro(valor: str, db: Session):
    """Get the ID of the given niveles de logro or create it if it doesn't exist."""

    valid_valores = ["A", "B", "C", "D"]

    if valor not in valid_valores:
        return None

    niveles_de_logro_obj = db.query(NivelLogro).filter(NivelLogro.valor == valor).first()

    if not niveles_de_logro_obj:
        niveles_de_logro_obj = NivelLogro(nivel_logro=valor)
        db.add(niveles_de_logro_obj)
        db.commit()

    return niveles_de_logro_obj.id

def get_description(texto):
    valor = texto.split("=", 1)[1].strip()
    return valor

def get_lista_de_criterios_evaluacion(df, curso_id: int, db: Session):
    """Obtiene criterios específicos para esta materia"""
    criterios_ids = []

    for _, row in df.iterrows():
        value = row.iloc[1]

        if (value.startswith("01 =") or
            value.startswith("02 =") or
            value.startswith("04 =") or
            value.startswith("03 =")):

            grade_description = get_description(value)

            # Debug: Verificar curso_id antes de obtener criterio
            print(f"Buscando criterio '{grade_description}' para materia_id: {curso_id}")

            criterio_id = get_criterio_de_evaluacion(grade_description, curso_id, db)

            # Debug: Verificar el criterio obtenido
            criterio = db.query(CriterioEvaluacion).get(criterio_id)
            print(f"Criterio ID: {criterio_id} - Materia asociada: {criterio.materia_id}")

            criterios_ids.append(criterio_id)

    return criterios_ids


def determinar_genero(nombre_completo: str) -> str:
    """
    Determina el género (masculino/femenino) basándose en el nombre completo.

    Args:
        nombre_completo (str): Nombre completo del estudiante

    Returns:
        str: 'MASCULINO' o 'FEMENINO'. 'MASCULINO' si no puede determinarse
    """

    terminaciones_femeninas = ['a', 'ia', 'na', 'dra', 'ela', 'nia', 'cia', 'lia', 'ta', 'ana']
    terminaciones_masculinas = ['o', 'io', 'os', 'er', 'es', 'an', 'el', 'in', 'on', 'or']

    nombres_femeninos = ['maria', 'ana', 'lucia', 'sofia', 'isabel', 'carmen', 'rosa', 'elena', 'patricia']
    nombres_masculinos = ['jose', 'juan', 'carlos', 'luis', 'miguel', 'antonio', 'david', 'francisco', 'alejandro']

    nombre = nombre_completo.lower().strip().split()[0]

    if nombre in nombres_femeninos:
        return 'FEMENINO'
    if nombre in nombres_masculinos:
        return 'MASCULINO'

    # 2. Analizar terminaciones del nombre
    for terminacion in terminaciones_femeninas:
        if nombre.endswith(terminacion):
            return 'FEMENINO'

    for terminacion in terminaciones_masculinas:
        if nombre.endswith(terminacion):
            return 'MASCULINO'

    if '-' in nombre:
        primera_parte = nombre.split('-')[0]
        if primera_parte in nombres_femeninos or any(primera_parte.endswith(t) for t in terminaciones_femeninas):
            return 'FEMENINO'
        if primera_parte in nombres_masculinos or any(primera_parte.endswith(t) for t in terminaciones_masculinas):
            return 'MASCULINO'

    return 'MASCULINO'
