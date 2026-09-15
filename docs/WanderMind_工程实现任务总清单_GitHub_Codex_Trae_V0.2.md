# WanderMind 工程实现任务总清单（GitHub / Codex / Trae 执行版）V0.2

> 用途：指导 Codex、Trae、Claude Code 等 Coding Agent 按顺序完成 WanderMind 的完整工程实现  
> 目标：通过“任务拆解 + 强制测试 + 阶段 Gate + 回归验证”形成一个完整、自洽、高完成度、可交付的软件  
> 项目：WanderMind  
> 核心引擎：Wander Engine  
> 关联文档：
>
> - `WanderMind_需求文档_V0.1.md`
> - `WanderMind_详细设计文档_V0.1.md`
>
> 正式仓库：`https://github.com/xxiaoxiong/WanderMind.git`
> 更新时间：2026-09-13

---


# 0.1 项目唯一代码仓库

WanderMind 的正式代码仓库固定为：

```text
https://github.com/xxiaoxiong/WanderMind.git
```

Repository：

```text
xxiaoxiong/WanderMind
```

所有 Codex / Trae / Claude Code 开发任务都必须围绕该仓库执行。

首次获取：

```bash
git clone https://github.com/xxiaoxiong/WanderMind.git
cd WanderMind
```

如果本地已经存在仓库：

```bash
git status
git remote -v
git fetch origin
git checkout main
git pull --ff-only origin main
```

严禁 Coding Agent：

- 在其他临时目录重新创建一套“WanderMind”并把它当正式项目；
- 删除 `.git`；
- 擅自修改远程仓库地址；
- `git push --force` 到 `main`；
- 覆盖用户未提交的本地修改；
- 在工作区存在不明改动时直接批量重写项目。

如果检测到未提交修改：

```bash
git status
```

Coding Agent 必须先识别这些修改是否属于当前任务，不能擅自丢弃。

---

# 0.2 Git 分支与 Task 映射

原则：

> **一个 Task ID 对应一个可追踪开发单元。**

推荐分支：

```text
task/T0.1-repository-baseline
task/T4.4-distance-band-retrieval
task/T7.4-local-wander
task/T9.3-codex-runtime
task/T14.3-benchmark-runner
```

统一格式：

```text
task/<task-id>-<short-description>
```

Bug：

```text
fix/<task-id>-<short-description>
```

文档：

```text
docs/<short-description>
```

实验：

```text
experiment/<short-description>
```

Coding Agent 开始 Task 前建议执行：

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b task/<TASK-ID>-<description>
```

如果用户明确要求直接在当前分支工作，则以用户要求为准。

---

# 0.3 Commit 规范

每个 Task 可以包含多个小 Commit，但必须保证最终提交历史可理解。

推荐 Conventional Commits：

```text
feat(T7.4): implement local wander traversal
test(T7.4): add deterministic local wander tests
fix(T7.4): prevent repeated node traversal
docs(T7.4): document local wander behavior
refactor(T9.3): isolate Codex runtime adapter
```

Task 完成前至少应存在与实现和测试相对应的变更记录。

禁止：

```text
update
fix
done
final
123
```

这种无法理解的 Commit Message。

---

# 0.4 GitHub PR / CI Gate

即使项目主要由个人开发，高风险模块仍推荐走 PR，以获得清晰 Diff 和 CI 验证。

强烈建议 PR 的阶段：

```text
Phase 4  Retrieval
Phase 5  Association
Phase 6  Cognitive Operators
Phase 7  Wander Engine
Phase 8  Wonder Scoring
Phase 9  Codex Runtime
Phase 10 Critic
Phase 11 Incubation
Phase 14 Evaluation
Phase 15 Hardening
```

PR 标题：

```text
[T7.4] Implement local wander
```

PR Body 至少包含：

```markdown
## Task
T7.4 Local Wander

## What Changed
- ...

## Tests
- ...

## Test Result
- ...

## Acceptance Criteria
- [x] ...

## Risks / Limitations
- ...
```

PR 合并条件：

```text
Implementation complete
+
Task tests PASS
+
Full required regression PASS
+
Lint PASS
+
Type check PASS
+
CI PASS
+
Acceptance Criteria PASS
```

---

# 0.5 GitHub 是任务状态的事实源

仓库内必须长期维护：

```text
TASKS.md
TEST_REPORTS.md
CHANGELOG.md
DECISIONS.md
```

其中：

### `TASKS.md`

保存本文件中的 Master Checklist 与当前实际状态。

例如：

```markdown
- [x] T4.3 Nearest Retrieval
- [ ] T4.4 Distance Band Retrieval
```

Coding Agent 不允许仅在聊天里声称“完成”。

必须更新仓库中的：

```text
TASKS.md
```

### `TEST_REPORTS.md`

每个 Task 记录：

```text
Task ID
date
tests executed
pass/fail
coverage
manual checks
known limitations
```

### `DECISIONS.md`

任何偏离详细设计的重大决策必须记录，例如：

```text
为什么更换数据库
为什么修改 Runtime Adapter
为什么改变 WonderScore
为什么修改 Patch 策略
```

### `CHANGELOG.md`

只记录对使用者或整体工程有意义的版本变化，不把每个微小 Commit 重复进去。

---

# 0.6 Codex / Trae 每次工作的 GitHub 操作顺序

推荐固定流程：

```text
1. cd WanderMind
2. git status
3. git remote -v
4. git fetch origin
5. 确认 main 最新
6. 读取 TASKS.md
7. 选择一个 Task ID
8. 创建 Task Branch
9. 实现
10. 测试
11. 更新 TASKS.md
12. 更新 TEST_REPORTS.md
13. git diff 自检
14. commit
15. push branch
16. CI
17. 必要时创建 PR
18. Gate PASS 后合并
19. 删除已完成 Task branch（可选）
20. 开始下一 Task
```

任何一步发现：

```text
conflict
unknown local modification
failing historical tests
unexpected architecture drift
```

必须先处理，不能继续堆代码。

---

# 0.7 Coding Agent 的仓库自检要求

每次新会话进入项目时，先执行仓库侦察，而不是假设项目仍处于上一次状态。

至少检查：

```bash
git status
git branch --show-current
git log -5 --oneline
```

并阅读：

```text
README.md
TASKS.md
DECISIONS.md
最近相关代码
最近相关测试
```

原因：

> Codex / Trae 的任务上下文可能是一次性的，而 Git 仓库才是跨会话持续存在的工程记忆。

因此：

```text
Conversation Context ≠ Project Truth
Git Repository = Project Truth
```

---

# 0.8 多个 Coding Agent 并行时的约束

如果未来同时使用 Codex + Trae：

不要让两个 Agent 同时修改相同核心模块。

适合并行：

```text
Agent A → Backend Domain
Agent B → Frontend
```

或：

```text
Agent A → Task T13.2 Metrics
Agent B → Task T16.5 Configuration Docs
```

不适合并行：

```text
Agent A → T7.4 Local Wander
Agent B → T7.6 Patch Switching
```

当后者强依赖前者时应串行。

并行开发必须：

```text
不同 branch
+
明确文件所有权
+
合并前完整 regression
```

---


# 0. 使用方式

这不是参考 Roadmap，而应直接作为项目的 **Master Implementation Checklist**。

Coding Agent 必须按如下闭环执行：

```text
读取当前 Task
→ 检查前置任务
→ 输出本任务实现计划
→ 编码
→ 补测试
→ 执行测试
→ 修复失败
→ 执行回归
→ 更新任务状态
→ 输出完成报告
→ 才允许进入下一 Task
```

禁止一次性跳过多个阶段“把整个项目写完”。

---

# 1. Coding Agent 总执行规则

## 1.1 一次只执行一个 Task ID

例如：

```text
当前只执行 T7.4
```

除非该 Task 明确要求修改依赖模块，否则不要提前实现后续 Task。

## 1.2 每个任务必须输出完成报告

```markdown
## Task Completion Report

