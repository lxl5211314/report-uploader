# Tasks: Excel/CSV 上传自动生成报表工具

**Input**: Design documents from `/specs/001-report-uploader/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included because quickstart.md's Pass Gate requires automated tests (pytest + Vitest) and research.md R10 defines the test strategy; test tasks are marked with their own IDs and come before corresponding implementation within each story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Web app per plan.md: `backend/` (Python/FastAPI) and `frontend/` (React/TS) at repository root. Tests live in `backend/tests/` and `frontend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create backend/ and frontend/ directory skeleton per plan.md Project Structure, including backend/uploads/, backend/exports/ with .gitignore entries, backend/tests/{unit,integration,contract}/, frontend/tests/
- [X] T002 Initialize backend dependencies in backend/requirements.txt (fastapi, uvicorn[standard], sqlalchemy>=2.0, pymysql, pandas, openpyxl, python-multipart, pydantic-settings, pytest, httpx) and create backend/app/main.py FastAPI app skeleton
- [X] T003 [P] Initialize frontend with Vite + React 18 + TypeScript in frontend/ (package.json, vite.config.ts with /api proxy → localhost:8000, vitest + @testing-library/react dev dependencies)
- [X] T004 [P] Create backend/.env.example and backend/app/config.py using pydantic-settings: MYSQL_* connection vars, UPLOAD_DIR, EXPORT_DIR, MAX_UPLOAD_BYTES=10485760 (FR-012: ≤10MB), MAX_ROWS=100000 (Assumptions)

