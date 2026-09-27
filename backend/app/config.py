from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "report_tool"

    database_url: str = ""

    upload_dir: str = "uploads"
    export_dir: str = "exports"

    max_upload_bytes: int = 10 * 1024 * 1024
    max_rows: int = 100_000

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
            f"?charset=utf8mb4"
        )

    @property
    def upload_path(self) -> Path:
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def export_path(self) -> Path:
        path = BASE_DIR / self.export_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
