"""T012: Unit tests for overview report computation (FR-007, SC-005)."""

import pandas as pd

from app.services.report import build_report_content

FIXTURE = pd.DataFrame(
    {
        "city": ["beijing", "shanghai", "beijing", None, "shanghai"],
        "amount": [100.0, 200.0, 300.0, None, 50.0],
        "note": ["", "x", "", "y", ""],
    }
)


def _file_meta():
    return {"name": "sample.csv", "generated_at": "2026-09-24T00:00:00"}


def test_overview_dataset_counts():
    content = build_report_content("overview", FIXTURE, _file_meta(), {})
    assert content["dataset"]["row_count"] == 5
    assert content["dataset"]["column_count"] == 3
    assert content["file"]["name"] == "sample.csv"


def test_overview_field_list():
    content = build_report_content("overview", FIXTURE, _file_meta(), {})
    fields = next(s for s in content["sections"] if s["title"] == "字段清单")
    names = [row[0] for row in fields["rows"]]
    assert names == ["city", "amount", "note"]


def test_overview_numeric_stats_exact():
    content = build_report_content("overview", FIXTURE, _file_meta(), {})
    stats = next(s for s in content["sections"] if s["title"] == "数值列统计")
    amount = next(i for i in stats["items"] if i["column"] == "amount")
    assert amount["min"] == 50.0
    assert amount["max"] == 300.0
    assert amount["mean"] == 162.5
    assert amount["null_count"] == 1


def test_overview_only_numeric_columns_have_stats():
    content = build_report_content("overview", FIXTURE, _file_meta(), {})
    stats = next(s for s in content["sections"] if s["title"] == "数值列统计")
    assert [i["column"] for i in stats["items"]] == ["amount"]
