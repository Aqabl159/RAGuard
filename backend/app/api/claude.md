# API — REST 端点

FastAPI 路由模块，每个文件定义一个 `APIRouter`，挂载于 `/api` 前缀下。

## 端点

- [documents.py](documents.py) — `/api/documents` 文档上传、列表、详情、删除、分块查询
- 冲突管理 — `/api/conflicts` 冲突列表、统计
- 扫描任务 — `/api/scans` 启动扫描、查询任务状态
- 消解管理 — `/api/resolutions` 批准/拒绝/修改消解方案
- 修复审计 — `/api/repair-actions` 修复动作审计日志
- QA 会话 — `/api/qa/sessions` 会话管理、消息收发

## 约定

- 状态码: 201 (创建成功), 204 (删除成功无内容), 400/404/409/413 (业务错误)
- 分页参数: `page` (默认 1), `per_page` (默认 20)
- 错误响应格式: `{ "detail": "...", "code": "..." }`
