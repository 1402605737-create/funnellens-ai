import os
import tempfile
from pathlib import Path


database_path = Path(tempfile.gettempdir()) / "funnellens_pytest.db"
database_path.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
os.environ["PUBLIC_API_BASE"] = "https://funnellens-ai-api.vercel.app"
os.environ["RATE_LIMIT_SALT"] = "pytest-rate-limit-salt"


def pytest_sessionfinish(session, exitstatus) -> None:
    from app.database import engine

    engine.dispose()
    database_path.unlink(missing_ok=True)
