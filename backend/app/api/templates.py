from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ReportTemplate
from ..schemas import TemplatesOut

router = APIRouter()


@router.get("/templates", response_model=TemplatesOut)
def list_templates(db: Session = Depends(get_db)) -> dict:
    templates = db.query(ReportTemplate).order_by(ReportTemplate.id).all()
    return {
        "templates": [
            {
                "id": t.id,
                "code": t.code,
                "name": t.name,
                "description": t.description,
                "requires_column": t.requires_column.value,
                "defaults": t.default_params or {},
            }
            for t in templates
        ]
    }