**Checkpoint**: Both projects scaffold and start (`uvicorn app.main:app`, `npm run dev`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⛔ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create SQLAlchemy ORM models in backend/app/models.py per data-model.md: directory (name NOT NULL, parent_id self-FK, unique sibling name), data_file (format ENUM csv/xlsx, size_bytes, directory_id FK, unique (directory_id,name)), report_template (code UNIQUE, requires_column ENUM none/group/top, default_params JSON), report (file_id+template_id UNIQUE, status ENUM generating/succeeded/failed, content_json JSON, error_message, params JSON)
- [X] T006 Implement database engine/session in backend/app/db.py (create_all startup hook) and backend/app/seed.py to insert the 3 read-only template rows (overview/requires_column=none, group_summary/requires_column=group, top_n/requires_column=top default {"n":10}) idempotently (FR-014)
- [X] T007 [P] Implement unified error contract helpers in backend/app/api/errors.py: response body {"code","message"}, exception handlers mapping 400 UNSUPPORTED_FORMAT, 404 NOT_FOUND, 409 *_CONFLICT/DIRECTORY_NOT_EMPTY, 413 FILE_TOO_LARGE, 422 MISSING_REQUIRED_PARAM/INVALID_PARAM/FILE_UNPARSEABLE/DIRECTORY_DEPTH_EXCEEDED (contracts/rest-api.md §Conventions)
- [X] T008 [P] Mount routers under /api/v1 in backend/app/main.py: create backend/app/api/{directories,files,templates,reports}.py stubs plus GET /api/v1/health returning {"status":"ok"} with DB connectivity check (quickstart self-check)
- [X] T009 [P] Define Pydantic request/response schemas in backend/app/schemas.py for all endpoints in contracts/rest-api.md (DirectoryCreate, FileMove, ReportCreate with params, error envelope)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 上传数据文件并生成报表 (Priority: P1) ⭐ MVP

**Goal**: 免登录上传 Excel/CSV 到目录，选"数据概览"模板生成报表并查看、下载（FR-001~003, FR-006~012, SC-001/002/004/005）。
**Independent Test**: 上传 sample.csv → GET templates 返回 3 条 → POST reports(template_id=overview) 返回 succeeded 且 content 行列数与源文件一致 → 下载 xlsx 可打开（quickstart V1/V4/V8/V9）。
### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Contract tests for POST /api/v1/files/upload in backend/tests/contract/test_files.py (201 happy path, 400 unsupported format, 413 >10MB, 409 same-name-in-directory)
- [X] T011 [P] [US1] Unit tests for parser in backend/tests/unit/test_parser.py (utf-8 and gbk CSV fallback, empty file raises FILE_UNPARSEABLE, >100000 rows rejected, column type inference string/number)
- [X] T012 [P] [US1] Unit tests for overview report computation in backend/tests/unit/test_report_overview.py asserting exact row_count, column_count, min/max/mean/null_count on a fixed fixture CSV (SC-005)

### Implementation for User Story 1

- [X] T013 [US1] Implement storage service in backend/app/services/storage.py: save upload to {UPLOAD_DIR}/{file_id}, validate extension ∈ {csv,xlsx} else 400 (reject .xls/.xlsm and all others per FR-002), size ≤ MAX_UPLOAD_BYTES else 413, unique (directory_id,name) check else 409 (data-model.md Validation Rules)
- [X] T014 [US1] Implement parser service in backend/app/services/parser.py: pandas read_csv (encoding utf-8→gbk fallback) / read_excel (openpyxl), reject empty/header-only/corrupt with 422 FILE_UNPARSEABLE, enforce MAX_ROWS, return columns [{name,type}] + row_count (research R3)
- [X] T015 [US1] Implement report service core in backend/app/services/report.py: content envelope {"file","dataset","sections"} per contracts/rest-api.md §4, overview section computation, xlsx export via openpyxl writing content sections to {EXPORT_DIR}/{report_id}.xlsx
- [X] T016 [US1] Implement GET /api/v1/directories (full tree with nested children + files arrays, shared space, no auth) in backend/app/api/directories.py (contracts §1 — read-only portion; create/move/delete are US2)
- [X] T017 [US1] Implement POST /api/v1/files/upload endpoint (multipart file + directory_id → 201 file object) in backend/app/api/files.py calling storage service
- [X] T018 [US1] Implement GET /api/v1/files/{id}/columns (parsed columns + row_count; 404 unknown file, 422 unparseable) in backend/app/api/files.py
- [X] T019 [US1] Implement GET /api/v1/templates returning the 3 seeded rows (read-only, no POST/PATCH/DELETE) in backend/app/api/templates.py (FR-014)
- [X] T020 [US1] Implement report endpoints in backend/app/api/reports.py: POST /api/v1/files/{id}/reports (overview only for this story; upsert on unique (file_id,template_id); 422 invalid params), GET /api/v1/reports/{id}, GET /api/v1/reports/{id}/download (xlsx attachment), GET /api/v1/files/{id}/reports
- [X] T021 [US1] Integration test full flow in backend/tests/integration/test_report_flow.py: upload → columns → generate overview → assert content matches fixture → download xlsx bytes non-empty (quickstart V1/V4/V8)
- [X] T022 [P] [US1] Create API client in frontend/src/services/api.ts wrapping all contracts/rest-api.md endpoints with typed responses and {code,message} error extraction
- [X] T023 [US1] Create WorkspacePage shell + read-only directory tree with files in frontend/src/pages/WorkspacePage.tsx and frontend/src/components/FileTree.tsx (name, size, nested directories)
- [X] T024 [US1] Create UploadButton component in frontend/src/components/UploadButton.tsx: pick target directory, upload with progress/state, surface 400/409/413 errors as user-readable messages (SC-004)
- [X] T025 [US1] Create TemplatePicker + ReportView in frontend/src/components/TemplatePicker.tsx and frontend/src/components/ReportView.tsx: list 3 templates, generate (overview needs no params), render content sections tables, download link (SC-001 flow ≤ 1 min)
- [X] T026 [US1] Frontend smoke tests in frontend/tests/workspace.test.tsx: renders tree after mocked fetch, upload error message shown, overview report renders section table (Vitest + Testing Library)

**Checkpoint**: MVP — upload → choose overview template → view/download report works end-to-end (quickstart V1/V4/V8 pass)

---

## Phase 4: User Story 2 - 创建目录并组织文件 (Priority: P2)

**Goal**: 创建目录、拖拽移动文件到不同目录，目录上下文生成报表（FR-004/005, Story2 acceptance scenarios, SC-003）。
**Independent Test**: API 创建"销售"目录 → 同名再建得 409 → move 文件到目标目录后树中位置改变且刷新保留 → 非空目录删除得 409（quickstart V2/V3, data-model Validation Rules）。
### Tests for User Story 2

- [X] T027 [P] [US2] Unit tests for directory rules in backend/tests/unit/test_directories.py: sibling name conflict → 409, depth >2 → 422 DIRECTORY_DEPTH_EXCEEDED, delete non-empty → 409 DIRECTORY_NOT_EMPTY, name whitespace trimming (data-model.md State transitions)
- [X] T028 [P] [US2] Contract tests for POST/PATCH/DELETE /api/v1/directories and POST /api/v1/files/{id}/move in backend/tests/contract/test_directories.py (201/200/204 happy paths + conflict codes per contracts §1)

### Implementation for User Story 2

- [X] T029 [US2] Implement POST/PATCH/DELETE /api/v1/directories in backend/app/api/directories.py: create with parent_id, rename, delete only when no children and no files else 409, enforce max depth 2 (Assumptions), unique sibling name (FR-004)
- [X] T030 [US2] Implement POST /api/v1/files/{id}/move in backend/app/api/files.py: change directory_id only (disk path unchanged per research R4), 409 on name conflict in target, 404 unknown file/directory (FR-005)
- [X] T031 [US2] Implement DELETE /api/v1/files/{id} in backend/app/api/files.py with cascade delete of its reports in backend/app/services/storage.py (note deletion behavior in task comment)
- [X] T032 [US2] Integration test directory flow in backend/tests/integration/test_directory_flow.py: create → duplicate 409 → move file → tree reflects new location → restart session/re-query shows persistence (FR-009, quickstart V3) → move-to-same-directory is a no-op and move-to-target-with-same-name returns 409 (spec Edge Cases)
- [X] T033 [US2] Create directory management UI in frontend/src/components/DirectoryActions.tsx: create dialog, rename, delete with empty-check error display, wired into WorkspacePage tree
- [X] T034 [US2] Implement HTML5 drag-and-drop file→directory in frontend/src/components/FileTree.tsx plus "移动到…" fallback menu in frontend/src/components/MoveMenu.tsx calling move API and refreshing tree (FR-005, SC-003, research R7)
- [X] T035 [US2] Frontend interaction tests in frontend/tests/directory.test.tsx: create directory renders, drag/drop handler calls move API, move-menu fallback present, conflict error surfaced

**Checkpoint**: Users can build directory structures and organize files by dragging; both stories work independently

---

## Phase 5: User Story 3 - 使用内置报表模板生成不同类型的报表 (Priority: P3)

**Goal**: 分组汇总与 TOP N 排行两个模板的必选参数校验与计算，同文件同模板重复生成覆盖（FR-015/FR-007, Story3 acceptance scenarios, SC-005/006）。
**Independent Test**: 对含 city/amount 的 fixture：group_summary(group_by=city) 聚合值与手工计算一致；top_n(amount, n=5) 返回全表最大 5 行；缺参数 422；同文件同模板二次生成覆盖无重复（quickstart V5/V6/V7）。
### Tests for User Story 3

- [X] T036 [P] [US3] Unit tests for template computations in backend/tests/unit/test_report_templates.py: group_summary exact group counts and sum/mean aggregates, top_n ordering and default n=10 / bounds 1–100 validation on fixed fixture (SC-005)
- [X] T037 [P] [US3] Contract tests for POST /api/v1/files/{id}/reports param validation in backend/tests/contract/test_reports.py: 422 MISSING_REQUIRED_PARAM (no group_by / no sort_by), 422 INVALID_PARAM (unknown column, non-numeric sort column, n out of range), overwrite returns single report per (file_id,template_id) (FR-015, SC-004)

### Implementation for User Story 3

- [X] T038 [US3] Implement group_summary computation + param validation in backend/app/services/report.py: require group_by column (string type), optional value_by numeric column with agg sum|mean default sum, output per-group row_count + aggregate (FR-015/FR-007)
- [X] T039 [US3] Implement top_n computation + param validation in backend/app/services/report.py: require sort_by numeric column, n integer 1–100 default 10, descending top-N rows with rank (FR-015/FR-007)
- [X] T040 [US3] Extend POST /api/v1/files/{id}/reports dispatch in backend/app/api/reports.py to route template_id → group_summary/top_n handlers with 422 mapping, keeping unique (file_id,template_id) upsert overwrite (R6, SC-006)
- [X] T041 [US3] Extend TemplatePicker in frontend/src/components/TemplatePicker.tsx: on selecting group_summary show group-column select (from GET files/{id}/columns); on top_n show numeric sort column select + N input default 10; disable generate until required params valid, display 422 messages inline (FR-015, SC-004)
- [X] T042 [US3] Integration test multi-template flow in backend/tests/integration/test_multi_template.py: same file generates overview + group_summary + top_n; second group_summary generation overwrites (report list shows 1 per template) (quickstart V5–V7)

**Checkpoint**: All three user stories independently functional; 3 templates produce correct distinct outputs

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T043 [P] Execute quickstart.md scenarios V1–V12 in specs/001-report-uploader/quickstart.md and fix any failures found (full end-to-end gate)
- [X] T044 [P] Add root README.md with setup/run instructions mirroring quickstart Prerequisites + Setup (Python/Node/MySQL versions, seed command, test commands)
- [X] T045 UX polish for SC-004: empty-state messages, loading indicators during upload/generation, timeout feedback copy when generation exceeds 10s (FR-013), consistent error toasts across frontend/src/components/ (no dead ends on any 4xx)
- [X] T046 Verify SC-002 performance: generate overview/group_summary on a 10000-row fixture 5 times, confirm ≤ 10s; profile and tune backend/app/services/parser.py or report.py if needed
- [X] T047 Run full test suites (backend: pytest; frontend: npm test) and lint/format both projects; ensure 0 failures before demo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - **MVP, do first**
- **User Story 2 (Phase 4)**: Depends on Foundational; E2E flow uses US1's upload endpoint but is independently testable via API fixtures/tests (T027/T028 don't need US1 UI)
- **User Story 3 (Phase 5)**: Depends on Foundational + US1's report endpoints (T020) for dispatch point; computations and tests independent
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundational → independent, delivers full MVP
- **User Story 2 (P2)**: Foundational → independent (API-level); integrates with US1's files in UI
- **User Story 3 (P3)**: Foundational → extends US1's report service/endpoints; compute functions independently unit-testable

