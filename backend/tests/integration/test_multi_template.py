def test_multi_template_flow(client, root_dir_id, sample_csv_bytes):
    r = client.post(
        "/api/v1/files/upload",
        files={"file": ("multi.csv", sample_csv_bytes, "text/csv")},
        data={"directory_id": str(root_dir_id)},
    )
    assert r.status_code == 201, r.text
    file_id = r.json()["id"]

    templates = {
        t["code"]: t["id"]
        for t in client.get("/api/v1/templates").json()["templates"]
    }

    # overview
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={"template_id": templates["overview"], "params": {}},
    )
    assert r.status_code == 201, r.text
    overview_content = r.json()["content"]
    assert overview_content["dataset"]["row_count"] == 5

    # group_summary
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={
            "template_id": templates["group_summary"],
            "params": {"group_by": "city", "value_by": "amount", "agg": "sum"},
        },
    )
    assert r.status_code == 201, r.text
    group_content = r.json()["content"]
    rows = next(
        s["rows"]
        for s in group_content["sections"]
        if s["title"].startswith("分组汇总")
    )
    assert ["beijing", 2, 400.0] in rows

    # top_n
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={
            "template_id": templates["top_n"],
            "params": {"sort_by": "amount", "n": 5},
        },
    )
    assert r.status_code == 201, r.text

    # all three templates present, one report each
    r = client.get(f"/api/v1/files/{file_id}/reports")
    reports = r.json()["reports"]
    assert sorted(rep["template"]["code"] for rep in reports) == [
        "group_summary",
        "overview",
        "top_n",
    ]

    # second group_summary generation overwrites — still one report per template
    r = client.post(
        f"/api/v1/files/{file_id}/reports",
        json={
            "template_id": templates["group_summary"],
            "params": {"group_by": "city"},
        },
    )
    assert r.status_code == 201, r.text
    r = client.get(f"/api/v1/files/{file_id}/reports")
    reports = r.json()["reports"]
    assert len(reports) == 3
    assert (
        sum(1 for rep in reports if rep["template"]["code"] == "group_summary")
        == 1
    )
    # overwrite switched params/content to count-only variant
    overwritten = next(
        rep for rep in reports if rep["template"]["code"] == "group_summary"
    )
    assert overwritten["params"] == {"group_by": "city"}
    assert overwritten["content"]["dataset"] == {"row_count": 5, "column_count": 3}

    # each report has a downloadable xlsx
    for rep in reports:
        r = client.get(f"/api/v1/reports/{rep['id']}/download")
        assert r.status_code == 200
        assert r.content[:2] == b"PK"
