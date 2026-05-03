from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    FILE_UPLOAD_PATH: str = "storage/uploads"
    REDIS_BROKER_URL: str = "redis://localhost:6379/0"
    REDIS_BACKEND_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