### Within Each User Story

- Tests written FIRST (must fail) → services → endpoints → integration → frontend → frontend tests
- Models (Phase 2) before services; services before endpoints; backend before frontend integration

### Parallel Opportunities

- Phase 1: T003, T004 parallel with T002
- Phase 2: T007, T008, T009 parallel (different files) after T005/T006
- US1: T010–T012 tests all parallel; T022 parallel with backend tasks T013–T020
- US2: T027/T028 parallel; T033/T034 frontend parallel after T029–T031
- US3: T036/T037 parallel; T038/T039 can be parallel (same file app/services/report.py — sequential if single owner, else coordinate)
- Across stories: with multiple devs, US2 and US3 can start together after Foundational

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract tests for upload in backend/tests/contract/test_files.py"
Task: "Unit tests for parser in backend/tests/unit/test_parser.py"
Task: "Unit tests for overview computation in backend/tests/unit/test_report_overview.py"

# Meanwhile, frontend API client can be built in parallel:
Task: "Create API client in frontend/src/services/api.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart V1/V4/V8/V9 pass → 核心链路跑通
5. Demo to stakeholders

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 upload + 数据概览 → test independently → MVP demo
3. US2 directories + drag-drop → test independently → organize demo
4. US3 分组汇总 + TOP N → test independently → full 3-template demo
5. Polish (quickstart V1–V12 full gate)

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Once Foundational done: Dev A → US1 (MVP first), Dev B → US2 backend endpoints, Dev C → US3 compute functions (unit-testable immediately)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable per spec's Independent Test criteria
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No auth/identity tasks: FR-001 mandates shared space with no login (research R8)
