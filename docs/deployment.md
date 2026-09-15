# 线上部署

当前试用实例：<https://wandermind-p6jg.onrender.com>。2026-09-15 验收时，首次 Docker 构建、Alembic `0001 -> 0002`、公开 `/health` 与匿名访问 401 均通过。用户名为 `wandermind`，密码由 Render 生成并保存在服务 Environment 页面。

## Render Blueprint

仓库包含 `render.yaml` 与根目录 `Dockerfile`。统一镜像在构建阶段编译 React，运行阶段由 FastAPI 同源提供 UI 和 API，并在每次启动前执行 `alembic upgrade head`。

1. 打开 [Deploy to Render](https://render.com/deploy?repo=https://github.com/xxiaoxiong/WanderMind)。
2. 登录 Render，检查 Blueprint 中的 Web Service 与 PostgreSQL 数据库，确认没有产生非预期付费项目。
3. 创建资源并等待 `/health` 变为 200。
4. 在 Web Service 的 Environment 页面以 Secret 添加 `WANDERMIND_LLM_API_KEY`；Blueprint 已配置 `openai`、Agnes APIHub URL 与 `agnes-2.5-flash`，但不会保存真实密钥。
5. 查看或重置 `WANDERMIND_ACCESS_PASSWORD`。
6. 访问服务 URL，用户名为 `wandermind`，密码为上一步的值。
7. 导入两条非敏感测试知识，执行 Wander 并对 Wonder 运行深度探索；确认 Runtime Session provider 为 `openai-compatible`，刷新页面后数据仍存在。

Blueprint 将 Render 的 `connectionString` 注入 `WANDERMIND_DATABASE_URL`。应用会把 `postgresql://` 或 `postgres://` 自动转换为 asyncpg URL。PostgreSQL 迁移会创建 `vector` 扩展及 V0.1 schema。

## 免费层边界

- 免费 Web Service 空闲时会休眠，首次请求可能需要等待冷启动。
- 免费 PostgreSQL 数据库创建 30 天后到期，不适合长期保存个人知识。
- 长期使用应升级数据库计划、启用平台备份，并定期验证 `pg_dump` 恢复。
- Scheduler 仅允许一个 Web Service 副本；扩容前设置 `WANDERMIND_ENABLE_SCHEDULER=false` 或实现 leader election。

## 安全

- 不要删除 `WANDERMIND_ACCESS_PASSWORD`；为空会关闭访问保护。
- 不要把 `WANDERMIND_LLM_API_KEY` 写进 Blueprint、镜像、构建参数或 Git；只使用 Render Secret，并在怀疑泄漏时立即轮换。
- 首次部署后轮换自动生成的密码，并使用密码管理器保存。
- Basic Auth 只能在平台提供的 HTTPS 地址上使用。
- `/health` 保持公开；UI、API、OpenAPI 文档和指标均需要认证。
- V0.1 没有租户隔离与速率限制，不应向不受信用户共享凭据。

## 回滚

1. 在 Render 选择上一个成功构建的 commit 重新部署。
2. 若迁移失败，不要手工修改 Alembic 版本；先从数据库备份恢复到隔离实例。
3. 验证 `/health`、匿名 401、授权 UI/API、知识数量与最近一个 Wonder。

## 临时隧道

Cloudflare Quick Tunnel 适合短时演示，但 URL、进程和本机在线状态都不持久。它会把本机服务经第三方网络暴露到公网；只有在数据库不含敏感信息、已设置强密码且使用者明确接受风险时才应启动。正式使用优先选择受控托管部署。
