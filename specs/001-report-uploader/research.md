# Phase 0 Research: Excel/CSV 上传自动生成报表工具

**Feature**: 001-report-uploader | **Date**: 2026-09-24 | **Plan**: [plan.md](./plan.md)

技术栈由用户指定：**React（前端）+ Python（后端）+ MySQL（数据库）**。以下研究在该约束内做选型，所有 Technical Context 中的 NEEDS CLARIFICATION 均已解决。

## R1 - 后端 Web 框架（Python）

- **Decision**: FastAPI + Uvicorn
- **Rationale**: 原生支持 multipart 文件上传、Pydantic 请求校验（直接映射上传大小/格式/必选列校验）、自动生成 OpenAPI 文档可校验 contracts；异步友好，适合"先跑起来"的快速验证。
- **Alternatives considered**: Flask（生态简单但校验与文档需自建）、Django/Django REST（自带 admin 与 ORM 过重，免登录单页面场景收益低）。

## R2 - 数据库访问与建表

- **Decision**: SQLAlchemy 2.0 ORM + PyMySQL 驱动；v1 用 `metadata.create_all` 建表 + `seed.py` 播种 3 个内置模板，不引入迁移工具。
- **Rationale**: 验证阶段表结构会随实现微调，重建表成本低于维护迁移脚本；MySQL 连接串成熟稳定。
- **Alternatives considered**: Alembic 迁移（验证期徒增步骤）、直接 SQL 驱动如 mysqlclient 裸写 SQL（无 ORM 映射，样板代码多）。
- **Follow-up**: 若 v1 验证通过进入迭代，再引入 Alembic。

## R3 - Excel/CSV 解析与统计计算

- **Decision**: pandas 统一读取（`read_csv` 带编码回退 `utf-8 → gbk`，`read_excel` 依赖 openpyxl 引擎），统计计算用 pandas 内置聚合。
- **Rationale**: 一个库覆盖 csv/xlsx 两类输入与分组汇总（groupby）、排序取前 N（nlargest/nlargest）全部需求；满足 SC-002 1 万行 ≤10s 的量级绰绰有余。
- **Alternatives considered**: openpyxl/csv 纯手写解析（需自行实现类型推断与聚合，易错）、polars（性能更好但团队陌生度高、与 MySQL 场景不匹配）。
- **Guardrails**: 解析前先查文件大小（≤10MB，FR-012）；解析后查行数（≤10 万）；空文件/仅表头/坏文件捕获异常映射为用户可读错误（FR-011、SC-004）。

## R4 - 文件存储方式

- **Decision**: 原始文件存本地磁盘（`backend/uploads/`，按文件 ID 命名），MySQL 只存元数据与报表内容 JSON；报表导出写 `backend/exports/`。
- **Rationale**: 避免 MySQL BLOB 的内存/性能陷阱；v1 单机验证无需对象存储；文件 ID 命名天然规避同名冲突与目录移动问题（移动只改 DB 中的 `directory_id`，不动磁盘）。
- **Alternatives considered**: MySQL BLOB（大文件内存压力）、S3/MinIO（验证阶段引入外部服务违背"先跑起来"）。

## R5 - 报表模板的实现形态

- **Decision**: 模板 = 数据库中的只读配置行（code/name/描述/参数要求）+ 后端 `report.py` 中 3 个对应计算函数；报表结果序列化为 JSON 存入 `report.content_json`，前端渲染，导出时用 openpyxl 写 xlsx。
- **Rationale**: 满足"预置模板、不可自定义"（FR-014）；JSON 存储使查看与导出共用一份数据；模板选择与必选列校验在 API 层完成（FR-015）。
- **三个模板定义**（v1 冻结）:
  1. `overview` **数据概览** — 文件信息、总行数/总列数、字段清单、数值列 min/max/mean/空值数。
  2. `group_summary` **分组汇总** — 必选：分组列（分类）；可选：1 个数值聚合列（sum/mean，二选一，默认 sum）；输出各组行数与聚合值。
  3. `top_n` **TOP N 排行** — 必选：排序数值列、N（默认 10，1–100）；输出前 N 行（按降序）及排名。
- **Alternatives considered**: 用户可编辑模板 DSL/公式（明确超出 v1 范围，spec Out-of-scope）；仅一个模板（无法满足"预置若干"）。

## R6 - 报表重复生成策略

- **Decision**: `report` 表对 `(file_id, template_id)` 唯一，重复生成覆盖更新（同参数或不同参数均覆盖）。
- **Rationale**: spec Assumptions 已定"覆盖旧报表"，唯一约束在数据库层面兜底并发重复插入。
- **Alternatives considered**: 保留历史版本（需版本链与列表 UI，验证期不必要）。

## R7 - 前端交互：目录树与拖拽

- **Decision**: React 18 + TypeScript + Vite；目录树 + 文件卡片视图；**原生 HTML5 Drag & Drop API** 实现文件拖到目录，移动成功后调用后端 move 接口并刷新树。
- **Rationale**: 原生 DnD 零依赖即可满足 FR-005；Vite 冷启动快，契合"先跑起来"。
- **Alternatives considered**: react-dnd/@dnd-kit（功能更强但本场景仅文件→目录单向拖拽，不需要）；后端渲染模板（无法实现拖拽体验）。
- **UX 兜底**: 提供拖拽之外的"移动到…"菜单，避免 DnD 在触控/辅助技术下不可用（SC-003 的 90% 独立完成率）。

## R8 - 免登录与共享空间（采纳自 clarify 推荐方案）

- **Decision**: 无任何身份/会话概念，前后端均不引入鉴权；所有请求读写同一共享数据集。
- **Rationale**: spec FR-001/FR-010 已明确单一共享空间；验证核心链路不需要鉴权，删除身份机制大幅减小数据模型与测试面。
- **Alternatives considered**: 预设身份选择器（spec 已澄清移除）、浏览器端隔离（引入 localStorage/会话态，与服务端持久化冲突）。
- **Consequence**: 安全边界依赖部署环境（内网/本机），不做越权测试，只做功能测试。

## R9 - API 风格与错误约定

- **Decision**: REST + JSON，统一前缀 `/api/v1`；错误响应统一 `{code, message}`，HTTP 状态码语义化（400 校验/格式、404 不存在、409 重名冲突、413 超限、422 业务校验如缺必选列）。
- **Rationale**: 前后端解耦的最小契约，OpenAPI 可自动导出校验。
- **Alternatives considered**: GraphQL（验证期过重）、非标准包装格式。

## R10 - 测试与验证策略

- **Decision**: 后端 pytest —— 单元（parser/report 纯函数）、契约（按 `contracts/rest-api.md` 打端点）、集成（上传→生成→下载全链路）；前端 Vitest + Testing Library 冒烟（渲染树、模板选择器校验提示）。端到端手工验证清单见 [quickstart.md](./quickstart.md)。
- **Rationale**: 报表数值正确性（SC-005）必须由自动化断言覆盖（对固定 fixture 数据核对聚合值）。
- **Alternatives considered**: Playwright 全链路 E2E（v1 先不引入，手工 quickstart 足够验证跑通）。

## Open Risks（不阻塞 plan，供 tasks 阶段关注）

1. CSV 中文编码（GBK/UTF-8 混杂）——parser 已规划编码回退，需 fixture 覆盖。
2. MySQL 在 Windows 环境的服务可用性——quickstart 提供连接自检步骤。
3. Constitution 未初始化——建议后续 `/speckit.constitution`。
