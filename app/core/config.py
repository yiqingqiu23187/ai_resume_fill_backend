from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Resume Autofill"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_resume_autofill"
    POSTGRES_PORT: int = 5432
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        values = info.data if hasattr(info, 'data') else {}
        return f"postgresql+asyncpg://{values.get('POSTGRES_USER', 'postgres')}:{values.get('POSTGRES_PASSWORD', 'postgres')}@{values.get('POSTGRES_SERVER', 'localhost')}:{values.get('POSTGRES_PORT', 5432)}/{values.get('POSTGRES_DB', 'ai_resume_autofill')}"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # AI Service (Dashscope - 阿里千问)
    DASHSCOPE_API_KEY: Optional[str] = None
    AI_MODEL: str = "qwen-turbo"
    
    # Activation Code Settings
    DEFAULT_ACTIVATION_USES: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()