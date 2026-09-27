from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .api import directories, files, reports, templates
from .db import get_db, init_db
from .errors import register_error_handlers
from .seed import seed_templates

app = FastAPI(title="Report Uploader API", version="0.1.0")

register_error_handlers(app)

API_PREFIX = "/api/v1"

app.include_router(directories.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    from .db import SessionLocal

    db = SessionLocal()
    try:
        seed_templates(db)
    finally:
        db.close()


@app.get(f"{API_PREFIX}/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
