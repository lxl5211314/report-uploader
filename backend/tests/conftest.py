import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="reporttool_test_"))


def _mysql_password() -> str:
    if pw := os.getenv("MYSQL_PASSWORD"):
        return pw
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("MYSQL_PASSWORD="):
                return line.split("=", 1)[1].strip()
    return ""


os.environ["DATABASE_URL"] = (
    f"mysql+pymysql://root:{_mysql_password()}@127.0.0.1:3306/report_tool_test"
)
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["EXPORT_DIR"] = str(_TMP / "exports")

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, engine, init_db
from app.models import Base
from app.seed import seed_templates


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    init_db()
    session = SessionLocal()
    try:
        seed_templates(session)
    finally:
        session.close()


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def root_dir_id(db) -> int:
    from app.models import Directory

    root = db.query(Directory).filter(Directory.name == "根目录").one()
    return root.id


@pytest.fixture()
def sample_csv_bytes() -> bytes:
    return (
        "city,amount,note\n"
        "beijing,100,\n"
        "shanghai,200,x\n"
        "beijing,300,\n"
        "shenzhen,,y\n"
        "shanghai,50,\n"
    ).encode("utf-8")
