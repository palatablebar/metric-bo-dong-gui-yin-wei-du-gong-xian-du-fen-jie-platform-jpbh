"""集中配置：全部来自环境变量，默认值与 .env.example 一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "swingattr"
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "swingattr"
    db_user: str = "swingattr"
    db_password: str = "swingattr_pw_2026"

    jwt_secret: str = "swingattr-jwt-secret-change-me-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480

    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_per_minute: int = 300
    rate_limit_write_per_minute: int = 60

    # 日报投递：配置后走真实 webhook；留空则模拟成功（演示环境无真实凭据）
    feishu_webhook_url: str = ""
    email_webhook_url: str = ""
    wecom_webhook_url: str = ""
    delivery_timeout_seconds: int = 5
    # 逗号分隔的渠道名（feishu,email,wecom）：强制这些渠道投递失败，演示重试链路
    delivery_fail_channels: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
