# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # tell pydantic-settings which .env file to load
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    MONGO_URI: str = "mongodb://localhost:27017"
    MASTER_DB: str = "org_master_db"
    JWT_SECRET: str = "secret_jwt_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
