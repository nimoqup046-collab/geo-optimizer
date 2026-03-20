# GitHub 双仓与协作工作流

## 1. 仓库拆分（已锁定）

- 代码仓（Private）：`geo-optimizer`
  - 本地目录：`D:\my-projects\geo-optimizer`
- 数据仓（Private）：`geo_feedback_optimizer_data`
  - 本地目录：`D:\geo_feedback_optimizer`

原则：代码和真实素材绝不混仓。

## 2. 首次上传（GitHub Desktop）

### 2.1 代码仓

1. 在 GitHub Desktop 选择 `Add` -> `Add existing repository`，指向 `D:\my-projects\geo-optimizer`。
2. 若提示不是 Git 仓库，选择创建本地仓库（或先 `git init`）。
3. 确认提交列表中不出现 `tmp_*`、`railway_*`、`backend/.env`、`_deploy_*`。
4. 首次提交信息：
   - `chore: initial private codebase import`
5. `Publish repository`，勾选 `Keep this code private`。

### 2.2 数据仓

1. 在 GitHub Desktop 选择 `Add` -> `Add existing repository`，指向 `D:\geo_feedback_optimizer`。
2. 首次提交信息建议：
   - `chore: initial private data repo import`
3. `Publish repository`，勾选 `Keep this code private`。

## 3. 分支与 PR 规范

- 默认分支：`main`（只放稳定版本）
- 分支命名：
  - Codex：`codex/<topic>`
  - Claude：`claude/<topic>`
- 合并要求：
  1. 每个功能一个 PR
  2. 合并前至少一次 smoke 验证
  3. 禁止把生产密钥和本地日志文件提交到 PR

### 3.1 私有仓分支保护限制说明

- 当前账号套餐下，GitHub 私有仓无法启用服务器端 Branch Protection（API 返回 403）。
- 已采用本地替代方案：
  - `scripts/install_main_guard_hook.py`
  - `启用防误推main.bat`
- 效果：默认阻止直接 `git push origin main`，必须走分支 + PR。
- 紧急放行（仅应急）：`ALLOW_MAIN_PUSH=1 git push origin main`

## 4. 安全基线

1. 已暴露过的密钥必须轮换：
   - 智谱 API Key
   - OpenRouter API Key
   - 豆包 API Key
   - Railway Token
2. 环境变量只保存在 Railway，不写入仓库。
3. 提交前执行：
   - `python scripts/repo_preflight.py`

## 5. 最小验收

1. 本地执行预检查通过。
2. GitHub 网页文件树无 `tmp_*`/`railway_*`/`.env`/`_deploy_*`。
3. 新建一个测试分支并发起 PR（哪怕只改一行 README），确认可 review 和 merge。
