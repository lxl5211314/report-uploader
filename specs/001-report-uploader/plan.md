# Implementation Plan: Excel/CSV 上传自动生成报表工具

**Branch**: `001-report-uploader` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-report-uploader/spec.md`

## Summary

构建一个免登录的 Web 工具：用户在共享工作区中创建目录、上传 Excel/CSV 文件、拖拽移动文件，并对文件从 3 个内置报表模板（数据概览、分组汇总、TOP N 排行）中选择其一生成可查看/下载的报表。技术栈按用户指定：React 前端 + Python 后端 + MySQL 数据库，目标是第一版尽快跑通核心链路（上传 → 组织 → 选模板 → 出报表）。

## Technical Context

**Language/Version**: Backend Python 3.11+；Frontend TypeScript + React 18

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, pandas, openpyxl, python-multipart（后端）；Vite, React, react-router（前端）

**Storage**: MySQL 8（目录/文件/模板/报表元数据与报表内容 JSON）+ 本地磁盘（上传的原始文件、报表导出文件）

**Testing**: pytest（后端单元/接口测试）；Vitest + React Testing Library（前端组件测试）

**Target Platform**: 桌面浏览器（本地/内网开发验证环境，Windows 主机）

**Project Type**: Web 应用（frontend + backend 双仓结构）

**Performance Goals**: 1 万行内文件 95% 的报表生成 ≤10s（SC-002）；上传即时反馈

**Constraints**: 单文件 ≤10MB、≤10 万行（FR-012）；免登录、单一共享空间、无权限控制（FR-001/FR-010）

**Scale/Scope**: 验证阶段，个位数并发用户；约 8 个 REST 端点、4 张核心表、3 个内置模板、3 个前端主要页面视图

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- `.specify/memory/constitution.md` 当前仍为**未填写的模板占位文件**（全部为 `[PRINCIPLE_x_NAME]` 占位符），无生效原则、无强制门禁。
- 结论：**PRE-PHASE 0 GATE = PASS（无可执行约束）**；同时在 Complexity Tracking 中记录"Constitution 未初始化"为已知风险，建议后续运行 `/speckit.constitution`。
- **POST-PHASE 1 RE-CHECK**: Constitution 仍为占位模板，无新增约束触发；设计产物（research/data-model/contracts/quickstart）与 spec 澄清结果一致 → **PASS**。

## Project Structure

### Documentation (this feature)

```text
specs/001-report-uploader/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── rest-api.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py          # FastAPI 应用入口与路由挂载
│   ├── config.py        # 数据库连接、上传路径、大小限制等配置
│   ├── db.py            # SQLAlchemy engine/session
│   ├── models.py        # Directory / File / ReportTemplate / Report ORM
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── api/
│   │   ├── directories.py
│   │   ├── files.py
│   │   ├── templates.py
│   │   └── reports.py
│   ├── services/
│   │   ├── storage.py   # 本地文件存取与格式校验
│   │   ├── parser.py    # pandas 解析 Excel/CSV（含编码回退、上限检查）
│   │   └── report.py    # 3 个模板的计算与报表导出
│   └── seed.py          # 初始化 3 个内置报表模板
├── tests/
│   ├── contract/
│   ├── integration/
│   └── unit/
├── uploads/             # 运行时上传文件（gitignore）
├── exports/             # 运行时报表导出文件（gitignore）
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── components/      # FileTree, FileCard, UploadButton, TemplatePicker, ReportView
│   ├── pages/           # WorkspacePage（主视图）
│   ├── services/        # API 客户端
│   └── App.tsx
├── tests/
├── package.json
└── vite.config.ts
```

**Structure Decision**: 采用 Web 应用双目录结构（backend/ + frontend/），与用户指定的 React/Python/MySQL 技术栈对应；前后端通过 `contracts/rest-api.md` 中的 REST JSON 接口解耦，可独立启动与测试。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution 未初始化（占位模板） | 当前无生效治理原则，无法执行真实门禁 | 建议验证通过后运行 `/speckit.constitution` 补齐；本阶段不阻塞 |
