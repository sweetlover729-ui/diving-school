"""
核心配置文件 - 班级制培训管理系统
"""
import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础
    APP_NAME: str = "消防潜水班级制培训管理系统"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # 数据库 - PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://wjjmac@127.0.0.1:5432/diving_platform"

    # JWT 认证
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-key-change-in-production-64bytes-00000000000000000000000000000000")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天

    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3099",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3099",
        "https://diving.alautoai.cn",
        "http://diving.alautoai.cn",
    ]

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB

    # 交互式教材数据目录
    INTERACTIVE_DATA_DIR: str = os.getenv(
        "INTERACTIVE_DATA_DIR",
        str(Path(__file__).parent.parent.parent / "static" / "interactive")
    )

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
