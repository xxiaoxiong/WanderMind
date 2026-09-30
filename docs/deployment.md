# 线上部署

当前试用实例：<https://wandermind-p6jg.onrender.com>。公开 UI 与 `/health` 无需登录；生产镜像启动时执行全部 Alembic 迁移。

## Render Blueprint

仓库包含 `render.yaml` 与根目录 `Dockerfile`。统一镜像在构建阶段编译 React，运行阶段由 FastAPI 同源提供 UI 和 API，并在每次启动前执行 `alembic upgrade head`。

1. 打开 [Deploy to Render](https://render.com/deploy?repo=https://github.com/xxiaoxiong/WanderMind)。
2. 登录 Render，检查 Blueprint 中的 Web Service 与 PostgreSQL 数据库，确认没有产生非预期付费项目。
3. 创建资源并等待 `/health` 变为 200。
4. 在 Web Service 的 Environment 页面以 Secret 添加 `WANDERMIND_LLM_API_KEY`；Blueprint 已配置 `openai`、Agnes APIHub URL 与 `agnes-2.5-flash`，但不会保存真实密钥。
5. 直接访问服务 URL。
6. 导入至少三条非敏感测试知识并执行 Wander；确认响应 `runtime.verified=true`、provider 为 `openai-compatible`、模型为预期 Agnes 模型、`calls >= 1`，且前端展示 Runtime 证据。若候选达到阈值，一轮完整调用应包含 `candidate_synthesis` 与 `candidate_review`。
7. 打开 `/#/autopilot`，确认 Campaign 为 `active`、主管在线，并观察至少两个完整轮次的累计 Candidate、Wonder 与回灌知识增长。

线上 Blueprint 没有 Codex App Server 凭据，实际使用 Agnes APIHub；本机 Codex Adapter 可通过 `python backend/scripts/run_live_codex_smoke.py --executable <codex-path>` 验证协议，并通过 `python backend/scripts/run_live_codex_wander.py --executable <codex-path>` 验证完整主流程。不要把 OpenAI-compatible/Agnes 调用描述为 Codex 调用。

Blueprint 将 Render 的 `connectionString` 注入 `WANDERMIND_DATABASE_URL`。应用会把 `postgresql://` 或 `postgres://` 自动转换为 asyncpg URL。PostgreSQL 迁移会创建 `vector` 扩展及 V0.1 schema。

## 免费层边界

- 免费 Web Service 在 15 分钟没有入站流量后会休眠；应用内 `ServiceGuardian` 每 30 秒检查并按需重启 Autopilot worker，Blueprint 每 5 分钟通过公网 `/health` 自请求一次，仓库的 `keepalive.yml` 每 10 分钟再从 GitHub Actions 外部探测 Autopilot 状态。
- 免费 PostgreSQL 数据库创建 30 天后到期，不适合长期保存个人知识。
- 进程内自请求与 GitHub Actions 定时任务都可能受平台策略、网络、配额或实例重启影响，因此免费层双重保活仍不等于长期运行 SLA。
- 长期使用应升级 Web Service 与数据库计划、启用平台备份，并定期验证 `pg_dump` 恢复。
- Autopilot 仅允许一个 Web Service 副本；扩容前关闭它或实现数据库租约/leader election。线上 Blueprint 已关闭旧 Scheduler。

## 安全

- 不要把 `WANDERMIND_LLM_API_KEY` 写进 Blueprint、镜像、构建参数或 Git；只使用 Render Secret，并在怀疑泄漏时立即轮换。
- 当前试用实例为公开单用户演示；不要导入隐私、机密或受监管数据。
- 若需限制访问，可同时设置 `WANDERMIND_ACCESS_USERNAME` 与非空的 `WANDERMIND_ACCESS_PASSWORD`；Basic Auth 只能在 HTTPS 上使用。
- V0.1 没有租户隔离、细粒度权限与公网速率限制，不适合作为多用户服务。

## 回滚

1. 在 Render 选择上一个成功构建的 commit 重新部署。
2. 若迁移失败，不要手工修改 Alembic 版本；先从数据库备份恢复到隔离实例。
3. 验证 `/health`、公开 UI/API、知识数量与最近一个 Wonder。

## 临时隧道

Cloudflare Quick Tunnel 适合短时演示，但 URL、进程和本机在线状态都不持久。它会把本机服务经第三方网络暴露到公网；只有在数据库不含敏感信息、已设置强密码且使用者明确接受风险时才应启动。正式使用优先选择受控托管部署。
