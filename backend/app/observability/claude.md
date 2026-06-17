# Observability — 可观测性

## Langfuse 集成

- [langfuse.py](langfuse.py) — Langfuse CallbackHandler 单例
  - `get_langfuse_handler()` — 获取或创建 Langfuse 回调处理器
  - `get_langfuse_traced_llm(llm)` — 将 LLM 实例包装为带追踪的实例
  - 如未配置密钥则静默返回 None，不影响主流程

## 配置

需设置环境变量:
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_HOST`

## 备注

代码中预留了 DeepSeek LLM 适配器注释，经由 OpenAI 兼容接口调用。
