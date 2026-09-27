def test_sibling_name_conflict_returns_409(client):
    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    assert r.status_code == 409
    assert r.json()["code"] == "DIRECTORY_NAME_CONFLICT"


def test_same_name_in_different_parent_allowed(client, root_dir_id):
    r = client.post(
        "/api/v1/directories", json={"name": "Q1", "parent_id": None}
    )
    assert r.status_code == 201
    top_id = r.json()["id"]

    r = client.post(
        "/api/v1/directories", json={"name": "Q1", "parent_id": top_id}
    )
    assert r.status_code == 201


def test_depth_exceeded_returns_422(client, root_dir_id):
    r = client.post(
        "/api/v1/directories", json={"name": "甲", "parent_id": root_dir_id}
    )
    assert r.status_code == 201, r.text
    child_id = r.json()["id"]

    r = client.post(
        "/api/v1/directories", json={"name": "乙", "parent_id": child_id}
    )
    assert r.status_code == 422
    assert r.json()["code"] == "DIRECTORY_DEPTH_EXCEEDED"


def test_unknown_parent_returns_404(client):
    r = client.post(
        "/api/v1/directories", json={"name": "x", "parent_id": 999999}
    )
    assert r.status_code == 404
    assert r.json()["code"] == "DIRECTORY_NOT_FOUND"


def test_delete_non_empty_returns_409(client, root_dir_id):
    r = client.post(
        "/api/v1/directories", json={"name": "父", "parent_id": None}
    )
    parent_id = r.json()["id"]
    r = client.post(
        "/api/v1/directories", json={"name": "子", "parent_id": parent_id}
    )
    assert r.status_code == 201

    r = client.delete(f"/api/v1/directories/{parent_id}")
    assert r.status_code == 409
    assert r.json()["code"] == "DIRECTORY_NOT_EMPTY"

    # remove child first, then parent succeeds
    child = next(
        n
        for n in client.get("/api/v1/directories").json()["tree"]
        if n["name"] == "父"
    )["children"][0]
    r = client.delete(f"/api/v1/directories/{child['id']}")
    assert r.status_code == 204
    r = client.delete(f"/api/v1/directories/{parent_id}")
    assert r.status_code == 204


def test_delete_directory_with_file_returns_409(client, root_dir_id, sample_csv_bytes):
    r = client.post(
        "/api/v1/files/upload",
        files={"file": ("a.csv", sample_csv_bytes, "text/csv")},
        data={"directory_id": str(root_dir_id)},
    )
    assert r.status_code == 201

    r = client.delete(f"/api/v1/directories/{root_dir_id}")
    assert r.status_code == 409
    assert r.json()["code"] == "DIRECTORY_NOT_EMPTY"


def test_name_whitespace_trimming(client):
    r = client.post(
        "/api/v1/directories", json={"name": "  销售  ", "parent_id": None}
    )
    assert r.status_code == 201
    assert r.json()["name"] == "销售"

    r = client.post(
        "/api/v1/directories", json={"name": "   ", "parent_id": None}
    )
    assert r.status_code == 422


def test_rename_conflict_returns_409(client):
    r = client.post(
        "/api/v1/directories", json={"name": "销售", "parent_id": None}
    )
    a_id = r.json()["id"]
    r = client.post(
        "/api/v1/directories", json={"name": "市场", "parent_id": None}
    )
    b_id = r.json()["id"]

    r = client.patch(f"/api/v1/directories/{b_id}", json={"name": "销售"})
    assert r.status_code == 409
    assert r.json()["code"] == "DIRECTORY_NAME_CONFLICT"

    r = client.patch(f"/api/v1/directories/{a_id}", json={"name": "  销售二  "})
    assert r.status_code == 200
    assert r.json()["name"] == "销售二"
