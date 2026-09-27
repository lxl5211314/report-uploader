def _upload(client, root_dir_id, sample_csv_bytes, name="sales.csv"):
    r = client.post(
        "/api/v1/files/upload",
        files={"file": (name, sample_csv_bytes, "text/csv")},
        data={"directory_id": str(root_dir_id)},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _template_id(client, code):
    return next(
        t["id"]
        for t in client.get("/api/v1/templates").json()["templates"]
        if t["code"] == code
    )


def test_group_summary_missing_required_param(client, root_dir_id, sample_csv_bytes):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    template_id = _template_id(client, "group_summary")

    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": template_id, "params": {}},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "MISSING_REQUIRED_PARAM"


def test_top_n_missing_required_param(client, root_dir_id, sample_csv_bytes):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    template_id = _template_id(client, "top_n")

    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": template_id, "params": {}},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "MISSING_REQUIRED_PARAM"


def test_invalid_params_rejected(client, root_dir_id, sample_csv_bytes):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    group_id = _template_id(client, "group_summary")
    top_id = _template_id(client, "top_n")

    cases = [
        (group_id, {"group_by": "no_such_column"}),
        (group_id, {"group_by": "city", "value_by": "note"}),
        (top_id, {"sort_by": "no_such_column"}),
        (top_id, {"sort_by": "city"}),
        (top_id, {"sort_by": "amount", "n": 0}),
        (top_id, {"sort_by": "amount", "n": 101}),
        (top_id, {"sort_by": "amount", "n": "abc"}),
    ]
    for template_id, params in cases:
        r = client.post(
            f"/api/v1/files/{file_id}/reports",
            json={"template_id": template_id, "params": params},
        )
        assert r.status_code == 422, (params, r.text)
        assert r.json()["code"] == "INVALID_PARAM", params


def test_group_summary_happy_and_overwrite(
    client, root_dir_id, sample_csv_bytes
):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    group_id = _template_id(client, "group_summary")
    params = {"group_by": "city", "value_by": "amount", "agg": "sum"}

    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": group_id, "params": params},
    )
    assert r.status_code == 201, r.text
    report_id = r.json()["id"]
    assert r.json()["status"] == "succeeded"
    rows = next(
        s["rows"]
        for s in r.json()["content"]["sections"]
        if s["title"].startswith("分组汇总")
    )
    assert ["beijing", 2, 400.0] in rows

    # regenerate (overwrite) — still a single report for this template
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": group_id, "params": params},
    )
    assert r.status_code == 201
    assert r.json()["id"] == report_id

    r = client.get(f"/api/v1/files/{file_id}/reports")
    reports = r.json()["reports"]
    assert len(reports) == 1
    assert reports[0]["template"]["code"] == "group_summary"


def test_top_n_happy(client, root_dir_id, sample_csv_bytes):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    top_id = _template_id(client, "top_n")

    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": top_id, "params": {"sort_by": "amount", "n": 5}},
    )
    assert r.status_code == 201, r.text
    section = next(
        s for s in r.json()["content"]["sections"] if s["title"].startswith("TOP")
    )
    assert section["rows"][0][0] == 1
    assert section["rows"][0][2] == 300.0
    # 全表 5 行（含 amount 为空的行，排在最后）
    assert len(section["rows"]) == 5
    assert section["rows"][-1][0] == 5


def test_unknown_template_404(client, root_dir_id, sample_csv_bytes):
    file_id = _upload(client, root_dir_id, sample_csv_bytes)
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": 999999, "params": {}},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "TEMPLATE_NOT_FOUND"


def test_unknown_file_404(client):
    r = client.post(
        "/api/v1/files/999999/reports",
        json={"template_id": 1, "params": {}},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "FILE_NOT_FOUND"
