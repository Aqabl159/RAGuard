# Models — Pydantic 数据模型

API 请求/响应的 Schema 定义，与 SQLite 表结构对应。

## 文件

- [document.py](document.py) — 文档 & 分块 (DocumentResponse, ChunkResponse, 列表响应)
- [conflict.py](conflict.py) — 冲突 & 扫描任务 (ConflictResponse, ScanJobResponse, 统计)
- [resolution.py](resolution.py) — 消解方案 (ResolutionResponse, 审批/修改请求, RepairActionResponse)
- [qa.py](qa.py) — QA 会话 & 消息 (QASessionResponse, QAMessageResponse, SourceInfo, ConflictWarningInfo)
- [common.py](common.py) — 通用模型 (HealthResponse, ErrorResponse, PaginationParams)

## 约定

- 使用 Pydantic v2 风格 (`BaseModel`)
- 字符串枚举使用 `Literal` 或 `pattern=` 验证
- 可选字段使用 `Optional[...]`，默认值用 `None`
- 列表响应遵循 `{ items, total, page, pages }` 分页格式
