from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Settings(BaseSettings):
    database_url: str = "sqlite:///./funnellens.db"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    frontend_origin: str = "http://localhost:5173"
    public_api_base: str = "http://127.0.0.1:8000"
    rate_limit_salt: str = "local-development-only"
    admin_seed_token: str | None = None
    public_project_ttl_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {"prepare_threshold": None}
engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": 1,
            "max_overflow": 2,
            "pool_recycle": 300,
        }
    )

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    if not inspect(engine).has_table("campaigns"):
        return
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
