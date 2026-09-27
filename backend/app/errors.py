from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .db import engine


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def unsupported_format(message: str = "不支持的文件格式，仅支持 .csv 与 .xlsx") -> ApiError:
    return ApiError("UNSUPPORTED_FORMAT", message, 400)


def file_too_large(message: str = "文件超出大小上限（10MB）") -> ApiError:
    return ApiError("FILE_TOO_LARGE", message, 413)


def directory_name_conflict(message: str = "同级目录名称已存在") -> ApiError:
    return ApiError("DIRECTORY_NAME_CONFLICT", message, 409)


def file_name_conflict(message: str = "目标目录中已存在同名文件") -> ApiError:
    return ApiError("FILE_NAME_CONFLICT", message, 409)


def directory_not_empty(message: str = "目录非空，请先清空其中的文件与子目录") -> ApiError:
    return ApiError("DIRECTORY_NOT_EMPTY", message, 409)


def not_found(code: str, message: str) -> ApiError:
    return ApiError(code, message, 404)


def depth_exceeded(message: str = "目录层级超过上限（根目录 + 子目录共 2 层）") -> ApiError:
    return ApiError("DIRECTORY_DEPTH_EXCEEDED", message, 422)


def missing_required_param(message: str) -> ApiError:
    return ApiError("MISSING_REQUIRED_PARAM", message, 422)


def invalid_param(message: str) -> ApiError:
    return ApiError("INVALID_PARAM", message, 422)


def file_unparseable(message: str = "文件无法解析（空文件、仅表头或内容损坏）") -> ApiError:
    return ApiError("FILE_UNPARSEABLE", message, 422)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, exc: SQLAlchemyError):
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务内部错误"},
        )
