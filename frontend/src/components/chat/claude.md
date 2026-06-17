# Chat — 聊天组件

智能问答界面的 UI 组件。

## 组件

- [ChatPanel.tsx](ChatPanel.tsx) — 聊天面板主组件，组合会话列表 + 消息区域 + 输入框
- [SessionList.tsx](SessionList.tsx) — 会话列表侧栏，支持创建/选择/删除会话
- [MessageBubble.tsx](MessageBubble.tsx) — 消息气泡，区分用户/AI 角色，渲染 Markdown
- [ChatInput.tsx](ChatInput.tsx) — 消息输入框，支持 Enter 发送
- [SourceCard.tsx](SourceCard.tsx) — 引用来源卡片，可展开查看详情和相关度
- [ConflictWarning.tsx](ConflictWarning.tsx) — 冲突警告横幅，显示冲突数量、描述和冲突分块对比

## 状态管理

通过 [useChat](../../hooks/useChat.ts) hook 管理聊天状态。
