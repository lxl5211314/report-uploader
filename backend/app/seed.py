"""Seed the 3 read-only built-in report templates (FR-014). Idempotent."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .models import Directory, ReportTemplate, RequiresColumn

TEMPLATES = [
    {
        "code": "overview",
        "name": "数据概览",
        "description": "文件基本信息、行列规模、字段清单与数值列基础统计（最小值/最大值/平均值/空值数）",
        "requires_column": RequiresColumn.none,
        "default_params": {},
    },
    {
        "code": "group_summary",
        "name": "分组汇总",
        "description": "按选定分组列汇总各组行数，并可对选定数值列求和/求平均",
        "requires_column": RequiresColumn.group,
        "default_params": {"agg": "sum"},
    },
    {
        "code": "top_n",
        "name": "TOP N 排行",
        "description": "按选定数值列降序取前 N 行（N 默认 10，范围 1-100）",
        "requires_column": RequiresColumn.top,
        "default_params": {"n": 10},
    },
]


def seed_templates(db: Session) -> None:
    for tpl in TEMPLATES:
        exists = db.execute(
            select(ReportTemplate).where(ReportTemplate.code == tpl["code"])
        ).scalar_one_or_none()
        if exists is None:
            db.add(ReportTemplate(**tpl))
    root = db.execute(
        select(Directory).where(
            Directory.name == "根目录", Directory.parent_id.is_(None)
        )
    ).scalar_one_or_none()
    if root is None:
        db.add(Directory(name="根目录", parent_id=None))
    db.commit()


def run_seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_templates(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
    print("Seeded 3 report templates.")
