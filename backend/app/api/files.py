from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..errors import file_name_conflict, not_found
from ..models import DataFile, Directory, Report
from ..schemas import ColumnsOut, FileMove, FileOut
from ..services.parser import infer_columns, read_table
from ..services.storage import delete_file, resolve_path, save_upload

router = APIRouter()


def _file_dict(data_file: DataFile) -> dict:
    return {
        "id": data_file.id,
        "name": data_file.name,
        "format": data_file.format.value,
        "size_bytes": data_file.size_bytes,
        "directory_id": data_file.directory_id,
        "uploaded_at": data_file.uploaded_at.isoformat()
        if data_file.uploaded_at
        else None,
    }


@router.post("/files/upload", status_code=201, response_model=FileOut)
def upload_file(
    file: UploadFile = File(...),
    directory_id: int = Form(...),
    db: Session = Depends(get_db),
) -> DataFile:
    return save_upload(file, directory_id, db)


@router.get("/files/{file_id}/columns", response_model=ColumnsOut)
def file_columns(file_id: int, db: Session = Depends(get_db)) -> dict:
    data_file = db.get(DataFile, file_id)
    if data_file is None:
        raise not_found("FILE_NOT_FOUND", "文件不存在")
    df = read_table(resolve_path(data_file), data_file.format.value, settings.max_rows)
    return {"columns": infer_columns(df), "row_count": int(len(df))}


@router.delete("/files/{file_id}", status_code=204)
def remove_file(file_id: int, db: Session = Depends(get_db)) -> None:
    data_file = db.get(DataFile, file_id)
    if data_file is None:
        raise not_found("FILE_NOT_FOUND", "文件不存在")
    for report in db.query(Report).filter(Report.file_id == file_id).all():
        db.delete(report)
    db.commit()
    delete_file(data_file, db)


@router.post("/files/{file_id}/move")
def move_file(file_id: int, body: FileMove, db: Session = Depends(get_db)) -> dict:
    data_file = db.get(DataFile, file_id)
    if data_file is None:
        raise not_found("FILE_NOT_FOUND", "文件不存在")
    target_id = body.target_directory_id
    target = db.get(Directory, target_id)
    if target is None:
        raise not_found("DIRECTORY_NOT_FOUND", "目标目录不存在")
    if target_id == data_file.directory_id:
        return _file_dict(data_file)
    duplicate = (
        db.query(DataFile)
        .filter(DataFile.directory_id == target_id, DataFile.name == data_file.name)
        .first()
    )
    if duplicate is not None:
        raise file_name_conflict(f"目标目录中已存在同名文件：{data_file.name}")
    data_file.directory_id = target_id
    db.commit()
    db.refresh(data_file)
    return _file_dict(data_file)
