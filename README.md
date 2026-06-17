# RAGuard — 知识库冲突检测引擎

RAGuard 是一个面向 RAG（检索增强生成）场景的知识库冲突检测与治理平台。系统上传多源文档后自动解析、分块、向量化索引，通过 LLM 扫描发现文档间的信息冲突（事实矛盾、数值不一致、时效冲突等），提供冲突消解方案并支持人工审核，最终通过 QA 聊天接口在回答中主动提示信息冲突。

---

## 功能概览

| 模块 | 说明 |
|---|---|
| 📄 **文档管理** | 上传 PDF / DOCX / Markdown，自动解析、分块、向量化、去重 |
| 🔍 **冲突扫描** | LLM 驱动扫描 5 类冲突：事实矛盾、数值不一致、时效冲突、定义不匹配、条件vs绝对 |
| 🛡️ **冲突消解** | 自动生成消解方案 → 人工审核（批准 / 拒绝 / 修改） → 执行修复 |
| 💬 **智能问答** | RAG 问答 + 主动冲突警告 + 来源追溯 |
| 📊 **可观测性** | Langfuse 集成 — LLM 调用追踪、性能监控 |
| 📋 **审计日志** | 修复操作完整追溯 (diff 对比) |

## 5 种冲突类型

| 类型 | 示例 |
|---|---|
| `factual_contradiction` | 「A 公司成立于 2010 年」 vs 「A 公司成立于 2012 年」 |
| `numerical_discrepancy` | 「Q3 营收 15M」 vs 「Q3 营收 22M」 |
| `temporal_conflict` | 「该政策已废止（2023）」 vs 「该政策仍有效（2025）」 |
| `definition_mismatch` | 「API 超时 30s」 vs 「API 超时 60s」（同术语不同定义） |
| `conditional_vs_absolute` | 「通常应该…」 vs 「必须…」（条件级别冲突） |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.12) |
| 元数据库 | SQLite |
| 向量存储 | Chroma (Docker / 本地 PersistentClient 双模式) |
| LLM | DeepSeek (OpenAI 兼容 API) |
| Embedding | SiliconFlow BGE-large-zh-v1.5 |
| 分块引擎 | Chunker V2 — 结构感知 + 语义边界 + token 精准切分 |
| 可观测性 | Langfuse |
| 前端框架 | React 19 + TypeScript |
| 构建工具 | Vite |
| 样式 | Tailwind CSS |
| 状态管理 | TanStack React Query |
| 路由 | React Router |
| 图标 | lucide-react |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+
- Docker Desktop（运行 Chroma 向量库，可选：也支持本地 PersistentClient 模式，无需 Docker）

### 1. 克隆项目

```bash
git clone <repo-url>
cd RAGuard
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必要的 API Key：

```env
# 必填
DEEPSEEK_API_KEY=sk-your-deepseek-key
SILICONFLOW_API_KEY=sk-your-siliconflow-key

# Chroma（Docker 模式）
CHROMA_HOST=localhost:8001
```

### 3. 启动 Chroma 向量数据库

**Docker 模式（推荐）：**

```bash
docker compose up -d chroma
```

**本地模式（无需 Docker）：**

在 `.env` 中将 `CHROMA_HOST` 留空或注释掉，系统自动使用本地 `PersistentClient`，数据存储在 `backend/data/chroma_db/`。

### 4. 启动后端

```bash
cd backend
pip install fastapi uvicorn chromadb httpx openai pydantic-settings \
  python-multipart pypdf python-docx tiktoken langfuse numpy
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档：http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端页面：http://localhost:5173

### 6. 一键启动全部服务

```bash
docker compose up -d
```

---

## 项目结构

