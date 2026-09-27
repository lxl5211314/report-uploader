def test_directory_crud_happy_paths(client):
    # create → 201
    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    assert r.status_code == 201
    dir_id = r.json()["id"]
    assert r.json()["name"] == "销售"

    # tree reflects it
    tree = client.get("/api/v1/directories").json()["tree"]
    assert any(n["name"] == "销售" for n in tree)

    # rename → 200
    r = client.patch(f"/api/v1/directories/{dir_id}", json={"name": "销售部"})
    assert r.status_code == 200
    assert r.json()["name"] == "销售部"

    # delete empty → 204
    r = client.delete(f"/api/v1/directories/{dir_id}")
    assert r.status_code == 204

    tree = client.get("/api/v1/directories").json()["tree"]
    assert not any(n["name"] == "销售部" for n in tree)


def test_rename_unknown_directory_404(client):
    r = client.patch("/api/v1/directories/999999", json={"name": "x"})
    assert r.status_code == 404
    assert r.json()["code"] == "DIRECTORY_NOT_FOUND"


def test_delete_unknown_directory_404(client):
    r = client.delete("/api/v1/directories/999999")
    assert r.status_code == 404
    assert r.json()["code"] == "DIRECTORY_NOT_FOUND"


def _upload(client, directory_id, name, sample_csv_bytes):
    r = client.post(
        "/api/v1/files/upload",
        files={"file": (name, sample_csv_bytes, "text/csv")},
        data={"directory_id": str(directory_id)},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_move_file_happy_path(client, root_dir_id, sample_csv_bytes):
    file_obj = _upload(client, root_dir_id, "a.csv", sample_csv_bytes)

    r = client.post(
        "/api/v1/directories", json={"name": "目标", "parent_id": None}
    )
    target_id = r.json()["id"]

    r = client.post(
        f"/api/v1/files/{file_obj['id']}/move",
        json={"target_directory_id": target_id},
    )
    assert r.status_code == 200
    assert r.json()["directory_id"] == target_id

    # tree reflects new location
    tree = client.get("/api/v1/directories").json()["tree"]
    target_node = next(n for n in tree if n["name"] == "目标")
    assert [f["name"] for f in target_node["files"]] == ["a.csv"]


def test_move_to_same_directory_is_noop(client, root_dir_id, sample_csv_bytes):
    file_obj = _upload(client, root_dir_id, "a.csv", sample_csv_bytes)
    r = client.post(
        f"/api/v1/files/{file_obj['id']}/move",
        json={"target_directory_id": root_dir_id},
    )
    assert r.status_code == 200
    assert r.json()["directory_id"] == root_dir_id


def test_move_name_conflict_409(client, root_dir_id, sample_csv_bytes):
    file_obj = _upload(client, root_dir_id, "a.csv", sample_csv_bytes)
    r = client.post(
        "/api/v1/directories", json={"name": "目标", "parent_id": None}
    )
    target_id = r.json()["id"]
    _upload(client, target_id, "a.csv", sample_csv_bytes)

    r = client.post(
        f"/api/v1/files/{file_obj['id']}/move",
        json={"target_directory_id": target_id},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "FILE_NAME_CONFLICT"


def test_move_unknown_targets_404(client, root_dir_id, sample_csv_bytes):
    file_obj = _upload(client, root_dir_id, "a.csv", sample_csv_bytes)

    r = client.post(
        f"/api/v1/files/{file_obj['id']}/move",
        json={"target_directory_id": 999999},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "DIRECTORY_NOT_FOUND"

    r = client.post("/api/v1/files/999999/move", json={"target_directory_id": 1})
    assert r.status_code == 404
    assert r.json()["code"] == "FILE_NOT_FOUND"


def test_delete_file_removes_it_and_its_reports(
    client, root_dir_id, sample_csv_bytes
):
    file_obj = _upload(client, root_dir_id, "a.csv", sample_csv_bytes)
    overview_id = next(
        t["id"]
        for t in client.get("/api/v1/templates").json()["templates"]
        if t["code"] == "overview"
    )
    r = client.post(
        f"/api/v1/files/{file_obj['id']}/reports",
        json={"template_id": overview_id, "params": {}},
    )
    assert r.status_code == 201
    report_id = r.json()["id"]

    r = client.delete(f"/api/v1/files/{file_obj['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/reports/{report_id}")
    assert r.status_code == 404

    tree = client.get("/api/v1/directories").json()["tree"]
    root_node = next(n for n in tree if n["id"] == root_dir_id)
    assert root_node["files"] == []
