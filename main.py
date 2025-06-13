from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.students.controllers import router as student_router
from app.api.v1.common.controllers import router as common_router
from app.api.v1.survey.controller import router as survey_router
from app.db.database import Base, engine
from app.core.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student_router, prefix="/api/v1")
app.include_router(common_router, prefix="/api/v1")
app.include_router(survey_router, prefix="/api/v1")


@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    """Retorna un mensaje de bienvenida."""
    return {"message": "Welcome to the students service API"}