Task ID:
Task Name:

### Changed Files
- ...

### Implemented
- ...

### Tests Added
- ...

### Tests Executed
- ...

### Result
- PASS / FAIL

### Coverage
- ...

### Acceptance Criteria
- [x] ...

### Known Limitations
- ...

### Follow-up
- ...
```

## 1.3 测试属于任务本身

```text
Implementation Done ≠ Task Done
```

只有：

```text
Implementation
+ Automated Tests
+ Acceptance Check
+ Documentation Update
```

全部完成后才允许勾选。

## 1.4 阶段结束必须执行 Phase Gate

Phase Gate 要求：

- 本阶段所有 Task 完成；
- 新增测试全部通过；
- 历史测试全部回归通过；
- lint / type-check 通过；
- 无新增高严重级错误；
- 文档同步；
- 存在可运行 Demo 或验证脚本。

任何一项失败，不进入下一阶段。

---

# 2. 全局 Definition of Done

任意 Task 完成前必须确认：

- [ ] 功能按设计实现
- [ ] 输入校验完成
- [ ] 异常路径处理完成
- [ ] 单元测试完成
- [ ] 必要集成测试完成
- [ ] 历史测试无回归
- [ ] 类型检查通过
- [ ] Lint 通过
- [ ] 关键日志存在
- [ ] 配置没有硬编码
- [ ] 无 Secret 写入仓库
- [ ] 关键行为有文档说明
- [ ] Acceptance Criteria 全部满足

---

# 3. 工程质量基线

## Backend

至少配置：

```text
pytest
pytest-asyncio
coverage
ruff
mypy 或 pyright
```

目标：

```text
Domain / Cognitive Core 覆盖率 >= 85%
整体 Backend 覆盖率 >= 75%
```

## Frontend

至少配置：

```text
TypeScript strict
unit/component tests
Playwright E2E
lint
```

## API

至少覆盖：

```text
happy path
invalid input
not found
conflict
runtime failure
timeout
unsafe input / permission boundary
```

---

# 4. 总体实施路径

```text
Phase 0   工程基线
Phase 1   Domain Model
Phase 2   Database / Repository
Phase 3   Knowledge Ingestion
Phase 4   Embedding / Retrieval
Phase 5   Patch / Association / Idea Graph
Phase 6   Cognitive Operators
Phase 7   Wander Engine Core
Phase 8   Candidate / Wonder Scoring
Phase 9   Codex Runtime Integration
Phase 10  Explore / Evidence / Critic
Phase 11  Incubation / Re-wonder
Phase 12  API / UI
Phase 13  Observability / Security
Phase 14  Evaluation / Regression
Phase 15  End-to-End Hardening
Phase 16  Release / Delivery
```

---

# PHASE 0 —— 工程初始化与质量护栏

目标：建立一个从第一天就可测试、可持续演进的工程骨架。

## T0.1 检查并建立正式仓库工程结构

正式仓库：

```text
https://github.com/xxiaoxiong/WanderMind.git
```

先检查仓库当前内容，在现有项目基础上增量建设；**不要重新 `git init`，不要另建同名正式项目**。

- [ ] 确认 `origin` 指向 `xxiaoxiong/WanderMind`
- [ ] 确认默认开发基线分支
- [ ] 保存现有文件，不无理由覆盖
- [ ] 建立/补齐 `backend/`
- [ ] `frontend/`
- [ ] `docs/`
- [ ] `scripts/`
- [ ] `tests/`
- [ ] `.env.example`
- [ ] `README.md`
- [ ] `CHANGELOG.md`
- [ ] `DECISIONS.md`
- [ ] `TASKS.md`
- [ ] `TEST_REPORTS.md`

### 测试
- [ ] Backend 空应用可启动
- [ ] Frontend 空应用可启动
- [ ] 空测试套件可执行

### 验收
- [ ] 新环境按照 README 可以复现启动

## T0.2 Backend 基础工程

- [ ] FastAPI Application Factory
- [ ] `/health`
- [ ] 配置系统
- [ ] 结构化日志
- [ ] 全局异常处理
- [ ] 环境区分：dev/test/prod

### 测试
- [ ] `/health` 200
- [ ] 缺失必要配置时给出明确错误
- [ ] Test App 可隔离启动

## T0.3 代码质量工具

- [ ] formatter
- [ ] lint
- [ ] type check
- [ ] coverage
- [ ] pre-commit
- [ ] CI

CI 至少执行：

```text
backend test
frontend test
lint
type check
build
```

### 验收
- [ ] 故意制造错误时 CI 会失败
- [ ] 修复后 CI 全绿

## T0.4 测试基础设施

- [ ] pytest fixtures
- [ ] async fixtures
- [ ] test database
- [ ] MockRuntime
- [ ] MockEmbedding
- [ ] deterministic random seed

核心测试不能依赖外网、真实 Codex 或生产 DB。

## Phase 0 Gate

- [ ] 项目可启动
- [ ] CI 可运行
- [ ] 测试骨架可用
- [ ] README 可复现
- [ ] 全部检查 PASS

---

# PHASE 1 —— Domain Model

目标：先定义 WanderMind 世界里存在什么对象。

## T1.1 KnowledgeItem

字段至少覆盖：

```text
id/type/title/content/summary
source/source_ref/topics/entities
importance/confidence/status
created_at/updated_at/event_time
metadata
```

### 测试
- [ ] 合法 type
- [ ] 非法 type
- [ ] confidence 边界
- [ ] status 校验
- [ ] serialization

## T1.2 KnowledgeEdge

关系至少支持：

```text
similar_to
contradicts
causes
derived_from
analogy_of
inspired_by
evidence_for
evidence_against
combines_with
abstracts
instantiates
questions
evolves_from
```

### 测试
- [ ] source/target
- [ ] self-loop 策略
- [ ] relation type
- [ ] weight/confidence 边界

## T1.3 Seed

来源：

```text
explicit
recent
unresolved
weak_idea
random_revival
```

字段至少：

```text
content/source/priority/status/created_at/last_used_at
```

## T1.4 Candidate

包含：

```text
candidate_type
statement
explanation
seed_id
source_items
operator
wander_path
scores
status
```

## T1.5 Wonder

类型：

```text
spark/question/connection/hypothesis/insight
```

包含：

```text
why_interesting
supporting_evidence
counter_evidence
assumptions
scores
confidence
status
parent_wonder_id
```

## T1.6 WanderSession / WanderTrace

Session：

```text
seed/state/budget/status/started_at/ended_at
```

Trace：

```text
states/patches/steps/operators/candidates/final_wonders
```

### Phase 1 Gate

- [ ] Domain 不依赖 FastAPI
- [ ] Domain 不依赖 Codex
- [ ] Domain 不依赖具体 ORM
- [ ] Domain 覆盖率 >= 90%
- [ ] 全部测试 PASS

---

# PHASE 2 —— Database / Repository

## T2.1 PostgreSQL Schema

创建：

```text
knowledge_items
knowledge_edges
seeds
wander_sessions
wander_steps
candidates
wonders
feedback
runtime_sessions
```

### 测试
- [ ] migration up
- [ ] migration down
- [ ] fresh DB init
- [ ] schema version

## T2.2 Repository Interfaces

定义：

```text
KnowledgeRepository
GraphRepository
SeedRepository
WonderRepository
SessionRepository
FeedbackRepository
```

必须有 InMemory 版本用于测试。

## T2.3 PostgreSQL Repository

每个 Repository 至少测试：

- [ ] create
- [ ] get
- [ ] update
- [ ] delete
- [ ] list
- [ ] pagination
- [ ] transaction rollback

## T2.4 JSONB Metadata

- [ ] arbitrary metadata 保存
- [ ] schema 不被破坏
- [ ] 常用 metadata 可查询

## Phase 2 Gate

- [ ] Repository contract test PASS
- [ ] PostgreSQL integration test PASS
- [ ] Migration test PASS

---

# PHASE 3 —— Knowledge Ingestion

## T3.1 Text Ingestion

支持：

```text
plain text
note
question
idea
```

流程：

```text
validate
→ normalize
→ summarize
→ extract topic/entity
→ persist
```

### 测试
- [ ] 短文本
- [ ] 长文本
- [ ] 空文本
- [ ] 中文/Unicode
- [ ] duplicate

## T3.2 DocumentLoader 抽象

不要求第一版支持所有格式，但必须存在统一接口。

### 测试
- [ ] mock document
- [ ] parse error
- [ ] partial content

## T3.3 Deduplication

实现：

```text
exact hash
normalized hash
semantic duplicate
```

### 测试
- [ ] 完全相同
- [ ] 轻微改写
- [ ] 不相关

## T3.4 Topic / Entity Extraction

结构化输出：

```json
{"topics":[],"entities":[]}
```

必须用固定 Mock 输出测试 parser。

## T3.5 Ingestion Integration

输入 50~100 条模拟知识：

```text
ingest → persist → searchable
```

## Phase 3 Gate

- [ ] 100 条知识稳定导入
- [ ] Dedup 生效
- [ ] 数据完整性 PASS

---

# PHASE 4 —— Embedding / Retrieval / Semantic Distance

## T4.1 EmbeddingAdapter

```text
embed_text
embed_batch
```

实现：

```text
MockEmbeddingAdapter
RealEmbeddingAdapter
```

### 测试
- [ ] deterministic mock
- [ ] batch
- [ ] empty input
- [ ] dimension validation

## T4.2 pgvector 集成

- [ ] vector column
- [ ] index
- [ ] similarity query

构造已知向量验证排序。

## T4.3 Nearest Retrieval

实现基础 Top-K，并用人工向量测试顺序。

## T4.4 Distance Band Retrieval

实现：

```text
near
moderate
remote
very_remote
```

优先依据候选集合分位区间，而不是固定 magic number。

### 测试
构造 100 个已知距离样本，验证 band 正确。

## T4.5 Controlled Remote Retrieval

必须同时具备：

```text
relevance floor
distance ceiling
```

确保：

- 太近被排除
- 适度远能进入
- 完全随机被排除

## T4.6 Historical Novelty Check

检查 Candidate 与：

```text
Knowledge
Candidate
Wonder
```

的历史相似度。

### 测试
- [ ] 原句
- [ ] 改写
- [ ] 真正新 Idea

## Phase 4 Gate

制作 CLI/测试页：

```text
输入 Seed
→ 输出 near / moderate / remote
```

人工检查至少 20 个 Seed，并记录结果。

---

# PHASE 5 —— Patch / Association / Idea Graph

## T5.1 Patch Model

支持：

```text
topic
cluster
project
domain
temporal
```

## T5.2 Patch Builder

第一版：

```text
topic grouping
+ embedding clustering
```

### 测试
使用 Agent / OS / Biology / Finance 多主题样本。

## T5.3 Patch Membership

一个 Item 可以属于多个 Patch。

## T5.4 Association Engine

第一批：

```text
semantic
contradiction
analogy_candidate
causal_candidate
temporal
shared_pattern
```

## T5.5 Idea Graph

支持：

```text
create edge
query neighbors
query lineage
query evidence
query contradiction
```

构造：

```text
Seed → Connection → Hypothesis → Evidence → Insight
```

并验证完整路径。

## Phase 5 Gate

任意 Item 均能：

- [ ] 查看 Patch
- [ ] 查看邻居
- [ ] 查看远距离候选
- [ ] 查看 Idea lineage

---

# PHASE 6 —— Cognitive Operators

原则：

> Operator 必须独立、结构化、可测试。

## T6.1 Operator Base Interface

```text
name
input_schema
output_schema
apply()
```

### 测试
- [ ] fake operator
- [ ] validation
- [ ] timeout
- [ ] malformed output

## T6.2 Analogy Operator

输出：

```text
source
target
shared_structure
mapping
break_points
possible_insight
```

必须包含 `where analogy breaks`。

## T6.3 Conceptual Blend

输出：

```text
input_a
input_b
generic_structure
blended_structure
emergent_properties
```

## T6.4 Counterfactual

输出：

```text
assumption
counterfactual
consequences
new_questions
```

## T6.5 Inversion

- [ ] 实现
- [ ] schema test
- [ ] golden case

## T6.6 Abstraction

- [ ] 实现
- [ ] schema test
- [ ] golden case

## T6.7 Second-order Consequence

- [ ] 实现
- [ ] 因果链测试

## T6.8 Operator Selector

规则起点：

```text
远距离两概念 → Analogy / Blend
强默认假设 → Counterfactual / Inversion
重复结构 → Abstraction
因果链 → Second-order
```

准备至少 20 个固定 case。

## T6.9 Operator Regression Set

创建：

```text
tests/fixtures/operators/
```

Prompt / Model 修改后必须回归。

## Phase 6 Gate

至少 5 个 Operator：

- [ ] 独立运行
- [ ] structured output
- [ ] regression test
- [ ] failure fallback

---

# PHASE 7 —— Wander Engine Core

这是第一个核心里程碑。

## T7.1 Cognitive State Machine

状态：

```text
IDLE
SEEDING
WANDER
COLLISION
GENERATE
SCORE
EXPLORE
CRITIQUE
PERSIST
SURFACE
STOPPED
FAILED
```

测试所有合法/非法转换。

## T7.2 WanderBudget

```text
max_steps
max_patch_switches
max_candidates
max_runtime_calls
time_budget
```

每个限制必须有触发测试。

## T7.3 Seed Selector

优先级：

```text
explicit
recent
unresolved
weak_idea
random_revival
```

## T7.4 Local Wander

在当前 Patch 内移动，并记录：

```text
distance
novelty_gain
relevance
reason
```

## T7.5 Marginal Novelty Gain

第一版结合：

```text
new_node_ratio
candidate_uniqueness
semantic_difference
```

构造“越来越重复”的测试数据，确认 novelty 下降。

## T7.6 Patch Switching

触发：

```text
low novelty
high repetition
patch exhausted
manual strategy
```

必须测试：

```text
Patch A → Patch B
```

## T7.7 Controlled Remote Jump

支持：

```text
moderate
remote
cross-domain
```

禁止直接 random item。

## T7.8 Collision Detection

输出：

```text
collision_score
bridge_explanation
recommended_operator
```

## T7.9 Candidate Generation

Collision + Operator → 1~N Candidate。

## T7.10 Stop Conditions

覆盖：

```text
budget exhausted
no novelty
candidate convergence
high-value found
too much repetition
manual stop
```

## T7.11 Wander Trace

任意 Session 可以重放结构化路径。

## T7.12 Deterministic Simulation Mode

实现：

```text
fixed random seed
mock LLM
mock embedding
```

保证完整 Wander 可稳定回放。

## Phase 7 Gate

准备 100~500 条测试知识，运行 20 个 Seeds。

要求：

- [ ] 无死循环
- [ ] Budget 生效
- [ ] 至少发生 Patch Switch
- [ ] 能产生 Candidate
- [ ] Trace 完整
- [ ] 不依赖 Codex
- [ ] Cognitive Core 覆盖率 >= 85%

> 如果这一阶段完全产生不了有意义 Candidate，不要继续做复杂 UI / Codex 集成，先修 Wander Algorithm。

---

# PHASE 8 —— Candidate / Wonder Scoring

## T8.1 Cheap Scorer

至少：

```text
novelty
relevance
coherence
non_triviality
redundancy
distance_quality
```

## T8.2 Surprise Scorer

必须区分：

```text
obvious
interesting surprise
random nonsense
```

测试期望：

```text
interesting > obvious
interesting > random
```

## T8.3 Generativity Scorer

评估 Idea 是否还能产生：

```text
new questions
predictions
implications
research directions
```

## T8.4 Personal Relevance

第一版仅使用：

```text
topic overlap
recent interest
explicit feedback
```

禁止做无依据人格推断。

## T8.5 WonderScore

权重必须配置化。

## T8.6 Threshold Policy

输出：

```text
reject
keep_candidate
deep_explore
surface
```

## T8.7 Historical Dedup

与历史 Wonder 高相似时 penalty 或 reject。

## T8.8 Score Explanation

每个 score 都保存：

```text
value
reason
```

## Phase 8 Gate

建立 `wonder_eval_v1`：

```text
20 obvious
20 interesting
20 random
20 duplicate
```

要求：

- [ ] interesting 平均分高于 obvious/random
- [ ] duplicate 可识别
- [ ] 保存 regression baseline



# PHASE 9 —— Codex Runtime Integration

目标：

> 让高潜力 Candidate 获得真实的搜索、读取、执行、验证能力，同时保持 WanderMind 不被具体 Runtime 锁死。

## T9.1 AgentRuntimeAdapter

定义稳定接口，例如：

```text
start_session
resume_session
run_task
stream_task
interrupt
close_session
```

### 测试
- [ ] fake implementation
- [ ] 生命周期
- [ ] timeout
- [ ] exception mapping

## T9.2 MockRuntimeAdapter

必须覆盖：

- [ ] success
- [ ] failure
- [ ] timeout
- [ ] malformed structured output
- [ ] interrupted

绝大部分业务测试优先使用 Mock Runtime。

## T9.3 CodexRuntimeAdapter

实现：

```text
session/thread start
turn execution
resume
stream
interrupt
structured output
```

> 具体 SDK/API 使用方式以执行该 Task 时 OpenAI 官方最新文档为准，不把不稳定内部协议泄漏到 Cognitive Core。

## T9.4 Runtime Session Persistence

记录：

```text
local_session_id
runtime_provider
runtime_thread_id
created_at
last_used_at
status
```

## T9.5 Sandbox Policy

默认：

```text
read-only
```

只有明确实验任务才允许：

```text
workspace-write
```

### 测试
- [ ] 默认权限正确
- [ ] 提权需要显式策略
- [ ] 非允许任务不得写工作区

## T9.6 Timeout / Retry

定义：

```text
timeout
retryable_error
non_retryable_error
max_retry
backoff
```

### 测试
- [ ] timeout
- [ ] retry success
- [ ] max retry exhausted
- [ ] non-retryable 不重试

## T9.7 Structured Output Validation

所有 Runtime 结果经过 schema validation。

失败时：

```text
retry once
or
mark failed
```

禁止静默接受 malformed output。

## T9.8 Real Codex Smoke Test

真实环境至少跑通：

```text
Candidate
→ Codex research
→ structured result
```

结果记录进：

```text
TEST_REPORTS.md
```

## Phase 9 Gate

- [ ] Runtime Mock 全测试 PASS
- [ ] 真实 Codex smoke PASS
- [ ] Codex 故障不会拖垮 Wander Engine
- [ ] Cognitive Core 不直接依赖 Codex SDK
- [ ] Runtime 可替换性验证 PASS

---

# PHASE 10 —— Explore / Evidence / Critic

目标：

> 把“看起来有意思”的 Candidate 变成更可信、更有解释力的 Wonder。

## T10.1 Explorer Service

输入：

```text
Candidate
```

输出：

```text
expanded_idea
implications
follow_up_questions
possible_support
possible_failure_modes
```

## T10.2 Evidence Service

输出：

```text
supporting_evidence
counter_evidence
source_refs
uncertainty
```

测试要求：

- [ ] 有证据
- [ ] 无证据
- [ ] 支持和反例同时存在
- [ ] source 缺失时不能伪造

## T10.3 Independent Critic

使用独立 Context / Thread。

输出：

```text
weakness
obviousness
over_analogy
factual_risk
alternative_explanation
verdict
```

## T10.4 Anti-Anchoring

Critic 尽量不看 Explorer 的完整生成上下文，只看：

```text
Candidate
Evidence
必要背景
```

### 测试
- [ ] Critic 能否决 Explorer 极度乐观结论
- [ ] Critic 不默认同意 Candidate

## T10.5 Over-analogy Detection

Analogy Candidate 必须回答：

```text
where mapping fails
```

## T10.6 Hallucination Risk

没有可验证 Evidence：

```text
confidence 不允许高
```

## T10.7 Candidate → Wonder Promotion

必须满足：

```text
final score threshold
+
critic pass
```

才晋升为 Wonder。

### 测试
- [ ] good candidate promoted
- [ ] random candidate rejected
- [ ] unsupported candidate 降低 confidence
- [ ] critic reject 后不 surface

## Phase 10 Gate

准备至少 20 个固定 Candidate，人工复核：

- [ ] Explorer 是否增加真实价值
- [ ] Evidence 是否可追溯
- [ ] Critic 是否真能淘汰垃圾 Idea
- [ ] Promotion 规则符合预期

---

# PHASE 11 —— Incubation / Re-Wonder

目标：

> 实现 WanderMind 最具差异化的长期思想孵化机制。

## T11.1 Incubation Scheduler

支持：

```text
manual trigger
scheduled trigger
```

第一版不需要复杂分布式调度。

## T11.2 Incubation Sampler

采样：

```text
recent knowledge
old knowledge
weak ideas
unresolved questions
random revival
```

必须可配置样本数量。

## T11.3 Cross-time Pairing

优先：

```text
new × old
old × old-never-connected
weak idea × new knowledge
unresolved question × new knowledge
```

而不是始终：

```text
recent × recent
```

## T11.4 Weak Idea Store

低分但未被否决的 Idea：

```text
status = incubating
```

## T11.5 Re-Wonder Trigger

触发来源：

```text
new related knowledge
time elapsed
user request
manual admin/test trigger
```

## T11.6 Re-Wonder Lineage

必须保留：

```text
Wonder v1
→ Wonder v2
→ Wonder v3
```

禁止覆盖历史版本。

## T11.7 Silent Run

Incubation 合法结果：

```text
0 Wonder
```

测试必须覆盖。

## Phase 11 Gate

构造：

```text
Day 1
Day 30
Day 90
```

三阶段模拟数据。

要求：

- [ ] 旧 Idea 可以被新知识激活
- [ ] lineage 保留
- [ ] 无价值运行可以保持 silent
- [ ] 不重复轰炸用户

---

# PHASE 12 —— API / Frontend

目标：

> 建立完整可操作的产品闭环。

## T12.1 Seed API

```text
POST /api/v1/seeds
GET  /api/v1/seeds
GET  /api/v1/seeds/{id}
```

覆盖成功和错误状态码。

## T12.2 Knowledge API

至少：

```text
POST /api/v1/knowledge
GET  /api/v1/knowledge/{id}
GET  /api/v1/knowledge/search
DELETE /api/v1/knowledge/{id}
```

## T12.3 Wander API

```text
POST /api/v1/wander
GET  /api/v1/wander/{session_id}
POST /api/v1/wander/{session_id}/stop
```

## T12.4 Streaming

允许前端看到：

```text
current state
current patch
patch switch
candidate count
status
```

禁止把模型私有 Chain-of-Thought 直接暴露给 UI。

仅展示结构化、可解释执行事件。

## T12.5 Wonder API

至少：

```text
GET /api/v1/wonders
GET /api/v1/wonders/{id}
POST /api/v1/wonders/{id}/explore
POST /api/v1/wonders/{id}/rewonder
```

## T12.6 Feedback API

支持：

```text
interesting
very_interesting
obvious
already_knew
too_random
wrong
irrelevant
continue_explore
save_for_later
inspired_new_idea
```

## T12.7 Inbox UI

核心输入：

```text
Drop a thought...
```

支持：

- [ ] text
- [ ] question
- [ ] idea
- [ ] note

## T12.8 Wander View

展示：

```text
Seed
current state
patch transitions
association
candidate count
```

不追求炫酷知识图谱。

## T12.9 Wonders View

每条 Wonder 至少：

```text
title
core statement
why interesting
score/confidence summary
Why?
Continue
Save
Not interesting
```

## T12.10 Wonder Detail

展示：

```text
core idea
why interesting
wander path
evidence
counter evidence
assumptions
confidence
follow-up questions
```

## T12.11 Frontend Component Tests

覆盖核心组件。

## T12.12 E2E

必须自动跑通：

```text
输入 Seed
→ Wander
→ Candidate
→ Explore
→ Wonder
→ Feedback
```

## Phase 12 Gate

新用户只根据 README 能：

```text
启动
输入 Seed
运行 Wander
看到 Wonder
提交 Feedback
```

---

# PHASE 13 —— Observability / Security / Reliability

目标：

> 让系统不仅能跑，还能知道“为什么跑坏了”。

## T13.1 Structured Logging

所有关键日志包含：

```text
session_id
seed_id
task_id
runtime_session_id
```

## T13.2 Metrics

至少：

```text
wander_duration
step_count
patch_switches
candidate_count
runtime_calls
runtime_failures
score_distribution
wonder_count
```

## T13.3 Runtime Cost Tracking

记录可获得的：

```text
calls
tokens/usage
duration
provider
```

## T13.4 Error Taxonomy

至少：

```text
validation
database
embedding
runtime
timeout
operator
evaluation
internal
```

## T13.5 Secret Management

- [ ] `.env` ignored
- [ ] repo secret scan
- [ ] logs 不打印 secret
- [ ] sample config 不含真实 token

## T13.6 Input Safety

覆盖：

- [ ] 超大输入
- [ ] 文件路径注入
- [ ] shell injection 风险
- [ ] runtime 越权
- [ ] 恶意 metadata

## T13.7 Data Deletion

测试删除：

```text
Knowledge
Wonder
Session
Feedback
```

并明确级联策略。

## T13.8 Backup / Restore

提供：

```text
backup script
restore script
documentation
```

## Phase 13 Gate

故障演练：

```text
Codex timeout
Database unavailable
Embedding failure
Malformed LLM response
```

要求系统可控失败，并保留足够诊断信息。

---

# PHASE 14 —— Evaluation / Regression System

目标：

> 防止 WanderMind “越改越能说，但越不会产生真正有价值的 Wonder”。

## T14.1 Golden Dataset

准备：

```text
100~500 KnowledgeItems
```

至少包含多个领域。

## T14.2 Known Connection Set

人工标注：

```text
obvious
interesting
nonsense
duplicate
```

## T14.3 Wonder Benchmark Runner

一次运行保存：

```text
seed
wander path
patches
candidates
scores
final wonders
```

## T14.4 Baseline V1

至少记录：

```text
Wonder Hit proxy
High-value proxy
Obvious Rate
Randomness Rate
Redundancy Rate
Cross-domain Yield
Runtime cost
```

## T14.5 Regression Threshold

定义不能明显恶化的指标，例如：

```text
Randomness Rate
Duplicate Rate
High-value proxy
```

## T14.6 Human Evaluation

人工评分：

```text
0 = useless
1 = obvious
2 = mildly interesting
3 = interesting
4 = surprising and useful
5 = genuinely insightful
```

## T14.7 Prompt / Model / Algorithm Change Gate

以下任一变化必须跑 benchmark：

```text
Prompt
Operator
Embedding
Model
Retrieval
Score weights
Patch strategy
Critic
```

## Phase 14 Gate

生成：

```text
docs/evaluation/evaluation_report_v0.1.md
```

禁止只写：

> “感觉效果不错。”

---

# PHASE 15 —— End-to-End Hardening

目标：

> 找出跨模块集成断点。

## T15.1 Explicit Seed E2E

```text
Seed
→ Wander
→ Wonder
→ Feedback
```

## T15.2 Recent Seed E2E

自动从近期知识挑 Seed。

## T15.3 Weak Idea Revival E2E

旧弱 Idea 被重新激活。

## T15.4 Incubation E2E

后台孵化输出 0 或 1 条高价值 Wonder。

## T15.5 Re-Wonder E2E

旧 Wonder 在新知识下产生新版本。

## T15.6 Runtime Failure E2E

Codex timeout 时：

```text
Candidate 保留
Explore 标记失败
不得伪造 Evidence
Session 可恢复
```

## T15.7 Database Restart

数据库重启后：

- [ ] 已完成数据不丢
- [ ] Session 状态可恢复/明确失败
- [ ] 没有 silent corruption

## T15.8 1,000 KnowledgeItems Test

验证：

```text
retrieval
patch
wander
graph
score
```

仍能合理运行。

## T15.9 100 Wander Sessions Test

检查：

```text
memory leak
duplicate explosion
session leak
runtime leak
unbounded table growth
```

## T15.10 Performance Smoke

记录：

```text
p50
p95
slowest stage
```

第一版不要求极限性能，但必须知道瓶颈。

## T15.11 UX Acceptance

人工真实使用至少 10 次 Seed。

记录：

```text
哪些步骤令人困惑
哪些 Wonder 无聊
哪些 Feedback 不够用
```

## Phase 15 Gate

- [ ] backend PASS
- [ ] frontend PASS
- [ ] integration PASS
- [ ] E2E PASS
- [ ] benchmark PASS
- [ ] security checks PASS
- [ ] manual acceptance 完成

---

# PHASE 16 —— Release / Delivery

目标：

> 最终拿到一个可安装、可演示、可测试、可继续开发的软件，而不是“开发者电脑上的代码”。

## T16.1 README

必须包含：

```text
What is WanderMind
Architecture
Requirements
Install
Configure
Run
Test
Evaluate
Troubleshooting
```

## T16.2 一键启动

至少提供一种：

```text
docker compose
```

或清晰的一键本地启动脚本。

## T16.3 Demo Dataset

提供小型可公开 Demo 数据。

## T16.4 Demo Workflow

README 可复现：

```text
导入 demo knowledge
→ create seed
→ run wander
→ view wonder
→ feedback
```

## T16.5 Configuration Docs

说明：

```text
database
embedding
reasoning model
Codex runtime
sandbox
scheduler
limits
```

## T16.6 Architecture Sync

最终代码必须与：

```text
详细设计
README
ADR
```

一致。

若偏离：

```text
修改实现
or
记录 ADR
```

禁止静默架构漂移。

## T16.7 Final Test Report

生成：

```text
docs/release/v0.1_test_report.md
```

记录：

```text
environment
test suites
pass/fail
coverage
benchmark
performance
known issues
```

## T16.8 Known Limitations

明确列出当前版本不能做什么。

## T16.9 Release Checklist

- [ ] version
- [ ] changelog
- [ ] clean repo
- [ ] no secrets
- [ ] tests all pass
- [ ] build works
- [ ] fresh install works
- [ ] demo works
- [ ] docs works
- [ ] release tag

---

# 5. 单任务标准提示词模板

每次把一个 Task 交给 Codex / Trae 时，建议使用：

```markdown
# Task <ID> — <Name>

