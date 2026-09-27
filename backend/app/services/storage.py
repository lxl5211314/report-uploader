from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..errors import file_name_conflict, file_too_large, not_found, unsupported_format
from ..models import DataFile, Directory, FileFormat

SUPPORTED_EXTENSIONS = {".csv": FileFormat.csv, ".xlsx": FileFormat.xlsx}


def save_upload(upload: UploadFile, directory_id: int, db: Session) -> DataFile:
    original_name = Path(upload.filename or "").name
    if not original_name:
        raise unsupported_format("缺少文件名")

    ext = Path(original_name).suffix.lower()
    fmt = SUPPORTED_EXTENSIONS.get(ext)
    if fmt is None:
        raise unsupported_format()

    content = upload.file.read()
    if len(content) > settings.max_upload_bytes:
        raise file_too_large(
            f"文件超出大小上限（{settings.max_upload_bytes // (1024 * 1024)}MB）"
        )

    directory = db.get(Directory, directory_id)
    if directory is None:
        raise not_found("DIRECTORY_NOT_FOUND", "目录不存在")

    duplicate = (
        db.query(DataFile)
        .filter(DataFile.directory_id == directory_id, DataFile.name == original_name)
        .first()
    )
    if duplicate is not None:
        raise file_name_conflict(f"目录中已存在同名文件：{original_name}")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = settings.upload_path / stored_name
    file_path.write_bytes(content)

    data_file = DataFile(
        name=original_name,
        format=fmt,
        size_bytes=len(content),
        directory_id=directory_id,
        stored_path=stored_name,
    )
    db.add(data_file)
    db.commit()
    db.refresh(data_file)
    return data_file


def resolve_path(data_file: DataFile) -> Path:
    return settings.upload_path / data_file.stored_path


def delete_file(data_file: DataFile, db: Session) -> None:
    path = resolve_path(data_file)
    if path.exists():
        path.unlink()
    db.delete(data_file)
    db.commit()
