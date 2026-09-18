# 配置指南

所有后端变量使用 `WANDERMIND_` 前缀，可写入根目录 `.env`。

| 变量 | 默认值 | 说明 |
|---|---:|---|
| `WANDERMIND_ENV` | `dev` | `dev/test/prod` |
| `WANDERMIND_LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `WANDERMIND_DATABASE_URL` | SQLite | SQLAlchemy async URL |
| `WANDERMIND_CORS_ORIGINS` | localhost:5173 | JSON 数组 |
| `WANDERMIND_ACCESS_USERNAME` | `wandermind` | 启用全站 Basic Auth 时的用户名 |
| `WANDERMIND_ACCESS_PASSWORD` | 空 | 非空时保护除 `/health` 外的所有 HTTP 路径 |
| `WANDERMIND_STATIC_DIR` | 空 | FastAPI 托管前端构建产物的目录 |
| `WANDERMIND_EMBEDDING_DIMENSIONS` | 96 | 确定性向量维度；Postgres schema 当前为 96 |
| `WANDERMIND_RUNTIME_ADAPTER` | `mock` | `mock`、`codex` 或 `openai` |
| `WANDERMIND_CODEX_EXECUTABLE` | `codex` | Codex CLI 路径 |
| `WANDERMIND_RUNTIME_CWD` | 当前目录 | Runtime 可见工作目录 |
| `WANDERMIND_LLM_BASE_URL` | Agnes APIHub | OpenAI-compatible `/v1` 根地址 |
| `WANDERMIND_LLM_API_KEY` | 空 | `openai` Runtime 必填 Secret |
| `WANDERMIND_LLM_MODEL` | `agnes-2.5-flash` | Chat Completions 模型名 |
| `WANDERMIND_LLM_TEMPERATURE` | 0.2 | 结构化输出温度，范围 0–2 |
| `WANDERMIND_LLM_MAX_OUTPUT_TOKENS` | 2000 | 单次响应 token 上限，范围 128–32000 |
| `WANDERMIND_RUNTIME_TIMEOUT_SECONDS` | 60 | 单次任务上限 |
| `WANDERMIND_RUNTIME_MAX_RETRIES` | 2 | 可重试错误次数 |
| `WANDERMIND_WONDER_THRESHOLD` | 0.58 | Surface 阈值 |
| `WANDERMIND_CHEAP_SCORE_THRESHOLD` | 0.40 | Deep Explore 阈值 |
| `WANDERMIND_SCORE_WEIGHTS` | JSON | 八个正向维度与三个风险罚分的完整权重集 |
| `WANDERMIND_ENABLE_SCHEDULER` | false | 启动孵化计划任务 |
| `WANDERMIND_INCUBATION_INTERVAL_MINUTES` | 360 | 孵化周期 |
| `WANDERMIND_MAX_REQUEST_BYTES` | 2100000 | API 请求上限 |
| `WANDERMIND_AUTO_CREATE_SCHEMA` | true | 本地自动建表；生产建议 false + Alembic |

前端变量：

| 变量 | 默认值 | 说明 |
|---|---:|---|
| `VITE_API_URL` | `/api/v1` | API 根路径；开发时 Vite 代理到 8000 |

## 数据库

生产推荐：

```dotenv
WANDERMIND_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/wandermind
WANDERMIND_AUTO_CREATE_SCHEMA=false
```

托管平台常见的 `postgresql://` 或 `postgres://` 连接串会自动转换为 SQLAlchemy asyncpg URL；本地仍建议显式使用 `postgresql+asyncpg://`。

迁移：

```bash
cd backend
alembic upgrade head
alembic current
```

不要在生产依赖 `create_all` 代替版本化迁移。备份应覆盖 PostgreSQL 数据与部署时使用的配置。

## 访问保护

```dotenv
WANDERMIND_ACCESS_USERNAME=wandermind
WANDERMIND_ACCESS_PASSWORD=<generate-a-long-random-value>
```

密码非空时，应用使用常量时间比较验证 Basic Auth。`/health` 保持公开，便于托管平台探活；API、文档、指标和静态 UI 均受保护。Basic Auth 必须只通过 HTTPS 使用，它不是多用户账户、租户隔离或细粒度授权系统。

## Runtime

主 Wander 在生成 Candidate 时至少使用一次配置的 Runtime；达到质量阈值且剩余预算不少于两次时，再分别执行 Evidence 与 Critic。`max_runtime_calls=3` 可覆盖一轮完整的综合、证据和批判；交互前端默认使用 6 次预算，以便首个候选未通过时继续尝试。

### Mock

默认 Mock 返回满足 JSON Schema 的确定性结果，适合开发、CI、离线 Demo 和故障注入。

### Codex App Server

```dotenv
WANDERMIND_RUNTIME_ADAPTER=codex
WANDERMIND_CODEX_EXECUTABLE=codex
WANDERMIND_RUNTIME_CWD=/absolute/readable/path
```

适配器使用 `initialize`、`thread/start`、`thread/resume`、`turn/start`、`turn/interrupt`、`thread/archive`。默认策略：

- `approvalPolicy=never`
- `sandbox=read-only`
- `networkAccess=false`
- 每个 Explorer/Evidence/Critic 使用独立线程
- 所有输出必须通过 JSON Schema 与 Pydantic

`workspace-write` 在 Adapter 构造时默认关闭，即使 RuntimeTask 请求写权限也会被拒绝。

### OpenAI-compatible / Agnes

Render Blueprint 的线上实例使用此 Adapter 和 Agnes 模型，不应标记为 Codex。`POST /wander` 返回的 `runtime.provider` 与 `runtime.model` 是实际调用证据。

```dotenv
WANDERMIND_RUNTIME_ADAPTER=openai
WANDERMIND_LLM_BASE_URL=https://apihub.agnes-ai.com/v1
WANDERMIND_LLM_API_KEY=<secret>
WANDERMIND_LLM_MODEL=agnes-2.5-flash
WANDERMIND_LLM_TEMPERATURE=0.2
WANDERMIND_LLM_MAX_OUTPUT_TOKENS=2000
```

该适配器调用 `/chat/completions`，优先请求 JSON mode；供应商明确拒绝 `response_format` 时会自动移除该字段重试一次。输出仍须通过本地 JSON Schema 和 Pydantic 校验。401/403/404 不重试，429/5xx 可按 `WANDERMIND_RUNTIME_MAX_RETRIES` 重试；单次请求使用 `WANDERMIND_RUNTIME_TIMEOUT_SECONDS`。

Evidence 只能返回 Context 中已有的非空 `source_ref`。出现未知引用、缺少引用或对抗性伪造引用时，服务端会清空支持/反证文本与引用，并把不确定性提高到至少 0.8。

API key 不会写入 Runtime Session、usage 或日志。生产环境应使用平台 Secret；不要把真实值写入 `.env.example`、Compose 文件或 `render.yaml`。

## 阈值

降低 `WONDER_THRESHOLD` 会提高命中率，也会提高明显、随机和重复内容比例。`SCORE_WEIGHTS` 必须提供 `ScoreWeights` 的全部字段，未知字段和越界值会在启动时失败。任何阈值、权重、算子或 Prompt 变化必须运行 `scripts/run_benchmark.py`，不得只凭主观感觉调整。

## Scheduler

计划任务只在单进程部署中安全。多副本部署必须确保只有一个 scheduler leader，否则会重复孵化。V0.1 没有分布式锁。

## 限制

`EMBEDDING_DIMENSIONS` 与迁移中的 pgvector 维度必须一致。若修改维度，需要新迁移并重建向量；不能只改环境变量。
