# Database — 数据访问层

## 组件

- **SQLite** — 元数据存储 (文档、分块、冲突、消解、QA 会话、修复动作)
  - [schema.sql](schema.sql) 定义完整表结构
  - 通过 `sqlite3` 标准库直连，单文件模式
- **Chroma** — 向量存储 (分块 embedding)
  - `chroma_client.py` — Chroma 客户端封装
  - 存储路径: `backend/data/chroma_db/`

## Schema 要点

- 所有主键使用 UUID 字符串
- 软删除模式 (`is_active` 标志)
- 冲突与分块为 N:N 关系，通过 `conflict_chunks` 关联表
- 提供视图 `v_open_conflict_chunks` 快速获取未解决冲突涉及的分块
- 修复动作表 (`repair_actions`) 提供完整审计追踪
