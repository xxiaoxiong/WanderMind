# Architecture Decision Records

## ADR-001 — Python 通过 Codex App Server 集成

**状态：Accepted，2026-09-14**

原详细设计提出 `openai-codex Python SDK`，但当前官方 Codex SDK 主要面向 TypeScript。WanderMind 后端必须保持 Python，因此选择 `codex app-server --stdio` 的 JSON-RPC 协议，并把它封装在 `AgentRuntimeAdapter` 后。

结果：

- Cognitive Core 不依赖 Codex。
- 非 TypeScript 客户端可使用同一 thread/turn 生命周期。
- 协议变更集中在一个 Adapter，并由本地生成的 App Server schema 与测试校验。
- 默认 read-only / no-network / never-approval。

## ADR-002 — V0.1 使用确定性 Hash Embedding

**状态：Accepted**

默认 Embedding 不调用网络服务，确保测试、CI、Demo 与 benchmark 可复现。Repository 与 EmbeddingAdapter 均为接口，后续可替换本地模型或托管 Embedding。Hash Embedding 只用于 V0.1 验证认知流水线，不代表生产语义质量上限。

## ADR-003 — PostgreSQL/pgvector 为生产数据面，SQLite 为降级实现

**状态：Accepted**

PostgreSQL 保存实体、Trace 与反馈，pgvector 支持语义检索。SQLite 使用 JSON 向量，服务本地开发与契约测试。所有访问经 Repository Protocol，避免认知核心绑定 SQLAlchemy。

## ADR-004 — 短任务同步执行，SSE 回放结构化 Trace

**状态：Accepted for V0.1**

`POST /wander` 当前同步完成预算化任务；SSE endpoint 可重放结构化步骤。优点是确定性、简单恢复和低运维成本；代价是不能提供真正的运行中事件。长任务与多副本版本应引入持久队列和事件总线。

## ADR-005 — 静默优先于弱输出

**状态：Accepted**

Engine 总是保存 Candidate、Score、Trace 和 stop reason，但只有达到阈值且风险可接受才创建 Wonder。Incubation 每次最多呈现一个结果；失败 Evidence 不会变成表面可信的“证据”。

## ADR-006 — 检索与历史去重使用混合信号

**状态：Accepted**

Hash Embedding 的确定性优先于语义上限，因此 Retrieval 叠加标题/主题词法锚点；历史冗余同时考虑文本相似度与来源重合。直接复述、任意拼接和无依据强因果使用硬风险门，不依赖单一总分掩盖风险。

## ADR-007 — Patch 是多维且允许多归属

**状态：Accepted**

Patch 同时来自 domain、project、topic、temporal 和 embedding cluster。一个 KnowledgeItem 可属于多个 Patch；Engine 选择最大高一致性 Patch 作为移动主分区，同时保留完整多归属计数与可解释元数据。

## ADR-008 — Runtime 调用必须可追踪

**状态：Accepted**

所有 RuntimeAdapter 由 TrackedRuntimeAdapter 包装。每个任务持久化 provider、purpose、external session、Wander 关联、状态、耗时、usage/cost 和失败信息，并以 Prometheus 指标与结构化日志暴露；删除 Wander 时仅解绑记录，不抹除审计轨迹。
