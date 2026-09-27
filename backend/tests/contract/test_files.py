"""T010: Contract tests for POST /api/v1/files/upload (FR-002/FR-003/FR-012)."""

import io


def _upload(client, root_dir_id, name="sample.csv", content=b"a,b\n1,2\n", directory_id=None):
    return client.post(
        "/api/v1/files/upload",
        files={"file": (name, io.BytesIO(content), "application/octet-stream")},
        data={"directory_id": str(directory_id if directory_id is not None else root_dir_id)},
    )


def test_upload_ok(client, root_dir_id, sample_csv_bytes):
    r = _upload(client, root_dir_id, content=sample_csv_bytes)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "sample.csv"
    assert body["format"] == "csv"
    assert body["size_bytes"] == len(sample_csv_bytes)
    assert body["directory_id"] == root_dir_id


def test_upload_unsupported_format(client, root_dir_id):
    r = _upload(client, root_dir_id, name="not-a-table.txt", content=b"hello")
    assert r.status_code == 400
    assert r.json()["code"] == "UNSUPPORTED_FORMAT"


def test_upload_xls_rejected(client, root_dir_id):
    r = _upload(client, root_dir_id, name="old.xls", content=b"\xd0\xcf\x11\xe0")
    assert r.status_code == 400
    assert r.json()["code"] == "UNSUPPORTED_FORMAT"


def test_upload_too_large(client, root_dir_id):
    big = b"x" * (10 * 1024 * 1024 + 1)
    r = _upload(client, root_dir_id, content=big)
    assert r.status_code == 413
    assert r.json()["code"] == "FILE_TOO_LARGE"


def test_upload_duplicate_name_conflict(client, root_dir_id, sample_csv_bytes):
    assert _upload(client, root_dir_id, content=sample_csv_bytes).status_code == 201
    r = _upload(client, root_dir_id, content=sample_csv_bytes)
    assert r.status_code == 409
    assert r.json()["code"] == "FILE_NAME_CONFLICT"


def test_upload_to_missing_directory(client):
    r = _upload(client, None, directory_id=99999)
    assert r.status_code == 404
    assert r.json()["code"] == "DIRECTORY_NOT_FOUND"
