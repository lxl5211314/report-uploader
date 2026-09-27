# 上传报表工具（report-uploader）

无登录的共享空间 Web 工具：**上传 Excel/CSV → 目录组织（可拖拽）→ 选内置模板生成报表 → 在线查看 / 下载 xlsx**。

## 功能特性

- **上传**：`.csv` / `.xlsx`，单文件 ≤10MB、≤10 万行；`.xls`、`.xlsm` 等格式明确拒绝
- **目录组织**：最多 2 层，同级不允许重名，非空目录不可删除；文件支持**拖拽**到目录，也可用行内"移动到…"下拉（无障碍回退）
- **报表模板**：内置 3 个只读模板（数据概览 / 分组汇总 / TOP N 排行），参数化选择列
- **生成与下载**：在线预览分区表格，一键下载 `.xlsx`；同一 (文件, 模板) 重复生成**覆盖旧记录**
- **体验**：加载/上传中状态、超过 10 秒的慢速提示（FR-013）、4xx 错误就地展示（无死路）

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2 · PyMySQL · pandas · openpyxl |
| 前端 | React 18 · TypeScript · Vite 5 · Vitest 2 + Testing Library |
| 存储 | MySQL 8（元数据/报表）+ 本地磁盘 `uploads/`（原始文件） |
| 测试 | pytest（单元/契约/集成）· Vitest（组件）· Playwright（E2E 冒烟） |

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── api/          # REST 路由：directories / files / templates / reports
│   │   ├── services/     # parser（解析）· report（模板计算）· storage（上传/导出）
│   │   ├── models.py     # Directory / DataFile / Template / Report
│   │   ├── seed.py       # 建表 + 播种 3 个内置模板（幂等）
│   │   └── config.py     # .env 驱动的设置
│   └── tests/            # unit / contract / integration
├── frontend/
│   ├── src/
│   │   ├── pages/WorkspacePage.tsx     # 主页面（上传区 + 树 + 生成面板）
│   │   └── components/                 # FileTree · UploadButton · TemplatePicker
│   │                                   # ReportView · DirectoryActions · MoveMenu
│   └── tests/                          # 组件测试
├── specs/001-report-uploader/          # 规格、契约、数据模型、验证指南、任务清单
└── README.md
```

## 快速开始

### 环境要求

- Python 3.11+（`python --version`）
- Node.js 18+（`node --version`）
- MySQL 8 运行中，并记下用户名/密码

### 1) 创建数据库

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS report_tool CHARACTER SET utf8mb4;"
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS report_tool_test CHARACTER SET utf8mb4;"  # 测试用
```

### 2) 后端

```powershell
cd backend
copy .env.example .env        # 填入你本机的 MYSQL_* 连接信息与上传限制
pip install -r requirements.txt
python -m app.seed            # 建表 + 播种 3 个内置模板（幂等）
uvicorn app.main:app --reload --port 8000
```

### 3) 前端（新终端）

```powershell
cd frontend
npm install
npm run dev                   # http://localhost:5173，/api 代理到 :8000
```

### 自检

- `GET http://localhost:8000/api/v1/health` → `{"status":"ok"}`
- `GET http://localhost:8000/api/v1/templates` → 返回 3 个模板（overview / group_summary / top_n）
- 浏览器打开 `http://localhost:5173`，上传一个 csv 走完全流程

## 使用流程

1. **上传**：左侧选择目标目录（默认根目录）→ 选文件 → 点"上传"
2. **组织**：新建目录（重名/超层级会就地报错），把文件拖进目录或用"移动到…"下拉
3. **选模板**：点选文件 → 右侧选择模板，按提示填参数（分组列/排序列等）
4. **生成**：点"生成报表"，在线预览分区表格
5. **下载**：点报表右上角"下载 xlsx"

## 内置模板

| 模板 | code | 必填参数 | 可选参数 | 说明 |
|---|---|---|---|---|
| 数据概览 | `overview` | — | — | 行列规模、字段清单、数值列基础统计 |
| 分组汇总 | `group_summary` | `group_by`（分组列） | `value_by`（聚合列，仅统计行数时留空）、`agg`（sum/avg，默认 sum） | 按列分组统计 |
| TOP N 排行 | `top_n` | `sort_by`（排序列） | `n`（1–100，默认 10）、降序 | 取前 N 行 |

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查（含 DB 连通性） |
| GET | `/api/v1/directories` | 目录树 + 各目录文件列表（一次拉取） |
| POST | `/api/v1/directories` | 新建目录（409 重名 / 422 超层级） |
| PATCH/DELETE | `/api/v1/directories/{id}` | 重命名 / 删除（409 非空） |
| POST | `/api/v1/files/upload` | 上传文件（multipart: file + directory_id） |
| POST | `/api/v1/files/{id}/move` | 移动文件 |
| DELETE | `/api/v1/files/{id}` | 删除文件（级联其报表记录） |
| GET | `/api/v1/files/{id}/columns` | 列名与类型（供模板选列） |
| GET | `/api/v1/templates` | 内置模板（只读） |
| POST | `/api/v1/files/{id}/reports` | 生成报表（同键覆盖） |
| GET | `/api/v1/reports/{id}` | 报表内容 |
| GET | `/api/v1/reports/{id}/download` | 下载 xlsx |
| GET | `/api/v1/files/{id}/reports` | 某文件的报表列表 |

完整请求/响应示例与错误码：[`specs/001-report-uploader/contracts/rest-api.md`](specs/001-report-uploader/contracts/rest-api.md)

## 测试

```powershell
# 后端（需已创建 report_tool_test 库，且 backend/.env 可连库）
cd backend;  pytest           # 单元 + 契约 + 集成，预期 54 passed

# 前端
cd frontend; npm test         # 组件测试（Vitest + Testing Library），预期 9 passed
cd frontend; npx tsc --noEmit # 类型检查
cd frontend; npm run build    # 生产构建（含 tsc）
```

## 限制与约定

- 仅支持 `.csv` / `.xlsx`（`.xls`/`.xlsm` 明确拒绝），单文件 ≤10MB，≤10 万行
- 目录最多 2 层，同级不允许重名；非空目录不可删除
- 报表模板只读 3 个；同一 (文件, 模板) 重复生成覆盖旧记录
- 无身份/登录：全部用户共享同一空间（FR-001）

## 规格文档

| 文档 | 内容 |
|---|---|
| [`spec.md`](specs/001-report-uploader/spec.md) | 用户故事与功能需求 |
| [`plan.md`](specs/001-report-uploader/plan.md) | 技术方案与数据流 |
| [`data-model.md`](specs/001-report-uploader/data-model.md) | 实体与关系 |
| [`contracts/rest-api.md`](specs/001-report-uploader/contracts/rest-api.md) | API 契约（权威） |
| [`quickstart.md`](specs/001-report-uploader/quickstart.md) | V1–V12 端到端验证场景 |
| [`tasks.md`](specs/001-report-uploader/tasks.md) | 实施任务清单（47/47 完成） |
