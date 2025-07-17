import os
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    
    # Basic app settings
    APP_NAME: str = "Romanian Public Procurement Platform"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # Database settings - provide defaults for Railway
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost/db",
        env="DATABASE_URL"
    )
    
    # Security settings - provide defaults
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Optional settings
    REDIS_URL: Optional[str] = None
    SICAP_API_URL: str = "https://sicap.gov.ro/api"
    ANRMAP_API_URL: str = "https://anrmap.gov.ro/api"
    LOG_LEVEL: str = "INFO"
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                # Handle list-like string
                return [i.strip().strip('"\'') for i in v.strip("[]").split(",")]
            else:
                # Handle comma-separated string
                return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields that might be set by Railway
        extra = "allow"

# Create settings instance
settings = Settings()