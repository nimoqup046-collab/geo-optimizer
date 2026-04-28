# PR 标题

chore: migrate deployment blueprint from Railway to Render for internal testing

## 变更摘要

本 PR 在不改动现有功能模板和代码结构的前提下，增加 Render 部署能力，供项目同事内测使用。

### 本次新增

- 新增 `render.yaml`（Render Blueprint）
  - `geo-backend`（FastAPI）
  - `geo-frontend`（Vue）
  - `geo-db`（PostgreSQL）
- 新增部署文档：
  - `docs/RENDER_DEPLOY.md`

### 本次调整

- `frontend/.env.production.example`
  - API 基地址示例从 Railway 改为 Render
- `backend/.env.example`
  - 数据库示例注释改为 Render/Railway 通用说明

## 不在本 PR 范围

- 不改任何业务 API 路径
- 不改页面结构与交互流程
- 不做自动发布平台扩展
- 不做数据库模型变更

## 验收清单

1. Render `Blueprint` 能识别 `render.yaml` 并创建 3 个资源。
2. 配置 `ZHIPU_API_KEY` 后，后端 `/health` 与 `/api/v1/system/readiness` 可访问。
3. 前端可正常打开并访问后端 API。
4. 六大模块可见，基础闭环可跑通。

## 风险与回滚

- 风险：Render 免费实例有冷启动，首开可能较慢。
- 回滚：不影响主业务代码，回滚本 PR 即可恢复“仅 Railway 文档/配置”状态。
