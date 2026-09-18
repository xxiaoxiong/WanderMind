# WanderMind V0.1 测试总览

日期：2026-09-18

## Runtime 主流程整改

| Gate | 结果 | 证据 |
|---|---|---|
| Backend full suite | PASS | Pytest 74/74，coverage 80.13% |
| Runtime main path | PASS | API 回归验证 `candidate_synthesis -> candidate_review`，单次主漫游 2/2 调用完成 |
| Early-stop regression | PASS | 低质量候选后继续尝试唯一知识对，测试至少生成 2 个候选 |
| Frontend | PASS | Vitest 8/8、ESLint、TypeScript、Vite production build |
| Cognitive benchmark | PASS | 12 cases；hit 100%、high-value 83.33%、明显/随机/重复错误呈现率 0%、Runtime 36 次 |
| Real Codex adapter smoke | PASS | `codex-app-server`，JSON Schema valid，119.449 秒；线程与进程在 finally 中关闭 |
| Real Codex Wander E2E | PASS | 主引擎真实完成 `candidate_synthesis` 与 `candidate_review` 2/2，Runtime verified，268.968 秒 |

Render 使用 `openai-compatible` Adapter 连接 Agnes APIHub；它不是 Codex。真实 Codex 能力由本机 Codex App Server 的 Adapter 与完整 Wander 两级测试独立验证，线上 Provider/模型以每次 Wander 响应中的 Runtime 摘要为准。

| Gate | 结果 | 证据 |
|---|---|---|
| Backend format/lint | PASS | Ruff 86 files |
| Backend type check | PASS | Mypy strict，79 source files |
| Backend tests | PASS | Pytest 60/60，coverage 80.39% |
| Cognitive coverage | PASS | line coverage 89.67%，门槛 85% |
| Frontend | PASS | ESLint、TypeScript、Vite build |
| Component tests | PASS | Vitest coverage task，5/5 |
| Browser E2E | PASS | Playwright Chromium 2/2 |
| Cognitive benchmark | PASS | 12 cases，全部回归阈值通过 |
| Scale smoke | PASS | 1000 items × 100 sessions，p95 0.5149 s，峰值 6.11 MB |
| Security | PASS | Secret scan、输入边界、递归日志脱敏测试 |
| Container/fresh DB | PASS | 三服务健康；Alembic 0002 up/down/up；旧 0001 卷无损升级 |
| Demo/restart | PASS | 120 条导入、Wonder 呈现、DB 重启后数据完整 |
| Backup/restore | PASS | pg_dump/pg_restore 临时库回放 120 条 |
| Unified online image | PASS | React + FastAPI 多阶段构建；静态 UI 200；匿名 401；授权 API/UI 200 |
| Hosted deployment config | PASS | Render Blueprint、托管 PostgreSQL URL 规范化、启动时 Alembic 迁移 |
| Public deployment | PASS | Render Web + PostgreSQL 创建成功；公网 health 200；匿名 UI 401 |
| GitHub Actions | PASS | `main` 首次推送后的远端 CI 全部成功 |

详细环境、命令、指标与发布边界见 `docs/release/v0.1_test_report.md`。人工 10 Seed UX 验收、branch protection 和 Git tag/release 仍需仓库所有者完成。
