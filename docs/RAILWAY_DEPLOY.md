# Railway 部署指南

## 前置条件

- Railway 账号（[railway.app](https://railway.app)）
- GitHub 仓库已关联 Railway 项目

## 项目结构

Railway 需要分别部署 **backend** 和 **frontend** 两个服务。

### Backend 服务

**Root Directory**: `backend`

Railway 会自动检测 `Procfile`，启动命令：

```
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**环境变量**（在 Railway Dashboard → Variables 中配置）：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串（Railway 提供，格式 `postgresql+asyncpg://...`） | 是 |
| `ZHIPU_API_KEY` | 智谱 AI API Key | 是 |
| `DOUBAO_API_KEY` | 豆包 API Key | 否 |
| `OPENROUTER_API_KEY` | OpenRouter API Key（Expert Team 功能需要） | 否 |
| `INTERNAL_API_KEY` | 内部接口鉴权密钥 | 是 |
| `DEBUG` | 生产环境设为 `false` | 是 |

**数据库**：推荐在 Railway 中添加 PostgreSQL 插件，自动注入 `DATABASE_URL`。将连接串中 `postgresql://` 替换为 `postgresql+asyncpg://` 以适配 SQLAlchemy async。

### Frontend 服务

**Root Directory**: `frontend`

**Build Command**: `npm ci && npm run build`

**Start Command**: 使用静态文件服务（如 `npx serve dist`）或配置 Nginx。

**环境变量**：

| 变量名 | 说明 |
|--------|------|
| `VITE_API_BASE_URL` | Backend 服务的内部 URL，如 `https://<backend-service>.railway.internal/api/v1` |

## 部署步骤

1. **创建项目**：Railway Dashboard → New Project → Deploy from GitHub Repo
2. **添加 PostgreSQL**：项目内 → Add Service → Database → PostgreSQL
3. **配置 Backend 服务**：
   - Settings → Root Directory: `backend`
   - Variables → 添加上述环境变量
   - `DATABASE_URL` 引用 PostgreSQL 插件提供的连接串
4. **配置 Frontend 服务**：
   - Settings → Root Directory: `frontend`
   - Build Command: `npm ci && npm run build`
   - Variables → 设置 `VITE_API_BASE_URL`
5. **生成域名**：Settings → Networking → Generate Domain

## 注意事项

- 生产环境 `DEBUG` 必须为 `false`，否则 Demo 端点无需认证
- SQLite 数据库文件在 Railway 重启后会丢失，**务必使用 PostgreSQL**
- 上传文件存储在本地 `data/uploads/`，Railway 无持久磁盘——大文件建议接入 S3（已支持 boto3）
- 部署前运行 `python scripts/repo_preflight.py` 检查是否有敏感文件泄漏
