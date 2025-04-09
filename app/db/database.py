from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Esta función provee una instancia de la base de datos para la solicitud actual de FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
