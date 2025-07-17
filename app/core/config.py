from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import os
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    
    # Basic app settings
    APP_NAME: str = "Romanian Public Procurement Platform"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    CORS_ORIGINS: Union[str, List[str]] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Redis settings (optional)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # External API settings
    SICAP_API_URL: str = Field(default="https://sicap.gov.ro/api", env="SICAP_API_URL")
    ANRMAP_API_URL: str = Field(default="https://anrmap.gov.ro/api", env="ANRMAP_API_URL")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Celery settings (for background tasks)
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("SECRET_KEY is required")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    """
    return Settings()

# Create global settings instance
settings = get_settings()