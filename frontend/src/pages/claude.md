# Pages — 路由页面

React Router 路由级别的页面组件。

## 页面

| 路由 | 页面 | 功能 |
|---|---|---|
| `/chat` | [ChatPage.tsx](ChatPage.tsx) | 智能问答 — 包裹 ChatPanel 组件 |
| `/governance` | [GovernancePage.tsx](GovernancePage.tsx) | 冲突治理 — 统计卡片 + 冲突列表 + 消解审核 |
| `/documents` | [DocumentsPage.tsx](DocumentsPage.tsx) | 文档管理 — 上传 + 列表 + 删除 + 状态展示 |
| `/audit` | [AuditPage.tsx](AuditPage.tsx) | 审计日志 — 修复操作时间线 + diff 对比 |

## 约定

- 每个页面一个 `.tsx` 文件
- 使用 React Query (`useQuery` / `useMutation`) 获取和变更数据
- 通过 `queryClient.invalidateQueries` 在变更后刷新缓存
