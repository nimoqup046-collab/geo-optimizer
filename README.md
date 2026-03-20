# GEO 闭环优化助手（V1）

产品闭环：
`品牌档案 -> 素材池 -> 分析报告 -> 内容生成 -> 半自动分发 -> 数据反馈 -> 下一轮优化`

## 技术栈

- 后端：FastAPI + SQLAlchemy + Pydantic
- 前端：Vue 3 + Naive UI + Vite
- 数据库：SQLite（本地）/ PostgreSQL（Railway）
- 大模型：智谱 / 豆包 / OpenRouter（可切换）

## 核心 API

- `POST /api/v1/brands`，`GET /api/v1/brands/:id`
- `POST /api/v1/assets/upload`，`POST /api/v1/assets/paste`，`GET /api/v1/assets`
- `POST /api/v1/analysis/run`，`GET /api/v1/analysis/reports`
- `POST /api/v1/content/generate`，`GET /api/v1/content`，`PATCH /api/v1/content/:id/status`
- `POST /api/v1/exports`
- `POST /api/v1/publish-tasks`，`GET /api/v1/publish-tasks`，`PATCH /api/v1/publish-tasks/:id`
- `POST /api/v1/performance/import`，`GET /api/v1/performance`
- `POST /api/v1/optimization-insights/run`，`GET /api/v1/optimization-insights`
- `GET /api/v1/system/readiness`
- `POST /api/v1/demo/bootstrap`，`GET /api/v1/demo/status`
- `POST /api/v1/prompt-profiles`，`GET /api/v1/prompt-profiles`，`PUT /api/v1/prompt-profiles/:id`
- `POST /api/v1/workflow-steps`，`GET /api/v1/workflow-steps`，`PATCH /api/v1/workflow-steps/:id`，`POST /api/v1/workflow-steps/:id/run`
- `POST /api/v1/creative/wechat-rich-post`（占位接口，受 feature flag 控制）
- `GET /health`

## Windows 脚本

- `scripts/start_system.ps1`
- `scripts/stop_system.ps1`
- `scripts/doctor.py`
- `scripts/smoke.py`
- `scripts/import_real_assets.py`
- `scripts/repo_preflight.py`
- `仓库上云前检查.bat`

## 真实资料导入（核心 20 份）

```bash
cd scripts
python import_real_assets.py --dry-run
python import_real_assets.py
```

导入报告输出：
- `data/reports/import-report-latest.json`

## 半自动分发边界（V1）

- 已支持：任务排队、排期时间、人工发布、链接回填、状态流转、人工确认
- 未支持：自动登录发帖、全自动浏览器发帖、账号密码托管

## 文档

- `docs/RAILWAY_DEPLOY.md`
- `docs/RUNBOOK.md`
- `docs/ITERATION2_LOCKED_BACKLOG.md`
- `docs/GITHUB_COLLAB_WORKFLOW.md`

## GitHub 协作约定（锁定）

- 代码仓：`D:\my-projects\geo-optimizer`（private）
- 数据仓：`D:\geo_feedback_optimizer`（private）
- 分支策略：
  - `main` 仅放稳定版本
  - `codex/<topic>`、`claude/<topic>` 通过 PR 合并
- 提交前执行：
  - `python scripts/repo_preflight.py`
