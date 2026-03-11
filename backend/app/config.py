from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://ktranslate:ktranslate@db:5432/ktranslate"
    redis_url: str = "redis://redis:6379"
    
    # Translation APIs
    google_translate_api_key: Optional[str] = None
    deepl_api_key: Optional[str] = None
    
    # App
    secret_key: str = "dev-secret-key-change-in-production"
    max_batch_size: int = 500
    max_file_size_mb: int = 25
    image_retention_days: int = 90
    
    # Storage
    storage_backend: str = "local"
    upload_dir: str = "/app/uploads"
    output_dir: str = "/app/outputs"
    
    class Config:
        env_file = ".env"

settings = Settings()
