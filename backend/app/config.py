"""BPLab Trace LIMS — FastAPI 配置"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 应用 ──
    APP_NAME: str = "BPLab Trace LIMS"
    APP_VERSION: str = "11.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "bplab-secret-change-in-production-use-env-var"

    # ── JWT ──
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    JWT_REFRESH_DAYS: int = 30

    # ── PostgreSQL ──
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "bplab"

    # ── 上传 ──
    UPLOAD_DIR: Path = Path("data/uploads")
    ATTACHMENT_DIR: Path = Path("data/attachments")
    SIGNATURE_DIR: Path = Path("data/signatures")
    TEMPLATE_DIR: Path = Path(__file__).parent.parent.parent / "templates"

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["*"]

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