```
RAGuard/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── api/                  # REST API 端点
│   │   │   ├── documents.py      #   文档上传、列表、删除、重索引
│   │   │   ├── scans.py          #   冲突扫描任务
│   │   │   ├── conflicts.py      #   冲突列表、统计
│   │   │   ├── governance.py     #   消解审批
│   │   │   ├── resolutions.py    #   消解管理
│   │   │   ├── evaluation.py     #   QA 评估
│   │   │   ├── qa.py             #   QA 会话管理
│   │   │   ├── health.py         #   健康检查
│   │   │   └── router.py         #   路由聚合
│   │   ├── conflict/             # 冲突检测引擎
│   │   │   ├── candidate_generator.py  #   候选对生成 (embedding 相似度)
│   │   │   ├── reranker.py       #   SiliconFlow Reranker 重排序
│   │   │   ├── fact_checker.py   #   DeepSeek LLM 事实矛盾判断
│   │   │   ├── scanner.py        #   离线扫描编排
│   │   │   └── aggregator.py     #   冲突聚合
│   │   ├── database/             # 数据访问层
│   │   │   ├── sqlite.py         #   SQLite 连接 + 自动迁移
│   │   │   ├── chroma_client.py  #   Chroma HTTP/本地双模式客户端
│   │   │   └── schema.sql        #   数据库 Schema
│   │   ├── ingestion/            # 文档摄入流水线 (V2)
│   │   │   ├── parser.py         #   结构化解析 (section 树)
│   │   │   ├── chunker.py        #   语义感知分块 (4 步流水线)
│   │   │   ├── tokenizer.py      #   tiktoken 统一 token 计量
│   │   │   ├── embedder.py       #   BGE Embedding 调用
│   │   │   └── pipeline.py       #   流水线编排
│   │   ├── models/               # Pydantic 数据模型
│   │   │   ├── document.py       #   文档 & 分块
│   │   │   ├── conflict.py       #   冲突 & 扫描任务
│   │   │   ├── resolution.py     #   消解方案 & 修复动作
│   │   │   ├── qa.py             #   QA 会话 & 消息
│   │   │   └── common.py         #   通用模型
│   │   ├── observability/        # Langfuse 集成
│   │   ├── qa/                   # RAG 问答模块
│   │   │   ├── retriever.py      #   向量检索
│   │   │   ├── conflict_guard.py #   冲突检查
│   │   │   ├── answer_generator.py  # DeepSeek 回答生成
│   │   │   └── router.py         #   问答路由
│   │   ├── resolution/           # 冲突消解模块
│   │   │   ├── state.py          #   消解状态机
│   │   │   ├── generator.py      #   消解方案生成
│   │   │   ├── graph.py          #   消解工作流
│   │   │   └── repair.py         #   修复执行
│   │   ├── config.py             # 全局配置
│   │   └── main.py               # FastAPI 应用入口
│   ├── tests/                    # 后端测试
│   └── data/                     # 运行时数据
├── frontend/                     # React 前端
│   └── src/
│       ├── api/client.ts         # HTTP 客户端
│       ├── components/
│       │   ├── chat/             # 聊天界面
│       │   ├── layout/           # 布局（侧边栏 + AppLayout）
│       │   ├── common/           # 通用组件
│       │   ├── documents/        # 文档管理组件
│       │   └── governance/       # 冲突治理组件
│       ├── hooks/useChat.ts      # 聊天状态管理
│       ├── pages/                # 路由页面
│       └── types/index.ts        # TypeScript 类型
├── docs/                         # 项目文档
├── data/                         # 项目数据目录
├── docker-compose.yml            # 服务编排
├── Dockerfile                    # 后端容器镜像
├── .env.example                  # 环境变量模板
└── README.md
```

---

## API 概览

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 系统健康检查 |
| `/api/documents/upload` | POST | 上传文档（最多10个，单文件≤20MB） |
| `/api/documents` | GET | 文档列表（分页 + 筛选） |
| `/api/documents/{id}` | GET | 文档详情 |
| `/api/documents/{id}` | DELETE | 软删除文档 |
| `/api/documents/{id}/chunks` | GET | 文档分块列表 |
| `/api/documents/{id}/reindex` | POST | 重索引单个文档 (V2 chunker) |
| `/api/documents/reindex-all` | POST | 批量重索引所有文档 |
| `/api/conflicts` | GET | 冲突列表 |
| `/api/conflicts/stats` | GET | 冲突统计（按状态/类型/严重度） |
| `/api/conflicts/{id}/resolve` | POST | 生成消解方案 |
| `/api/scans/start` | POST | 启动离线扫描任务 |
| `/api/resolutions/{id}/approve` | POST | 批准消解方案 |
| `/api/resolutions/{id}/reject` | POST | 拒绝消解方案 |
| `/api/resolutions/{id}/modify` | POST | 修改消解方案 |
| `/api/repair-actions` | GET | 修复审计日志 |
| `/api/qa/sessions` | GET/POST | 问答会话管理 |
| `/api/qa/sessions/{id}/messages` | POST | 发送消息 |

---

## 核心流程详解

### 文档导入流程

```
上传文件 → 校验类型/大小 → 计算MD5去重 → 保存到磁盘
→ 创建数据库记录(status=pending) → 异步启动处理:
  ① 解析 (PDF/DOCX/MD → 结构化 ParsedDocument + section 树)
  ② 分块 (Chunker V2: 结构边界 → 语义边界 → token 兜底 → metadata 装配)
  ③ Embedding (SiliconFlow BGE API)
  ④ 写入 Chroma 向量库 (含 section_path, heading_level, token_count)
  ⑤ 写入 SQLite 分块表 (含 prev_chunk_id / next_chunk_id 双向链)
→ status = indexed
```

