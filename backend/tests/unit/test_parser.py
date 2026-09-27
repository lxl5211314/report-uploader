"""T011: Unit tests for parser service (FR-011, encoding fallback, limits)."""

import pytest

from app.errors import ApiError
from app.services.parser import infer_columns, read_table


def _write(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_read_csv_utf8(tmp_path):
    p = _write(tmp_path, "a.csv", "city,amount\nbeijing,100\n".encode("utf-8"))
    df = read_table(p, "csv", max_rows=1000)
    assert list(df.columns) == ["city", "amount"]
    assert len(df) == 1


def test_read_csv_gbk_fallback(tmp_path):
    p = _write(tmp_path, "g.csv", "城市,金额\n北京,100\n".encode("gbk"))
    df = read_table(p, "csv", max_rows=1000)
    assert list(df.columns) == ["城市", "金额"]
    assert df.iloc[0]["金额"] == 100


def test_read_csv_empty_file_raises(tmp_path):
    p = _write(tmp_path, "e.csv", b"")
    with pytest.raises(ApiError) as e:
        read_table(p, "csv", max_rows=1000)
    assert e.value.code == "FILE_UNPARSEABLE"
    assert e.value.status_code == 422


def test_read_csv_header_only_raises(tmp_path):
    p = _write(tmp_path, "h.csv", b"a,b\n")
    with pytest.raises(ApiError) as e:
        read_table(p, "csv", max_rows=1000)
    assert e.value.code == "FILE_UNPARSEABLE"


def test_read_csv_corrupt_raises(tmp_path):
    p = _write(tmp_path, "c.csv", b"\xff\xfe\x00\x00garbage,\x80\x81\n")
    with pytest.raises(ApiError) as e:
        read_table(p, "csv", max_rows=1000)
    assert e.value.code == "FILE_UNPARSEABLE"


def test_read_csv_row_limit(tmp_path):
    rows = "".join(f"v{i}\n" for i in range(10))
    p = _write(tmp_path, "big.csv", ("x\n" + rows).encode("utf-8"))
    with pytest.raises(ApiError) as e:
        read_table(p, "csv", max_rows=5)
    assert e.value.code == "FILE_UNPARSEABLE"
    assert e.value.status_code == 422


def test_infer_columns_types():
    import pandas as pd

    df = pd.DataFrame({"city": ["a", "b"], "amount": [1, 2], "mix": [1, "x"]})
    cols = {c["name"]: c["type"] for c in infer_columns(df)}
    assert cols == {"city": "string", "amount": "number", "mix": "string"}
