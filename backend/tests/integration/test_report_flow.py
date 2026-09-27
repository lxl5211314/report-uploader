def test_full_report_flow(client, root_dir_id, sample_csv_bytes):
    # upload
    r = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.csv", sample_csv_bytes, "text/csv")},
        data={"directory_id": str(root_dir_id)},
    )
    assert r.status_code == 201, r.text
    file_id = r.json()["id"]

    # columns
    r = client.get(f"/api/v1/files/{file_id}/columns")
    assert r.status_code == 200, r.text
    columns_payload = r.json()
    assert columns_payload["row_count"] == 5
    names = [c["name"] for c in columns_payload["columns"]]
    assert names == ["city", "amount", "note"]

    # templates
    r = client.get("/api/v1/templates")
    assert r.status_code == 200
    templates = r.json()["templates"]
    assert len(templates) == 3
    overview = next(t for t in templates if t["code"] == "overview")

    # generate overview report
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": overview["id"], "params": {}},
    )
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["status"] == "succeeded"
    content = report["content"]
    assert content["dataset"]["row_count"] == columns_payload["row_count"]
    assert content["dataset"]["column_count"] == 3
    assert content["sections"], "overview must render sections"
    titles = [s["title"] for s in content["sections"]]
    assert "字段清单" in titles and "数值列统计" in titles

    # report is queryable by id
    r = client.get(f"/api/v1/reports/{report['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == report["id"]

    # report appears in file report list
    r = client.get(f"/api/v1/files/{file_id}/reports")
    assert r.status_code == 200
    listed = r.json()["reports"]
    assert len(listed) == 1
    assert listed[0]["template"]["code"] == "overview"

    # download xlsx
    r = client.get(f"/api/v1/reports/{report['id']}/download")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
    assert len(r.content) > 0
    assert r.content[:2] == b"PK", "xlsx is a zip container"

    # regenerate overview overwrites the same report row (FR-007)
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": overview["id"], "params": {}},
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"] == report["id"]
    r = client.get(f"/api/v1/files/{file_id}/reports")
    assert len(r.json()["reports"]) == 1
