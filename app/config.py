from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    server_port: int = 8080
    db_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/journal_monitor"
    db_dsn_sync: str = ""  # optional; default derived from db_dsn
    redis_addr: str = "localhost:6379"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_template_realtime: str = ""
    wechat_template_daily: str = ""
    jwt_secret: str = "change-me-to-something-secure"
    fetch_interval_minutes: int = 30
    web_dist: str = "web/dist"

    def sync_dsn(self) -> str:
        if self.db_dsn_sync:
            return self.db_dsn_sync
        return self.db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    def validate_for_run(self) -> None:
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must not be empty")

    def redis_host_port(self) -> tuple[str, int]:
        host, _, port = self.redis_addr.partition(":")
        return host or "localhost", int(port or "6379")

@lru_cache
def get_settings() -> Settings:
    return Settings()
