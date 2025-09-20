"""
Core configuration module for the application.
Handles environment variables and application settings.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field, BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Security
    secret_key: str = Field(default="please_change_me", env="SECRET_KEY")
    
    # Database
    database_url: str = Field(default="sqlite:///./data/app.db", env="DATABASE_URL")
    
    # JWT Configuration
    jwt_access_ttl_seconds: int = Field(default=900, env="JWT_ACCESS_TTL_SECONDS")  # 15 minutes
    jwt_refresh_ttl_seconds: int = Field(default=1209600, env="JWT_REFRESH_TTL_SECONDS")  # 14 days
    jwt_algorithm: str = "HS256"
    
    # Cookie Configuration
    cookie_secure: bool = Field(default=True, env="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", env="COOKIE_SAMESITE")
    cookie_httponly: bool = True
    
    # Registration
    allow_self_register: bool = Field(default=False, env="ALLOW_SELF_REGISTER")
    
    # SMTP Configuration
    smtp_host: str = Field(default="smtp.example.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str = Field(default="no-reply@example.com", env="SMTP_USER")
    smtp_pass: str = Field(default="", env="SMTP_PASS")
    smtp_use_tls: bool = True
    
    # Frontend
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")
    
    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 5
    
    # Application
    app_name: str = "MeidaSupport Admin System"
    debug: bool = Field(default=False, env="DEBUG")
    
    # CSV Export Configuration
    exports_dir: Path = Field(default=Path("./data/exports"), env="EXPORTS_DIR")
    appointments_csv: Path = Field(default=Path("./data/exports/appointments.csv"), env="APPOINTMENTS_CSV")
    
    # File Upload Configuration
    upload_root: Path = Field(default=Path("./data/uploads"), env="UPLOAD_ROOT")
    ticket_receipt_dir: str = Field(default="tickets", env="TICKET_RECEIPT_DIR")
    max_upload_mb: int = Field(default=8, env="MAX_UPLOAD_MB")
    allowed_image_types: str = Field(default="jpg,jpeg,png,webp", env="ALLOWED_IMAGE_TYPES")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保导出目录存在
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        # 确保上传目录存在
        self.upload_root.mkdir(parents=True, exist_ok=True)
        (self.upload_root / self.ticket_receipt_dir).mkdir(parents=True, exist_ok=True)
    
    @property
    def allowed_image_types_list(self) -> list[str]:
        """Get allowed image types as a list."""
        return [t.strip().lower() for t in self.allowed_image_types.split(',')]
    
    @property
    def max_upload_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 