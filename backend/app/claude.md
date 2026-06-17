# App — 后端应用主包

FastAPI 应用的核心 Python 包，包含所有业务逻辑模块。

## 模块

| 模块 | 职责 |
|---|---|
| [api/](api/) | REST API 端点 (文档管理、冲突、消解、QA) |
| [conflict/](conflict/) | 冲突检测引擎 — 候选对生成、LLM 比较、扫描任务 |
| [database/](database/) | 数据访问层 — SQLite 元数据、Chroma 向量库客户端 |
| [ingestion/](ingestion/) | 文档摄入 — 解析 (PDF/DOCX/MD)、分块、流水线编排 |
| [models/](models/) | Pydantic 数据模型 — 请求/响应 schema |
| [observability/](observability/) | Langfuse 可观测性集成 |
| [qa/](qa/) | RAG 问答模块 — 检索、生成、冲突提示 |
| [resolution/](resolution/) | 冲突消解模块 — 方案生成、人工审核、修复执行 |

## 入口

- `main.py` — FastAPI 应用实例，挂载所有路由
- `config.py` — 配置管理 (Settings)，从环境变量读取
