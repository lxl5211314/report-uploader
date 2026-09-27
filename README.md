# 上传报表工具（Excel/CSV 自动生成报表）

无登录的共享空间 Web 工具：上传 Excel/CSV → 目录组织（可拖拽）→ 选内置模板生成报表 → 在线查看 / 下载 xlsx。

- 规格说明：`specs/001-report-uploader/spec.md`
- 接口契约：`specs/001-report-uploader/contracts/rest-api.md`
- 验证指南：`specs/001-report-uploader/quickstart.md`

## 环境要求

- Python 3.11+（`python --version`）
- Node.js 18+（`node --version`）
- MySQL 8 运行中，并记下用户名/密码

## 初始化

```powershell
# 1) 数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS report_tool CHARACTER SET utf8mb4;"

# 2) 后端
cd backend
copy .env.example .env        # 填入你本机的 MYSQL_* 连接信息与上传限制
pip install -r requirements.txt
python -m app.seed            # 建表 + 播种 3 个内置模板（幂等）
uvicorn app.main:app --reload --port 8000

# 3) 前端（新终端）
cd frontend
npm install
npm run dev                   # http://localhost:5173，/api 代理到 :8000
```

**自检**：`GET http://localhost:8000/api/v1/health` → `{"status":"ok"}`；
`GET /api/v1/templates` 返回 3 个模板（overview / group_summary / top_n）。

## 测试

```powershell
cd backend;  pytest           # 单元 + 契约 + 集成
cd frontend; npm test         # 组件冒烟（Vitest + Testing Library）
cd frontend; npx tsc --noEmit # 类型检查
```

## 限制与约定

- 仅支持 `.csv` / `.xlsx`（`.xls`/`.xlsm` 明确拒绝），单文件 ≤10MB，≤10 万行
- 目录最多 2 层，同级不允许重名；非空目录不可删除
- 报表模板只读 3 个；同一 (文件, 模板) 重复生成覆盖旧记录
- 无身份/登录：全部用户共享同一空间（FR-001）
