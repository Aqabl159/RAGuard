# Components — UI 组件

可复用的 React 组件，按功能域分组。

## 分组

| 目录 | 功能 |
|---|---|
| [chat/](chat/) | 聊天界面 — 消息气泡、输入框、来源卡片、冲突警告、会话列表 |
| [common/](common/) | 通用组件 — 跨页面共用的 UI 元素 |
| [documents/](documents/) | 文档管理 — 文档列表、上传、详情 |
| [governance/](governance/) | 冲突治理 — 冲突列表、消解审核 |
| [layout/](layout/) | 布局 — 应用外壳、侧边栏导航 |

## 组件风格

- 函数组件 + TypeScript
- Props 使用 `interface Props { ... }` 定义
- Tailwind CSS 原子类
- lucide-react 图标组件
