# AI Agent 数据分析平台 — 架构设计文档 v1.0

> 文档状态：初稿 | 最后更新：2026-07-04
> 文档类型：技术架构设计文档（TAD）
> 适用范围：MVP（第一阶段）
> 前置文档：[需求文档](./AI_Agent数据分析平台_需求文档.md)

---

## 目录

1. [系统架构总览](#1-系统架构总览)
2. [LangGraph Agent 执行引擎设计](#2-langgraph-agent-执行引擎设计)
3. [Agent 详细设计](#3-agent-详细设计)
4. [Tool 详细设计](#4-tool-详细设计)
5. [Skills 与 MCP 设计](#5-skills-与-mcp-设计)
6. [数据流设计](#6-数据流设计)
7. [数据库设计](#7-数据库设计)
8. [API 设计](#8-api-设计)
9. [项目目录结构](#9-项目目录结构)
10. [RAG 知识库架构（第二阶段）](#10-rag-知识库架构第二阶段)
11. [MVP 开发路线图](#11-mvp-开发路线图)

---

## 1. 系统架构总览

### 1.1 分层架构

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                       客户端层（Vue 3 + Element Plus）                 │
 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
 │  │ 上传页   │ │ 数据集   │ │ 数据集   │ │ 对话页   │ │ 任务     │  │
 │  │          │ │ 列表页   │ │ 详情页   │ │          │ │ 进度页   │  │
 │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │ HTTP / SSE / WebSocket
 ┌────────────────────────────┴─────────────────────────────────────────┐
 │                    API 层（FastAPI + Pydantic v2）                     │
 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
 │  │ 文件管理 │ │ 数据集   │ │ 任务管理 │ │ 对话     │ │ 报告     │  │
 │  │ API      │ │ 管理 API │ │ API      │ │ API/SSE  │ │ API      │  │
 │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │
 ┌────────────────────────────┴─────────────────────────────────────────┐
 │                    Service 层（业务逻辑编排）                           │
 │  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐       │
 │  │ 文件服务   │ │ 数据集服务 │ │ 任务服务 │ │ 对话服务     │       │
 │  └────────────┘ └────────────┘ └──────────┘ └──────────────┘       │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │
 ┌────────────────────────────┴─────────────────────────────────────────┐
 │                    Agent 层（LangGraph 编排）                          │
 │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐         │
 │  │ Data Ingestion   │ │ Data Profiler    │ │ Analysis     │         │
 │  │ Agent            │ │ Agent            │ │ Agent        │         │
 │  └──────────────────┘ └──────────────────┘ └──────────────┘         │
 │  ┌────────────────────────────────┐                                  │
 │  │        Chat Agent              │                                  │
 │  └────────────────────────────────┘                                  │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │ 调用 Tool
 ┌────────────────────────────┴─────────────────────────────────────────┐
 │                    Tool 层（原子能力）                                  │
 │  ┌──────┐ ┌──────┐ ┌─────────┐ ┌──────┐ ┌──────────┐ ┌──────┐      │
 │  │Parse │ │Stats│ │ChartRec │ │Plotly│ │PythonExec│ │File  │      │
 │  │Tool  │ │Tool  │ │ Tool    │ │Tool  │ │ Tool     │ │Tool  │      │
 │  └──────┘ └──────┘ └─────────┘ └──────┘ └──────────┘ └──────┘      │
 │  ┌────────┐ ┌──────────────┐                                         │
 │  │Export  │ │ RAGSearch    │                                         │
 │  │Tool    │ │ Tool(Phase2) │                                         │
 │  └────────┘ └──────────────┘                                         │
 └────────────────────────────┬─────────────────────────────────────────┘
                              │
 ┌────────────────────────────┴─────────────────────────────────────────┐
 │                  Repository / 数据访问层                               │
 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                 │
 │  │PostgreSQL│ │ 本地文件  │ │  Redis   │ │  Milvus  │                 │
 │  │ + asyncpg│ │  系统     │ │ (缓存)   │ │ (Phase2) │                 │
 │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                 │
 └──────────────────────────────────────────────────────────────────────┘
```

### 1.2 各层职责

| 层级 | 职责 | 关键技术 |
|------|------|----------|
| **客户端层** | 用户界面、数据可视化、交互逻辑 | Vue 3 + Composition API + TypeScript |
| **客户端 UI** | Element Plus 组件库、ECharts 图表展示 | Element Plus + ECharts + Pinia |
| **API 层** | RESTful API、SSE 流式响应、请求校验 | FastAPI + Pydantic v2 + asyncpg |
| **Service 层** | 业务逻辑编排、事务管理、事件发布 | Python 3.11+ asyncio |
| **Agent 层** | AI Agent 编排、LLM 调用、Tool 路由 | LangGraph + LangChain Core |
| **Tool 层** | 原子能力：文件解析、统计计算、图表生成 | Polars + Plotly + OpenPyXL |
| **Repository 层** | 数据持久化、缓存、文件存储 | SQLAlchemy async + asyncpg + Redis |

### 1.3 技术选型总表

| 分类 | 技术 | 版本 | 许可证 | 用途 |
|------|------|------|--------|------|
| **后端框架** | FastAPI | ≥0.110 | MIT | Web 框架 |
| **ASGI 服务器** | Uvicorn | ≥0.29 | BSD-3 | 异步服务器 |
| **Agent 框架** | LangGraph | ≥0.2 | MIT | Agent 编排 |
| **LangChain** | LangChain Core | ≥0.3 | MIT | LLM 调用抽象 |
| **数据处理** | Polars | ≥1.0 | MIT | DataFrame 处理 |
| **列式格式** | PyArrow | ≥16.0 | Apache 2.0 | 数据序列化 |
| **Excel 解析** | OpenPyXL / Calamine | — | MIT / MIT | Excel 读取 |
| **图表引擎** | Plotly | ≥5.20 | MIT | 交互式图表 |
| **Python 沙箱** | RestrictedPython | — | Zope | 安全代码执行 |
| **数据库** | PostgreSQL | ≥16 | PostgreSQL License | 主数据库 |
| **异步驱动** | asyncpg | — | Apache 2.0 | PG 异步驱动 |
| **ORM** | SQLAlchemy 2.0 | ≥2.0 | MIT | ORM + Core |
| **迁移工具** | Alembic | — | MIT | 数据库迁移 |
| **缓存** | Redis | ≥7.0 | RSALv2 | 缓存、任务队列 |
| **向量数据库** | Milvus (Phase 2) | — | Apache 2.0 | 向量检索 |
| **前端框架** | Vue 3 | ≥3.4 | MIT | SPA 框架 |
| **UI 组件** | Element Plus | ≥2.5 | MIT | UI 组件库 |
| **图表展示** | ECharts | ≥5.5 | Apache 2.0 | 前端图表 |
| **状态管理** | Pinia | ≥2.1 | MIT | 状态管理 |
| **构建工具** | Vite | ≥5.0 | MIT | 前端构建 |
| **容器化** | Docker + Compose | — | Apache 2.0 | 部署 |

**注**：Redis 使用 RSALv2 许可证，经用户确认可用于本项目的内部部署场景。

---

## 2. LangGraph Agent 执行引擎设计

### 2.1 LangGraph 核心概念映射

| LangGraph 概念 | 本系统中的映射 | 说明 |
|----------------|---------------|------|
| **State** | `AnalysisState` (TypedDict) | 全局共享状态，所有 Agent 可读写 |
| **Node** | Agent 函数 (AgentNode) | 每个 Agent 是一个异步 Node |
| **Edge** | 固定顺序边 / 条件边 | 定义 Agent 执行顺序 |
| **Router** | `route_decision()` | 根据 State 状态决定下一节点 |
| **Checkpoint** | `PostgresSaver` | PostgreSQL 持久化 Checkpoint |
| **Thread** | `task_id` → thread_id | 每个分析任务对应一个线程 |
| **Interrupt** | Human-in-Loop 断点 | Agent 执行过程中等待用户确认 |

### 2.2 Graph 定义（Mermaid 状态图）

```mermaid
graph TD
    START([START]) --> validate_input{validate_input}
    
    validate_input -->|有效| ingestion[Data Ingestion Agent]
    validate_input -->|无效| error_handler[Error Handler]
    
    ingestion -->|成功| schema_router{schema_router}
    ingestion -->|失败| error_handler
    
    schema_router -->|置信度 > 0.8| profiler[Data Profiler Agent]
    schema_router -->|置信度 <= 0.8| human_confirm[Human-in-Loop: 等待用户确认]
    schema_router -->|解析后直接分析| profiler
    
    human_confirm -->|用户确认| profiler
    human_confirm -->|用户修改| profiler
    
    profiler -->|成功| analysis[Analysis Agent]
    profiler -->|失败| error_handler
    
    analysis --> chat_router{chat_router}
    analysis -->|失败| error_handler
    
    chat_router -->|继续对话| chat[Chat Agent]
    chat_router -->|分析完成| report[Report Generation]
    chat_router -->|重新分析| profiler
    
    chat -->|用户新指令| chat_router
    chat -->|换图| chart_regenerate[Chart Regeneration]
    chat -->|筛选数据| filter[Data Filter] --> analysis
    
    chart_regenerate --> chat
    report --> END([END])
    error_handler --> END
```

### 2.3 State 设计

```python
from typing import TypedDict, Optional, Any
from datetime import datetime

class AnalysisState(TypedDict):
    """全局共享状态—所有 Agent 可读写"""
    
    # --- 任务元信息 ---
    task_id: str                    # 分析任务 ID
    dataset_id: str                 # 数据集 ID
    thread_id: str                  # LangGraph Thread ID（= task_id）
    status: str                     # pending / running / completed / failed / paused
    current_phase: str              # 当前阶段标识
    progress: float                 # 0.0 ~ 1.0
    error_message: Optional[str]    # 错误信息
    created_at: str                 # ISO 时间戳
    
    # --- 文件与解析 ---
    file_id: str                    # 文件 ID
    file_path: str                  # 文件存储路径
    file_type: str                  # xlsx / csv / json
    parse_result: Optional[dict]    # 解析结果（预览数据、行数、列数）
    sheet_names: list[str]          # Excel Sheet 名称
    selected_sheet: Optional[str]   # 选中的 Sheet
    
    # --- Schema 信息 ---
    columns: list[dict]             # 列信息：[{name, dtype, semantic_type, confidence, description}]
    schema_confirmed: bool          # 用户是否已确认 Schema
    
    # --- 数据质量 ---
    quality_report: Optional[dict]  # 质量报告：{missing, duplicates, outliers, score}
    
    # --- 统计分析结果 ---
    stats_results: Optional[dict]   # 统计结果：{descriptive, correlations, trends, distributions, top_n}
    
    # --- 图表 ---
    charts: list[dict]              # 图表列表：[{type, config, description, html_path}]
    chart_count: int                # 图表数量
    
    # --- 报告 ---
    report: Optional[dict]          # 分析报告：{summary, findings, suggestions, risks}
    
    # --- 对话上下文 ---
    messages: list[dict]            # 对话历史：[{role, content, timestamp}]
    chat_iteration: int             # 对话轮次计数
    
    # --- 执行审计 ---
    agent_trace: list[dict]         # Agent 执行轨迹：[{agent, input, output, tokens, duration}]
    tool_trace: list[dict]          # Tool 调用轨迹：[{tool, input, output, duration}]
```

### 2.4 条件路由（Router）逻辑

```
route_schema():
    IF max(columns[].confidence) < 0.8:
        → WAIT_FOR_HUMAN (返回 schema 到前端等待确认)
    ELSE:
        → PROFILER

route_chat():
    IF 用户要求"重新分析":
        → PROFILER
    IF 用户要求"换图"或"新图表":
        → CHART_REGENERATE (Chat Agent 内部子流程)
    IF 用户要求"筛选/过滤":
        → FILTER (Chat Agent 内部子流程) → ANALYSIS
    IF 分析已完成 且 用户无新指令:
        → REPORT
    ELSE:
        → CHAT (继续对话)
```

### 2.5 错误处理与重试策略

| 错误类型 | 处理方式 | 重试策略 |
|----------|----------|----------|
| LLM API 调用失败 | 捕获异常 → 记录错误 → 重试 | 最多 3 次，指数退避（1s → 4s → 16s）|
| Tool 执行异常 | 捕获异常 → 记录 ToolLog → 返回错误信息给 Agent | 不重试，Agent 自行决定降级 |
| 文件解析错误 | 返回友好提示 → 等待用户重新上传 | 不重试 |
| 超时（Tool/Agent） | 中断执行 → 标记任务为 failed | 不重试 |
| 状态持久化失败 | 记录日志 → 继续执行（非致命）| 不重试 |

### 2.6 Checkpoint 持久化方案

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 使用 PostgreSQL 作为 Checkpoint 后端
checkpointer = PostgresSaver(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/dataviz"
)

# 每个 task_id 作为独立的 LangGraph Thread
graph = builder.compile(checkpointer=checkpointer)

# 恢复执行时通过 thread_id + checkpoint_id 恢复状态
config = {
    "configurable": {
        "thread_id": task_id,        # = task.id
        "checkpoint_id": checkpoint_id  # 指定恢复点
    }
}
```

Checkpoint 触发时机：
- 每个 Agent 节点执行完毕后自动保存
- Human-in-Loop 断点处保存
- 异常终止时保存（用于恢复）

---

## 3. Agent 详细设计

### 3.1 Data Ingestion Agent（数据摄取 Agent）

| 属性 | 说明 |
|------|------|
| **职责** | 接收用户上传的文件，解析为结构化数据，自动推断 Schema |
| **触发条件** | 用户上传文件后自动触发 |
| **执行轮次** | 约 0.5-1 轮 LLM 调用 |
| **绑定的 Tool** | ParseTool（主）、FileTool（辅助） |

**输入**：
```
file_path: str          # 文件存储路径
file_type: str          # xlsx | csv | json
file_id: str            # 文件 ID
dataset_id: str         # 数据集 ID
```

**输出（写入 State）**：
```
parse_result: dict      # 解析结果（预览数据、行/列数、各列样本值）
columns: list[dict]     # Schema 推断结果 [{name, dtype, semantic_type, confidence}]
current_phase: str      # "schema_inference"
progress: float         # 0.1 ~ 0.2
```

**LLM Prompt 设计原则**：
1. 传入前 50 行数据样本 + 每列的统计描述（非空值数、唯一值数、示例值）
2. LLM 不需要理解全部数据，只需要基于样本推断每列的语义含义
3. 输出格式为结构化的 JSON（列名 → 语义类型映射）
4. 语义类型包括：`金额/数量/百分比/日期/时间/地区/分类/标签/ID/名称/描述/布尔/未知`

**执行流程**：
```
1. FileTool 验证文件存在
2. ParseTool 解析文件 → 返回 DataFrame 预览 + 元信息
3. LLM 基于样本推断 Schema → 返回列语义定义
4. 更新 State.columns
5. Router 判断是否需要 Human-in-Loop（低置信度字段 → 等待用户确认）
```

### 3.2 Data Profiler Agent（数据剖析 Agent）

| 属性 | 说明 |
|------|------|
| **职责** | 分析数据质量、执行基础统计、生成质量报告 |
| **触发条件** | Schema 确认后自动触发 |
| **执行轮次** | 约 2-5 轮 LLM 调用 |
| **绑定的 Tool** | StatsTool（主力）、FileTool（辅助）|

**输入（State 读取）**：
```
file_path: str
columns: list[dict]     # 已确认的 Schema
parse_result: dict
```

**输出（写入 State）**：
```
quality_report: dict    # {missing, duplicates, outliers, score, details}
stats_results: dict     # {descriptive, correlations, trends, distributions, top_n}
current_phase: str      # "profiling" | "quality_analysis" | "statistical_analysis"
progress: float         # 0.2 ~ 0.5
```

**LLM Prompt 设计原则**：
1. LLM 不直接计算统计值——它负责**决定"分析什么"**
2. 根据字段特征决定：哪些列需要做分布分析、哪些需要相关性分析、有日期字段则做趋势分析
3. 将分析计划（分析指令列表）传给 StatsTool 批量执行
4. 基于 StatsTool 返回的结果，生成质量报告的文本解读

**执行流程**：
```
1. LLM 检查字段列表 → 决定分析维度（描述统计/分布/趋势/相关性/异常检测）
2. 调用 StatsTool 批量执行统计分析 → 返回统计结果
3. LLM 解读统计结果 → 生成质量报告（文本 + 评分）
4. 更新 State.quality_report + State.stats_results
```

### 3.3 Analysis Agent（分析 Agent）

| 属性 | 说明 |
|------|------|
| **职责** | 生成图表、撰写分析报告 |
| **触发条件** | 剖析完成后自动触发 |
| **执行轮次** | 约 3-8 轮 LLM 调用（最重的 Agent）|
| **绑定的 Tool** | ChartRecommendTool、PlotlyTool、PythonExecTool、ExportTool |

**输入（State 读取）**：
```
columns: list[dict]
quality_report: dict
stats_results: dict
```

**输出（写入 State）**：
```
charts: list[dict]      # [{chart_type, config, description, html_path}]
report: dict            # {summary, findings, suggestions, risks}
current_phase: str      # "chart_generation" | "report_generation"
progress: float         # 0.5 ~ 0.9
```

**LLM Prompt 设计原则**：
1. **第一步**：LLM 分析字段特征和统计结果 → 决定需要生成哪些图表（每种图附上"为什么推荐"）
2. **第二步**：对每种推荐的图表，先用 ChartRecommendTool 验证推荐是否合理
3. **第三步**：调用 PlotlyTool 生成图表（Mode 1，优先采用）
4. **降级策略**：当标准 Plotly 图表不能满足需求时，LLM 生成 Python 代码 → PythonExecTool 执行 → 返回图表（Mode 2）
5. **第四步**：LLM 基于所有分析结果和图表的解读 → 综合分析报告

**Mode 1 vs Mode 2 机制**：

```
                     ┌──────────────────────────────┐
                     │     ChartRecommendTool        │
                     │  推荐图表类型 + 字段映射       │
                     └──────────┬───────────────────┘
                                │ 推荐结果
                                ▼
                    ┌───────────────────────┐
                    │  是否可以 Plotly 实现？ │
                    └───────┬───────┬───────┘
                            │ 是    │ 否
                            ▼       ▼
                    ┌──────────┐ ┌──────────────────┐
                    │ Mode 1   │ │ Mode 2 (降级)     │
                    │PlotlyTool│ │ LLM → Python代码  │
                    │ 标准调用  │ │ → PythonExecTool  │
                    └──────────┘ └──────────────────┘
                            │       │
                            ▼       ▼
                    ┌──────────────────────┐
                    │ 图表 HTML 输出         │
                    │ + 推荐理由文本          │
                    └──────────────────────┘
```

**支持的图表类型**：

| 图表类型 | 适用场景 | Mode |
|----------|----------|------|
| 柱状图（Bar） | 分类对比、TopN | 1 |
| 折线图（Line） | 时间趋势 | 1 |
| 散点图（Scatter）| 两数值字段关系 | 1 |
| 饼图（Pie） | 占比分布 | 1 |
| 直方图（Histogram）| 数值分布 | 1 |
| 箱线图（Box） | 分布 + 异常值 | 1 |
| 热力图（Heatmap）| 相关性矩阵 | 1 |
| 面积图（Area） | 累积趋势 | 1 |
| 堆叠柱状图 | 分类 + 时间组成 | 2 |
| 气泡图 | 三维数据关系 | 2 |
| 雷达图 | 多维度对比 | 2 |
| 自定义图表 | 特殊需求 | 2 |

### 3.4 Chat Agent（对话 Agent）

| 属性 | 说明 |
|------|------|
| **职责** | 多轮对话交互，理解用户意图，执行后续操作 |
| **触发条件** | 用户发送消息到分析报告页 |
| **执行轮次** | 约 1-3 轮 LLM 调用/轮次 |
| **绑定的 Tool** | 全部 Tool（按需调用）|

**输入**：
```
messages: list[dict]    # 对话历史（含系统消息 + 历史消息）
query: str              # 用户最新问题
```

**输出（写入 State）**：
```
messages: list[dict]    # 追加新消息
chat_iteration: int     # +1
(可选) 修改其他 State 字段（如筛选后重新分析 → 更新 stats_results 等）
```

**意图分类体系**：

```
用户消息
    ├── 追问:"为什么销量下降了？" "代表什么？"
    │    → 基于已有分析结果，LLM 生成文本回答（不调 Tool）
    │
    ├── 换图:"换成年比看看" "用饼图看看"
    │    → 调用 PlotlyTool 重新生成图表
    │
    ├── 筛选:"只看北京的数据" "过滤掉 2023 年之前的"
    │    → 调用 FileTool/ParseTool 筛选数据
    │    → 重新触发 StatsTool 统计分析
    │    → 重新触发 PlotlyTool 生成图表
    │
    ├── 重新分析:"按品类重新分析" "按月份聚合看看"
    │    → 修改分组/聚合参数
    │    → 重新触发 StatsTool + PlotlyTool
    │
    ├── 导出:"帮我导出报告" "导出为 PDF"
    │    → 调用 ExportTool
    │
    └── 闲聊/无关:"你好" "你是谁"
        → LLM 直接回复（不调 Tool）
```

**流式对话方案**：
- 使用 Server-Sent Events（SSE）实现流式响应
- 前端逐 token 渲染，提供打字机效果
- 当 Agent 内部需要等待 Tool 执行时，发送中间状态消息
- Chat Agent 需维护对话上下文（保留最近 N 轮对话 + 当前分析结果的摘要）

---

## 4. Tool 详细设计

### 4.1 Tool 注册与发现

```python
# Tool 注册机制
class BaseTool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema
    
    @abstractmethod
    async def arun(self, **kwargs) -> Any:
        """异步执行 Tool"""

# LangGraph Tool 集成
from langchain_core.tools import BaseTool as LangChainTool

tool_registry: dict[str, BaseTool] = {
    "parse": ParseTool(),
    "stats": StatsTool(),
    "chart_recommend": ChartRecommendTool(),
    "plotly": PlotlyTool(),
    "python_exec": PythonExecTool(),
    "file": FileTool(),
    "export": ExportTool(),
    "rag_search": RAGSearchTool(),  # Phase 2
}
```

### 4.2 ParseTool（文件解析工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `parse` |
| **用途** | 根据文件类型选择解析器，将文件解析为统一格式的 DataFrame |
| **不使用 LLM** | ✅ 纯代码逻辑 |

**输入参数**：
```json
{
  "file_path": {"type": "string", "description": "文件路径"},
  "file_type": {"type": "string", "enum": ["xlsx", "xls", "csv", "json"]},
  "sheet_name": {"type": "string", "description": "Excel Sheet 名称（可选）"},
  "encoding": {"type": "string", "description": "CSV 编码（自动检测时忽略）"},
  "sample_rows": {"type": "integer", "description": "预览行数", "default": 50}
}
```

**输出结果**：
```json
{
  "row_count": 10000,
  "column_count": 15,
  "columns": [{"name": "日期", "dtype": "date", "non_null": 9980, "unique": 365, "sample_values": ["2024-01-01", ...]}],
  "preview_data": [{"日期": "2024-01-01", "销售额": 1234.5, ...}],
  "memory_usage_mb": 2.3,
  "warnings": ["column '备注' has 90% null values"]
}
```

**错误处理**：
| 错误场景 | 处理方式 |
|----------|----------|
| 文件不存在 | 抛出 FileNotFoundError |
| 文件损坏/加密 | 抛出 ValueError("文件已损坏或受密码保护") |
| CSV 编码检测失败 | 自动尝试 UTF-8/GBK/Latin-1/CP1252 |
| Excel Sheet 不存在 | 抛出 ValueError("Sheet 不存在") |
| 空文件 | 抛出 ValueError("文件为空") |
| 列数不匹配（CSV）| 尝试智能合并/分割列 |

### 4.3 StatsTool（统计分析工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `stats` |
| **用途** | 执行批量统计分析，所有计算基于 Polars |
| **不使用 LLM** | ✅ 纯代码逻辑 |

**输入参数**：
```json
{
  "file_path": {"type": "string", "description": "文件路径"},
  "analyses": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "type": {"type": "string", "enum": ["describe", "freq", "correlation", "trend", "distribution", "aggregate", "outlier"]},
        "columns": {"type": "array", "items": {"type": "string"}},
        "params": {"type": "object", "description": "按分析类型的具体参数"}
      }
    }
  }
}
```

**分析类型说明**：

| 分析类型 | 计算内容 | 参数 |
|----------|----------|------|
| `describe` | 数值列：count/mean/std/min/25%/50%/75%/max; 分类列：count/unique/top/freq | `columns` |
| `freq` | 频次统计 + TopN | `columns`, `top_n` |
| `correlation` | Pearson 相关系数矩阵 | `columns` |
| `trend` | 按时间聚合的趋势 | `date_column`, `value_columns`, `agg_method` |
| `distribution` | 直方图分桶统计 | `columns`, `bins` |
| `aggregate` | GroupBy 聚合 | `group_by`, `aggregations` |
| `outlier` | IQR/Z-Score 异常检测 | `columns`, `method`, `threshold` |

**输出结果**：
```json
{
  "results": [
    {
      "type": "describe",
      "columns": ["销售额"],
      "data": {"count": 9980, "mean": 15234.5, "std": 3456.7, "min": 100.0, "25%": 8500.0, "50%": 12000.0, "75%": 18000.0, "max": 50000.0}
    }
  ],
  "execution_time_ms": 345
}
```

### 4.4 ChartRecommendTool（图表推荐工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `chart_recommend` |
| **用途** | 根据字段类型和数量推荐最合适的图表类型 |
| **使用 LLM** | ✅ 轻量 LLM 调用 |

**输入参数**：
```json
{
  "columns": {
    "type": "array",
    "items": {"type": "object", "properties": {
      "name": {"type": "string"},
      "dtype": {"type": "string"},
      "semantic_type": {"type": "string"},
      "unique_count": {"type": "integer"},
      "non_null_ratio": {"type": "number"}
    }}
  },
  "stats_summary": {"type": "object", "description": "StatsTool 结果的摘要"},
  "user_request": {"type": "string", "description": "用户特殊要求（可选）"}
}
```

**图表推荐矩阵**：

| 字段组合 | 推荐图表类型 | 优先级 |
|----------|-------------|--------|
| 1 个分类 + 1 个数值 | 柱状图 | 1 |
| 1 个日期 + 1 个数值 | 折线图 | 1 |
| 2 个数值 | 散点图 | 1 |
| 1 个分类（少类别）| 饼图 | 1 |
| 1 个数值 | 直方图 | 1 |
| 1 个数值（分组）| 箱线图 | 1 |
| 多个数值（全量）| 热力图（相关性）| 1 |
| 1 个日期 + 多数值 | 面积图 | 2 |
| 多分类 + 多数值 | 堆叠柱状图 | 2 |

**输出**：
```json
{
  "recommendations": [
    {
      "type": "bar",
      "title": "各地区销售额分布",
      "x_column": "地区",
      "y_column": "销售额",
      "reason": "地区是分类字段（7 个类别），销售额是数值字段，柱状图最适合对比各类别间的数值差异",
      "priority": 1
    }
  ],
  "total_recommendations": 3
}
```

### 4.5 PlotlyTool（图表生成工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `plotly` |
| **用途** | 使用 Plotly 生成交互式 HTML 图表 |
| **不使用 LLM** | ✅ 纯代码逻辑（参数由 ChartRecommendTool 或 Chat Agent 提供）|

**输入参数**：
```json
{
  "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "pie", "histogram", "box", "heatmap", "area"]},
  "file_path": {"type": "string"},
  "x_column": {"type": "string"},
  "y_column": {"type": "string", "description": "需要时"},
  "color_column": {"type": "string", "description": "分组着色字段（可选）"},
  "title": {"type": "string"},
  "aggregation": {"type": "string", "enum": ["sum", "mean", "count", "max", "min", "none"], "default": "none"},
  "top_n": {"type": "integer", "description": "TopN（可选）"},
  "filters": {"type": "array", "description": "筛选条件（可选）"}
}
```

**输出**：
```json
{
  "chart_html_path": "data/charts/abc123_chart_001.html",
  "chart_data_summary": "柱状图显示：华东地区销售额最高（¥1,234,567），西北最低（¥234,567）",
  "width": 800,
  "height": 500,
  "chart_type": "bar"
}
```

**Plotly 配置要点**：
- 使用 Plotly 的 JSON 配置格式，不直接传递 DataFrame 给 Plotly
- 在 Tool 内部读取文件 → Polars 处理 → 转换为 Plotly 可接受的格式
- 输出为独立的 HTML 文件（含 Plotly.js CDN 引用），方便嵌入报告和分享
- 图表支持交互：悬停提示、缩放、下载为 PNG

### 4.6 PythonExecTool（Python 代码执行工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `python_exec` |
| **用途** | 当 Plotly 标准图表模式不满足需求时，LLM 生成 Python 代码，在沙箱中执行 |
| **使用 LLM** | ✅ LLM 生成代码（Tool 本身只负责沙箱执行）|

**输入参数**：
```json
{
  "code": {"type": "string", "description": "Python 代码"},
  "file_path": {"type": "string", "description": "数据文件路径"},
  "timeout": {"type": "integer", "default": 30}
}
```

**输出**：
```json
{
  "success": true,
  "result": {"chart_type": "bubble", "chart_config": {...}, "html_path": "..."},
  "stdout": "",
  "execution_time_ms": 1234
}
```

**沙箱安全策略**：

| 安全维度 | 策略 |
|----------|------|
| **模块白名单** | 仅允许：plotly, pandas（降级用）, numpy, json, math, datetime |
| **禁用功能** | os, subprocess, sys, eval, exec, open, import（白名单外）, __import__ |
| **资源限制** | 最大执行时间 30s，最大内存 256MB |
| **数据访问** | 只读指定文件路径，不对外网络访问 |
| **输出限制** | 只允许返回 JSON 可序列化的结果 |

**实现方案**：使用 `RestrictedPython` 或 Docker 容器沙箱。MVP 阶段优先采用 `RestrictedPython` + 线程超时控制。

### 4.7 FileTool（文件操作工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `file` |
| **用途** | 文件读写、采样、格式转换、编码检测 |
| **不使用 LLM** | ✅ 纯代码逻辑 |

**主要功能**：
- `read(path, encoding, n_rows)` — 读取文件片段
- `sample(path, strategy, n_rows)` — 采样（头部/随机/分层）
- `detect_encoding(path)` — 自动检测编码（基于 chardet）
- `detect_delimiter(path)` — 自动检测分隔符（CSV）
- `filter(path, conditions)` — 按条件筛选数据 → 输出新临时文件
- `get_metadata(path)` — 获取文件元信息（大小/行数/修改时间/MD5）

### 4.8 ExportTool（报告导出工具）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `export` |
| **用途** | 将分析报告导出为 HTML 或 Markdown 格式 |
| **不使用 LLM** | ✅ 纯代码逻辑 |

**输入参数**：
```json
{
  "report": {"type": "object", "description": "报告内容"},
  "charts": {"type": "array", "description": "图表 HTML 路径列表"},
  "format": {"type": "string", "enum": ["html", "markdown"]},
  "dataset_name": {"type": "string"}
}
```

**输出**：
```json
{
  "export_path": "data/exports/report_abc123.html",
  "format": "html",
  "file_size_bytes": 234567
}
```

**HTML 报告模板**：
- 自包含 HTML（所有 CSS/JS 内嵌或 CDN 引用）
- 含目录导航（Anchor 跳转）
- 图表通过 iframe 或嵌入式 HTML 展示
- 移动端适配（响应式布局）
- 打印友好样式

### 4.9 RAGSearchTool（知识库检索工具 — 第二阶段预留）

| 属性 | 说明 |
|------|------|
| **Tool ID** | `rag_search` |
| **用途** | 从企业知识库中检索业务指标定义、口径说明、行业知识 |
| **使用 LLM** | ✅ 检索后 LLM 阅读理解 |

**预留接口**（Phase 2 实现）：
```python
class RAGSearchTool(BaseTool):
    name = "rag_search"
    description = "从知识库检索业务指标口径和行业知识"
    
    async def arun(self, query: str, top_k: int = 5) -> dict:
        # Phase 2 实现：Embedding → Vector Store → 检索 → 返回
        pass
```

---

## 5. Skills 与 MCP 设计

### 5.1 Skills 设计

#### 5.1.1 Skills 概念模型

Skills（技能）是平台中 **可复用的能力模块**，位于 Agent 层与 Tool 层之间。与 Tool 的核心区别：

| 维度 | Tool（工具） | Skill（技能） |
|------|-------------|---------------|
| **粒度** | 原子操作，一次调用完成 | 复合操作，可编排多个 Tool + LLM 调用 |
| **状态** | 无状态 | 有状态（可维护上下文和中间结果） |
| **LLM 调用** | 通常无（纯代码逻辑） | 可包含 LLM 调用（理解/推理/生成） |
| **复用范围** | 被多个 Agent 调用 | 被多个 Agent 组合使用 |
| **错误处理** | 简单（成功/失败） | 复杂（降级/重试/部分成功） |

```
Agent 层
    │
    │  编排 Skills
    ▼
Skill 层  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ FileIngestion│ │Statistical   │ │ ChartGen     │
          │ Skill        │ │ AnalysisSkill│ │ Skill        │
          └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                 │                │                │
    ┌────────────┼────────────────┼────────────────┼──────────┐
    │            ▼                ▼                ▼           │
Tool 层    ParseTool   StatsTool   ChartRecommendTool         │
    │     FileTool         ▲       PlotlyTool                  │
    │                      │       PythonExecTool              │
    └──────────────────────┼──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  LLM 调用    │
                    │ (按需)       │
                    └─────────────┘
```

#### 5.1.2 Skills 目录

| Skill ID | 名称 | 所属 Agent | 编排的 Tool + LLM 调用 | 说明 |
|----------|------|-----------|----------------------|------|
| `skill.file_ingestion` | 文件接入 Skill | Ingestion Agent | FileTool → ParseTool → LLM(Schema 推断) | 文件接入全流程 |
| `skill.schema_inference` | Schema 推断 Skill | Ingestion Agent | LLM(字段语义推断) + FileTool(样本提取) | 独立的 Schema 推断能力 |
| `skill.data_quality` | 数据质量 Skill | Profiler Agent | StatsTool(缺失/异常/重复) → LLM(质量解读) | 数据质量分析和报告 |
| `skill.statistical_analysis` | 统计分析 Skill | Profiler Agent | LLM(分析计划) → StatsTool(批量执行) → LLM(结果解读) | 多维度统计分析 |
| `skill.chart_recommendation` | 图表推荐 Skill | Analysis Agent | LLM(字段分析) → ChartRecommendTool(验证) | 图表类型推荐 |
| `skill.chart_generation` | 图表生成 Skill | Analysis Agent | PlotlyTool(Mode 1) → [降级: LLM → PythonExecTool(Mode 2)] | 图表生成含降级 |
| `skill.report_composition` | 报告撰写 Skill | Analysis Agent | LLM(综合所有结果) → ExportTool(导出) | 分析报告生成 |
| `skill.conversation` | 对话交互 Skill | Chat Agent | LLM(意图分类) → [按需调用各 Tool] | 多轮对话处理 |
| `skill.data_filter` | 数据筛选 Skill | Chat Agent | FileTool(filter) → StatsTool(recalc) | 筛选后重新分析 |

#### 5.1.3 Skill 接口定义

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class SkillContext:
    """Skill 执行的上下文，包含状态引用和可用的 Tool"""
    def __init__(self, state: dict, tool_registry: dict, llm: Any):
        self.state = state          # AnalysisState 引用
        self.tools = tool_registry  # 可用 Tool 注册表
        self.llm = llm              # LLM 调用接口
        self.metadata = {}          # 执行元信息（耗时、token 等）

class BaseSkill(ABC):
    """Skill 基类"""
    
    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Skill 唯一标识"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Skill 描述"""
        pass
    
    @property
    @abstractmethod
    def dependencies(self) -> list[str]:
        """依赖的其他 Skill ID 列表"""
        pass
    
    @abstractmethod
    async def execute(self, ctx: SkillContext, params: dict) -> dict:
        """执行 Skill，返回结果"""
        pass
    
    async def validate(self, params: dict) -> bool:
        """校验参数（可选重写）"""
        return True
```

#### 5.1.4 Skill 实现示例

```python
class ChartGenerationSkill(BaseSkill):
    """图表生成 Skill — 含 Mode 1 → Mode 2 降级"""
    
    skill_id = "skill.chart_generation"
    description = "根据推荐配置生成图表，支持 Plotly 和 Python 代码两种模式"
    dependencies = ["skill.chart_recommendation"]
    
    async def execute(self, ctx: SkillContext, params: dict) -> dict:
        recommendations = params["recommendations"]
        file_path = params["file_path"]
        charts = []
        
        for rec in recommendations:
            # Mode 1: PlotlyTool 标准生成
            plotly_tool = ctx.tools["plotly"]
            try:
                result = await plotly_tool.arun(
                    chart_type=rec["type"],
                    file_path=file_path,
                    x_column=rec.get("x_column"),
                    y_column=rec.get("y_column"),
                    title=rec.get("title", ""),
                )
                charts.append({
                    "type": rec["type"],
                    "html_path": result["chart_html_path"],
                    "description": rec.get("reason", ""),
                    "mode": "plotly",
                })
            except Exception as e:
                # Mode 2: 降级到 Python 代码生成
                python_tool = ctx.tools["python_exec"]
                code = self._generate_plotly_code(rec)
                result = await python_tool.arun(
                    code=code,
                    file_path=file_path,
                )
                charts.append({
                    "type": rec["type"],
                    "html_path": result["html_path"],
                    "description": rec.get("reason", "") + "（降级模式）",
                    "mode": "python",
                })
        
        return {"charts": charts, "total": len(charts)}
    
    def _generate_plotly_code(self, recommendation: dict) -> str:
        """生成 Plotly Python 代码（Mode 2 降级）"""
        # 使用模板生成标准 Plotly Python 代码
        pass
```

#### 5.1.5 Skills 注册表

```python
# skills/registry.py

skill_registry: dict[str, BaseSkill] = {
    "skill.file_ingestion": FileIngestionSkill(),
    "skill.schema_inference": SchemaInferenceSkill(),
    "skill.data_quality": DataQualitySkill(),
    "skill.statistical_analysis": StatisticalAnalysisSkill(),
    "skill.chart_recommendation": ChartRecommendationSkill(),
    "skill.chart_generation": ChartGenerationSkill(),
    "skill.report_composition": ReportCompositionSkill(),
    "skill.conversation": ConversationSkill(),
    "skill.data_filter": DataFilterSkill(),
}
```

#### 5.1.6 Skills 与 Agent 的绑定关系

```
Data Ingestion Agent
    ├── skill.file_ingestion       # 主流程
    └── skill.schema_inference     # Schema 推断

Data Profiler Agent
    ├── skill.data_quality         # 质量分析
    └── skill.statistical_analysis # 统计分析

Analysis Agent
    ├── skill.chart_recommendation # 图表推荐
    ├── skill.chart_generation     # 图表生成
    └── skill.report_composition   # 报告撰写

Chat Agent
    ├── skill.conversation         # 对话处理
    └── skill.data_filter          # 数据筛选（按需）
```

---

### 5.2 MCP（Model Context Protocol）设计

#### 5.2.1 MCP 概念与定位

MCP（Model Context Protocol）是由 Anthropic 推出的开放协议，用于标准化 AI 模型与外部工具/数据源之间的交互方式。在本平台中，MCP 承担两个角色：

```
┌──────────────────────────────────────────────────────────────┐
│                     AI Agent 数据分析平台                      │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │ MCP Server   │     │ MCP Client  │     │ 内部 Agent  │    │
│  │ (对外暴露能力) │     │ (接入外部能力) │     │ 编排引擎    │    │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘    │
│         │                   │                    │            │
│         ▼                   ▼                    ▼            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ 外部 AI 客户端 │   │ 外部 MCP     │   │ 内部 Skills/Tools│ │
│  │ (Claude/Cursor│   │ Server 生态  │   │                  │ │
│  │  /其他AI IDE) │   │ (DB/FS/Web) │   │                  │ │
│  └──────────────┘   └──────────────┘   └──────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2.2 角色一：平台作为 MCP Server（对外暴露）

平台自身运行一个 MCP Server，将内部的分析能力以标准化接口暴露给外部 AI 客户端（如 Claude Desktop、VS Code 扩展、Cursor 等）。

**MCP Server 配置**：

```json
{
  "mcpServers": {
    "data-analysis-platform": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "env": {
        "MCP_HOST": "localhost",
        "MCP_PORT": "8100"
      }
    }
  }
}
```

**暴露的 MCP 资源（Resources）**：

| Resource URI | 类型 | 说明 |
|-------------|------|------|
| `dataviz://datasets` | 资源列表 | 所有数据集 |
| `dataviz://datasets/{id}` | 资源 | 数据集详情 |
| `dataviz://datasets/{id}/schemas` | 资源 | 字段 Schema |
| `dataviz://datasets/{id}/charts` | 资源 | 生成的图表 |
| `dataviz://datasets/{id}/report` | 资源 | 分析报告 |
| `dataviz://tasks/{id}` | 资源 | 任务状态 |

**暴露的 MCP 工具（Tools）**：

| Tool Name | 对应内部 Tool | 说明 |
|-----------|--------------|------|
| `upload_file` | 文件上传 API | 上传并解析数据文件 |
| `list_datasets` | 数据集 API | 浏览已有数据集 |
| `start_analysis` | 任务 API | 启动全自动分析 |
| `ask_question` | Chat Agent API | 对数据集发起对话分析 |
| `generate_chart` | PlotlyTool | 指定参数生成图表 |
| `export_report` | ExportTool | 导出分析报告 |

**对外暴露的价值**：
- 用户可以在 Claude Desktop 中直接连接平台："分析我本地的销售数据"
- VS Code 中开发时可直接调取平台分析能力
- 第三方应用可通过 MCP 协议与平台集成

#### 5.2.3 MCP Server 实现方案

```python
# backend/app/mcp/server.py

"""
MCP Server 实现 — 将平台能力暴露给外部 AI 客户端

使用 mcp 库（pip install mcp）快速搭建 MCP 服务器。
"""

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from app.services.dataset_service import DatasetService
from app.services.task_service import TaskService
from app.tools.plotly_tool import PlotlyTool

# 创建 MCP Server 实例
server = Server("data-analysis-platform")

# ── 资源定义 ──

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="dataviz://datasets",
            name="All Datasets",
            description="所有数据集列表",
            mimeType="application/json",
        ),
        types.Resource(
            uri="dataviz://datasets/{id}",
            name="Dataset Details",
            description="指定数据集的详细信息",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: types.AnyUrl) -> str:
    if str(uri).startswith("dataviz://datasets"):
        # 返回数据集数据
        service = DatasetService()
        datasets = await service.list_datasets()
        return json.dumps(datasets, ensure_ascii=False)
    raise ValueError(f"Unknown resource: {uri}")

# ── 工具定义 ──

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="start_analysis",
            description="上传文件并启动全自动数据分析",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径（支持 .xlsx/.csv/.json）",
                    },
                    "dataset_name": {
                        "type": "string",
                        "description": "数据集名称（可选）",
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="ask_question",
            description="对已分析的数据集进行对话式追问",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["dataset_id", "question"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "start_analysis":
        task_service = TaskService()
        task = await task_service.create_and_start(arguments["file_path"])
        return [types.TextContent(
            type="text",
            text=f"分析任务已启动（ID: {task.id}），正在自动分析数据..."
        )]
    elif name == "ask_question":
        # 调用 Chat Agent 处理问题
        ...
    raise ValueError(f"Unknown tool: {name}")

# ── 启动 MCP Server ──

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="data-analysis-platform",
                server_version="1.0.0",
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

#### 5.2.4 角色二：平台作为 MCP Client（接入外部能力）

在第二阶段，平台将通过 MCP Client 接入外部 MCP Server，扩展数据源接入能力：

```python
# backend/app/mcp/client.py

"""
MCP Client 实现 — 接入外部 MCP Server 扩展平台能力
"""

class MCPClientManager:
    """MCP 客户端管理器，管理外部 MCP Server 连接"""
    
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.tool_registry: dict[str, ExternalTool] = {}
    
    async def connect_server(self, name: str, command: str, args: list[str]):
        """连接外部 MCP Server"""
        # 使用 mcp 客户端库连接外部 server
        process = await create_process(command, args)
        session = await ClientSession(process.stdout, process.stdin).__aenter__()
        self.sessions[name] = session
        
        # 获取 Server 能力声明
        tools = await session.list_tools()
        for tool in tools:
            self.tool_registry[f"{name}:{tool.name}"] = ExternalTool(
                server_name=name,
                session=session,
                tool_def=tool,
            )
    
    async def get_external_tool(self, name: str) -> Optional["ExternalTool"]:
        """获取外部 Tool"""
        return self.tool_registry.get(name)
```

**计划接入的外部 MCP Server**：

| 外部 MCP Server | 用途 | Phase |
|----------------|------|-------|
| **Database MCP Server** | 直接连接 MySQL/PostgreSQL 进行数据查询和分析 | Phase 2 |
| **File System MCP Server** | 访问远端文件系统（NAS/S3/共享目录）| Phase 2 |
| **Knowledge Base MCP Server** | 企业知识库检索（指标口径、业务文档）| Phase 2 |
| **Web Search MCP Server** | 联网搜索补充行业背景知识 | Phase 2 |

**与 RAG 架构的关系**：
```
Chat Agent
    │
    ├── skill.conversation ───→ 内部 Skills/Tools
    │
    └── RAGSearchTool ───→ MCP Client Manager
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            KnowledgeBase   Database    WebSearch
            MCP Server     MCP Server  MCP Server
```

#### 5.2.5 MCP 目录结构

```
backend/app/mcp/
├── __init__.py
├── server.py          # MCP Server 实现（对外暴露能力）
├── client.py          # MCP Client 管理器（接入外部能力）
├── resources.py       # Resource 定义和处理器
├── tools.py           # 暴露给外部的 Tool 定义
└── schemas.py         # MCP 相关的 Pydantic Schema
```

---

## 6. 数据流设计

### 6.1 Happy Path 全链路数据流（时序图）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API 层
    participant Service as Service 层
    participant Graph as LangGraph
    participant PG as PostgreSQL
    
    User->>Frontend: 1. 上传文件
    Frontend->>API: POST /api/v1/files/upload
    API->>Service: 保存文件到本地
    Service-->>API: file_id + 文件信息
    API-->>Frontend: 上传成功 + file_id
    
    Frontend->>API: 2. POST /api/v1/tasks/{id}/start
    
    API->>Service: 创建分析任务
    Service->>PG: INSERT task (status=running)
    Service->>Graph: 启动 LangGraph (thread_id=task_id)
    
    Note over Graph: ── Phase 1: Ingestion ──
    Graph->>Graph: Data Ingestion Agent
    Graph-->>API: 状态更新: schema_inference
    API-->>Frontend: Progress: 20%
    
    Note over Graph: ── Phase 2: Profiling ──
    Graph->>Graph: Data Profiler Agent
    Graph-->>API: 状态更新: quality_analysis
    API-->>Frontend: Progress: 40%
    
    Note over Graph: ── Phase 3: Statistics ──
    Graph->>Graph: Stats Analysis
    Graph-->>API: 状态更新: statistical_analysis
    API-->>Frontend: Progress: 60%
    
    Note over Graph: ── Phase 4: Visualization ──
    Graph->>Graph: Chart Generation
    Graph-->>API: 状态更新: chart_generation
    API-->>Frontend: Progress: 80%
    
    Note over Graph: ── Phase 5: Report ──
    Graph->>Graph: Report Generation
    Graph-->>API: 状态更新: report_generation
    API-->>Frontend: Progress: 95%
    
    Graph->>PG: 保存完整结果
    Graph-->>API: 任务完成
    Service->>PG: UPDATE task (status=completed)
    API-->>Frontend: 任务完成 + 结果数据
    
    User->>Frontend: 3. 查看分析结果
    Frontend->>API: GET /api/v1/datasets/{id}
    API-->>Frontend: 完整分析结果（Schema/统计/图表/报告）
    
    User->>Frontend: 4. "为什么销售额下降了？"
    Frontend->>API: POST /api/v1/chat/stream (SSE)
    API->>Service: 处理对话
    Service->>Graph: Chat Agent 处理
    Graph-->>API: 流式输出
    API-->>Frontend: SSE 流式返回
```

### 6.2 多轮对话数据流

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API 层 (SSE)
    participant Graph as LangGraph
    participant Tools as Tool 层
    
    User->>Frontend: "换成饼图看看各品类占比"
    Frontend->>API: POST /api/v1/chat/stream {query, task_id}
    API->>Graph: Chat Agent 处理
    
    Graph->>Graph: 意图分类 → "换图"
    Graph->>Tools: PlotlyTool (pie, 品类, 销售额)
    Tools-->>Graph: 饼图 HTML
    
    Graph-->>API: {"type": "chart", "html_path": "..."}
    API-->>Frontend: SSE: [chart] event
    
    Graph-->>API: {"type": "text", "content": "以下是各品类销售额占比..."}
    API-->>Frontend: SSE: [text] event (逐 token)
    
    Frontend-->>User: 渲染饼图 + 文字解释
    
    User->>Frontend: "只看前 5 个品类"
    Frontend->>API: SSE 新的查询
    
    Graph->>Tools: FileTool.filter() → 临时文件
    Graph->>Tools: PlotlyTool (pie, top5)
    Tools-->>Graph: 新饼图
    
    Graph-->>API: SSE events
    API-->>Frontend: 新图表 + 解释
    Frontend-->>User: 更新显示
```

### 6.3 Human-in-Loop 数据流

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API 层
    participant Graph as LangGraph
    
    Note over Graph: Ingestion Agent 完成 Schema 推断
    Graph->>Graph: schema_router: 低置信度 → 需要用户确认
    
    Graph-->>API: INTERRUPT: wait_for_schema_confirmation
    API-->>Frontend: 返回 Schema 候选 + 等待确认
    
    Frontend-->>User: 显示字段列表（高亮低置信度字段）
    User->>Frontend: 修改"客户ID"类型为"文本"
    Frontend->>API: PUT /api/v1/tasks/{id}/confirm-schema
    
    API->>Graph: 恢复执行 + 用户修正的 Schema
    Graph->>Graph: 继续 Profiler Agent
```

### 6.4 Checkpoint 状态持久化数据流

```mermaid
sequenceDiagram
    participant Graph as LangGraph
    participant Checkpoint as PostgresSaver
    participant PG as PostgreSQL
    
    Note over Graph: Agent 1 执行完毕
    Graph->>Checkpoint: 保存 State
    Checkpoint->>PG: INSERT INTO checkpoints (thread_id, checkpoint_id, parent_checkpoint_id, checkpoint_data)
    PG-->>Checkpoint: 确认
    Checkpoint-->>Graph: checkpoint_id
    
    Note over Graph: Agent 2 开始（从 checkpoint 恢复可选）
    
    Note over Graph: ⚠️ 服务重启/崩溃
    
    Note over Graph: 恢复流程
    Graph->>Checkpoint: get_state(thread_id)
    Checkpoint->>PG: SELECT ... WHERE thread_id = ?
    PG-->>Checkpoint: 最新 checkpoint 数据
    Checkpoint-->>Graph: 恢复 State
    Note over Graph: 从断点节点继续执行
```

Checkpoint 数据格式：
```json
{
  "thread_id": "task_abc123",
  "checkpoint_id": "1ef2a3b4-...",
  "parent_checkpoint_id": "9z8y7x6w-...",
  "checkpoint_data": {
    "state": { /* AnalysisState 的完整快照 */ },
    "ts": "2026-07-04T10:30:00Z"
  }
}
```

---

## 7. 数据库设计

### 7.1 ER 图

```mermaid
erDiagram
    datasets ||--o{ files : contains
    datasets ||--|{ tasks : has
    datasets ||--o{ column_schemas : defines
    
    files ||--o{ column_schemas : derived_from
    
    tasks ||--o{ checkpoints : persists
    tasks ||--o{ charts : generates
    tasks ||--o{ reports : produces
    tasks ||--o{ chat_messages : has
    tasks ||--o{ agent_executions : traces
    tasks ||--o{ tool_logs : logs
    
    agent_executions ||--o{ tool_logs : includes

    datasets {
        uuid id PK
        varchar name
        text description
        varchar status
        int row_count
        int column_count
        text storage_path
        timestamp created_at
        timestamp updated_at
    }

    files {
        uuid id PK
        uuid dataset_id FK
        varchar filename
        varchar file_type
        bigint file_size
        varchar md5
        varchar storage_path
        varchar encoding
        text sheet_names
        varchar selected_sheet
        int row_count
        int column_count
        jsonb parse_metadata
        timestamp created_at
    }

    column_schemas {
        uuid id PK
        uuid dataset_id FK
        uuid file_id FK
        varchar column_name
        varchar detected_dtype
        varchar semantic_type
        float confidence
        text description
        boolean user_corrected
        varchar corrected_dtype
        varchar corrected_semantic_type
        int non_null_count
        int unique_count
        jsonb sample_values
        timestamp created_at
    }

    tasks {
        uuid id PK
        uuid dataset_id FK
        varchar status
        varchar current_phase
        float progress
        text error_message
        varchar thread_id
        jsonb state_summary
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
    }

    checkpoints {
        uuid id PK
        uuid task_id FK
        uuid thread_id
        varchar checkpoint_id
        uuid parent_checkpoint_id
        jsonb checkpoint_data
        timestamp created_at
    }

    charts {
        uuid id PK
        uuid task_id FK
        varchar chart_type
        text title
        jsonb config_json
        text description
        varchar html_path
        varchar data_summary
        int sort_order
        timestamp created_at
    }

    reports {
        uuid id PK
        uuid task_id FK
        text content_md
        varchar html_path
        varchar export_format
        timestamp created_at
    }

    chat_messages {
        uuid id PK
        uuid task_id FK
        varchar role
        text content
        varchar msg_type
        jsonb context_data
        int iteration
        timestamp created_at
    }

    agent_executions {
        uuid id PK
        uuid task_id FK
        varchar agent_name
        text input_summary
        text output_summary
        int tokens_used
        int duration_ms
        varchar status
        timestamp created_at
    }

    tool_logs {
        uuid id PK
        uuid execution_id FK
        varchar tool_name
        text input_summary
        text output_summary
        int duration_ms
        varchar status
        text error_message
        timestamp created_at
    }
```

### 7.2 表详细设计

#### datasets — 数据集

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| name | VARCHAR(255) | NOT NULL | 数据集名称（默认文件名） |
| description | TEXT | NULL | 描述 |
| status | VARCHAR(50) | NOT NULL DEFAULT 'active' | active / archived / deleted |
| row_count | INTEGER | NULL | 总行数 |
| column_count | INTEGER | NULL | 总列数 |
| storage_path | TEXT | NOT NULL | 数据文件存储路径 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | |

**索引**：`idx_datasets_created_at` ON (created_at DESC)

---

#### files — 上传文件

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| dataset_id | UUID | FK → datasets.id | |
| filename | VARCHAR(255) | NOT NULL | 原始文件名 |
| file_type | VARCHAR(20) | NOT NULL | xlsx / csv / json |
| file_size | BIGINT | NOT NULL | 字节数 |
| md5 | VARCHAR(32) | NOT NULL | 文件 MD5 |
| storage_path | TEXT | NOT NULL | 存储路径 |
| encoding | VARCHAR(20) | NULL | CSV 编码 |
| sheet_names | TEXT[] | NULL | Excel Sheet 列表 |
| selected_sheet | VARCHAR(255) | NULL | 选中的 Sheet |
| row_count | INTEGER | NULL | 解析后的行数 |
| column_count | INTEGER | NULL | 解析后的列数 |
| parse_metadata | JSONB | NULL | 解析元信息 |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_files_md5` ON (md5), `idx_files_dataset_id` ON (dataset_id)

---

#### column_schemas — 字段 Schema

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| dataset_id | UUID | FK → datasets.id | |
| file_id | UUID | FK → files.id | |
| column_name | VARCHAR(255) | NOT NULL | 原始列名 |
| detected_dtype | VARCHAR(50) | NOT NULL | Polars 检测的数据类型 |
| semantic_type | VARCHAR(50) | NOT NULL | LLM 推断的语义类型 |
| confidence | REAL | NOT NULL DEFAULT 0.0 | 置信度 0~1 |
| description | TEXT | NULL | LLM 生成的字段描述 |
| user_corrected | BOOLEAN | NOT NULL DEFAULT FALSE | 用户是否手动修正 |
| corrected_dtype | VARCHAR(50) | NULL | 用户修正的数据类型 |
| corrected_semantic_type | VARCHAR(50) | NULL | 用户修正的语义类型 |
| non_null_count | INTEGER | NULL | 非空值数 |
| unique_count | INTEGER | NULL | 唯一值数 |
| sample_values | JSONB | NULL | 样本值（前 10 个）|
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_schemas_dataset_id` ON (dataset_id), `idx_schemas_file_id` ON (file_id)

---

#### tasks — 分析任务

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| dataset_id | UUID | FK → datasets.id | |
| status | VARCHAR(50) | NOT NULL DEFAULT 'pending' | pending / running / paused / completed / failed / cancelled |
| current_phase | VARCHAR(100) | NULL | uploading / parsing / schema_inference / profiling / analysis / chart_generation / report_generation / chatting |
| progress | REAL | NOT NULL DEFAULT 0.0 | 0.0 ~ 1.0 |
| error_message | TEXT | NULL | 失败原因 |
| thread_id | VARCHAR(255) | NOT NULL | LangGraph thread_id |
| state_summary | JSONB | NULL | 状态摘要（用于前端展示）|
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| completed_at | TIMESTAMPTZ | NULL | |

**索引**：`idx_tasks_dataset_id` ON (dataset_id), `idx_tasks_status` ON (status), `idx_tasks_thread_id` ON (thread_id) UNIQUE

---

#### checkpoints — LangGraph Checkpoint

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id | |
| thread_id | VARCHAR(255) | NOT NULL | LangGraph thread_id |
| checkpoint_id | VARCHAR(255) | NOT NULL | LangGraph checkpoint_id |
| parent_checkpoint_id | VARCHAR(255) | NULL | 父 checkpoint_id |
| checkpoint_data | JSONB | NOT NULL | State 快照 |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_checkpoints_thread` ON (thread_id, checkpoint_id), `idx_checkpoints_task_id` ON (task_id)

**说明**：此表由 LangGraph 的 `PostgresSaver` 自动管理，应用层不需要直接操作。

---

#### charts — 图表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id | |
| chart_type | VARCHAR(50) | NOT NULL | bar / line / scatter / pie / histogram / box / heatmap / area |
| title | TEXT | NOT NULL | 图表标题 |
| config_json | JSONB | NOT NULL | Plotly 配置（不含数据）|
| description | TEXT | NULL | 为什么推荐此图的解释 |
| html_path | VARCHAR(500) | NULL | 图表 HTML 文件路径 |
| data_summary | TEXT | NULL | 数据衍生摘要 |
| sort_order | INTEGER | NOT NULL DEFAULT 0 | 显示顺序 |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_charts_task_id` ON (task_id)

---

#### reports — 分析报告

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id | |
| content_md | TEXT | NULL | Markdown 内容 |
| html_path | VARCHAR(500) | NULL | HTML 文件路径 |
| export_format | VARCHAR(20) | NULL | html / markdown |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_reports_task_id` ON (task_id)

---

#### chat_messages — 对话消息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id | |
| role | VARCHAR(20) | NOT NULL | user / assistant / system |
| content | TEXT | NOT NULL | 消息内容（Markdown）|
| msg_type | VARCHAR(50) | NOT NULL DEFAULT 'text' | text / chart / report / system |
| context_data | JSONB | NULL | 上下文数据（如图表引用）|
| iteration | INTEGER | NOT NULL DEFAULT 0 | 对话轮次 |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_chat_task_created` ON (task_id, created_at ASC)

---

#### agent_executions — Agent 执行日志

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| task_id | UUID | FK → tasks.id | |
| agent_name | VARCHAR(100) | NOT NULL | ingestion / profiler / analysis / chat |
| input_summary | TEXT | NULL | 输入摘要（前 200 字符）|
| output_summary | TEXT | NULL | 输出摘要 |
| tokens_used | INTEGER | NOT NULL DEFAULT 0 | LLM token 消耗 |
| duration_ms | INTEGER | NOT NULL DEFAULT 0 | 执行耗时 |
| status | VARCHAR(50) | NOT NULL DEFAULT 'success' | success / failed / skipped |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_agent_exec_task` ON (task_id)

---

#### tool_logs — Tool 执行日志

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| execution_id | UUID | FK → agent_executions.id | |
| tool_name | VARCHAR(100) | NOT NULL | parse / stats / chart_recommend / plotly / python_exec / file / export |
| input_summary | TEXT | NULL | 输入参数摘要 |
| output_summary | TEXT | NULL | 输出摘要 |
| duration_ms | INTEGER | NOT NULL DEFAULT 0 | 执行耗时 |
| status | VARCHAR(50) | NOT NULL DEFAULT 'success' | success / failed |
| error_message | TEXT | NULL | 错误信息 |
| created_at | TIMESTAMPTZ | NOT NULL | |

**索引**：`idx_tool_log_exec` ON (execution_id), `idx_tool_log_tool` ON (tool_name)

### 7.3 JSONB 字段设计说明

| 表 | JSONB 字段 | 内容结构 | 查询需求 |
|------|-----------|----------|----------|
| files | parse_metadata | `{delimiter, encoding_details, columns, warnings}` | 不直接查询 |
| tasks | state_summary | `{current_phase, progress_percentage, phase_details}` | 前端轮询展示 |
| charts | config_json | `{layout, traces, axis_config}` | 前端直接使用 ECharts 转化 |
| chat_messages | context_data | `{chart_refs, data_refs, filter_conditions}` | 对话上下文恢复 |

### 7.4 命名规范

| 规则 | 示例 |
|------|------|
| 表名 | 小写、下划线分隔、复数 `datasets, chat_messages` |
| 主键 | `id` — UUID v4 |
| 外键 | `{table_name}_id` — `dataset_id`, `task_id` |
| 时间戳 | `created_at`, `updated_at`, `completed_at` |
| JSONB | `{entity}_json` — 不使用 `_data`, `_metadata` 以外的后缀 |

---

## 8. API 设计

### 8.1 设计规范

| 规范项 | 约定 |
|--------|------|
| **Base URL** | `/api/v1` |
| **请求体** | JSON（Content-Type: `application/json`）|
| **响应格式** | `{"code": 0, "message": "success", "data": {...}}` |
| **错误格式** | `{"code": 40001, "message": "文件格式不支持", "detail": {...}}` |
| **分页** | `?page=1&page_size=20` → `{"items": [], "total": 100, "page": 1, "page_size": 20}` |
| **身份认证** | Phase 2 实现（预留 `Authorization: Bearer <token>` 头）|
| **API 版本** | URI 路径版本化: `/api/v1/...` |

### 8.2 错误码标准

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 40001 | 文件格式不支持 |
| 40002 | 文件大小超限 |
| 40003 | 文件解析失败 |
| 40004 | 请求参数校验失败 |
| 40401 | 数据集不存在 |
| 40402 | 任务不存在 |
| 40403 | 文件不存在 |
| 50001 | 服务器内部错误 |
| 50002 | LLM 调用失败 |
| 50003 | Tool 执行失败 |
| 50004 | Agent 执行超时 |

### 8.3 文件管理 API

#### `POST /api/v1/files/upload`

上传数据文件。

**请求**：`multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 数据文件（.xlsx/.xls/.csv/.json）|
| dataset_name | String | 否 | 数据集名称（默认用文件名）|
| sheet_name | String | 否 | Excel Sheet 名（默认第一个）|

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "file_id": "uuid",
    "filename": "sales_2024.xlsx",
    "file_type": "xlsx",
    "file_size": 1234567,
    "md5": "a1b2c3d4...",
    "dataset_id": "uuid"
  }
}
```

**错误场景**：
| 条件 | HTTP Status | Error Code |
|------|-------------|------------|
| 格式不支持 | 400 | 40001 |
| 文件大小 > 100MB | 400 | 40002 |
| 文件 MD5 已存在 | 409 | 40001（提示重复）|

---

#### `GET /api/v1/files/{file_id}/preview`

获取文件数据预览。

**响应**：
```json
{
  "code": 0,
  "data": {
    "columns": [{"name": "日期", "dtype": "date", "non_null": 9980, "unique": 365}],
    "preview_rows": 50,
    "preview_data": [{"日期": "2024-01-01", "销售额": 1234.5}],
    "total_rows": 10000,
    "total_columns": 10
  }
}
```

### 8.4 数据集管理 API

#### `GET /api/v1/datasets`

获取数据集列表。

**参数**：`?page=1&page_size=20&sort=created_at&order=desc`

**响应**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "2024年销售数据",
        "status": "active",
        "row_count": 10000,
        "column_count": 10,
        "created_at": "2026-07-04T10:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

#### `GET /api/v1/datasets/{id}`

获取数据集完整信息（含 Schema、统计、图表、报告）。

**响应**：
```json
{
  "code": 0,
  "data": {
    "dataset": { "...基本信息..." },
    "files": [ "...文件列表..." ],
    "schemas": [ "...字段 Schema 列表..." ],
    "stats": { "...统计结果..." },
    "charts": [ "...图表列表..." ],
    "report": { "...报告..." },
    "quality": { "...质量报告..." }
  }
}
```

#### `GET /api/v1/datasets/{id}/schemas`

获取字段 Schema（前端 Tab 页用）。

**响应**：
```json
{
  "code": 0,
  "data": {
    "columns": [
      {
        "column_name": "销售额",
        "detected_dtype": "Float64",
        "semantic_type": "金额",
        "confidence": 0.95,
        "description": "订单金额，单位元",
        "user_corrected": false
      }
    ]
  }
}
```

#### `PUT /api/v1/datasets/{id}/schemas`

用户修正字段 Schema。

**请求**：
```json
{
  "columns": [
    {
      "column_name": "客户ID",
      "corrected_dtype": "String",
      "corrected_semantic_type": "ID"
    }
  ]
}
```

### 8.5 任务管理 API

#### `POST /api/v1/tasks`

创建分析任务。

**请求**：
```json
{
  "file_id": "uuid",
  "dataset_id": "uuid",
  "auto_start": true
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "task_id": "uuid",
    "status": "pending",
    "created_at": "2026-07-04T10:00:00Z"
  }
}
```

#### `POST /api/v1/tasks/{id}/start`

启动分析任务。

#### `POST /api/v1/tasks/{id}/pause`

暂停运行中的任务。

#### `POST /api/v1/tasks/{id}/resume`

恢复已暂停的任务。

#### `POST /api/v1/tasks/{id}/cancel`

取消进行中的任务。

#### `GET /api/v1/tasks/{id}`

获取任务状态和进度。

**响应**：
```json
{
  "code": 0,
  "data": {
    "task_id": "uuid",
    "status": "running",
    "current_phase": "chart_generation",
    "progress": 0.75,
    "phase_details": {
      "uploading": {"status": "completed", "progress": 1.0},
      "parsing": {"status": "completed", "progress": 1.0},
      "schema_inference": {"status": "completed", "progress": 1.0},
      "profiling": {"status": "completed", "progress": 1.0},
      "analysis": {"status": "completed", "progress": 1.0},
      "chart_generation": {"status": "running", "progress": 0.6},
      "report_generation": {"status": "pending", "progress": 0.0}
    }
  }
}
```

#### `PUT /api/v1/tasks/{id}/confirm-schema`

Human-in-Loop：用户确认或修正 Schema 后通知任务继续。

**请求**：
```json
{
  "columns": [{"column_name": "日期", "semantic_type": "日期", "dtype": "date"}]
}
```

### 8.6 对话 API

#### `POST /api/v1/chat/stream`

流式对话（SSE）。

**请求**：
```json
{
  "task_id": "uuid",
  "query": "为什么销售额下降了？",
  "history": [{"role": "user", "content": "..."}]
}
```

**响应（SSE）**：
```
event: message
data: {"type": "status", "content": "正在分析数据..."}

event: message
data: {"type": "text", "content": "根据数据分析，销售额下降主要"}

event: message
data: {"type": "text", "content": "受到以下因素影响："}

event: message
data: {"type": "chart", "content": {"chart_type": "line", "html_path": "...", "title": "月度销售额趋势"}}

event: message
data: {"type": "done", "content": {"iteration": 3}}
```

**SSE Event 类型**：

| 类型 | 用途 | 前端处理 |
|------|------|----------|
| `status` | Agent 正在处理中 | 显示"正在分析…"提示 |
| `text` | 文本回复片段（逐 token） | 追加到对话气泡 |
| `chart` | 插入图表 | 在对话中渲染图表 |
| `tool_call` | Agent 正在调用 Tool | 显示 Tool 调用状态 |
| `error` | 错误信息 | 显示错误提示 |
| `done` | 本轮对话结束 | 更新 UI 状态 |

**前端 SSE 连接代码示例**：
```typescript
// frontend/src/api/chat.ts
export function streamChat(
  taskId: string,
  query: string,
  onMessage: (event: SSEEvent) => void
) {
  const url = `/api/v1/chat/stream`;
  const eventSource = new EventSource(url);
  
  // 使用 fetch + ReadableStream 进行 POST SSE
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, query }),
  }).then(async (response) => {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      // 解析 SSE 格式的 chunk
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          onMessage(JSON.parse(line.slice(6)));
        }
      }
    }
  });
}
```

### 8.7 报告 API

#### `GET /api/v1/reports/{id}`

获取报告内容。

#### `GET /api/v1/reports/{id}/export?format=html`

导出报告为指定格式。

### 8.8 系统 API

#### `GET /api/v1/system/health`

健康检查。

**响应**：
```json
{
  "code": 0,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "services": {
      "postgresql": "connected",
      "redis": "connected",
      "llm": "available"
    },
    "uptime_seconds": 12345
  }
}
```

#### `POST /api/v1/system/upload-config`

更新系统配置（文件大小限制、超时时间、模型选择等）。

### 8.9 WebSocket 任务进度推送

除 REST API 外，任务进度通过 WebSocket 实时推送。

**连接**：`ws://host/api/v1/ws/task/{task_id}`

