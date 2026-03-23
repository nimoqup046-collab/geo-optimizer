# GEO Optimizer 待办备忘录

> 记录已发现但暂未修复的问题、后续改进想法，汇报项目进度时逐一过一遍。

---

## 已知 Bug

### 1. GeoScoreAdapter 引用不存在的 GEOScorer 类
- **文件**: `backend/services/workflow_executor.py:156`
- **现象**: `from services.geo_scorer import GEOScorer` — `GEOScorer` 类不存在，实际应使用 `compute_geo_score()` 函数
- **影响**: 工作流中调用 `geo_score` 适配器会在运行时报 ImportError
- **建议修复**: 将 `GeoScoreAdapter.execute()` 改为使用 `compute_geo_score(content, platform=platform)`，返回 `score_card.to_dict()`
- **发现时间**: 2026-03-23（Skill 设计哲学升级实施过程中）

---

## 后续改进方向

（待补充）
