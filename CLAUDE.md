# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Agent 驱动的 Schema-Free 数据分析平台** — 用户上传数据文件（Excel/CSV/JSON），AI Agent 自动完成解析、Schema 推断、数据质量分析、统计分析、图表生成、报告撰写和多轮对话。无需预定义 Schema，无需手写代码。

### Core Principles

- **Schema-Free**: 系统不依赖预定义 Schema，Agent 自动发现字段类型、语义含义和字段间关系
- **Agent-First**: 业务逻辑由 LangGraph Agent 编排，而非硬编码流程
- **Harness Engineering**: 使用 Claude Code Workflow 系统（pipeline/parallel/agent）实现，每个阶段有 Writer → Reviewer → Test 三轮

## Tech Stack

| 层 | 技术 | 许可证 |
|----|------|--------|
| 后端框架 | FastAPI + Uvicorn | MIT |
| Agent 引擎 | LangGraph + LangChain Core | MIT |
| 数据处理 | Polars + PyArrow + openpyxl | MIT |
| 可视化 | Plotly | MIT |
| 数据库 | PostgreSQL (asyncpg + SQLAlchemy async) | MIT/BSD |
| 缓存 | Redis (hiredis) | RSALv2 |
| 迁移 | Alembic | MIT |
| 前端框架 | Vue 3 + TypeScript | MIT |
| UI 库 | Element Plus | MIT |
| 前端图表 | ECharts（备用 Apache 2.0） | MIT |
| 状态管理 | Pinia | MIT |
| 构建工具 | Vite | MIT |
| 虚拟环境 | uv (ADVP venv) | MIT |
| 沙箱 | RestrictedPython | MIT |
| MCP 协议 | mcp >=1.0.0 | MIT |
| 报表模板 | Jinja2 | BSD |

## Architecture

```
Client Layer (Vue 3 + Element Plus)
    │ HTTP / SSE / WebSocket
API Layer (FastAPI + Pydantic v2)
    │
Service Layer (Business Logic)
    │
Agent Layer (LangGraph Orchestration)
    │ Data Ingestion | Data Profiler | Analysis | Chat
    │
Tool Layer (Atomic Capabilities)
    │ Parse | Stats | ChartRecommend | Plotly | PythonExec | File | Export | RAGSearch
    │
Data Layer (PostgreSQL + Redis + Local FS)
```

### 4 Core Agents

1. **Data Ingestion Agent**: 文件验证 → 解析 → 预览 → Schema 推断
2. **Data Profiler Agent**: 质量分析（缺失/异常/重复）→ 统计计算（描述统计/趋势/相关性/分布/聚合）
3. **Analysis Agent**: 图表推荐 → 图表生成（Mode1: PlotlyTool / Mode2: PythonExecTool 降级）→ 报告生成
4. **Chat Agent**: 多轮对话管理 → 意图理解 → Agent 协调 → 流式响应（SSE）

### Key Design Patterns

- **二阶段图表生成**: Mode 1 用 PlotlyTool 直接生成（首选），Mode 2 用 Code Agent 生成 Python 代码 → PythonExecTool 沙箱执行（降级）
- **Human-in-the-Loop**: 分析方向确认、图表选择、报告审核需用户确认后再继续
- **Streaming**: 大幅操作使用 SSE 流式响应，耗时任务使用 WebSocket 推送进度
- **Two Roles of MCP**: 平台既作为 MCP Server（暴露能力给 Claude Desktop/VS Code），也作为 MCP Client（消费外部 DB/KnowledgeBase 服务）

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # 6 个 API 路由模块（files/datasets/tasks/chat/reports/system）
│   ├── core/            # 配置(config.py)、数据库(database.py)、Redis(redis.py)、日志(logger.py)、异常(exceptions.py)
│   ├── agents/          # 4 个 Agent + 4 个 Prompt 文件
│   ├── tools/           # 8 个 Tool（parse/stats/chart_recommend/plotly/python_exec/file/export/rag_search）
│   ├── graph/           # LangGraph 图定义（state/builder/nodes/routers/checkpointer）
│   ├── models/          # SQLAlchemy ORM（10 张表）
│   ├── schemas/         # Pydantic v2 请求/响应（7 个模块）
│   ├── services/        # 5 个服务（file/dataset/task/chat/report）
│   ├── mcp/             # MCP 协议（server/client/resources/tools/schemas）
│   └── utils/           # 工具函数（file_utils/polars_utils/encode_utils/template_utils）
├── tests/               # 测试目录
├── data/                # 运行时数据（uploads/charts/exports/temp）
└── alembic/             # 数据库迁移

frontend/
├── src/
│   ├── views/           # 4 个视图页面（HomePage/DatasetList/DatasetDetail/TaskProgress）
│   ├── components/      # 20 个组件（layout/upload/dataset/chat/common）
│   ├── stores/          # 4 个 Pinia store（app/dataset/chat/task）
│   ├── api/             # 6 个 API 客户端
│   ├── composables/     # 3 个组合式函数（useWebSocket/useSSE/useFileUpload）
│   └── types/           # TypeScript 类型定义（api/dataset/chat/task）
```

## Task Breakdown & Implementation Records

See [docs/任务拆分与实施记录.md](docs/任务拆分与实施记录.md) for the complete task breakdown (~30 feature points across 6 phases).

**Workflow for each feature:**
1. User picks a feature point from the breakdown
2. I present the implementation plan (tech approach / files changed / key logic)
3. User reviews and approves
4. I write code
5. I update `docs/任务拆分与实施记录.md` (mark done + log details) and this file

## Development Commands

### Backend
```bash
# 激活虚拟环境
source ADVP/bin/activate       # Linux/Mac
source ADVP/Scripts/activate   # Windows Git Bash
.venv\Scripts\activate         # Windows cmd

