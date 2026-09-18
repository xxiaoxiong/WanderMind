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
| 9 Runtime | 完成 | 主漫游候选综合/证据/批判均接入 Adapter；Mock/Codex/OpenAI-compatible；会话与成本持久化 |
| 10 Explorer/Evidence/Critic | 完成 | 独立会话、无引用不造证据、失败默认 reject |
| 11 Incubation/Re-Wonder | 完成 | Scheduler、老/新配对、静默、Recent Seed、血缘 |
| 12 API/UI | 完成 | REST、SSE、统一错误、四页 React UI、组件测试、E2E |
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

- [x] 主 `POST /wander` 流程真实调用 `candidate_synthesis`，高分候选继续调用 `evidence` 与 `critic`，不再用本地状态跳转伪装 Runtime 阶段。
- [x] 候选对去重，不再生成镜像重复组合；单个任意性、幻觉或低新颖度候选只淘汰自身，不再提前终止整轮搜索。
- [x] 响应返回脱敏 Runtime 摘要（Provider、模型、调用/失败数、耗时、token、用途），前端直接展示验证状态。
- [x] 没有 Wonder 时展示最高分 Candidate、解释、分数与完成原因；预算/搜索空间耗尽属于正常 `completed`。
- [x] `backend/scripts/run_live_codex_smoke.py` 真实连接本机 Codex App Server，验证 JSON Schema 输出并在 `finally` 中关闭线程与进程。
- [x] 本机真实 Codex 冒烟通过：`codex-app-server`、schema valid、119.168 秒。
- [ ] Render 线上连续真实任务验收（部署本次提交后执行并记录）。

## 需要仓库所有者完成

- 完成至少 10 次真实 Seed 的人工 UX 验收并填写人评表。
- 配置 GitHub branch protection，通过 CI 后创建 `v0.1.0` tag/release。
- 长期线上使用前升级持久数据库、配置定期备份并轮换初始访问密码。
