# Backend Data — 运行时数据目录

存放后端运行时的持久化数据。

## 子目录

- [chroma_db/](chroma_db/) — Chroma 向量嵌入存储
- [uploads/](uploads/) — 用户上传的原始文档文件

## 注意

- 此目录被 `.gitignore` 排除 (除目录结构外)
- `uploads/` 在 Dockerfile 中创建为 `/app/uploads`
