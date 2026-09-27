# Phase 1 Data Model: Excel/CSV 上传自动生成报表工具

**Feature**: 001-report-uploader | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

存储：MySQL 8（元数据 + 报表内容）+ 本地磁盘（原文件 `backend/uploads/`、导出件 `backend/exports/`）。共享空间、无用户维度（FR-001/FR-010）。

## Entities

### directory（目录）

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BIGINT PK | auto-increment | |
| name | VARCHAR(191) | NOT NULL | 同级唯一（FR-004） |
| parent_id | BIGINT NULL | FK → directory.id | NULL = 根级 |
| created_at | DATETIME | NOT NULL | |

- **Uniqueness**: UNIQUE(`parent_id`, `name`)；根级 parent 为 NULL 时以哨兵值（如 0）参与唯一判定或用应用层校验。
- **Validation**: 名称非空、去首尾空白；同级重名 → 409（FR-004, Story2-AS4）。
- **State transitions**: 删除仅允许在**无子目录且无文件**时（否则 409 提示先清空，Assumptions）。
- **Depth**: v1 固定 2 层（根 + 子目录），API 层拒绝更深（422，FR-004）。

### data_file（数据文件）

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BIGINT PK | auto-increment | |
| name | VARCHAR(255) | NOT NULL | 显示名（含扩展名） |
| format | ENUM('csv','xlsx') | NOT NULL | 由扩展名判定；v1 仅支持这两种（FR-002） |
| size_bytes | BIGINT | NOT NULL | ≤10MB 校验（FR-012） |
| directory_id | BIGINT | FK → directory.id, NOT NULL | 拖拽移动只改此字段（R4） |
| stored_path | VARCHAR(255) | NOT NULL | 磁盘相对路径 `uploads/{id}` |
| uploaded_at | DATETIME | NOT NULL | |

- **Uniqueness**: UNIQUE(`directory_id`, `name`) — 同目录同名上传 → 409 拒绝（Assumptions：拒绝并提示）。
- **Validation**: 扩展名 ∈ {csv,xlsx}，其余（含 .xls/.xlsm）400 拒绝（FR-002/FR-003）；size ≤ 10MB → 否则 413（FR-012）。
- **State transitions**: move（`directory_id` 变更，目标目录同名冲突 → 409）；delete（级联删除其 reports，或先导出提示）。

### report_template（报表模板，只读种子数据）

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | SMALLINT PK | | |
| code | VARCHAR(32) UNIQUE | NOT NULL | `overview` / `group_summary` / `top_n` |
| name | VARCHAR(64) | NOT NULL | 中文显示名 |
| description | VARCHAR(255) | | 模板说明（模板列表展示） |
| requires_column | ENUM('none','group','top') | NOT NULL | 必选参数类型（FR-015） |
| default_params | JSON | | 如 top_n 默认 `{"n": 10}` |

- **Seeded rows**（seed.py，3 行，FR-014）: overview/requires_column=none；group_summary/requires_column=group；top_n/requires_column=top。
- **Lifecycle**: v1 无增删改 API，仅 GET 列表；应用层禁止写入。

### report（报表）

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BIGINT PK | auto-increment | |
| file_id | BIGINT | FK → data_file.id, NOT NULL | |
| template_id | SMALLINT | FK → report_template.id, NOT NULL | |
| params | JSON | | 如 `{"group_by":"city"}` / `{"sort_by":"amount","n":10}` |
| status | ENUM('generating','succeeded','failed') | NOT NULL | 见状态机 |
| content_json | JSON NULL | | 报表结构化内容（R5） |
| error_message | VARCHAR(255) NULL | | status=failed 时展示 |
| export_path | VARCHAR(255) NULL | | 导出 xlsx 的磁盘路径 |
| generated_at | DATETIME | | 最近一次生成成功时间 |

- **Uniqueness**: UNIQUE(`file_id`, `template_id`) — 重复生成覆盖（R6、Story3-AS4、SC-006）。
- **State transitions**:
  - `generating → succeeded`：写入 content_json、generated_at。
  - `generating → failed`：写入 error_message，content_json 置空（FR-011：不产出残缺报表）。
  - 重新生成：从 `succeeded/failed → generating`（同键覆盖更新）。

## Relationships

```text
directory 1 ──── * directory   (parent_id, 自引用层级)
directory 1 ──── * data_file   (directory_id)
data_file 1 ──── * report      (file_id)
report_template 1 ── * report  (template_id)
```

## Derived / Non-persisted

- **目录树**：一次查询全部 directory 服务端组树（共享空间数据量小，无需闭包表）。
- **文件列清单**：按需解析文件头部得到（供分组汇总/TOP N 选列），不落库；文件内容不入 MySQL（R4）。

## Validation Rules（映射需求）

| Rule | Violation → HTTP |
|------|------------------|
| 扩展名非 csv/xlsx | 400 + message（FR-003） |
| size > 10MB | 413（FR-012） |
| 同级目录/文件重名 | 409（FR-004 / Assumptions） |
| 解析失败/空文件/仅表头/超 10 万行 | 422 + 可读 message（FR-011） |
| 模板必选列缺失或类型不符 | 422（FR-015, SC-004） |
| 删除非空目录 | 409（Assumptions） |
| 目录深度 > 2 层 | 422（Assumptions） |
