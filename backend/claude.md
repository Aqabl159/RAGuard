# Backend

FastAPI 后端应用，提供 REST API、文档处理流水线、冲突检测、消解管理和 RAG 问答服务。

## 目录

- [app/](app/) — 应用主包
- [tests/](tests/) — 测试代码
- [data/](data/) — 运行时数据 (Chroma 向量库、上传文件)

## 启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 依赖

- FastAPI + Uvicorn
- Chroma (向量数据库)
- LangChain / Langfuse
- pypdf, python-docx (文档解析)
- tiktoken (token 估算)
- OpenAI SDK (DeepSeek 调用)

## 配置

通过环境变量或 `.env` 文件配置，参见 `app.config.settings`。
