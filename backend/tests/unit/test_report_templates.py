import pandas as pd
import pytest

from app.errors import ApiError
from app.services.report import build_report_content

FIXTURE = pd.DataFrame(
    {
        "city": ["beijing", "shanghai", "beijing", "shenzhen", "shanghai"],
        "amount": [100.0, 200.0, 300.0, None, 50.0],
        "note": ["", "x", "", "y", ""],
    }
)

META = {"name": "fixture.csv", "generated_at": "2026-01-01T00:00:00"}


def _section(content, title):
    return next(s for s in content["sections"] if s["title"] == title)


def test_group_summary_exact_aggregates():
    content = build_report_content(
        "group_summary",
        FIXTURE,
        META,
        {"group_by": "city", "value_by": "amount", "agg": "sum"},
    )
    section = _section(content, "分组汇总（按 city）")
    assert section["type"] == "table"
    assert section["columns"] == ["city", "行数", "amount_sum"]
    # sorted by 行数 desc; ties keep alphabetical group order
    assert section["rows"] == [
        ["beijing", 2, 400.0],
        ["shanghai", 2, 250.0],
        ["shenzhen", 1, 0.0],
    ]


def test_group_summary_mean_and_count_only():
    content = build_report_content(
        "group_summary",
        FIXTURE,
        META,
        {"group_by": "city", "value_by": "amount", "agg": "mean"},
    )
    section = _section(content, "分组汇总（按 city）")
    assert section["rows"] == [
        ["beijing", 2, 200.0],
        ["shanghai", 2, 125.0],
        ["shenzhen", 1, None],  # mean of all-null group → NaN → null
    ]

    content = build_report_content(
        "group_summary", FIXTURE, META, {"group_by": "city"}
    )
    section = _section(content, "分组汇总（按 city）")
    assert section["columns"] == ["city", "行数"]
    assert section["rows"] == [
        ["beijing", 2],
        ["shanghai", 2],
        ["shenzhen", 1],
    ]


def test_group_summary_missing_group_by_raises():
    with pytest.raises(ApiError) as exc:
        build_report_content("group_summary", FIXTURE, META, {})
    assert exc.value.code == "MISSING_REQUIRED_PARAM"
    assert exc.value.status_code == 422


def test_group_summary_invalid_params_raise():
    with pytest.raises(ApiError) as exc:
        build_report_content(
            "group_summary", FIXTURE, META, {"group_by": "nope"}
        )
    assert exc.value.code == "INVALID_PARAM"

    with pytest.raises(ApiError) as exc:
        build_report_content(
            "group_summary",
            FIXTURE,
            META,
            {"group_by": "city", "value_by": "note"},
        )
    assert exc.value.code == "INVALID_PARAM"

    with pytest.raises(ApiError) as exc:
        build_report_content(
            "group_summary",
            FIXTURE,
            META,
            {"group_by": "city", "agg": "median"},
        )
    assert exc.value.code == "INVALID_PARAM"


def test_top_n_ordering_and_default_n():
    content = build_report_content(
        "top_n", FIXTURE, META, {"sort_by": "amount"}
    )
    section = _section(content, "TOP 10 排行（按 amount 降序）")
    assert section["columns"] == ["排名", "city", "amount", "note"]
    assert section["rows"][0] == [1, "beijing", 300.0, ""]
    assert section["rows"][1] == [2, "shanghai", 200.0, "x"]
    # default n=10 covers the whole table; NaN amount ranks last
    assert section["rows"][-1] == [5, "shenzhen", None, "y"]
    assert len(section["rows"]) == 5


def test_top_n_explicit_n():
    content = build_report_content(
        "top_n", FIXTURE, META, {"sort_by": "amount", "n": 2}
    )
    section = next(
        s for s in content["sections"] if s["title"].startswith("TOP")
    )
    assert section["title"] == "TOP 2 排行（按 amount 降序）"
    assert len(section["rows"]) == 2
    assert [r[0] for r in section["rows"]] == [1, 2]


@pytest.mark.parametrize("bad_n", [0, -1, 101, "abc"])
def test_top_n_bounds_validation(bad_n):
    with pytest.raises(ApiError) as exc:
        build_report_content(
            "top_n", FIXTURE, META, {"sort_by": "amount", "n": bad_n}
        )
    assert exc.value.code == "INVALID_PARAM"
    assert exc.value.status_code == 422


def test_top_n_param_validation():
    with pytest.raises(ApiError) as exc:
        build_report_content("top_n", FIXTURE, META, {})
    assert exc.value.code == "MISSING_REQUIRED_PARAM"

    with pytest.raises(ApiError) as exc:
        build_report_content("top_n", FIXTURE, META, {"sort_by": "nope"})
    assert exc.value.code == "INVALID_PARAM"

    with pytest.raises(ApiError) as exc:
        build_report_content("top_n", FIXTURE, META, {"sort_by": "city"})
    assert exc.value.code == "INVALID_PARAM"
