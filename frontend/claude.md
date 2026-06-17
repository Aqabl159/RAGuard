# Frontend — React 单页应用

React 19 + TypeScript + Vite 构建的前端界面，提供知识库管理、冲突治理和智能问答 UI。

## 技术栈

- React 19 + TypeScript
- Vite (构建/HMR)
- Tailwind CSS (样式)
- React Router (路由)
- React Query (@tanstack/react-query) (服务端状态)
- react-markdown + remark-gfm (Markdown 渲染)
- lucide-react (图标)

## 结构

- [public/](public/) — 静态资源 (favicon, icons)
- [src/](src/) — 源代码
  - [api/](src/api/) — HTTP 客户端
  - [components/](src/components/) — UI 组件
  - [hooks/](src/hooks/) — 自定义 hooks
  - [pages/](src/pages/) — 路由页面
  - [types/](src/types/) — TypeScript 类型定义