### 冲突扫描流程

```
触发扫描 → 从 Chroma 获取所有 embedding
→ 计算 N×N 余弦相似度矩阵
→ 筛选高于阈值(0.75)的候选对
→ 排除同一文档内的对 (同 document_id 跳过)
→ Reranker 重排序 (SiliconFlow BGE Reranker)
→ 取 top-k 对送入 LLM 判断:
  「以下两段文本是否存在信息冲突？是哪种类型？」
→ 记录冲突到 SQLite (conflicts + conflict_chunks)
```

### 冲突消解流程

```
冲突详情页点击「生成消解方案」
→ LLM 提取声明 → 分析矛盾 → 生成消解方案（同步返回）
→ 5 种消解动作:
  · replace_both     — 替换双方分块内容
  · keep_a_remove_b  — 保留来源A，移除来源B
  · keep_b_remove_a  — 保留来源B，移除来源A
  · merge            — 合并双方为一致版本
  · manual_rewrite   — 人工重写（需用户提供内容）
→ 人工审核:
  批准 → 执行修复 → 写入 repair_actions 审计日志
  拒绝 → 记录原因，冲突标记为 dismissed
  修改 → 可更改动作类型或内容 → 重新提交
```

### 智能问答流程

```
用户提问 → Embedding 查询文本
→ Chroma 检索 top-k 相关分块
→ 检查检索到的分块是否涉及未解决冲突
→ 构建 prompt: 分块内容 + 冲突警告 + 用户问题
→ LLM 生成回答 + 引用来源 + 冲突提示
→ 记录 QA 消息 (token 用量、延迟)
```

---

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 必填 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |
| `SILICONFLOW_API_KEY` | SiliconFlow API Key（Embedding） | 必填 |
| `EMBEDDING_MODEL` | Embedding 模型 | `BAAI/bge-large-zh-v1.5` |
| `CHROMA_HOST` | Chroma 服务器地址 | 空 = 本地模式 |
| `CHROMA_DATA_PATH` | Chroma 本地数据路径 | `./data/chroma_db` |
| `DATABASE_URL` | SQLite 路径 | `sqlite:///data/raguard.db` |
| `CHUNK_TARGET_TOKENS` | 分块目标 token 数 | `512` |
| `CHUNK_OVERLAP_TOKENS` | 分块重叠 token 数 | `50` |
| `CHUNK_SEMANTIC_THRESHOLD` | 语义边界检测相似度阈值 | `0.7` |
| `CHUNK_USE_SEMANTIC` | 启用语义边界检测 | `true` |
| `SIMILARITY_THRESHOLD` | 冲突候选相似度阈值 | `0.75` |
| `RERANKER_THRESHOLD` | Reranker 相关性阈值 | `0.3` |
| `LANGFUSE_SECRET_KEY` | Langfuse Secret Key | 可选 |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Public Key | 可选 |
| `LANGFUSE_HOST` | Langfuse 服务地址 | `http://localhost:3000` |

---

## Docker 部署

### 仅启动 Chroma

```bash
docker compose up -d chroma
```

### 启动全部服务（后端 + 前端 + Chroma + Langfuse）

```bash
# 基本模式（后端 + 前端 + Chroma）
docker compose up -d

# 全量模式（含 Langfuse 可观测性平台）
docker compose --profile full up -d
```

### 镜像加速（国内用户）

如果 Docker Hub 拉取慢，先通过代理拉取：

```bash
docker pull docker.1ms.run/chromadb/chroma:latest
docker tag docker.1ms.run/chromadb/chroma:latest chromadb/chroma:latest
```

---

## 开发说明

- 后端代码遵循 FastAPI 最佳实践：路由用 `APIRouter`、数据校验用 Pydantic v2
- 前端状态管理统一使用 React Query，与后端分页格式 `{ items, total, page, pages }` 对齐
- 软删除模式：文档/分块标记 `is_active = FALSE` 而非物理删除
- Chroma 客户端支持双模式：本地 `PersistentClient` / Docker `HttpClient`（通过 `CHROMA_HOST` 切换）
- Chunker V2：结构化 section 感知 + 语义边界检测（paragraph embedding 余弦相似度）+ tiktoken 精准 token 切分
- 分块元数据扩展：`section_path`（章节路径）、`heading_level`、`prev_chunk_id/next_chunk_id`（同文档双向链）
- 重索引机制：`POST /api/documents/{id}/reindex` 支持升级 chunker 后重新处理已有文档
- LLM 调用均预留 Langfuse 追踪挂钩点
- 冲突扫描为手动触发（`POST /api/scans/start`），上传文档后不会自动扫描

## License

MIT
