# Hooks — 自定义 React Hooks

## [useChat.ts](useChat.ts)

聊天功能的完整状态管理 hook，封装:

- **会话管理**: 加载列表、创建、删除
- **消息管理**: 加载历史、发送消息、乐观更新
- **状态**: `sessions`, `activeSessionId`, `messages`, `loading`
- **错误处理**: 发送失败时显示错误消息气泡

所有 API 调用通过 `apiRequest` 进行，返回类型使用 [types/](../types/index.ts) 中的接口定义。
