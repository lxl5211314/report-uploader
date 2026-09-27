# Interface Contract: REST API (v1)

**Feature**: 001-report-uploader | **Style**: REST + JSON，前缀 `/api/v1` | **Auth**: 无（共享空间，FR-001）

**Conventions**:
- 请求/响应均为 JSON（上传除外，`multipart/form-data`）。
- 错误统一结构：`{"code": "<机器码>", "message": "<用户可读中文>"}`。
- 状态码：400 格式非法、404 不存在、409 冲突（重名/非空删除）、413 超限、422 业务校验失败。
- 字段命名 snake_case；时间 ISO-8601。

## 1. 目录 Directories

### GET /api/v1/directories
返回全部目录树与各目录下文件列表（共享空间一次拉取）。

```json
{ "tree": [ { "id": 1, "name": "销售", "parent_id": null,
              "children": [ { "id": 2, "name": "Q1", "parent_id": 1, "children": [] } ],
              "files": [ { "id": 10, "name": "a.csv", "format": "csv",
                           "size_bytes": 2048, "uploaded_at": "..." } ] } ] }
```

### POST /api/v1/directories
`{"name": "销售", "parent_id": null}` → 201 `{"id": 1, ...}`
- 409 `DIRECTORY_NAME_CONFLICT`：同级重名（FR-004）
- 422 `DIRECTORY_DEPTH_EXCEEDED`：父级深度 ≥2（Assumptions）

### PATCH /api/v1/directories/{id}
`{"name": "新名字"}` → 200（重命名，冲突同上）

### DELETE /api/v1/directories/{id}
- 204 无内容；409 `DIRECTORY_NOT_EMPTY`：存在子目录或文件（Assumptions）

## 2. 文件 Files

### POST /api/v1/files/upload
`multipart/form-data`：`file` + `directory_id`
→ 201 `{"id": 10, "name": "a.csv", "format": "csv", "size_bytes": 2048, "directory_id": 1, "uploaded_at": "..."}`
- 400 `UNSUPPORTED_FORMAT`：非 csv/xlsx（含 .xls/.xlsm 等，FR-002/FR-003）
- 413 `FILE_TOO_LARGE`：>10MB（FR-012）
- 409 `FILE_NAME_CONFLICT`：同目录同名（Assumptions）

### POST /api/v1/files/{id}/move
`{"target_directory_id": 2}` → 200 文件对象（FR-005；磁盘不移动，只改 directory_id — R4）
- 409 `FILE_NAME_CONFLICT`：目标目录已有同名
- 404 `FILE_NOT_FOUND` / `DIRECTORY_NOT_FOUND`

### DELETE /api/v1/files/{id}
- 204（级联处理其报表记录；导出件保留或一并删除由实现定，需在 tasks 明示）

### GET /api/v1/files/{id}/columns
供模板选列：返回解析出的列名与推断类型。
```json
{ "columns": [ {"name": "city", "type": "string"},
               {"name": "amount", "type": "number"} ],
  "row_count": 1200 }
```
- 422 `FILE_UNPARSEABLE`：空文件/仅表头/坏文件（FR-011）

## 3. 模板 Templates

### GET /api/v1/templates
```json
{ "templates": [
  { "id": 1, "code": "overview", "name": "数据概览", "description": "...",
    "requires_column": "none", "defaults": {} },
  { "id": 2, "code": "group_summary", "name": "分组汇总", "requires_column": "group",
    "defaults": { "agg": "sum" } },
  { "id": 3, "code": "top_n", "name": "TOP N 排行", "requires_column": "top",
    "defaults": { "n": 10 } } ] }
```
只读；无 POST/PATCH/DELETE（FR-014）。

## 4. 报表 Reports

### POST /api/v1/files/{id}/reports
```json
{ "template_id": 2,
  "params": { "group_by": "city", "agg": "sum", "value_by": "amount" } }
```
→ 201 `{"id": 30, "file_id": 10, "template_id": 2, "status": "succeeded",
         "generated_at": "...", "content": { ... } }`
- 201（或 200，覆盖时）：同一 (file_id, template_id) 已存在则**覆盖**（R6）
- 422 `MISSING_REQUIRED_PARAM`：缺 group_by（分组汇总）/ sort_by（TOP N）（FR-015）
- 422 `INVALID_PARAM`：列不存在、类型非数值、N 越界（1–100）
- 422 `FILE_UNPARSEABLE`：解析失败（FR-011）；500 以外的失败落 report.status=failed

**content 通用信封**（所有模板，FR-007）:
```json
{ "file": {"name": "a.csv", "generated_at": "..."},
  "dataset": {"row_count": 1200, "column_count": 5},
  "sections": [ { "type": "table", "title": "...", "columns": [...], "rows": [...] },
                { "type": "stats", "title": "...", "items": [...] } ] }
```

### GET /api/v1/reports/{id}
→ 200 报表对象（含 content）；404 `REPORT_NOT_FOUND`

### GET /api/v1/reports/{id}/download
→ 200 `application/octet-stream`（xlsx 导出，`Content-Disposition: attachment`）（FR-008）

### GET /api/v1/files/{id}/reports
→ 200 `{"reports": [ {"id": 30, "template": {...}, "generated_at": "..."} ]}`（某文件现有报表列表，每模板至多一条）

## 5. 健康检查

### GET /api/v1/health → `{"status":"ok"}`（含 DB 连通性，供 quickstart 自检）
