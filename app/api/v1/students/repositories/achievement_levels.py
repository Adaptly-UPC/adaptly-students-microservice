from app.api.v1.students.models import NivelLogro

class AchievementLevelsRepository:
    """Repositorio para manejo de niveles de logro"""
    def __init__(self, db):
        self.db = db

    def get_achievement_level_by_name(self, achievement_value: str) -> NivelLogro:
        """Obtiene un nivel de logro de la base de datos"""
        return self.db.query(NivelLogro).filter(NivelLogro.valor == achievement_value).first()

    def create_achievement_level(self, achievement_value: str) -> NivelLogro:
        """Crea un nivel de logro en la base de datos"""
        achievement_level = NivelLogro(valor=achievement_value)
        self.db.add(achievement_level)
        self.db.commit()
        self.db.refresh(achievement_level)
        return achievement_level

    def get_or_create_achievement_level(self, achievement_value: str) -> NivelLogro:
        """Obtiene o crea un nivel de logro en la base de datos"""
        achievement_level = self.get_achievement_level_by_name(achievement_value)
        if not achievement_level:
            achievement_level = self.create_achievement_level(achievement_value)
        return achievement_level

