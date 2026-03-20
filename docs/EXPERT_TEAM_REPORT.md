# GEO Optimizer 专家团队对标分析与优化报告

## 一、竞品调研概览

### 1.1 高相似度项目

| 项目 | GitHub | 相似度 | 核心特色 |
|------|--------|--------|---------|
| **GetCito** | [ai-search-guru/getcito](https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool) | ★★★★★ | 全球首个开源 AIO/AEO/GEO 工具，多引擎品牌追踪 |
| **AutoGEO** | [cxcscmu/AutoGEO](https://github.com/cxcscmu/AutoGEO) | ★★★★☆ | ICLR'26，规则提取+RL优化，50%可见性提升 |
| **Gego** | [AI2HU/gego](https://github.com/AI2HU/gego) | ★★★★☆ | 多 LLM GEO 追踪，自动关键词提取，定时调度 |
| **GEO-Analyzer** | [houtini-ai/geo-analyzer](https://github.com/houtini-ai/geo-analyzer) | ★★★☆☆ | Claude 驱动本地语义分析，citability/extractability 评分 |
| **GEO-optim** | [GEO-optim/GEO](https://github.com/GEO-optim/GEO) | ★★★☆☆ | 学术框架，GEO-Bench 基准，可插拔优化方法 |

### 1.2 较高相似度项目

| 项目 | 相似度 | 可借鉴点 |
|------|--------|---------|
| SEO-GEO Toolkit | ★★★☆☆ | CLI 工具链，传统 SEO + GEO 融合 |
| RivalSee AI-SEO-Tools | ★★☆☆☆ | AI 爬虫优化提示词集合 |
| ContentSwift | ★★☆☆☆ | 免费内容研究/优化工具 |
| TensorZero | ★★☆☆☆ | 工业级 LLM 优化栈 |

---

## 二、差距分析与短板识别

### 2.1 功能差距矩阵

| 功能维度 | geo-optimizer (升级前) | GetCito | AutoGEO | Gego | GEO-Analyzer |
|---------|----------------------|---------|---------|------|-------------|
| **AI 模型** | gpt-4o-mini 单模型 | Azure GPT-4 + Gemini 双模型 | GPT-4 + RL 模型 | 6+ LLM | Claude Sonnet 4.5 |
| **GEO 评分** | 无 | answer-readiness 评分 | GEO/GEU 双评分 | 关键词统计 | citability/extractability/readability |
| **多引擎追踪** | 无 | ChatGPT/Claude/Perplexity | 多引擎偏好挖掘 | 多 LLM 调度 | 无 |
| **内容优化** | 单 LLM 直出 | 基础优化 | 规则提取+自动改写 | 无 | 语义分析建议 |
| **专家协作** | 无 | 无 | 无 | 无 | 无 |
| **前端 GUI** | 基础表单 | Next.js 现代 UI | 无 (纯 Python) | CLI | CLI (MCP) |
| **闭环流程** | 完整但粗糙 | 部分 | 无 | 部分 | 无 |

### 2.2 核心短板总结

1. **AI 模型单一** — 仅用 gpt-4o-mini，缺乏深度推理能力
2. **无 GEO 评分体系** — 无法量化内容在 AI 搜索中的可见性
3. **内容生成质量低** — 单角色直出，缺乏策略→生成→审核 pipeline
4. **无优化策略框架** — 缺少引用增强、统计增强等 GEO 优化手段
5. **分析报告浅层** — 仅基础关键词分层，缺乏语义深度分析

---

## 三、专家团队架构设计

### 3.1 5 位专家角色

| 角色 | 模型 (OpenRouter) | 职责 | 能力来源 |
|------|-------------------|------|---------|
| **GEO 首席策略师** | `anthropic/claude-sonnet-4-6` | 全局策略规划、SWOT 分析、竞品对标 | Claude 深度推理 |
| **内容架构师** | `anthropic/claude-sonnet-4-6` | 内容结构设计、可引用性优化、平台适配 | Claude 创意写作 |
| **数据分析师** | `google/gemini-3.1-pro` | 关键词深度分析、覆盖率评估、趋势预测 | Gemini 数据分析 |
| **质量审核官** | `anthropic/claude-sonnet-4-6` | 多维度评分、合规检查、修改建议 | Claude 评估能力 |
| **GEO 优化师** | `google/gemini-3.1-pro` | 引用增强、统计增强、问答结构化、断言前置 | Gemini 结构优化 |

### 3.2 编排流程

```
输入：品牌 + 关键词 + 素材
    │
    ▼
[GEO 首席策略师] → 策略报告 (SWOT + 行动路线图)
    │
    ├──→ [数据分析师] → 深度关键词分析 + 覆盖率缺口
    │                    (并行执行)
    ├──→ [GEO 优化师] → 优化策略 + 引用增强建议
    │
    ▼
[内容架构师] → 基于策略+分析生成高质量多平台内容
    │
    ▼
[质量审核官] → GEO 评分卡 + 修改建议
    │
    ▼
输出：专家团队报告 + 优化内容 + GEO 评分卡
```

### 3.3 GEO 评分体系（借鉴 GEO-Analyzer）

| 指标 | 权重 | 目标 | 说明 |
|------|------|------|------|
| **Citability（可引用性）** | 30% | ≥70 | 可被 AI 直接引用的断言比例 |
| **Claim Density（断言密度）** | 25% | ≥4/100字 | 事实性断言密度 |
| **Extractability（可提取性）** | 25% | ≥70 | AI 提取答案的友好度 |
| **Readability（可读性）** | 20% | ≥70 | 句子长度、结构清晰度 |

### 3.4 GEO 优化策略（借鉴 AutoGEO + GEO-optim）

| 策略 | 预期提升 | 来源 |
|------|---------|------|
| **引用增强** | 30-40% | GEO-optim 研究实证 |
| **统计增强** | 25-35% | GEO-optim 研究实证 |
| **问答结构化** | 20-30% | 搜索引擎友好格式 |
| **断言前置** | 25-35% | GEO-Analyzer 最佳实践 |
| **实体丰富** | 15-25% | 提升专业性和可信度 |

---

## 四、升级后竞争力对比

| 维度 | 升级前 | 升级后 | 对标结果 |
|------|--------|--------|---------|
| AI 模型 | gpt-4o-mini | Claude Sonnet 4.6 + Gemini 3.1 Pro | **超越** GetCito（仅 2 模型）|
| 分析深度 | 基础关键词分层 | 5 专家协作 + GEO 语义评分 | **超越** 所有竞品 |
| 内容质量 | 单 LLM 直出 | 策略→分析→生成→审核 pipeline | **独创** - 竞品无此功能 |
| 优化策略 | 无 | 5 种可插拔策略 | **对齐** GEO-optim |
| 前端体验 | 基础表单 | GEO 雷达图 + 专家面板 + 仪表盘 | **超越** Gego (CLI) |
| 全栈闭环 | 有但粗糙 | 专家级闭环 | **独特优势** |

### 4.1 独特竞争优势

1. **全栈专家协作** — 业界首个 5 角色 AI 专家团队协作的 GEO 工具
2. **双引擎深度推理** — Claude Sonnet 4.6 (策略/内容/审核) + Gemini 3.1 Pro (分析/优化)
3. **量化 GEO 评分** — 4 维度语义评分体系，可追踪优化效果
4. **可插拔优化策略** — 5 种 GEO 优化方法，可组合使用
5. **闭环自动化** — 从品牌档案到内容发布的完整链路

---

## 五、技术实现清单

### 5.1 新增文件（7 个）

| 文件 | 功能 |
|------|------|
| `backend/services/expert_team.py` | 专家团队编排器 |
| `backend/services/expert_prompts.py` | 5 专家提示词模板 |
| `backend/services/geo_scorer.py` | GEO 语义评分器 |
| `backend/services/geo_strategies.py` | 5 种优化策略 |
| `backend/api/expert_team.py` | 专家团队 API |
| `frontend/src/views/ExpertTeam.vue` | 专家团队面板 |
| `frontend/src/api/expertTeam.ts` | API 客户端 |

### 5.2 修改文件（8 个）

| 文件 | 变更 |
|------|------|
| `backend/config.py` | 新增 5 个专家模型配置 + feature flag |
| `backend/services/llm_service.py` | 新增 `generate_with_expert_role()` |
| `backend/main.py` | 注册 expert_team router |
| `frontend/src/router/index.ts` | 新增 `/expert-team` 路由 |
| `frontend/src/views/Layout.vue` | 新增专家团队菜单项 |
| `frontend/src/views/AnalysisCenter.vue` | 专家深度分析 + GEO 评分展示 |
| `frontend/src/views/Workshop.vue` | 专家协作生成模式 |
| `frontend/src/views/Overview.vue` | 专家团队状态 + 统计 |
| `frontend/src/api/index.ts` | 导出 expertTeam API |
| `frontend/src/constants/uiText.ts` | 新增菜单文本 |

---

## 六、API 端点清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/expert-team/config` | 获取专家团队配置 |
| `GET` | `/api/v1/expert-team/roles` | 列出所有专家角色 |
| `GET` | `/api/v1/expert-team/strategies` | 列出 GEO 优化策略 |
| `POST` | `/api/v1/expert-team/analyze` | 运行完整 5 专家 pipeline |
| `POST` | `/api/v1/expert-team/expert/run` | 运行单个专家 |
| `POST` | `/api/v1/expert-team/geo-score` | 计算 GEO 语义评分 |
| `POST` | `/api/v1/expert-team/optimize` | 应用 GEO 优化策略 |
