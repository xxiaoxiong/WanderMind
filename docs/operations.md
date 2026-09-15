# 运维手册

## 启停

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose down
```

`docker compose down` 不删除数据库卷；只有显式 `down -v` 才会删除数据。

## 健康与指标

- Liveness：`GET /health`，期望 `status=ok`。
- Metrics：`GET /metrics`。
- API Docs：`GET /docs`。
- UI probe：Nginx `/healthz`。

重点告警：

- HTTP 5xx 比率与 p95 延迟。
- `wandermind_wander_runs_total{outcome="failed"}`。
- Runtime timeout / malformed / unavailable。
- PostgreSQL 容量、连接和慢查询。
- Scheduler 重复执行或长时间无执行。

## 备份与恢复

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/backup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/restore.ps1 `
  -InputPath ./backups/wandermind_YYYYMMDD_HHMMSS.dump -Force
```

脚本使用容器内 `pg_dump` / `pg_restore`，避免 Windows PowerShell 5 对二进制重定向的编码风险。恢复必须显式传入 `-Force`。

恢复后执行：

1. `alembic current` 确认 schema 版本。
2. 检查 Knowledge、Session、Wonder、Feedback 数量。
3. 抽取至少一个 Session 验证 Trace 与 final wonder IDs。
4. 运行 API smoke 与 benchmark。

## 故障处理

### 数据库不可用

停止写流量，检查 pgvector 容器、连接串与磁盘。不要自动切换到临时 SQLite，以免形成分叉数据。

### Runtime 不可用

核心 Wander 不依赖 Runtime。Deep Explore 会返回失败 Evidence、Critic reject，不能伪造来源。恢复后可重新点击 Continue Exploring。

### Scheduler 重复

立即将 `WANDERMIND_ENABLE_SCHEDULER=false`，保留一个 leader 后再启用。检查近期开启的 Random Revival Seeds。

### 迁移失败

备份数据库，保留 Alembic 输出。禁止手工跳过 revision；在隔离副本验证 downgrade/upgrade 后再恢复。

## 安全

- 不提交 `.env`、私钥或访问令牌；CI 运行 `scripts/check_secrets.py`。
- 反向代理与应用同时限制请求体。
- 只接受 UTF-8 文本文档；V0.1 不解析 PDF/Office/HTML。
- Codex Runtime 默认只读、无网络、无审批提示。
- 公网部署必须设置非空 `WANDERMIND_ACCESS_PASSWORD` 并只使用 HTTPS；`/health` 是唯一公开路径。
- V0.1 的 Basic Auth 只提供单用户访问门；不提供公网速率限制、租户隔离或细粒度权限。
- 轮换密码后重启所有 Web Service 副本，并验证匿名 UI/API 返回 401。

托管平台部署、密码获取和回滚步骤见 `docs/deployment.md`。
