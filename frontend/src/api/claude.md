# API — HTTP 客户端

前端与后端 REST API 的通信层。

## [client.ts](client.ts)

- `apiRequest<T>(endpoint, options)` — 通用请求函数
  - 自动拼接 `BASE_URL` (`/api`)
  - 支持 GET/POST/PUT/DELETE
  - JSON 请求体自动序列化，FormData 直接透传
  - 错误统一抛出 `Error` (含后端 `detail` 消息)
  - 204 响应返回 `undefined`
- `createFormData(files)` — 构建文件上传 FormData

## 使用方式

```ts
import { apiRequest } from '../api/client'

const docs = await apiRequest<PaginatedResponse<Document>>('/documents')
```
