from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/org_db"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"


settings = Settings()
