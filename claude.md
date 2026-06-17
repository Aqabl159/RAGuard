# RAGuard — 知识库冲突检测引擎

RAGuard 是一个面向 RAG（检索增强生成）场景的知识库冲突检测与治理平台。系统上传多源文档后自动解析、分块、向量化索引，通过 LLM 扫描发现文档间的信息冲突（事实矛盾、数值不一致、时效冲突等），提供冲突消解方案并支持人工审核，最终通过 QA 聊天接口在回答中主动提示信息冲突。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.12) |
| 数据库 | SQLite (元数据) + Chroma (向量存储) |
| LLM | DeepSeek (OpenAI 兼容 API) |
| 可观测性 | Langfuse |
| 前端框架 | React 19 + TypeScript |
| 构建工具 | Vite |
| 样式 | Tailwind CSS |
| 状态管理 | React Query (@tanstack/react-query) |
| 路由 | React Router |
| Markdown 渲染 | react-markdown + remark-gfm |
| 图标 | lucide-react |

## 项目结构

```
RAGuard/
├── backend/                  # FastAPI 后端
│   ├── app/                  # 应用主包
│   │   ├── api/              # REST API 端点
│   │   ├── conflict/         # 冲突检测引擎
│   │   ├── database/         # SQLite + Chroma 数据层
│   │   ├── ingestion/        # 文档解析、分块、流水线
│   │   ├── models/           # Pydantic 数据模型
│   │   ├── observability/    # Langfuse 集成
│   │   ├── qa/              # RAG 问答模块
│   │   └── resolution/       # 冲突消解模块
│   ├── tests/                # 测试
│   └── data/                 # 运行时数据 (Chroma, 上传文件)
├── frontend/                 # React 前端
│   └── src/
│       ├── api/              # HTTP 客户端封装
│       ├── assets/           # 静态资源
│       ├── components/       # UI 组件
│       ├── hooks/            # 自定义 hooks
│       ├── pages/            # 页面组件
│       └── types/            # TypeScript 类型定义
├── data/                     # 项目级数据目录
├── Dockerfile                # 容器构建文件
└── .gitignore
```

## 核心流程

1. **文档导入**: 上传 PDF/DOCX/Markdown → 解析提取文本 → 递归分块 → embedding → 存入 Chroma
2. **冲突扫描**: 对活跃分块生成候选对 → LLM 比较检测矛盾 → 记录冲突 (5 种类型)
3. **冲突消解**: 为每个冲突生成消解方案 → 人工审核 (批准/拒绝/修改) → 执行修复动作
4. **智能问答**: 用户提问 → 检索相关分块 → LLM 生成回答 + 冲突警告 + 引用来源
