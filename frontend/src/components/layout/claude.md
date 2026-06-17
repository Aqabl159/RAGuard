# Layout — 布局组件

应用级布局组件。

## 组件

- [AppLayout.tsx](AppLayout.tsx) — 应用外壳布局: 侧边栏 + 主内容区 (`<Outlet />`)
- [Sidebar.tsx](Sidebar.tsx) — 侧边栏导航
  - Logo: "RAGuard" (知识库冲突检测引擎)
  - 导航项: 智能问答、冲突治理、文档管理、审计日志
  - 底部: "启动离线扫描" 按钮
  - 使用 `react-router-dom` 的 `NavLink` 实现路由高亮
