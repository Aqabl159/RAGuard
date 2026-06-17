# Resolution — 冲突消解模块

为检测到的冲突生成消解方案，并支持人工审核与执行。

## 消解动作类型

| 动作 | 说明 |
|---|---|
| `replace_both` | 替换双方分块内容 |
| `keep_a_remove_b` | 保留源 A，移除源 B |
| `keep_b_remove_a` | 保留源 B，移除源 A |
| `merge` | 合并双方内容 |
| `manual_rewrite` | 人工重写 |

## 工作流

1. **生成方案**: LLM 分析冲突 → 提出 `proposed_action` + `proposed_content` + `reasoning`
2. **人工审核**: 状态流转 `pending_review` → `approved` / `rejected` / `modified`
3. **执行修复**: 批准后创建 `repair_actions` 记录 (审计追踪):
   - `delete_chunk` — 删除分块
   - `update_chunk` — 更新分块内容
   - `create_chunk` — 创建新分块
   - `merge_chunks` — 合并分块
