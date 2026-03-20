# GEO V1 运行手册

## 1）启动 / 停止

- 启动：`scripts/start_system.ps1`（或双击 `启动系统.bat`）
- 停止：`scripts/stop_system.ps1`（或双击 `停止系统.bat`）

运行期文件：
- `data/run/backend.pid`
- `data/run/frontend.pid`
- `data/run/backend.out.log`
- `data/run/backend.err.log`
- `data/run/frontend.out.log`
- `data/run/frontend.err.log`

## 2）体检（Doctor）

- 执行：`scripts/doctor.py`（或双击 `体检系统.bat`）
- 输出：`data/reports/doctor-report-latest.json`

检查项包含：
- Python / npm 可用性
- backend / frontend 入口文件
- `.env` 对 `.env.example` 的键完整性
- 端口状态（8000 / 5173）
- PID 文件存在性

## 3）冒烟验收（Smoke）

- 执行：`scripts/smoke.py`（或双击 `冒烟验收.bat`）
- 输出：`data/reports/smoke-report-latest.json`

闭环顺序：
1. 创建品牌
2. 粘贴素材
3. 执行分析
4. 生成内容
5. 创建发布任务
6. 导入表现数据
7. 生成优化建议

## 4）Readiness 健康检查

- `GET /api/v1/system/readiness`
- 检查数据库、目录、LLM 配置状态和 feature flags。

## 5）真实资料导入

```bash
cd scripts
python import_real_assets.py --dry-run
python import_real_assets.py
```

默认来源目录：
- `D:\geo_feedback_optimizer\...`

默认策略：
- 导入核心 20 份（文本优先 + xlsx + 图片无 OCR 占位）

导入报告：
- `data/reports/import-report-latest.json`

## 6）Railway

部署细节见 `docs/RAILWAY_DEPLOY.md`。

## 7）GitHub 上传前检查

- 执行：`python scripts/repo_preflight.py`（或双击 `仓库上云前检查.bat`）
- 输出：`data/reports/repo-preflight-latest.json`

检查项包含：
- `.gitignore` 是否包含关键忽略规则
- 当前 git 状态是否包含高风险文件（`tmp_*`、`railway_*`、`_deploy_*`、`.env`）
- 仓库内是否出现明显密钥模式
