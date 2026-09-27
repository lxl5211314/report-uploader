def test_directory_flow_end_to_end(client, root_dir_id, sample_csv_bytes):
    # create
    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    assert r.status_code == 201
    sales_id = r.json()["id"]

    # duplicate → 409
    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    assert r.status_code == 409
    assert r.json()["code"] == "DIRECTORY_NAME_CONFLICT"

    # upload file into 根目录 then move it to 销售
    r = client.post(
        "/api/v1/files/upload",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
        data={"directory_id": str(root_dir_id)},
    )
    assert r.status_code == 201
    file_id = r.json()["id"]

    r = client.post(
        f"/api/v1/files/{file_id}/move",
        json={"target_directory_id": sales_id},
    )
    assert r.status_code == 200

    # tree reflects new location
    tree = client.get("/api/v1/directories").json()["tree"]
    sales_node = next(n for n in tree if n["name"] == "销售")
    assert [f["name"] for f in sales_node["files"]] == ["sales.csv"]
    root_node = next(n for n in tree if n["id"] == root_dir_id)
    assert all(f["name"] != "sales.csv" for f in root_node["files"])

    # persistence (FR-009): fresh session re-query shows the row
    from app.db import SessionLocal
    from app.models import DataFile

    fresh = SessionLocal()
    try:
        stored = fresh.get(DataFile, file_id)
        assert stored is not None
        assert stored.directory_id == sales_id
    finally:
        fresh.close()

    # move-to-same-directory is a no-op
    r = client.post(
        f"/api/v1/files/{file_id}/move",
        json={"target_directory_id": sales_id},
    )
    assert r.status_code == 200
    assert r.json()["directory_id"] == sales_id

    # move to target with same-name file → 409
    r = client.post(
        "/api/v1/directories", json={"name": "归档", "parent_id": None}
    )
    archive_id = r.json()["id"]
    r = client.post(
        "/api/v1/files/upload",
        files={"file": ("sales.csv", sample_csv_bytes, "text/csv")},
        data={"directory_id": str(archive_id)},
    )
    assert r.status_code == 201
    r = client.post(
        f"/api/v1/files/{file_id}/move",
        json={"target_directory_id": archive_id},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "FILE_NAME_CONFLICT"
