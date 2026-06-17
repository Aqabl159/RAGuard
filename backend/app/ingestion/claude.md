# Ingestion — 文档摄入流水线

## 组件

- [parser.py](parser.py) — 多格式文档解析器
  - 支持 PDF (pypdf)、DOCX (python-docx)、Markdown
  - 返回 `ParsedDocument` (文本 + 页数 + 标题)
  - 通过 `PARSER_MAP` 注册表分发
- [chunker.py](chunker.py) — 文本分块器
  - 递归字符分割策略 (RecursiveCharacterTextSplitter)
  - 分隔符优先级: 段落 → 句子 → 短语 → 字符
  - 支持中英文混合文本
  - 使用 tiktoken `cl100k_base` 估算 token 数
- 流水线编排: `create_document_record` → `process_document`
  - 解析 → 分块 → 生成 embedding → 写入 Chroma + SQLite
  - 支持校验和去重
