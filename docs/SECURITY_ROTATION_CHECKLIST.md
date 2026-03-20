# 安全轮换清单（首次上云后）

## 1）必须轮换的密钥

- 智谱 `ZHIPU_API_KEY`
- OpenRouter `OPENROUTER_API_KEY`
- 豆包 `DOUBAO_API_KEY`
- Railway 访问令牌（若曾在终端/日志中暴露）

## 2）轮换执行顺序

1. 在各平台控制台生成新 Key。
2. 先更新 Railway 环境变量。
3. 在线上验证 `GET /api/v1/system/readiness`。
4. 验证通过后，立即吊销旧 Key。

## 3）GitHub 协作者最小权限

- 仅添加必要协作者。
- 默认给 `Write`，避免 `Admin`。
- 合作开发统一走分支 + PR，不直接推 `main`。

## 4）本地提交前固定动作

1. 运行：`python scripts/repo_preflight.py`
2. 确认：无 `tmp_*` / `railway_*` / `.env` / `_deploy_*`
3. 再提交并推送分支。
