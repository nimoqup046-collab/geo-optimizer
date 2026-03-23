# GEO V1 运行手册

## 1. 启动 / 停止

- 启动：`scripts/start_system.ps1`（或双击 `启动系统.bat`）
- 停止：`scripts/stop_system.ps1`（或双击 `停止系统.bat`）

运行时文件：
- `data/run/backend.pid`
- `data/run/frontend.pid`
- `data/run/backend.out.log`
- `data/run/backend.err.log`
- `data/run/frontend.out.log`
- `data/run/frontend.err.log`

## 2. 体检（doctor）

- 执行：`python scripts/doctor.py`（或双击 `体检系统.bat`）
- 报告：`data/reports/doctor-report-latest.json`

检查项包括：
- Python / npm 是否可用
- backend / frontend 入口文件是否存在
- `backend/.env` 与 `.env.example` 键完整性
- 端口状态（8000 / 5173）
- PID 文件是否有效
- 运行时环境（`ComSpec` / `PATHEXT`）

## 3. 冒烟验收（smoke）

- 执行：`python scripts/smoke.py`（或双击 `冒烟验收.bat`）
- 报告：`data/reports/smoke-report-latest.json`

闭环顺序：
1. 创建品牌
2. 粘贴素材
3. 运行分析
4. 生成内容
5. 创建发布任务
6. 导入表现数据
7. 生成优化建议

## 4. readiness 健康检查

- 接口：`GET /api/v1/system/readiness`
- 检查：数据库、目录、LLM 配置、feature flags
- 运行时诊断字段：
  - `runtime_shell_ok`
  - `runtime_python_ok`
  - `runtime_git_ok`
  - `runtime_npm_ok`
  - `runtime_env_detail`

## 4.1 PR 运行时检查与审查回路

- 运行时检查：
  - `python scripts/pr_runtime_check.py`
  - 报告：`data/reports/pr-runtime-check-latest.json`
- PR 审查回路：
  - `python scripts/pr_review_loop.py --pr <编号>`
  - 报告：`data/reports/pr-review-latest.json`

## 4.2 异常会话恢复 SOP（60 秒）

当终端出现命令不可识别或 `ComSpec` / `PATHEXT` 异常时：
1. 先执行：`python scripts/pr_runtime_check.py`
2. 若失败，重开终端后执行：`scripts/start_system.ps1`
3. 再执行：`python scripts/pr_runtime_check.py`，确认 `pass`
4. 继续执行 `体检系统.bat` 和 `冒烟验收.bat`

## 5. 真实资料导入

```bash
python scripts/import_real_assets.py --dry-run
python scripts/import_real_assets.py
```

默认来源目录：
- `D:\geo_feedback_optimizer\...`

默认策略：
- 导入核心 20 份（文本优先 + xlsx + 图片无 OCR 占位）

导入报告：
- `data/reports/import-report-latest.json`

## 6. Railway

部署细节见：`docs/RAILWAY_DEPLOY.md`

## 7. GitHub 上传前检查

- 执行：`python scripts/repo_preflight.py`（或双击 `仓库上云前检查.bat`）
- 报告：`data/reports/repo-preflight-latest.json`

检查项包括：
- `.gitignore` 是否覆盖关键忽略规则
- 当前改动是否包含高风险文件（`tmp_*`、`railway_*`、`_deploy_*`、`.env`）
- 仓库内是否出现疑似密钥模式

## 8. 前端依赖注意事项（Windows）

若出现 `Cannot find module ... node_modules/vite/bin/vite.js`：
1. 进入 `frontend` 目录
2. 执行：`npm install --include=dev`
3. 再执行：`npm run build`

说明：部分环境设置了生产依赖模式，会导致 devDependencies 未安装。