## Goal
只完成本任务定义目标。

## Read First
- WanderMind_需求文档_V0.1.md
- WanderMind_详细设计文档_V0.1.md
- TASKS.md
- 与本 Task 直接相关代码和测试

## Constraints
1. 不提前实现后续 Task。
2. 不修改无关模块。
3. 不删除已有测试来让 CI 通过。
4. 不弱化类型检查。
5. 不用 hardcode 绕过设计。
6. 失败路径必须处理。
7. 测试属于任务本身。
8. 如果实际实现需要偏离设计，先在 DECISIONS.md 写明原因。

## Before Coding
先输出：
- 当前理解
- 影响模块
- 实现步骤
- 测试计划

## Implementation
- [ ] ...

## Tests

### Unit
- [ ] ...

### Integration
- [ ] ...

### Regression
- [ ] 现有测试全部通过

## Acceptance Criteria
- [ ] ...

## Required Output
完成后输出 Task Completion Report。
```

---

# 6. Agent 开始每个 Task 前必须执行

1. 读取 `TASKS.md`
2. 确认前置 Task 已完成
3. 阅读直接相关设计文档
4. 阅读相关代码
5. 阅读相关测试
6. 检查是否已有类似实现
7. 输出简短实现计划
8. 再开始编码

禁止：

> 未读现有实现就进行大规模重写。

---

# 7. Agent 完成每个 Task 后固定执行顺序

除测试外，必须把结果落回 GitHub 工程状态。



```text
1. formatter
2. lint
3. type check
4. affected unit tests
5. integration tests
6. full regression（阶段 Gate 或高风险模块）
7. coverage
8. update TASKS.md
9. update TEST_REPORTS.md
10. git diff / git status 自检
11. commit 当前 Task
12. push 当前 Task branch
13. 等待/检查 CI Gate（若仓库已配置）
14. 必要时创建/更新 PR
15. output completion report
```

---

# 8. 必须人工 Review 的模块

即使自动测试通过，也建议人工评审：

```text
T4.x  Semantic Distance
T5.x  Association
T6.x  Cognitive Operators
T7.x  Wander Engine
T8.x  Wonder Scoring
T10.x Critic
T11.x Incubation
T14.x Evaluation
```

因为：

> “代码正确”不等于“认知结果有价值”。

---

# 9. Coding Agent 禁止事项

## 9.1 禁止偷换需求

任务要求：

```text
Distance Band Retrieval
```

不能只实现普通 Top-K 然后宣称完成。

## 9.2 禁止通过修改测试预期掩盖 Bug

测试修改必须在完成报告中解释。

## 9.3 禁止用 Mock 冒充真实集成完成

例如 Codex Runtime：

```text
Mock Test
+
至少一次 Real Smoke Test
```

两者都需要。

## 9.4 禁止把认知系统退化成一个大 Prompt

不接受：

```text
“请自由发散，然后自己研究、自己批判、输出最好结果。”
```

必须保持：

```text
Wander
→ Association
→ Operator
→ Candidate
→ Score
→ Explore
→ Critic
→ Wonder
```

各阶段可观察、可测试、可替换。

## 9.5 禁止过早引入复杂基础设施

没有当前任务需求时，不引入：

```text
Kafka
Kubernetes
Neo4j
复杂微服务
大规模 Agent Swarm
```

## 9.6 禁止为了“每次有结果”降低质量阈值

合法结果允许：

```text
0 Wonder
```

---

# 10. 测试金字塔

```text
                 ┌─────────┐
                 │   E2E   │
                 │ 少量关键 │
                 └────┬────┘
                ┌─────▼─────┐
                │Integration│
                └─────┬─────┘
          ┌───────────▼───────────┐
          │      Unit Tests       │
          │      大量、快速        │
          └───────────────────────┘
