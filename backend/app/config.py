from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Interview Mirror API"
    cors_origins: str = "http://localhost:5173"
    max_resume_size_mb: int = 10
    database_path: str = "interview_mirror.db"
    auth_secret: str = "change-this-secret-in-production"
    auth_token_expire_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
