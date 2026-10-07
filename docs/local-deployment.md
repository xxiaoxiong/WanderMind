# Windows 本机长期运行

本方案把本机 Docker Compose 作为长期主实例：PostgreSQL 数据保存在命名卷中，
三个容器都使用 `restart: unless-stopped`，应用内 Guardian 守护 Autopilot，Windows
计划任务再从主机侧探活和备份。服务只监听 `127.0.0.1`，不会直接暴露到局域网或公网。

## 首次配置

1. 安装并启动 Docker Desktop。
2. 复制 `.env.example` 为 `.env`。
3. 为 `WANDERMIND_POSTGRES_PASSWORD` 设置至少 16 位、仅包含字母、数字、`_`、`-`
   的随机值。
4. 配置真实 Runtime；Agnes APIHub 示例：

```dotenv
WANDERMIND_RUNTIME_ADAPTER=openai
WANDERMIND_LLM_BASE_URL=https://apihub.agnes-ai.com/v1
WANDERMIND_LLM_API_KEY=<secret>
WANDERMIND_LLM_MODEL=agnes-2.5-flash
WANDERMIND_RUNTIME_TIMEOUT_SECONDS=45
WANDERMIND_RUNTIME_MAX_RETRIES=1
WANDERMIND_ENABLE_AUTOPILOT=true
```

密钥只保存在被 Git 忽略的本机 `.env` 中，不得写入 Compose、脚本、日志或提交历史。

## 启动与安装守护

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/start_local_stack.ps1 -Build
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/install_local_service.ps1
```

第一条命令会等待 Docker、同步持久卷中的数据库角色密码、构建镜像并等待应用、
Autopilot 与 Guardian 全部健康。第二条命令会安装：

- 当前用户登录时的隐藏启动入口；
- 每 5 分钟执行一次的 `WanderMind Stack Guardian`；
- 每 6 小时执行一次的 `WanderMind Database Backup`；
- 交流供电下不自动睡眠、不自动休眠的电源设置。

## 使用与观察

- UI：<http://127.0.0.1:8080/#/autopilot>
- 健康检查：<http://127.0.0.1:8080/health>
- API 文档：<http://127.0.0.1:8000/docs>

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:8080/api/v1/autopilot/status
docker compose ps
docker compose logs --tail=200 backend
```

正常状态应满足 `status=ok`、`autopilot_worker_running=true`、
`guardian.running=true`、Campaign 为 `active`。完整轮次可能需要数分钟；轮次运行中可通过
当前 Session Trace 与 Runtime Session 观察实时推进，轮次结束后累计 Candidate、Wonder、
Runtime calls 和回灌知识会一次性结算。

同一 API 密钥不要同时运行多个 Autopilot 主实例。切换到本机作为主实例后，应暂停线上
Campaign，保留线上数据只读查看，避免重复调用、配额竞争和重复成果。

## 备份与恢复

计划任务调用 `scripts/backup_and_prune.ps1`，默认保留最近 56 份备份：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/backup_and_prune.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/restore.ps1 `
  -InputPath ./backups/wandermind_YYYYMMDD_HHMMSS.dump -Force
```

恢复前先复制目标备份，恢复后检查 `alembic current`、知识数量、Campaign 状态与最近一次
Session Trace。不要执行 `docker compose down -v`，该命令会删除持久数据库卷。

## 停用主机守护

```powershell
schtasks.exe /Delete /TN "WanderMind Stack Guardian" /F
schtasks.exe /Delete /TN "WanderMind Database Backup" /F
Remove-Item "$([Environment]::GetFolderPath('Startup'))/WanderMind.cmd"
docker compose down
```

`docker compose down` 会停止容器但保留数据卷。需要恢复系统原电源策略时，再使用
Windows 电源设置或 `powercfg` 设置所需的交流睡眠与休眠超时。
