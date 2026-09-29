# V0.1 实现状态

此文件把原始总清单映射到当前代码证据；原始需求与设计文档保持不改。

| Phase | 状态 | 主要证据 |
|---|---|---|
| 0 工程基线 | 完成 | pyproject、pnpm lock、编辑器配置、pre-commit、CI |
| 1 领域模型 | 完成 | `models/*` 与 domain tests |
| 2 数据层 | 完成 | ORM、Repository Protocol、Memory/SQL、Alembic、重启测试 |
| 3 知识导入 | 完成 | 规范化、摘要、主题/实体、去重、上传与 API |
| 4 Embedding/Retrieval | 完成 | Adapter、距离带、近邻与受控远距检索 |
| 5 Patch/Graph | 完成 | 五类 Patch、多归属、质心一致性、邻居/血缘/证据/矛盾查询 |
| 6 Cognitive Operators | 完成 | 六算子、schema、break points、selector tests |
| 7 Wander Engine | 完成 | 状态机、预算、移动、碰撞、候选、停止、Trace |
| 8 Scoring | 完成 | 多维评分、三类惩罚、sweet spot、阈值与解释 |
| 9 Runtime | 完成 | 主漫游候选综合/统一独立审查均接入 Adapter；Mock/Codex/OpenAI-compatible；会话与成本持久化 |
| 10 Explorer/Evidence/Critic | 完成 | 独立会话、无引用不造证据、失败默认 reject |
| 11 Incubation/Re-Wonder | 完成 | Scheduler、Autopilot 持久循环、老/新配对、质量回灌、Recent Seed、血缘 |
| 12 API/UI | 完成 | REST、SSE、统一错误、Autopilot 控制台、组件测试、E2E |
| 13 安全/可观测性 | 完成 | 深层输入校验、递归脱敏、Basic Auth、细粒度 metrics、级联删除、备份恢复 |
| 14 评估/回归 | 完成 | 120 条数据、12 known cases、baseline、runner、人评模板 |
| 15 E2E/Hardening | 完成（人工 UX 待产品验收） | 重启、runtime failure、1000×100、p50/p95、Playwright |
| 16 Release/Delivery | 完成（Git tag 待仓库所有者） | Docker Compose、统一线上镜像、Render Blueprint、README、报告 |

## 质量门

- Backend：Ruff、Mypy strict、Pytest、coverage ≥75%。
- Frontend：TypeScript strict、ESLint、Vitest、Vite production build、Playwright。
- Cognitive：known-connection regression gate。
- Scale：1000 KnowledgeItems × 100 Wander Sessions。
- Security：秘密扫描、请求限制、Runtime sandbox。
- Delivery：Compose config/build 与健康检查。

## 2026-09-18 Runtime 整改验收

- [x] 主 `POST /wander` 流程真实调用 `candidate_synthesis`，高分候选继续调用单次 `candidate_review` 完成证据与批判，不再用本地状态跳转伪装 Runtime 阶段。
- [x] 候选对去重，不再生成镜像重复组合；单个任意性、幻觉或低新颖度候选只淘汰自身，不再提前终止整轮搜索。
- [x] 响应返回脱敏 Runtime 摘要（Provider、模型、调用/失败数、耗时、token、用途），前端直接展示验证状态。
- [x] 没有 Wonder 时展示最高分 Candidate、解释、分数与完成原因；预算/搜索空间耗尽属于正常 `completed`。
- [x] `backend/scripts/run_live_codex_smoke.py` 真实连接本机 Codex App Server，验证 JSON Schema 输出并在 `finally` 中关闭线程与进程。
- [x] 本机真实 Codex 冒烟通过：`codex-app-server`、schema valid、119.449 秒。
- [x] 本机真实 Codex 主流程通过：`candidate_synthesis -> candidate_review` 2/2 调用完成，严格 JSON Schema 有效，Runtime verified，268.968 秒。
- [x] 主流程每个完整候选由 3 次 Runtime 降为 2 次；前端默认最多 4 次调用，可完整尝试两个候选，并显示等待秒数。
- [x] Review 辅助晋级仍受 redundancy / arbitrariness / hallucination guard 约束；12-case 回归中明显、随机、重复错误呈现率均为 0。
- [x] Runtime 可覆盖 Hash Embedding 的弱关联假阴性，并把低风险 `revise` 修订为带不确定性的可验证假设；荒诞 Seed、重复、幻觉风险与 reject 仍禁止呈现。
- [x] Render 线上连续真实任务验收：3/3 正向任务产出 Wonder，1/1 荒诞任务被拦截；29.19–39.82 秒，均 `runtime.verified=true`，Provider/模型为 `openai-compatible` / `agnes-2.5-flash`。

## 需要仓库所有者完成

- 完成至少 10 次真实 Seed 的人工 UX 验收并填写人评表。
- 配置 GitHub branch protection，通过 CI 后创建 `v0.1.0` tag/release。
- 长期线上使用前升级持久数据库、配置定期备份并轮换初始访问密码。

## 2026-09-29 持续探索验收

- [x] Campaign、当前 Session、累计 Candidate/Wonder/Runtime、失败退避和下一轮时间持久化。
- [x] 有限深度 Wander 自动串联，重启后恢复活动 Session，单轮失败不会终止长期目标。
- [x] 达标 Wonder 回灌为 `insight` 并写入 `derived_from` 血缘，后续轮次优先混合新旧知识。
- [x] `/autopilot` 控制台展示实时检查点、累计指标和最新高质量结果，并支持暂停、继续、停止。
- [x] Render Blueprint 启用 Autopilot、关闭旧 Scheduler、延长优雅关闭；GitHub Actions 每 10 分钟探测主管。
- [ ] 免费 PostgreSQL 到期前升级为长期持久计划并启用备份；免费资源无法提供无人值守 SLA。
