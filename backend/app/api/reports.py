from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..errors import ApiError, not_found
from ..models import DataFile, Report, ReportStatus, ReportTemplate
from ..schemas import ReportCreate, ReportListOut, ReportOut
from ..services.parser import read_table
from ..services.report import build_report_content, export_xlsx
from ..services.storage import resolve_path

router = APIRouter()


def _template_out(t: ReportTemplate) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "description": t.description,
        "requires_column": t.requires_column.value,
        "defaults": t.default_params or {},
    }


def _report_out(report: Report, template: ReportTemplate | None = None) -> dict:
    return {
        "id": report.id,
        "file_id": report.file_id,
        "template_id": report.template_id,
        "template": _template_out(template) if template is not None else None,
        "status": report.status.value,
        "params": report.params or {},
        "content": report.content_json,
        "error_message": report.error_message,
        "generated_at": report.generated_at.isoformat()
        if report.generated_at
        else None,
    }


@router.post("/files/{file_id}/reports", status_code=201, response_model=ReportOut)
def generate_report(
    file_id: int, body: ReportCreate, db: Session = Depends(get_db)
) -> dict:
    data_file = db.get(DataFile, file_id)
    if data_file is None:
        raise not_found("FILE_NOT_FOUND", "文件不存在")
    template = db.get(ReportTemplate, body.template_id)
    if template is None:
        raise not_found("TEMPLATE_NOT_FOUND", "报表模板不存在")

    df = read_table(resolve_path(data_file), data_file.format.value, settings.max_rows)
    file_meta = {
        "name": data_file.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    content = build_report_content(template.code, df, file_meta, body.params)

    report = (
        db.query(Report)
        .filter(Report.file_id == file_id, Report.template_id == body.template_id)
        .first()
    )
    if report is None:
        report = Report(
            file_id=file_id,
            template_id=body.template_id,
            status=ReportStatus.generating,
        )
        db.add(report)
    else:
        report.status = ReportStatus.generating
        report.error_message = None
    report.params = body.params
    db.commit()
    db.refresh(report)

    try:
        export_path = settings.export_path / f"report_{report.id}.xlsx"
        export_xlsx(content, export_path)
    except Exception:
        report.status = ReportStatus.failed
        report.error_message = "报表导出失败"
        db.commit()
        raise ApiError("EXPORT_FAILED", "报表导出失败", 500)

    report.status = ReportStatus.succeeded
    report.content_json = content
    report.export_path = f"report_{report.id}.xlsx"
    report.generated_at = datetime.now()
    db.commit()
    db.refresh(report)
    return _report_out(report, template)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if report is None:
        raise not_found("REPORT_NOT_FOUND", "报表不存在")
    template = db.get(ReportTemplate, report.template_id)
    return _report_out(report, template)


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise not_found("REPORT_NOT_FOUND", "报表不存在")
    path: Path = settings.export_path / (
        report.export_path or f"report_{report.id}.xlsx"
    )
    if not path.exists():
        if not report.content_json:
            raise not_found("REPORT_NOT_FOUND", "报表内容不存在")
        export_xlsx(report.content_json, path)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"report_{report.id}.xlsx",
    )


@router.get("/files/{file_id}/reports", response_model=ReportListOut)
def list_file_reports(file_id: int, db: Session = Depends(get_db)) -> dict:
    if db.get(DataFile, file_id) is None:
        raise not_found("FILE_NOT_FOUND", "文件不存在")
    reports = (
        db.query(Report)
        .filter(Report.file_id == file_id)
        .order_by(Report.template_id)
        .all()
    )
    out = []
    for r in reports:
        template = db.get(ReportTemplate, r.template_id)
        out.append(_report_out(r, template))
    return {"reports": out}
