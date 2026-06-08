# FunnelLens AI 部署手册

目标交付：**GitHub 仓库 + 线上 Demo + 2 分钟演示视频**。

## 1. GitHub 仓库

在 GitHub 新建仓库，例如 `funnellens-ai`，不要勾选初始化 README。

本地执行：

```powershell
cd "F:\Codex\260605\1 数据库和后端"
git init
git add .
git commit -m "Initial FunnelLens AI portfolio app"
git branch -M main
git remote add origin https://github.com/<your-name>/funnellens-ai.git
git push -u origin main
```

提交前必须确认：

- 不提交 `.env`
- 不提交 DeepSeek API key
- 不提交 Supabase 数据库密码
- 不提交 `backend/.venv`
- 不提交 `frontend/node_modules`

## 2. Supabase Free 数据库

1. 创建 Supabase Free 项目。
2. 进入 `Project Settings` -> `Database` -> `Connection string`。
3. 选择 **Transaction pooler**，端口应为 `6543`。
4. 复制连接串并替换密码。
5. 后端 Vercel 环境变量使用：

```text
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

后端冷启动会对已有数据库执行 Alembic 迁移；如果本机已经安全配置 `DATABASE_URL`，也可以在 `backend` 目录手动执行：

```powershell
alembic upgrade head
python scripts/seed_official_demos.py --clear-all --analyze
```

迁移负责升级已有 Supabase 表结构；样例脚本会幂等创建五个官方样例。`--clear-all` 会清理公开体验数据，只应在重置 Demo 时使用。Vercel 加密环境变量无法被 CLI 拉回本机时，先部署后端并访问 `/health` 触发迁移，再使用带 `X-Admin-Token` 的 `/api/admin/reset-demo` 重建样例。

常见坑：

- 必须使用 Transaction Pooler，不要使用 Direct Connection。
- 端口必须是 `6543`。
- URL scheme 建议写成 `postgresql+psycopg://`，不要只写 `postgresql://`。
- 数据库密码如果有 `@`、`#`、`/`、`:` 等字符，需要 URL encode。
- Free 项目可能休眠，面试前先打开一次 Demo 预热。

## 3. Vercel 后端

在 Vercel 新建项目，选择 GitHub 仓库。

配置：

```text
Root Directory: backend
Framework Preset: Other
Build Command: 留空
Output Directory: 留空
Install Command: pip install -r requirements.txt
```

环境变量：

```text
DEEPSEEK_API_KEY=<your-deepseek-key>
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=<supabase-transaction-pooler-url>
FRONTEND_ORIGIN=https://<your-frontend>.vercel.app
PUBLIC_API_BASE=https://<your-backend>.vercel.app
RATE_LIMIT_SALT=<long-random-secret>
ADMIN_SEED_TOKEN=<long-random-secret>
```

部署后验证：

```text
https://<your-backend>.vercel.app/health
```

应该返回：

```json
{
  "status": "ok",
  "model": "deepseek-v4-flash",
  "database": "postgres",
  "deepseek_configured": true
}
```

## 4. Vercel 前端

再新建一个 Vercel 项目，仍然选择同一个 GitHub 仓库。

配置：

```text
Root Directory: frontend
Framework Preset: Vite
Build Command: npm run build
Output Directory: dist
```

环境变量：

```text
VITE_API_BASE=https://<your-backend>.vercel.app
```

部署后验证：

1. 打开前端 Vercel 链接。
2. 点击 `运行诊断`。
3. 确认能看到中文诊断、承诺映射、Agent 轨迹、证据库、实验方案。

## 5. 演示视频

录屏 2 分钟左右。推荐顺序：

1. 产品定位：中文开发者工具广告转化诊断 Agent。
2. 展示中文广告样例。
3. 点击 `运行诊断`。
4. 展示 `承诺映射`。
5. 展示 `Agent 轨迹`。
6. 展示 `证据库`。
7. 展示 `实验方案`。
8. 结尾展示 GitHub README 和线上 Demo 链接。

视频建议放到国内可访问位置：B 站、飞书文档、腾讯文档、阿里云 OSS，或作为面试材料附件。

## 6. 面试前检查

- 用无痕窗口打开前端 Demo。
- 用手机流量打开前端 Demo。
- 找朋友帮忙点链接。
- 浏览器 DevTools 搜索 `DEEPSEEK` 和 `DATABASE_URL`，确认没有密钥泄露。
- `/health` 里 `database` 必须是 `postgres`，如果是 `sqlite` 说明线上没配 Supabase。
- `/health` 里 `deepseek_configured` 必须是 `true`，否则线上没配 DeepSeek key。
- 如果 “运行诊断” 结果里显示“本地规则”，说明 DeepSeek 调用失败但 fallback 生效；面试前最好修好 key 或模型名。
- 准备本地启动和录屏作为兜底。
