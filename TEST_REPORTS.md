# WanderMind V0.1 测试总览

日期：2026-10-07

## Windows 本机长期运行验收

| Gate | 结果 | 证据 |
|---|---|---|
| Backend format/lint/type | PASS | 本次改动文件 Ruff 与 Mypy strict 全部通过 |
| Backend full suite | PASS | Pytest 91/91，coverage 80.92% |
| Frontend | PASS | ESLint、Vitest 12/12、TypeScript、Vite production build |
| Compose production stack | PASS | PostgreSQL/Backend/Frontend 三容器全部 healthy，仅绑定 `127.0.0.1` |
| Schema drift recovery | PASS | 旧持久卷发现并修复 `runtime_sessions.last_used_at` 漂移；Alembic `20260930_0004`；`alembic check` 无差异 |
| Long-seed regression | PASS | 近 2 万字符 Seed 可完整启动；Trace reason 截断到 2000 字符并保留 SHA-256 指纹，不再触发 `ValidationError` |
| Evidence provenance | PASS | 自动假设、拒绝知识与污染快照不能作为证据；每个晋级结果至少引用 2 个独立原始来源 |
| Runtime revision rescore | PASS | Reviewer 修订结论后重新评分，旧文本与旧分数保留审计但不能用于晋级 |
| Real Agnes cycle | PASS | 真实轮次运行 148 秒、24 Trace steps、2 Candidates、4 Runtime calls；高风险结果被 reject/revise，未强行生成 Wonder |
| Historical data quarantine | PASS | 10 条乱码 Render 快照与 11 条递归派生 Autopilot 知识无损隔离；Quality Gate v2 活跃自动知识归零 |
| Cognitive benchmark | PASS | 12 cases 回归门通过；hit 100%、high-value 50%、obvious/random 0%、Runtime 36 次 |
| Scale canary | PASS | 1000 items × 10 sessions，10/10 完成，p95 5.791 s，峰值 203.53 MB |
| Crash recovery | PASS | Backend 进程强制终止后自动恢复；Campaign、当前 Session 与 120 条知识保持一致，恢复后 Runtime Session 4→5、Trace 21→24 |
| Host watchdog | PASS | Docker Desktop 改用官方 CLI 启动，跨过原约 6 分钟退出窗口；Frontend 异常仍由主机 Guardian 修复 |
| Backup archive | PASS | 数据修复前生成 38,081,509-byte custom dump，可完整恢复 Knowledge 与 Autopilot Campaign |
| Windows persistence | PASS | 登录启动项、5 分钟 Guardian、6 小时备份任务已安装；交流睡眠与休眠超时均为 0 |

Render 重复 Campaign 已暂停，避免与本机主实例竞争同一 Agnes 配额。本机 `.env` 保持 Git 忽略，Secret 扫描在临时移出本机配置后通过。

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
| Render live positive suite | PASS | 中/英文 3/3 产出 Wonder；29.19–39.82 秒；均为 `openai-compatible` / `agnes-2.5-flash` 且 Runtime verified |
| Render live negative control | PASS | 荒诞 Seed 生成 0 Wonder，2 个候选均命中 arbitrariness guard；Runtime 轨迹完整 |
| Hosted browser acceptance | PASS | 无登录框、中文无替换字符、洞见详情可打开；评分字段契约回归测试禁止 `NaN` |

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
