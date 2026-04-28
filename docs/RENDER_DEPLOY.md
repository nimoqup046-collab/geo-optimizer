# Render 部署指南（内测）

本文档用于把 `geo-optimizer` 从 Railway 迁移到 Render，供团队内测使用。

## 1. 前置准备

- GitHub 仓库已包含根目录 `render.yaml`
- 你有 Render 账号并已绑定 GitHub
- 已准备好 API Key（至少 `ZHIPU_API_KEY`）

## 2. 一键创建（Blueprint）

1. 打开 Render Dashboard。
2. 点击 `New` -> `Blueprint`。
3. 选择仓库：`nimoqup046-collab/geo-optimizer`。
4. Render 会自动识别 `render.yaml`，将创建：
   - `geo-backend`（FastAPI）
   - `geo-frontend`（Vue）
   - `geo-db`（PostgreSQL）

## 3. 必填环境变量

创建后，进入 `geo-backend` 的 `Environment`，至少补齐：

- `ZHIPU_API_KEY`（必填）
- `INTERNAL_API_KEY`（建议，前后端内部鉴权）

可选：

- `OPENROUTER_API_KEY`
- `DOUBAO_API_KEY`

说明：

- `DATABASE_URL` 由 `fromDatabase` 自动注入，无需手填。
- `CORS_ORIGINS` 默认给了前端域名占位值，部署后请替换成你的真实前端 URL。

## 4. 前后端联通

`render.yaml` 里前端 `VITE_API_BASE_URL` 默认是占位地址：

`https://geo-backend.onrender.com/api/v1`

部署后请按真实后端域名修改成：

`https://<your-backend-service>.onrender.com/api/v1`

然后手动 `Deploy latest commit` 重新部署 `geo-frontend`。

## 5. 验收清单（5 分钟）

1. 后端健康检查：
   - 打开 `https://<backend>.onrender.com/health`
   - 返回 `{"status":"ok"}` 或等价健康响应
2. 就绪检查：
   - 打开 `https://<backend>.onrender.com/api/v1/system/readiness`
   - 确认 DB、上传目录、导出目录为就绪
3. 前端打开：
   - 打开 `https://<frontend>.onrender.com`
   - 六大模块可见，不空白
4. 最小闭环：
   - 品牌档案 -> 素材池 -> 分析中心 -> 内容工坊 -> 分发与反馈

## 6. 内测建议配置

- `VITE_DEMO_MODE=1`：用于汇报/演示稳定展示
- 切真实业务时改为 `VITE_DEMO_MODE=0`
- 免费实例冷启动较慢，首次访问等待 30-90 秒属正常现象

## 7. 常见问题

### Q1: 前端空白或接口 404

- 检查 `VITE_API_BASE_URL` 是否指向真实后端域名
- 检查后端服务是否成功启动（Render Logs）

### Q2: 生成报告内容很泛

- 检查 `ZHIPU_API_KEY` 是否可用
- 检查 `DEFAULT_LLM_PROVIDER=zhipu` 是否生效
- 若 LLM 调用失败，系统会回退模板文案，表现会偏泛化

### Q3: 跨域报错

- 把 `CORS_ORIGINS` 改为前端真实域名，多个域名用逗号分隔
