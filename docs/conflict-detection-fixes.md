# 冲突检测修复待办

> 诊断日期：2026-06-17  
> 问题：上传含数值差异的两份文档后，系统未检测到任何冲突。

---

## 诊断摘要

| 根因 | 严重度 | 说明 |
|---|---|---|
| 上传后未自动触发扫描 | 🔴 直接原因 | `process_document()` 完成后不触发扫描，用户无提示 |
| 未排除同文档候选对 | 🔴 关键 Bug | README 描述的功能未实现，同文档重复 chunk 占满 top-5 槽位 |
| 阈值过高 | 🟡 放大因素 | 细微数值差异导致跨文档相似度跌至 0.74-0.78，低于默认 0.85 |

---

## 修复 A：添加同文档排除

**文件**：`backend/app/conflict/candidate_generator.py`

**问题**：`generate_candidate_pairs()` 遍历 Chroma 全量 embedding 生成 N×N 候选对时，不检查两个 chunk 是否属于同一文档。当文档内部存在大量重复文本（如本次案例中各段落被复制粘贴 4-8 次），每个 chunk 的 top-5 候选被同文档的重复 chunk 占满，跨文档的真正冲突对无法进入候选列表。

**修改点**：在生成 pair 时增加判断：

```python
# 跳过同一文档内的候选对
if meta_a.get("document_id") == meta_b.get("document_id"):
    continue
```

**具体位置**：约第 102 行，`pairs.append(...)` 之前。

**预期效果**：V1 内部 35+ 对自匹配被过滤，top-5 槽位释放给跨文档对。

---

## 修复 B：上传后自动触发扫描

**方案选择**（二选一，推荐 B1）：

### B1（推荐）：前端提示 + 后端轻量通知

**后端** — `backend/app/api/documents.py` 的 `upload_documents()` 返回值增加提示字段：

```python
return {
    "documents": results,
    "suggestion": {
        "action": "run_scan",
        "message": "文档已索引，建议立即扫描冲突",
        "endpoint": "POST /api/scans/start",
    }
}
```

**前端** — 上传完成后弹 toast："✅ 3 个文档已索引，是否立即扫描冲突？" 按钮跳转触发扫描。

### B2：上传完成后自动触发全库扫描

**文件**：`backend/app/ingestion/pipeline.py`

在 `process_document()` 成功完成（status = 'indexed'）后，自动调用 `run_scan()`：

```python
# pipeline.py 末尾，document status = 'indexed' 之后
from app.conflict.scanner import create_scan_job, run_scan
scan_job_id = create_scan_job(threshold=settings.SIMILARITY_THRESHOLD)
asyncio.create_task(run_scan(scan_job_id))
```

**风险**：频繁上传会触发多次全库扫描，LLM 调用量可能激增。

---

## 修复 C：降低默认相似度阈值 + 按文档对扫描

### C1：降低默认阈值

**文件**：`backend/app/config.py`

```python
SIMILARITY_THRESHOLD: float = 0.75  # 从 0.85 降到 0.75
```

**依据**：本次实测中，采购管理差异（`10万→20万`）的跨文档相似度为 0.77，资产管理差异（`设备10年→20年，运输5年→10年`）为 0.74。当前阈值 0.85 无法捕获这些差异。

### C2：扫描 API 支持指定文档范围

**文件**：`backend/app/api/scans.py`

在 `POST /api/scans/start` 增加可选参数 `document_ids: list[str] | None = None`。传入时只扫描指定文档的交叉对，不传则全库扫描。

**具体改动**：
1. `scans.py` 端点接收参数
2. `candidate_generator.py` 增加 `document_ids` 过滤参数
3. 传给 `run_scan()` → `generate_candidate_pairs(document_ids=...)`

**优势**：上传 A 和 B 后，只对 A×B 扫描，避免全库的 O(N²) 爆炸。

---

## 实施顺序建议

1. **先修 A**（同文档排除）— 1 行代码，影响最大
2. **再修 C1**（降低阈值）— 1 行配置，配合 A 生效
3. **然后 B1**（前端提示）— 改善用户体验，避免再次"无冲突"困惑
4. **最后 C2**（指定文档扫描）— 优化性能，可选