# 安装/更新依赖
uv pip install -r backend/requirements.txt
uv pip install -e backend/     # 可编辑模式安装

# 运行服务
uvicorn backend.app.main:app --reload --port 8000

# 运行测试
pytest backend/tests/ -v
pytest backend/tests/test_api/ -v           # API 测试
pytest backend/tests/test_agents/ -v        # Agent 测试
pytest backend/tests/test_services/ -v      # 服务测试
pytest backend/tests/test_tools/ -v         # Tool 测试
pytest backend/tests/ -k "test_name" -v     # 单个测试

# 数据库迁移
alembic -c backend/alembic.ini revision --autogenerate -m "message"
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini downgrade -1

# 代码检查
ruff check backend/
ruff format --check backend/
```

### Frontend
```bash
cd frontend
npm install

# 开发服务器
npm run dev

# 构建
npm run build

# 类型检查
vue-tsc --noEmit

# lint
npm run lint
```

### Docker
```bash
docker compose up -d                        # 启动全部服务
docker compose up -d postgres redis         # 仅启动数据库
docker compose down
docker compose logs -f backend              # 查看后端日志
```

## Coding Standards

### Python (Backend)

1. **类型注解**: 所有函数参数和返回值必须标注类型，使用 `from __future__ import annotations` 启用延迟求值
2. **Async First**: 所有 I/O 操作使用 async/await（数据库/Redis/HTTP），CPU 密集任务用 `asyncio.to_thread` 或 `anyio.to_thread`
3. **Pydantic v2**: 所有 API 请求/响应使用 Pydantic v2 BaseModel 校验，ORM 与 Schema 分离
4. **LangGraph State**: Agent State 使用 TypedDict 定义，每个字段必须有类型注解和描述
5. **Error Handling**: 使用自定义异常体系（AppException → NotFoundException / ValidationException / AgentException），不允许 `except: pass`
6. **Tool 设计**: 每个 Tool 继承 BaseTool，实现 `async def execute(params: dict) -> dict` 接口
7. **Agent 设计**: 每个 Agent 继承 BaseAgent，实现 `def build_node() -> Callable` 接口
8. **日志**: 使用结构化日志（structured logging），所有 Agent/Tool 调用记录 token 消耗和执行时间
9. **数据库**: ORM 使用 SQLAlchemy 2.0 style（`select()` / `await session.execute()`），禁止使用 `session.query()`
10. **配置**: 所有环境变量通过 `pydantic-settings` 读取，禁止硬编码配置
11. **代码注释**:
    - 公共函数/方法必须写 docstring（三重引号），说明功能、参数、返回值、异常
    - 复杂逻辑块（超过 5 行）必须写行内注释说明意图，而非描述"做了什么"
    - Agent Prompt 文件必须包含版本号和变更记录注释
    - Tool/Agent 的边界 case 和特殊处理逻辑必须有注释标注
    - 禁止注释掉的死代码，一律删除

### TypeScript (Frontend)

1. **Vue 3 Composition API**: 使用 `<script setup lang="ts">`，禁止 Options API
2. **TypeScript Strict**: 启用 `strict: true`，禁止 `any` 类型
3. **Pinia Stores**: 使用 Setup Store 语法（`export const useXStore = defineStore('x', () => { ... })`）
4. **API 客户端**: 所有请求通过统一的 `api/client.ts` 封装，使用泛型定义响应类型
5. **组件命名**: 多单词组件名（PascalCase），文件名 kebab-case，如 `chat-panel/ChatPanel.vue`
6. **状态管理**: 组件本地状态用 `ref`/`reactive`，跨组件共享用 Pinia，禁止 `provide/inject` 滥用
7. **代码注释**:
    - 组件 Props/Emits 必须有类型注释说明用途
    - 工具函数（composables/utils）必须写 JSDoc 注释
    - 复杂响应式逻辑（watch/computed 链）必须标注依赖关系和触发条件
    - 禁止注释掉的死代码，一律删除

## Prohibited Operations

- **数据不可逆操作**：删除/覆盖用户上传的原始数据文件须先确认
- **API 破坏性变更**：不允许修改已有 API 端点签名而不更新前端调用方；必须版本化（v1 → v2）
- **静默吞异常**：不允许 `except: pass` 或 `try {} catch(e) {}` 空语句
- **硬编码敏感信息**：API Key、数据库密码、密钥等必须通过环境变量注入
- **付费软件依赖**：所有中间件和库必须使用开源免费许可证（MIT/Apache 2.0/BSD）
- **Schema 硬编码**：不允许硬编码数据字段 Schema，必须以动态推断方式实现
- **阻塞主线程**：前端不允许同步 XHR 请求，后端不允许在请求处理中执行同步 CPU 密集操作超过 100ms
- **空文件提交**：不允许提交空占位文件到版本控制
