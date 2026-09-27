from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FileFormat(str, enum.Enum):
    csv = "csv"
    xlsx = "xlsx"


class RequiresColumn(str, enum.Enum):
    none = "none"
    group = "group"
    top = "top"


class ReportStatus(str, enum.Enum):
    generating = "generating"
    succeeded = "succeeded"
    failed = "failed"


class Directory(Base):
    __tablename__ = "directory"
    __table_args__ = (UniqueConstraint("parent_id", "name", name="uq_dir_parent_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("directory.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    parent: Mapped[Directory | None] = relationship(remote_side=[id])


class DataFile(Base):
    __tablename__ = "data_file"
    __table_args__ = (UniqueConstraint("directory_id", "name", name="uq_file_dir_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[FileFormat] = mapped_column(Enum(FileFormat), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    directory_id: Mapped[int] = mapped_column(ForeignKey("directory.id"), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class ReportTemplate(Base):
    __tablename__ = "report_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    requires_column: Mapped[RequiresColumn] = mapped_column(
        Enum(RequiresColumn), nullable=False
    )
    default_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (UniqueConstraint("file_id", "template_id", name="uq_report_file_template"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("data_file.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("report_template.id"), nullable=False
    )
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), nullable=False)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    export_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
