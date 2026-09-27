# Quickstart Validation Guide: Excel/CSV 上传自动生成报表工具

**Feature**: 001-report-uploader | **Spec**: [spec.md](./spec.md) | **API**: [contracts/rest-api.md](./contracts/rest-api.md) | **Model**: [data-model.md](./data-model.md)

验证目标：端到端跑通"上传 → 建目录 → 拖拽 → 选模板 → 出报表 → 下载"，对应 Spec 的三个用户故事与成功标准。

## Prerequisites

- Python 3.11+（`python --version`）
- Node.js 18+（`node --version`）
- MySQL 8 运行中，已创建空库（默认 `report_tool`），并记下用户名/密码

## Setup

```powershell
# 1) 后端
cd backend
copy .env.example .env          # 填入 MYSQL_* 连接信息与上传限制
pip install -r requirements.txt
python -m app.seed              # 建表 + 播种 3 个内置模板（幂等）
uvicorn app.main:app --reload --port 8000

# 2) 前端（新终端）
cd frontend
npm install
npm run dev                     # 默认 http://localhost:5173，代理 /api → 8000
```

**自检**: `GET http://localhost:8000/api/v1/health` → `{"status":"ok"}`；`GET /api/v1/templates` 返回 3 个模板（overview/group_summary/top_n）。

## Validation Scenarios

准备 fixture：`sample.csv`（含分类列 `city`、数值列 `amount`，≥20 行）、`empty.csv`（0 字节）、`not-a-table.txt`、`wide.csv`（10.1MB 或 >10 万行，用于超限）。

| # | 对应需求 | Steps | Expected |
|---|---------|-------|----------|
| V1 | US1, FR-002, SC-001 | 打开前端 → 上传 `sample.csv`（根目录） | 文件即时出现在树中，显示名称/大小；全流程 ≤3 分钟 |
| V2 | US2, FR-004 | 新建目录"销售" → 再建同名"销售" | 第一次成功；第二次 409 提示同级重名 |
| V3 | US2, FR-005 | 把 `sample.csv` 拖到"销售"目录 | 文件从原位置消失并出现在目标目录；刷新页面后仍在（FR-009） |
| V4 | US1, FR-007, SC-005 | 对文件选"数据概览"→ 生成 → 查看 | 展示行数/列数/字段清单/数值统计；与 `sample.csv` 人工核对一致 |
| V5 | US3, FR-015 | 选"分组汇总"不选分组列 → 生成；再选 `city` 生成 | 前者 422 提示缺必选列（SC-004）；后者输出各 city 分组行数与聚合值，与手工计算一致 |
| V6 | US3 | 选"TOP N 排行"，`amount` 降序，N=5 | 输出 5 行，金额为全表最大 5 个 |
| V7 | US3, SC-006 | 同文件同模板再生成一次 | 覆盖旧报表，无重复记录（报表列表每模板至多 1 条） |
| V8 | FR-008 | 打开任一报表 → 下载 | 得到可离线打开的 xlsx，内容与页面一致 |
| V9 | FR-003/011/012, SC-004 | 依次上传 `not-a-table.txt`、`empty.csv`、`wide.csv`；对 empty 生成报表 | 全部得到可理解的中文错误提示，界面不崩溃、无残缺报表 |
| V10 | FR-009, FR-010 | 关闭并重开浏览器/重启后端 | 目录、文件、报表全部保留；无身份选择入口（共享空间） |
| V11 | SC-002 | 对 1 万行 CSV 连续生成 5 次 | ≥4 次在 10 秒内完成 |
| V12 | SC-003 | 不给文档让新用户完成 建目录+拖拽+生成 | ≥90% 测试者独立完成（可拖拽，也可用"移动到…"兜底菜单） |

## Test Commands

```powershell
cd backend;  pytest            # 单元 + 契约 + 集成（报表数值断言覆盖 SC-005）
cd frontend; npm test          # 组件冒烟（树渲染、模板选择校验提示）
```

## Pass Gate

- V1–V12 全部通过，且后端/前端自动化测试通过 → 核心功能跑通，可进入 `/speckit.tasks` 的实现验证或 `/speckit.implement`。
- 任一场景失败：记录场景编号与实际行为，回到对应 spec 条目/contract 端点排查。
