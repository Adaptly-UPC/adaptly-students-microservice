import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()

class Settings(BaseSettings):
    """Clase de configuración de la aplicación FastAPI, proveendo variables de entorno."""
    database_url: str = os.getenv("DATABASE_URL")
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