```

不要主要依赖 E2E 才发现核心逻辑错误。

---

# 11. Cognitive 模块特殊测试策略

认知模块禁止只写：

```text
assert result is not None
```

至少需要：

## 11.1 Schema Test

结构正确。

## 11.2 Invariant Test

例如：

```text
Randomness 很高时，不应同时获得极高 Coherence。
```

## 11.3 Golden Case

固定经典样本用于回归。

## 11.4 Human Evaluation

人工回答：

> 这个结果到底有没有意思？

传统自动测试不能替代它。

---

# 12. 最终验收场景

## Scenario A —— 显式脑洞

输入：

```text
Agent Harness 会不会越来越像操作系统？
```

期望发生：

```text
Seed
→ OS Patch
→ 其他 Patch
→ Operator
→ Candidate
→ Research
→ Critic
→ Wonder
```

## Scenario B —— 跨时间孵化

历史：

```text
3 个月前：组织设计
1 个月前：Agent Scheduler
今天：Agent Governance
```

系统应有机会形成：

```text
组织治理 × Agent Governance
```

相关 Wonder。

不要求固定文本。

## Scenario C —— 垃圾联想过滤

内部产生：

```text
Agent ↔ Banana
```

若不存在真实 bridge，应被 Randomness / Coherence 过滤。

## Scenario D —— 过度类比

Candidate：

```text
企业完全等于操作系统
```

Critic 必须指出 mapping break。

## Scenario E —— 没有好结果

合法输出：

```text
0 Wonder surfaced
```

## Scenario F —— Codex 故障

Codex timeout：

```text
Candidate 保留
Explore failed
Evidence 不伪造
Session 可恢复
```

---

# 13. 里程碑策略

## Milestone 1 —— Knowledge Substrate

```text
Phase 0 ~ 4
```

得到：

> 可存储、可检索、可计算语义距离的知识底座。

## Milestone 2 —— Wander Core

```text
Phase 5 ~ 7
```

得到：

> 第一版真正会 Wander 的 Cognitive Engine。

这是最重要检查点。

如果这时无法产生有意义 Candidate：

> 不继续堆 UI / Runtime / Incubation，优先修核心算法。

## Milestone 3 —— Interestingness

```text
Phase 8
```

得到：

> 第一版区分“有趣”和“随机”的筛选系统。

## Milestone 4 —— Deep Exploration

```text
Phase 9 ~ 10
```

得到：

> Candidate 可以被 Codex 深入研究、验证和批判。

## Milestone 5 —— Long-term Mind

```text
Phase 11
```

得到：

> WanderMind 开始具备长期孵化。

## Milestone 6 —— Productized V0.1

```text
Phase 12 ~ 16
```

得到：

> 完整、可用、可评估、可回归、可交付的软件。

---

# 14. 项目完成判定

## 工程完成

- [ ] 所有 Phase Gate PASS
- [ ] 全套自动测试 PASS
- [ ] Fresh Install PASS
- [ ] Demo PASS

## 架构完成

- [ ] Cognitive Core 独立于 Codex
- [ ] Runtime 可替换
- [ ] Memory / Graph / Wander / Score 边界清楚
- [ ] 关键架构决策已记录

## 质量完成

- [ ] Benchmark 可重复
- [ ] Regression 可运行
- [ ] Trace 可解释
- [ ] 故障可恢复
- [ ] 不依赖隐式手工步骤

## 产品命题完成

在真实知识集上，系统能够至少偶尔产生用户认为：

> **“这个角度我以前确实没想到，而且值得继续探索。”**

的 Wonder。

---

# 15. 最重要的项目优先级

始终保持：

```text
Wonder Quality
>
Explainability
>
Evaluation
>
Reliability
>
UI polish
>
Scale
```

不要反过来。

---

# 16. Master Checklist

## Phase 0
- [ ] T0.1 项目仓库结构
- [ ] T0.2 Backend 基础
- [ ] T0.3 代码质量工具
- [ ] T0.4 测试基础设施
- [ ] Phase 0 Gate

## Phase 1
- [ ] T1.1 KnowledgeItem
- [ ] T1.2 KnowledgeEdge
- [ ] T1.3 Seed
- [ ] T1.4 Candidate
- [ ] T1.5 Wonder
- [ ] T1.6 WanderSession / Trace
- [ ] Phase 1 Gate

## Phase 2
- [ ] T2.1 PostgreSQL Schema
- [ ] T2.2 Repository Interfaces
- [ ] T2.3 PostgreSQL Repositories
- [ ] T2.4 JSONB Metadata
- [ ] Phase 2 Gate

## Phase 3
- [ ] T3.1 Text Ingestion
- [ ] T3.2 DocumentLoader
- [ ] T3.3 Deduplication
- [ ] T3.4 Topic / Entity Extraction
- [ ] T3.5 Ingestion Integration
- [ ] Phase 3 Gate

## Phase 4
- [ ] T4.1 EmbeddingAdapter
- [ ] T4.2 pgvector
- [ ] T4.3 Nearest Retrieval
- [ ] T4.4 Distance Band
- [ ] T4.5 Controlled Remote Retrieval
- [ ] T4.6 Historical Novelty
- [ ] Phase 4 Gate

## Phase 5
- [ ] T5.1 Patch Model
- [ ] T5.2 Patch Builder
- [ ] T5.3 Patch Membership
- [ ] T5.4 Association Engine
- [ ] T5.5 Idea Graph
- [ ] Phase 5 Gate

## Phase 6
- [ ] T6.1 Operator Interface
- [ ] T6.2 Analogy
- [ ] T6.3 Conceptual Blend
- [ ] T6.4 Counterfactual
- [ ] T6.5 Inversion
- [ ] T6.6 Abstraction
- [ ] T6.7 Second-order
- [ ] T6.8 Operator Selector
- [ ] T6.9 Operator Regression
- [ ] Phase 6 Gate

## Phase 7
- [ ] T7.1 Cognitive State Machine
- [ ] T7.2 WanderBudget
- [ ] T7.3 Seed Selector
- [ ] T7.4 Local Wander
- [ ] T7.5 Marginal Novelty
- [ ] T7.6 Patch Switching
- [ ] T7.7 Remote Jump
- [ ] T7.8 Collision Detection
- [ ] T7.9 Candidate Generation
- [ ] T7.10 Stop Conditions
- [ ] T7.11 Wander Trace
- [ ] T7.12 Deterministic Simulation
- [ ] Phase 7 Gate

## Phase 8
- [ ] T8.1 Cheap Scorer
- [ ] T8.2 Surprise
- [ ] T8.3 Generativity
- [ ] T8.4 Personal Relevance
- [ ] T8.5 WonderScore
- [ ] T8.6 Threshold Policy
- [ ] T8.7 Historical Dedup
- [ ] T8.8 Score Explanation
- [ ] Phase 8 Gate

## Phase 9
- [ ] T9.1 RuntimeAdapter
- [ ] T9.2 Mock Runtime
- [ ] T9.3 Codex Runtime
- [ ] T9.4 Runtime Persistence
- [ ] T9.5 Sandbox Policy
- [ ] T9.6 Retry / Timeout
- [ ] T9.7 Structured Output
- [ ] T9.8 Real Smoke Test
- [ ] Phase 9 Gate

## Phase 10
- [ ] T10.1 Explorer
- [ ] T10.2 Evidence
- [ ] T10.3 Critic
- [ ] T10.4 Anti-Anchoring
- [ ] T10.5 Over-analogy
- [ ] T10.6 Hallucination Risk
- [ ] T10.7 Promotion
- [ ] Phase 10 Gate

## Phase 11
- [ ] T11.1 Scheduler
- [ ] T11.2 Sampler
- [ ] T11.3 Cross-time Pairing
- [ ] T11.4 Weak Idea Store
- [ ] T11.5 Re-Wonder Trigger
- [ ] T11.6 Lineage
- [ ] T11.7 Silent Run
- [ ] Phase 11 Gate

## Phase 12
- [ ] T12.1 Seed API
- [ ] T12.2 Knowledge API
- [ ] T12.3 Wander API
- [ ] T12.4 Streaming
- [ ] T12.5 Wonder API
- [ ] T12.6 Feedback API
- [ ] T12.7 Inbox
- [ ] T12.8 Wander View
- [ ] T12.9 Wonders View
- [ ] T12.10 Wonder Detail
- [ ] T12.11 Component Tests
- [ ] T12.12 E2E
- [ ] Phase 12 Gate

## Phase 13
- [ ] T13.1 Logging
- [ ] T13.2 Metrics
- [ ] T13.3 Cost Tracking
- [ ] T13.4 Error Taxonomy
- [ ] T13.5 Secret Management
- [ ] T13.6 Input Safety
- [ ] T13.7 Data Deletion
- [ ] T13.8 Backup / Restore
- [ ] Phase 13 Gate

## Phase 14
- [ ] T14.1 Golden Dataset
- [ ] T14.2 Known Connections
- [ ] T14.3 Benchmark Runner
- [ ] T14.4 Baseline V1
- [ ] T14.5 Regression Threshold
- [ ] T14.6 Human Evaluation
- [ ] T14.7 Prompt / Model Change Gate
- [ ] Phase 14 Gate

## Phase 15
- [ ] T15.1 Explicit Seed E2E
- [ ] T15.2 Recent Seed E2E
- [ ] T15.3 Weak Idea Revival
- [ ] T15.4 Incubation E2E
- [ ] T15.5 Re-Wonder E2E
- [ ] T15.6 Runtime Failure
- [ ] T15.7 DB Restart
- [ ] T15.8 1,000 Items
- [ ] T15.9 100 Sessions
- [ ] T15.10 Performance Smoke
- [ ] T15.11 UX Acceptance
- [ ] Phase 15 Gate

## Phase 16
- [ ] T16.1 README
- [ ] T16.2 一键启动
- [ ] T16.3 Demo Dataset
- [ ] T16.4 Demo Workflow
- [ ] T16.5 Configuration Docs
- [ ] T16.6 Architecture Sync
- [ ] T16.7 Final Test Report
- [ ] T16.8 Known Limitations
- [ ] T16.9 Release Checklist
- [ ] WanderMind V0.1 RELEASED

---

# 17. 给 Codex / Trae 的最终总指令

> **不要试图一次把 WanderMind 写完。严格按照 Task 依赖逐个构建，每完成一个模块，都必须用自动测试、集成测试、回归测试和必要的人工认知评估证明它真的工作，再进入下一模块。最终交付的不只是“能运行”的代码，而是一套可解释、可评估、可回归、可替换 Runtime、可长期迭代的 Wander Engine。**


---

# 18. 仓库级最终交付标准

WanderMind V0.1 只有在正式 GitHub 仓库：

```text
https://github.com/xxiaoxiong/WanderMind.git
```

满足以下条件时，才视为真正完成：

- [ ] `main` 为可运行状态
- [ ] `TASKS.md` 状态真实
- [ ] 所有阶段 Gate 有测试记录
- [ ] CI 为绿色
- [ ] README 从零可复现
- [ ] Demo 可复现
- [ ] 没有只存在于某个 Agent 本地工作区、却未提交到 GitHub 的核心代码
- [ ] 没有只存在于聊天上下文、却未落到文档/代码的重大架构决策
- [ ] Release/Test Report 已进入仓库
- [ ] 已创建 V0.1 对应 Tag/Release（发布阶段）

最终原则：

> **GitHub 仓库中的代码、测试、文档和任务状态才是 WanderMind 的真实交付物。**

> **Agent 的聊天回答不是交付；通过测试并进入 `xxiaoxiong/WanderMind` 的可追踪变更才是交付。**