**推送消息**：
```json
{
  "type": "progress",
  "data": {
    "current_phase": "chart_generation",
    "progress": 0.75,
    "phase_details": {...}
  }
}
```

```json
{
  "type": "status_change",
  "data": {
    "status": "completed",
    "completed_at": "2026-07-04T10:30:00Z"
  }
}
```

---

## 9. 项目目录结构

```
data-visualization-platform/
│
├── backend/                          # 后端项目（Python + FastAPI）
│   ├── alembic/                      # 数据库迁移
│   │   ├── versions/                 # 迁移版本文件
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── app/                          # 应用核心代码
│   │   ├── __init__.py
│   │   │
│   │   ├── api/                      # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # 路由聚合
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── files.py          # 文件管理 API
│   │   │   │   ├── datasets.py       # 数据集管理 API
│   │   │   │   ├── tasks.py          # 任务管理 API
│   │   │   │   ├── chat.py           # 对话 API（SSE）
│   │   │   │   ├── reports.py        # 报告 API
│   │   │   │   └── system.py         # 系统 API
│   │   │   └── deps.py              # 依赖注入（数据库 session 等）
│   │   │
│   │   ├── core/                     # 核心配置
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # 全局配置（Pydantic Settings）
│   │   │   ├── database.py           # 数据库连接（asyncpg + SQLAlchemy）
│   │   │   ├── redis.py              # Redis 客户端
│   │   │   ├── logger.py             # 日志配置（结构化日志）
│   │   │   └── exceptions.py         # 全局异常处理
│   │   │
│   │   ├── agents/                   # Agent 定义
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BaseAgent 抽象类
│   │   │   ├── ingestion_agent.py    # Data Ingestion Agent
│   │   │   ├── profiler_agent.py     # Data Profiler Agent
│   │   │   ├── analysis_agent.py     # Analysis Agent
│   │   │   ├── chat_agent.py         # Chat Agent
│   │   │   └── prompts/              # Prompt 模板
│   │   │       ├── __init__.py
│   │   │       ├── ingestion.py      # Ingestion Agent Prompts
│   │   │       ├── profiler.py       # Profiler Agent Prompts
│   │   │       ├── analysis.py       # Analysis Agent Prompts
│   │   │       └── chat.py           # Chat Agent Prompts
│   │   │
│   │   ├── tools/                    # Tool 实现
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BaseTool 抽象类
│   │   │   ├── parse_tool.py         # ParseTool
│   │   │   ├── stats_tool.py         # StatsTool
│   │   │   ├── chart_recommend_tool.py  # ChartRecommendTool
│   │   │   ├── plotly_tool.py        # PlotlyTool
│   │   │   ├── python_exec_tool.py   # PythonExecTool
│   │   │   ├── file_tool.py          # FileTool
│   │   │   ├── export_tool.py        # ExportTool
│   │   │   └── rag_search_tool.py    # RAGSearchTool (Phase 2 stub)
│   │   │
│   │   ├── graph/                    # LangGraph 图定义
│   │   │   ├── __init__.py
│   │   │   ├── state.py              # AnalysisState 定义
│   │   │   ├── builder.py            # Graph 构建与编译
│   │   │   ├── nodes.py              # Node 函数定义
│   │   │   ├── routers.py            # 条件路由函数
│   │   │   └── checkpointer.py       # Checkpoint 配置
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 声明基类（DeclarativeBase）
│   │   │   ├── dataset.py
│   │   │   ├── file.py
│   │   │   ├── column_schema.py
│   │   │   ├── task.py
│   │   │   ├── checkpoint.py
│   │   │   ├── chart.py
│   │   │   ├── report.py
│   │   │   ├── chat_message.py
│   │   │   ├── agent_execution.py
│   │   │   └── tool_log.py
│   │   │
│   │   ├── schemas/                  # Pydantic v2 请求/响应
│   │   │   ├── __init__.py
│   │   │   ├── common.py             # 通用响应模型
│   │   │   ├── file.py
│   │   │   ├── dataset.py
│   │   │   ├── task.py
│   │   │   ├── chat.py
│   │   │   ├── report.py
│   │   │   └── system.py
│   │   │
│   │   ├── services/                 # 业务服务层
│   │   │   ├── __init__.py
│   │   │   ├── file_service.py       # 文件服务
│   │   │   ├── dataset_service.py    # 数据集服务
│   │   │   ├── task_service.py       # 任务服务（调用 LangGraph）
│   │   │   ├── chat_service.py       # 对话服务
│   │   │   └── report_service.py     # 报告服务
│   │   │
│   │   └── utils/                    # 工具函数
│   │       ├── __init__.py
│   │       ├── file_utils.py         # 文件路径/类型/MD5 工具
│   │       ├── polars_utils.py       # Polars 辅助函数
│   │       ├── encode_utils.py       # 编码检测工具
│   │       └── template_utils.py     # 报告模板渲染
│   │
│   ├── tests/                        # 测试
│   │   ├── __init__.py
│   │   ├── conftest.py               # pytest 配置/fixtures
│   │   ├── test_api/
│   │   │   ├── test_files.py
│   │   │   ├── test_datasets.py
│   │   │   ├── test_tasks.py
│   │   │   └── test_chat.py
│   │   ├── test_agents/
│   │   │   ├── test_ingestion_agent.py
│   │   │   ├── test_profiler_agent.py
│   │   │   ├── test_analysis_agent.py
│   │   │   └── test_chat_agent.py
│   │   ├── test_tools/
│   │   │   ├── test_parse_tool.py
│   │   │   ├── test_stats_tool.py
│   │   │   ├── test_plotly_tool.py
│   │   │   └── test_file_tool.py
│   │   └── test_services/
│   │       ├── test_file_service.py
│   │       └── test_task_service.py
│   │
│   ├── data/                         # 运行时数据目录
│   │   ├── uploads/                  # 上传文件存储
│   │   ├── charts/                   # 图表 HTML 文件
│   │   ├── exports/                  # 报告导出文件
│   │   └── temp/                     # 临时文件
│   │
│   ├── pyproject.toml                # Python 项目配置
│   ├── requirements.txt             # 依赖清单
│   ├── Dockerfile
│   └── .env.example                  # 环境变量示例
│
├── frontend/                         # 前端项目（Vue 3 + TypeScript）
│   ├── public/
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── App.vue                   # 根组件
│   │   ├── main.ts                   # 入口文件
│   │   │
│   │   ├── api/                      # API 客户端
│   │   │   ├── client.ts             # Axios 实例 + 拦截器
│   │   │   ├── files.ts              # 文件 API
│   │   │   ├── datasets.ts           # 数据集 API
│   │   │   ├── tasks.ts              # 任务 API
│   │   │   ├── chat.ts               # 对话 API (SSE)
│   │   │   └── reports.ts            # 报告 API
│   │   │
│   │   ├── router/                   # 路由
│   │   │   └── index.ts
│   │   │
│   │   ├── stores/                   # Pinia 状态管理
│   │   │   ├── dataset.ts            # 数据集状态
│   │   │   ├── task.ts               # 任务状态
│   │   │   ├── chat.ts               # 对话状态
│   │   │   └── app.ts                # 全局状态
│   │   │
│   │   ├── views/                    # 页面
│   │   │   ├── HomePage.vue          # 首页/上传页
│   │   │   ├── DatasetList.vue       # 数据集列表页
│   │   │   ├── DatasetDetail.vue     # 数据集详情页（Tabs 容器）
│   │   │   └── TaskProgress.vue      # 任务进度页
│   │   │
│   │   ├── components/               # 通用组件
│   │   │   ├── layout/               # 布局组件
│   │   │   │   ├── AppSidebar.vue    # 侧边栏
│   │   │   │   ├── AppHeader.vue     # 顶部栏
│   │   │   │   └── AppLayout.vue     # 整体布局
│   │   │   │
│   │   │   ├── upload/               # 上传组件
│   │   │   │   ├── FileUploader.vue   # 拖拽/点击上传区域
│   │   │   │   └── UploadProgress.vue # 上传进度
│   │   │   │
│   │   │   ├── dataset/              # 数据集组件
│   │   │   │   ├── DataPreview.vue   # 数据预览表格
│   │   │   │   ├── SchemaEditor.vue  # Schema 编辑
│   │   │   │   ├── QualityReport.vue # 质量报告
│   │   │   │   ├── StatsView.vue     # 统计结果展示
│   │   │   │   ├── ChartViewer.vue   # 图表查看（ECharts）
│   │   │   │   └── InsightView.vue   # 分析洞察
│   │   │   │
│   │   │   ├── chat/                 # 对话组件
│   │   │   │   ├── ChatPanel.vue     # 对话面板
│   │   │   │   ├── ChatBubble.vue    # 消息气泡
│   │   │   │   └── ChatInput.vue     # 输入框
│   │   │   │
│   │   │   └── common/               # 通用组件
│   │   │       ├── LoadingOverlay.vue # 加载遮罩
│   │   │       ├── ProgressBar.vue   # 进度条
│   │   │       ├── EmptyState.vue    # 空状态
│   │   │       └── ErrorBoundary.vue # 错误边界
│   │   │
│   │   ├── composables/              # Composition API 函数
│   │   │   ├── useWebSocket.ts       # WebSocket 连接
│   │   │   ├── useSSE.ts             # SSE 连接
│   │   │   └── useFileUpload.ts      # 文件上传逻辑
│   │   │
│   │   ├── types/                    # TypeScript 类型
│   │   │   ├── dataset.ts
│   │   │   ├── task.ts
│   │   │   ├── chat.ts
│   │   │   └── api.ts
│   │   │
│   │   └── styles/                   # 全局样式
│   │       ├── variables.scss        # SCSS 变量
│   │       └── global.scss           # 全局样式
│   │
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
│
├── docker-compose.yml                # Docker Compose（PostgreSQL + Redis + 后端 + 前端）
├── docker-compose.dev.yml            # 开发环境扩展配置
├── .gitignore
├── .env.example                      # 环境变量示例
├── README.md                         # 项目说明
└── Makefile                          # 常用命令快捷方式
```

