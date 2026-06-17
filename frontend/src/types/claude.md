# Types — TypeScript 类型定义

## [index.ts](index.ts)

集中定义前端所需的全部 TypeScript 接口，与后端 Pydantic Schema 对应。

### 核心类型

- `Document`, `Chunk` — 文档与分块
- `Conflict`, `ConflictChunkInfo`, `ScanJob` — 冲突与扫描
- `Resolution`, `RepairAction` — 消解与审计
- `QASession`, `QAMessage` — 问答会话
- `SourceInfo`, `ConflictWarning` — 回答来源与冲突提示
- `ConflictStats` — 冲突统计
- `PaginatedResponse<T>` — 通用分页响应

### 约定

- 状态字段使用字符串字面量联合类型
- 可选字段使用 `?:` 语法
- 与后端 Python 模型保持一致命名 (snake_case)
