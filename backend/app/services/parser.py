from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..errors import file_unparseable

SUPPORTED_EXTENSIONS = {".csv": "csv", ".xlsx": "xlsx"}


def read_table(path: Path, fmt: str, max_rows: int) -> pd.DataFrame:
    try:
        if fmt == "csv":
            df = _read_csv(path)
        elif fmt == "xlsx":
            df = pd.read_excel(path, engine="openpyxl")
        else:
            raise file_unparseable(f"不支持的格式：{fmt}")
    except Exception:
        raise file_unparseable()

    if df is None or len(df.columns) == 0 or len(df) == 0:
        raise file_unparseable("文件为空或仅有表头")
    if len(df) > max_rows:
        raise file_unparseable(f"行数超过上限（{max_rows} 行）")
    return df


def _read_csv(path: Path) -> pd.DataFrame:
    last_decode_error: Exception | None = None
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_decode_error = exc
            continue
        except Exception:
            raise file_unparseable()
    if last_decode_error is not None:
        raise file_unparseable("文件编码无法识别")
    raise file_unparseable()


def infer_columns(df: pd.DataFrame) -> list[dict]:
    columns = []
    for name in df.columns:
        series = df[name]
        if pd.api.types.is_numeric_dtype(series):
            col_type = "number"
        elif pd.api.types.is_datetime64_any_dtype(series):
            col_type = "other"
        else:
            col_type = "string"
        columns.append({"name": str(name), "type": col_type})
    return columns
