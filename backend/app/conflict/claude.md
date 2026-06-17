# Conflict — 冲突检测引擎

检测知识库文档间的信息冲突。核心流程：

1. **候选对生成**: 对所有活跃分块生成候选对 (基于 embedding 相似度过滤)
2. **LLM 比较**: 调用 DeepSeek 模型判断每对分块是否包含矛盾
3. **冲突识别**: 将冲突分为 5 种类型:
   - `factual_contradiction` — 事实矛盾 (如"A 公司成立于 2010 年" vs "A 公司成立于 2012 年")
   - `numerical_discrepancy` — 数值不一致
   - `temporal_conflict` — 时效冲突
   - `definition_mismatch` — 定义不匹配
   - `conditional_vs_absolute` — 条件陈述 vs 绝对陈述

## 扫描任务

- 通过 `/api/scans/start` 触发
- 使用 SQLite 表 `scan_jobs` 跟踪状态
- 可配置相似度阈值 (默认 0.85)
- 检测方法: `embedding` / `llm` / `rule_based`