---

## 10. RAG 知识库架构（第二阶段）

### 10.1 设计目标

在第二阶段将 RAG（Retrieval-Augmented Generation）能力接入 Chat Agent，使 Agent 在回答用户问题时，不仅能基于数据分析结果，还能结合企业知识库中的业务定义、指标口径、行业知识。

### 10.2 可插拔接口设计

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Document:
    id: str
    content: str
    metadata: dict

# --- Embedding 接口 ---
class EmbeddingBase(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本 → 向量"""
        pass
    
    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """查询文本 → 向量（与 embed 可能不同）"""
        pass

# --- 向量存储接口 ---
class VectorStoreBase(ABC):
    @abstractmethod
    async def add_documents(self, docs: list[Document], embeddings: list[list[float]]):
        """存入文档 + 向量"""
        pass
    
    @abstractmethod
    async def similarity_search(self, query_embedding: list[float], top_k: int = 5) -> list[Document]:
        """相似度检索"""
        pass
    
    @abstractmethod
    async def delete_documents(self, doc_ids: list[str]):
        """删除文档"""
        pass

# --- 文档加载器接口 ---
class DocumentLoaderBase(ABC):
    @abstractmethod
    async def load(self, source: str) -> list[Document]:
        """从源加载文档"""
        pass

# --- 检索器接口 ---
class RetrieverBase(ABC):
    def __init__(self, vector_store: VectorStoreBase, embedding: EmbeddingBase):
        self.vector_store = vector_store
        self.embedding = embedding
    
    async def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        """检索流程：query → 向量 → 相似度搜索 → 返回文档"""
        query_embedding = await self.embedding.embed_query(query)
        return await self.vector_store.similarity_search(query_embedding, top_k)
```

### 10.3 集成方式

```
                             ┌──────────────────┐
                             │   Chat Agent      │
                             └────────┬─────────┘
                                      │ 需要业务知识
                                      ▼
                             ┌──────────────────┐
                             │  RAGSearchTool    │
                             └────────┬─────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  ▼                   ▼                   ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
          │ Embedding     │  │ Milvus       │  │ Document Loader  │
          │ (text-embedding│  │ Vector Store  │  │ (PDF/Word/DB)    │
          │  -3-small)    │  │              │  │                  │
          └──────────────┘  └──────────────┘  └──────────────────┘
```

### 10.4 知识库管理界面（预留）

- **知识库管理页面**：上传文档、查看索引状态、删除索引
- 支持的文档类型：PDF、Word、Markdown、Notion/Confluence 导出
- 文档自动分段（Chunking）、向量化、索引

---

## 11. MVP 开发路线图

### 11.1 总体路线图

| Phase | 周次 | 里程碑 | 核心交付物 |
|-------|------|--------|-----------|
| **Phase 1**: 基础设施 | 第 1-2 周 | 项目骨架可运行 | Docker 环境、项目骨架、数据库、API 框架 |
| **Phase 2**: 文件处理 | 第 3-4 周 | 文件上传 + 解析 + Schema | 上传组件、解析引擎、Schema 推断 |
| **Phase 3**: 分析引擎 | 第 5-7 周 | 自动分析全流程 | Agent 编排、统计分析、图表生成 |
| **Phase 4**: 对话交互 | 第 8-9 周 | 多轮对话可用 | Chat Agent、SSE 流式、Human-in-Loop |
| **Phase 5**: 报告导出 | 第 10-11 周 | 完整产品闭环 | 报告生成、HTML 导出、任务管理 |
| **Phase 6**: 集成优化 | 第 12 周 | MVP 可交付 | E2E 测试、性能优化、文档完善 |

### 11.2 详细计划

#### Phase 1: 基础设施（第 1-2 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 1.1 Docker Compose 环境搭建 | PostgreSQL + Redis 可运行 | 1 天 |
| 1.2 后端项目初始化 | FastAPI 项目骨架、配置管理 | 1 天 |
| 1.3 数据库模型创建 | Alembic 迁移、10 张表 | 2 天 |
| 1.4 前端项目初始化 | Vue 3 + Vite + Element Plus + Pinia | 1 天 |
| 1.5 前端布局框架 | 侧边栏 + 主内容区 + 路由 | 1 天 |
| 1.6 基础 API 测试 | health check、CRUD 基础端点 | 1 天 |
| 1.7 CI 配置 + 代码规范 | Makefile、lint、pre-commit | 1 天 |

**Milestone**：`make up` 后可在浏览器看到前端页面，API 健康检查通过。

---

#### Phase 2: 文件处理（第 3-4 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 2.1 文件上传 API | POST/GET 文件端点 + MD5 去重 | 1 天 |
| 2.2 FileUploader 组件 | 拖拽/点击上传 + 进度显示 | 1 天 |
| 2.3 ParseTool | Excel/CSV/JSON 解析 + 编码检测 | 2 天 |
| 2.4 FileTool | 文件操作工具（读/采样/元信息） | 1 天 |
| 2.5 Data Ingestion Agent | LLM 驱动的 Schema 推断 | 2 天 |
| 2.6 SchemaEditor 组件 | 字段类型/语义编辑 + 置信度显示 | 1 天 |
| 2.7 DataPreview 组件 | 前 N 行数据表格展示 | 1 天 |

**Milestone**：上传一个 Excel → 自动解析 → 显示预览 + Schema 推断结果。

---

#### Phase 3: 分析引擎（第 5-7 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 3.1 StatsTool | 描述统计/分布/趋势/相关性/异常检测 | 3 天 |
| 3.2 Data Profiler Agent | 质量分析 + 统计计划 + 报告生成 | 3 天 |
| 3.3 ChartRecommendTool | 图表推荐逻辑 | 2 天 |
| 3.4 PlotlyTool | Plotly 图表生成（7 种类型） | 3 天 |
| 3.5 Analysis Agent | Mode 1 + Mode 2 图表生成 + 报告撰写 | 4 天 |
| 3.6 前端图表展示 | ChartViewer 组件（ECharts 适配）| 2 天 |
| 3.7 StatsView 组件 | 统计结果可视化展示 | 1 天 |
| 3.8 QualityReport 组件 | 质量评分 + 缺失/异常展示 | 1 天 |

**Milestone**：上传文件 → 全自动完成分析 → 生成统计结果 + 图表 + 文字总结。

---

#### Phase 4: 对话交互（第 8-9 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 4.1 Chat Agent 意图分类 | 追问/换图/筛选/重新分析分类 | 2 天 |
| 4.2 SSE 流式 API | POST /chat/stream + 多事件类型 | 2 天 |
| 4.3 ChatPanel 组件 | 对话面板 + 流式渲染 | 2 天 |
| 4.4 换图/筛选/重分析流程 | 与 Analysis Agent 联动 | 3 天 |
| 4.5 Human-in-Loop | Schema 确认断点 + 恢复流程 | 2 天 |
| 4.6 对话上下文管理 | 历史保留 + 状态恢复 | 1 天 |

**Milestone**：分析完成后，用户可打字追问/换图/筛选，Agent 实时响应。

---

#### Phase 5: 报告与导出（第 10-11 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 5.1 InsightView 组件 | 执行摘要 + 关键发现 + 建议展示 | 2 天 |
| 5.2 ExportTool | HTML/Markdown 报告导出 | 2 天 |
| 5.3 报告模板 | 响应式 HTML 模板 + 移动端适配 | 2 天 |
| 5.4 任务管理页面 | TaskProgress 组件 + 暂停/恢复/取消 | 2 天 |
| 5.5 WebSocket 进度推送 | 实时任务进度 | 1 天 |
| 5.6 数据集列表页 | 卡片/表格视图 + 搜索排序 | 1 天 |

**Milestone**：完整的分析产品闭环：上传 → 分析 → 对话 → 导出报告。

---

#### Phase 6: 集成与优化（第 12 周）

| 任务 | 产出 | 工时 |
|------|------|------|
| 6.1 E2E 集成测试 | 完整业务流程测试 | 2 天 |
| 6.2 性能测试与优化 | 大文件/多并发/响应时间优化 | 2 天 |
| 6.3 PythonExecTool 沙箱 | 安全沙箱集成 + 测试 | 1 天 |
| 6.4 错误处理完善 | 全局异常 + 友好提示 | 1 天 |
| 6.5 文档完善 | API 文档 + README + 部署说明 | 1 天 |
| 6.6 代码审查 + 重构 | 代码质量 review | 1 天 |

**Milestone**：MVP v1.0 可交付。

### 11.3 依赖顺序

```
Phase 1 ──────────────────────────────────────────────┐
  └─ Phase 2 ────────────────────────────────────┐     │
     └─ Phase 3 ─────────────────────────────┐   │     │
        └─ Phase 4 ──────────────────────┐   │   │     │
           └─ Phase 5 ───────────────┐   │   │   │     │
              └─ Phase 6 ────────┐   │   │   │   │     │
                                 ▼   ▼   ▼   ▼   ▼     ▼
                                MVP v1.0 发布
```

- Phase 1 是基础，所有后续 Phase 依赖
- Phase 2 → Phase 3 → Phase 4 串行（分析流）
- Phase 5 可与 Phase 3/4 部分并行（报告模板准备）
- Phase 6 最后进行整体优化

---

## 附录 A：关键配置项

```yaml
# 系统配置（app.core.config）

# 服务配置
SERVICE_NAME: "AI-Agent-Data-Visualization"
SERVICE_VERSION: "1.0.0"
DEBUG: false

# 文件上传
UPLOAD_DIR: "./data/uploads"
MAX_FILE_SIZE_MB: 100
ALLOWED_EXTENSIONS: [".xlsx", ".xls", ".csv", ".json"]
CHART_DIR: "./data/charts"
EXPORT_DIR: "./data/exports"
TEMP_DIR: "./data/temp"

# 数据库
DATABASE_URL: "postgresql+asyncpg://user:pass@localhost:5432/dataviz"

# Redis
REDIS_URL: "redis://localhost:6379/0"

# LLM
LLM_MODEL: "gpt-4o"  # 或兼容的 API
LLM_API_KEY: "${LLM_API_KEY}"
LLM_MAX_TOKENS: 4096
LLM_TEMPERATURE: 0.1  # 分析任务使用较低温度

# Agent
AGENT_TIMEOUT_SECONDS: 120
AGENT_MAX_RETRIES: 3
CHAT_MAX_HISTORY: 20  # 保留最近对话轮次

# 沙箱
SANDBOX_TIMEOUT_SECONDS: 30
SANDBOX_MAX_MEMORY_MB: 256
```

## 附录 B：核心依赖清单

```txt
# backend/requirements.txt
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
langgraph>=0.2.0
langchain-core>=0.3.0
langchain-openai>=0.1.0
polars>=1.0.0
pyarrow>=16.0.0
openpyxl>=3.1.0
calamine>=0.1.0
plotly>=5.20.0
python-multipart>=0.0.9
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
redis[hiredis]>=5.0.0
chardet>=5.2.0
aiofiles>=23.2.0
jinja2>=3.1.0
rich>=13.7.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
RestrictedPython>=7.0
```

## 附录 C：目录结构说明

| 目录 | 用途 | 是否纳入版本控制 |
|------|------|------------------|
| `backend/data/uploads/` | 上传的原始文件 | ❌（gitignore） |
| `backend/data/charts/` | 生成的图表 HTML | ❌（gitignore） |
| `backend/data/exports/` | 导出的报告文件 | ❌（gitignore） |
| `backend/data/temp/` | 临时处理文件 | ❌（gitignore） |
| `backend/alembic/versions/` | 数据库迁移版本 | ✅ |
| `backend/tests/` | 测试代码 | ✅ |
| `frontend/src/` | 前端源码 | ✅ |
| `docker-compose*.yml` | 部署配置 | ✅ |

---

> **文档版本记录**
>
> | 版本 | 日期 | 修改人 | 修改内容 |
> |------|------|--------|----------|
> | v1.0 | 2026-07-04 | AI | 初稿 — 完整架构设计文档 |
