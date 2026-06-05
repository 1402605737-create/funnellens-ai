# GitHub / Vercel 安全检查

发布前确认：

- `.env` 未提交
- `backend/.env` 未提交
- `frontend/.env` 未提交
- DeepSeek API key 未出现在源码、README、截图、录屏里
- Supabase 数据库密码未出现在源码、README、截图、录屏里
- 前端只配置 `VITE_API_BASE`
- Supabase 连接串只放在后端 Vercel 环境变量
- DeepSeek key 只放在后端 Vercel 环境变量
- 浏览器 DevTools 的 Network 响应里没有密钥
- GitHub 仓库设置为 public 前，再检查一次提交历史
- Vercel 前端必须配置 `VITE_API_BASE`，否则线上会请求 `localhost:8000`
- Vercel 后端必须配置 `FRONTEND_ORIGIN`，否则浏览器可能被 CORS 拦截
- Supabase 连接串必须用 Transaction Pooler 的 `6543` 端口
- Supabase 密码如果包含 `@`、`#`、`/`、`:` 等符号，必须 URL encode
- DeepSeek 模型名如果线上不可用，系统会 fallback，但面试前必须确认模型调用是真成功还是 fallback

常用检查命令：

```powershell
git status --short
git ls-files | Select-String -Pattern "\.env|funnellens\.db|node_modules|\.venv"
Get-ChildItem -Recurse -File | Select-String -Pattern "DEEPSEEK_API_KEY|DATABASE_URL|supabase|pooler" -ErrorAction SilentlyContinue
```

线上检查接口：

```text
https://<your-backend>.vercel.app/health
```

期望看到：

```json
{
  "status": "ok",
  "database": "postgres",
  "deepseek_configured": true
}
```
