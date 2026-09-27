from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ErrorBody(BaseModel):
    code: str
    message: str


class DirectoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=191)
    parent_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("目录名称不能为空")
        return v


class DirectoryRename(BaseModel):
    name: str = Field(min_length=1, max_length=191)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("目录名称不能为空")
        return v


class FileOut(BaseModel):
    id: int
    name: str
    format: Literal["csv", "xlsx"]
    size_bytes: int
    directory_id: int
    uploaded_at: datetime


class DirectoryNode(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    children: list["DirectoryNode"] = []
    files: list[FileOut] = []


class TreeOut(BaseModel):
    tree: list[DirectoryNode]


class FileMove(BaseModel):
    target_directory_id: int


class ColumnOut(BaseModel):
    name: str
    type: Literal["string", "number", "other"]


class ColumnsOut(BaseModel):
    columns: list[ColumnOut]
    row_count: int


class TemplateOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    requires_column: Literal["none", "group", "top"]
    defaults: dict[str, Any] = {}


class TemplatesOut(BaseModel):
    templates: list[TemplateOut]


class ReportCreate(BaseModel):
    template_id: int
    params: dict[str, Any] = Field(default_factory=dict)


class ReportOut(BaseModel):
    id: int
    file_id: int
    template_id: int
    template: Optional[TemplateOut] = None
    status: Literal["generating", "succeeded", "failed"]
    params: dict[str, Any] = {}
    content: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    generated_at: Optional[datetime] = None


class ReportListOut(BaseModel):
    reports: list[ReportOut]


class HealthOut(BaseModel):
    status: str
