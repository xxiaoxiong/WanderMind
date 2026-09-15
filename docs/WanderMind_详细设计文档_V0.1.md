# WanderMind 详细设计文档（V0.1）

> 文档类型：系统详细设计 / Technical Design Document  
> 项目：WanderMind  
> 核心引擎：Wander Engine  
> 当前阶段：MVP / 核心命题验证  
> 更新时间：2026-09-13  
> 关联文档：`WanderMind_需求文档_V0.1.md`

---

# 0. 文档目标

本文档用于把《WanderMind 需求文档 V0.1》中定义的产品目标进一步落成一套可以实际开发的系统设计。

本阶段不追求一次性构建完整的“机器心智”。

第一版只围绕一个核心问题：

> **Can a Machine Wander—and Discover Wonders?**

即：

> 当系统拥有一批用户知识、历史想法和零散信息后，它能否在没有明确任务的情况下，通过思维漫游、跨域联想、问题生成、筛选和进一步探索，稳定产生少量值得用户继续思考的 Wonder？

---

# 1. 核心术语

为了后续设计统一，固定以下术语。

## 1.1 WanderMind

整个产品 / 系统名称。

---

## 1.2 Wander Engine

WanderMind 中负责：

- 思维种子选择；
- 语义漫游；
- 知识跳跃；
- 跨域连接；
- Cognitive Operator 调用；
- Candidate Idea 产生；
- Wonder Score 计算；
- Explore / Critic 决策；

的核心认知引擎。

---

## 1.3 Wandering

系统从一个 Seed 出发，在知识空间中进行低约束探索的过程。

Wandering 的目标不是立即回答问题，而是寻找：

- 意外联系；
- 潜在矛盾；
- 新问题；
- 新假设；
- 可迁移结构；
- 值得进一步研究的方向。

---

## 1.4 Wonder

经过筛选后，值得用户注意的高价值结果。

Wonder 可以是：

- Spark；
- Question；
- Connection；
- Hypothesis；
- Insight。

---

## 1.5 Seed

一次 Wandering 的起点。

可能来自：

- 用户输入的一句话；
- 一条笔记；
- 一个历史问题；
- 最近学习内容；
- 某个未解决 Idea；
- 某个知识节点；
- 系统自动发现的异常关系。

---

## 1.6 Cognitive Operator

对当前知识进行某一种“思维变换”的操作。

例如：

- Analogy；
- Conceptual Blend；
- Counterfactual；
- Inversion；
- Abstraction；
- Perspective Shift；
- Causal Expansion；
- Constraint Removal。

Operator 是 WanderMind 中比“多个角色 Agent”更核心的抽象。

---

# 2. 设计目标

V0.1 的系统设计必须满足以下目标。

## G1：核心认知逻辑独立于 Agent Runtime

不能形成：

```text
WanderMind = 一个很长的 Codex Prompt
```

应该是：

```text
WanderMind Cognitive Core
        ↓
RuntimeAdapter
        ↓
Codex / 其他 Agent Runtime
```

未来可以替换 Runtime，而不需要重写 Wander Engine。

---

## G2：允许“低约束思考”，但必须可控

系统必须允许：

```text
Seed
→ 漂移
→ 远距离联想
→ 跨领域跳跃
```

但不能退化成随机文本生成。

所以 Wandering 必须存在：

- exploration budget；
- semantic distance control；
- patch switching；
- redundancy detection；
- relevance floor；
- stop condition。

---

## G3：生成与评价解耦

不能让一个上下文同时承担：

```text
“大胆想”
+
“严格批判”
```

因为两者目标相互冲突。

系统设计上必须拆成：

```text
Divergent Generation
        ↓
Independent Evaluation
```

必要时使用不同 Thread / Context。

---

## G4：只向用户展示少量结果

内部可以生成：

```text
20 / 50 / 100 candidates
```

但最终可能只展示：

```text
1~3 Wonders
```

产品价值取决于 Signal-to-Noise Ratio，而不是生成数量。

---

## G5：所有 Wonder 都必须可追溯

每一个最终结果应该能够回答：

- 从哪个 Seed 出发？
- 使用了哪些知识？
- 经过了哪些 Operator？
- 哪一次跳跃产生了关键连接？
- 哪些证据支持？
- 哪些反例存在？
- 为什么最终被保留？

避免系统成为不可解释的“脑洞机”。

---

## G6：长期知识积累应该提高效果

随着用户持续使用，系统应逐渐拥有：

- 更多知识；
- 更多历史 Idea；
- 更准确的兴趣模型；
- 更清楚的“什么会让用户兴奋”；
- 更好的去重能力。

---

# 3. 非目标

V0.1 不解决：

- 通用 AGI；
- 自主科研闭环；
- 多用户企业权限；
- 大规模 Agent Swarm；
- 复杂知识图谱可视化；
- 自动执行商业决策；
- 24×7 无限自主运行；
- 完整笔记软件；
- 完整搜索引擎；
- 社交推荐；
- 自动发布内容；
- 自我修改核心代码。

---

# 4. 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                         WanderMind                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  UI / API                                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Seed Inbox │ Wonders │ Explore │ Memory │ Feedback   │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
├─────────────────────────────┼───────────────────────────────┤
│  Application Layer          │                               │
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Wander Service │ Explore Service │ Incubation Service │  │
│  │ Memory Service │ Feedback Service │ Evaluation Service│  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
├─────────────────────────────┼───────────────────────────────┤
│                      COGNITIVE CORE                         │
│                             │                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Seed Selector                                         │  │
│  │ Semantic Forager                                      │  │
│  │ Patch Manager                                         │  │
│  │ Association Engine                                    │  │
│  │ Cognitive Operator Engine                             │  │
│  │ Candidate Generator                                   │  │
│  │ Wonder Scorer                                         │  │
│  │ Critic / Novelty / Evidence Evaluator                 │  │
│  │ Cognitive State Controller                            │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
├─────────────────────────────┼───────────────────────────────┤
│  MEMORY / KNOWLEDGE         │                               │
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Semantic Memory │ Episodic Memory │ Idea Memory       │  │
│  │ Idea Graph      │ User Interest   │ Feedback History  │  │
│  │ Embeddings      │ Evidence Store  │ Wander Trace      │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
├─────────────────────────────┼───────────────────────────────┤
│  RUNTIME ABSTRACTION        │                               │
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ReasoningModelAdapter                                 │  │
│  │ AgentRuntimeAdapter                                   │  │
│  │ SearchAdapter │ FileAdapter │ ToolAdapter             │  │
│  └───────────────┬───────────────────────────────────────┘  │
│                  │                                          │
│           ┌──────▼────────┐                                 │
│           │ Codex Runtime │                                 │
│           │ Python SDK    │                                 │
│           └───────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

---

# 5. 一个重要的架构边界

WanderMind 自己负责：

```text
WHAT should be wondered about?
WHERE should the thought wander?
WHEN should it switch direction?
WHICH operator should be used?
IS the result interesting?
SHOULD it be researched further?
SHOULD the user be interrupted?
```

Codex Runtime 负责：

```text
Search
Read
Inspect
Execute
Verify
Compare
Analyze
Use tools
Use MCP
Run code
Produce structured research result
```

因此：

> **WanderMind 是 Cognitive Controller。Codex 是 Focused Agent Runtime。**

Codex 不能成为系统的总循环。

---

# 6. 系统核心状态机

一次 Wander Session 建议使用显式状态机，而不是靠 Prompt 自由运行。

```text
                  ┌─────────┐
                  │  IDLE   │
                  └────┬────┘
                       │ select seed
                       ▼
                  ┌─────────┐
                  │ SEEDING │
                  └────┬────┘
                       ▼
                  ┌─────────┐
        ┌────────▶│ WANDER  │◀────────┐
        │         └────┬────┘         │
        │              │              │
        │              ▼              │
        │         ┌──────────┐         │
        │         │ COLLISION│         │
        │         └────┬─────┘         │
        │              ▼               │
        │         ┌──────────┐          │
        │         │ GENERATE │          │
        │         └────┬─────┘          │
        │              ▼                │
        │         ┌──────────┐          │
        │         │  SCORE   │          │
        │         └─┬──────┬─┘          │
        │           │      │            │
        │ low score │      │ promising  │
        └───────────┘      ▼            │
                     ┌──────────┐        │
                     │ EXPLORE  │        │
                     └────┬─────┘        │
                          ▼              │
                     ┌──────────┐         │
                     │ CRITIQUE │         │
                     └────┬─────┘         │
                          ▼               │
                     ┌──────────┐          │
                     │  KEEP?   │          │
                     └─┬──────┬─┘          │
                       │      │             │
                   no  │      │ yes         │
                       │      ▼             │
                       │ ┌──────────┐        │
                       │ │ PERSIST  │        │
                       │ └────┬─────┘        │
                       │      ▼              │
                       │ ┌──────────┐         │
                       │ │ SURFACE  │         │
                       │ └──────────┘         │
                       │                     │
                       └─────────────────────┘
```

---

# 7. Cognitive State

状态不仅表示流程，还要记录“思维模式”。

建议核心状态：

```text
FOCUS
WANDER
EXPLORE
CRITIQUE
INCUBATE
```

---

## 7.1 FOCUS

高约束。

目标：

> 已经知道当前需要解决什么。

用于：

- 验证假设；
- 深入调研；
- 找证据；
- 编写实验；
- 调用 Codex。

---

## 7.2 WANDER

低约束。

目标：

> 不急着得到答案，允许在知识空间中移动。

特点：

- 可以跨 Topic；
- 可以跳到远距离节点；
- 鼓励非显然关系；
- 不要求立即正确。

---

## 7.3 EXPLORE

中等约束。

目标：

> 一个 Candidate 已经显示出价值，需要进一步理解。

---

## 7.4 CRITIQUE

高约束。

目标：

- 找漏洞；
- 查重复；
- 找反例；
- 检查事实；
- 检查是不是“语言上听起来高级，实际没内容”。

---

## 7.5 INCUBATE

后台状态。

目标：

- 弱 Idea 暂存；
- 旧 Idea 与新知识重新碰撞；
- 跨时间重组。

---

# 8. 一次完整 Wander Session

标准处理流程：

```text
1. Select Seed
       ↓
2. Build Seed Context
       ↓
3. Identify Knowledge Patch
       ↓
4. Local Wandering
       ↓
5. Detect Marginal Novelty Drop
       ↓
6. Switch Patch
       ↓
7. Remote Association
       ↓
8. Cognitive Operator
       ↓
9. Candidate Generation
       ↓
10. Cheap Scoring
       ↓
11. Top Candidates
       ↓
12. Codex Focused Exploration
       ↓
13. Independent Critic
       ↓
14. Final Wonder Score
       ↓
15. Persist
       ↓
16. Surface 0~3 Wonders
```

注意：

> 一次 Session 允许最终输出 0 个 Wonder。

这是非常重要的设计。

系统必须允许：

```text
“这次没想到什么值得打扰用户的。”
```

而不是每次强行输出。

---

# 9. Seed Selector

Seed Selector 负责回答：

> 这一次从什么开始想？

Seed 来源分为 5 类。

## 9.1 Explicit Seed

用户主动输入。

例如：

```text
“Agent 为什么一定需要任务？”
```

优先级最高。

---

## 9.2 Recent Seed

最近 24h / 7d 高活跃内容。

例如用户近期连续研究：

```text
Agent Harness
Runtime
Memory
Scheduler
```

---

## 9.3 Unresolved Seed

过去没有解决的问题。

例如：

```text
Question.status = unresolved
```

---

## 9.4 Weak Idea Seed

历史上评分一般，但没有被否决的 Idea。

未来可能因为新知识而升值。

---

## 9.5 Random Revival Seed

从历史知识中随机复活一个旧节点。

要求：

- 时间距离较远；
- 近期未被使用；
- 与当前知识存在至少一个潜在连接。

作用：

> 防止系统只围绕最近的话题打转。

---

# 10. Memory Model

WanderMind 不应该只有一个 Vector Store。

至少需要区分四种 Memory。

---

## 10.1 Semantic Memory

“我知道什么”。

例如：

```text
Concept
Fact
Theory
Document
Topic
Entity
```

---

## 10.2 Episodic Memory

“发生过什么”。

例如：

```text
2026-09-13
用户研究了 Wander Agent

2026-08-30
用户研究了 vLLM Scheduler
```

时间是重要信息。

---

## 10.3 Idea Memory

“我/系统想过什么”。

包括：

```text
Question
Hypothesis
Connection
Spark
Insight
RejectedIdea
```

---

## 10.4 Preference Memory

“什么东西对用户来说有意思”。

例如：

```text
user likes:
- system architecture
- cross-domain analogy
- deep causal explanation

user dislikes:
- generic brainstorming
- obvious conclusions
- empty philosophical language
```

Preference 主要来自用户反馈，而不是系统臆测。

---

# 11. 统一 KnowledgeItem 数据模型

建议第一版所有知识统一抽象为：

```text
KnowledgeItem
```

核心字段：

```yaml
id:
type:
  - note
  - concept
  - fact
  - document
  - question
  - hypothesis
  - idea
  - insight
  - evidence

title:
content:
summary:

source:
source_ref:

created_at:
updated_at:
event_time:

topics: []
entities: []

embedding:
importance:
confidence:

status:
  - active
  - archived
  - rejected
  - unresolved

metadata: {}
```

---

# 12. Idea Graph

不建议 V0.1 立即引入独立图数据库。

第一版可以用关系表表达 Graph。

核心：

```text
knowledge_items
knowledge_edges
```

Edge：

```yaml
id:
source_id:
target_id:

relation_type:
  - similar_to
  - contradicts
  - causes
  - derived_from
  - analogy_of
  - inspired_by
  - evidence_for
  - evidence_against
  - combines_with
  - abstracts
  - instantiates
  - questions
  - evolves_from

weight:
confidence:
created_by:
created_at:
metadata:
```

这样已经可以表达：

```text
Seed
  │ inspired_by
  ▼
Connection
  │ derives
  ▼
Hypothesis
  │ evidence_for
  ▼
Evidence
  │ evolves_from
  ▼
Insight
```

---

# 13. 为什么 V0.1 不直接用 Neo4j

原因：

第一阶段真正需要验证的是：

```text
Wander Quality
```

而不是：

```text
Graph Traversal Benchmark
```

PostgreSQL 已经足够承担：

- 基础数据；
- JSONB；
- Edge Table；
- 全文搜索；
- 向量索引；
- 用户反馈；
- Session；
- Trace。

如果未来出现：

- 超大规模多跳遍历；
- 图算法；
- 社区发现；
- path search；

再增加专门 Graph Store。

---

# 14. Semantic Forager

这是 Wander Engine 的核心组件。

职责：

> 决定思维如何在知识空间里移动。

---

# 15. Knowledge Patch

把知识空间划分成多个 Patch。

Patch 可以来自：

- Topic；
- Embedding Cluster；
- Project；
- Domain；
- 时间段；
- 用户标签；
- 系统聚类。

例如：

```text
Patch A
Agent Runtime

Patch B
Operating System

Patch C
Organization Theory

Patch D
Evolution

Patch E
Economics
```

---

# 16. Local Explore

系统首先在当前 Patch 内部漫游。

例如：

```text
Agent Harness
→ Runtime
→ Scheduler
→ Resource
→ Concurrency
```

记录每一步：

```yaml
node:
semantic_distance:
new_information:
novelty_gain:
relevance:
```

---

# 17. Patch Switching

不能无限在一个区域探索。

定义：

```text
marginal_novelty_gain
```

当连续 N 步：

```text
novelty_gain < threshold
```

则考虑：

```text
SWITCH PATCH
```

其他触发：

- 重复率过高；
- Candidate 全部相似；
- 当前 Patch 节点已充分覆盖；
- Curiosity Score 较低。

---

# 18. Remote Retrieval

传统 RAG：

```text
Top-K nearest neighbors
```

WanderMind 需要：

```text
Near
Mid-distance
Far-but-related
Contradictory
Temporal-distant
Cross-domain
Random-controlled
```

---

## 18.1 推荐的距离采样方式

不要直接固定：

```text
cosine similarity > 0.75
```

因为不同 embedding 模型尺度不同。

建议采用相对分位区间。

例如对 Seed 的候选集合：

```text
P0 ~ P10    = closest
P10 ~ P35   = near
P35 ~ P65   = moderate
P65 ~ P85   = remote
P85 ~ P100  = probably unrelated
```

Wander 优先从：

```text
moderate + remote
```

抽样。

---

## 18.2 Semantic Sweet Spot

理想区域：

```text
Value
 ▲
 │                 ╭─────╮
 │              ╭──╯     ╰──╮
 │           ╭──╯           ╰──╮
 │___________╯___________________╰____
           obvious             nonsense
                     Distance →
```

系统目标不是：

> 最大距离。

而是：

> **Non-obvious but explainable relationship。**

---

# 19. Association Engine

Association Engine 负责发现节点间潜在关系。

建议至少实现：

```text
Semantic Association
Structural Association
Temporal Association
Analogical Association
Contradiction Association
Causal Association
Shared-pattern Association
```

---

# 20. Cognitive Operator Engine

V0.1 不建议超过 6~8 个 Operator。

第一批建议：

---

## OP1：Analogy

问题：

> A 和哪个不同领域对象拥有类似结构？

输出：

```yaml
source:
target:
shared_structure:
mapping:
break_points:
possible_insight:
```

---

## OP2：Conceptual Blend

问题：

> 把 A 与 B 的部分结构组合后，会出现什么新模型？

输出：

```text
Input Space A
Input Space B
Generic Structure
Blended Structure
Emergent Property
```

---

## OP3：Counterfactual

问题：

> 如果关键前提不存在 / 相反，会怎样？

例：

```text
如果 Agent 不以 Task 为核心？
```

---

## OP4：Inversion

问题：

> 我们是否默认把因果方向想反了？

例如：

```text
不是 Memory 服务 Agent，
而是 Agent 的行为不断重写 Memory。
```

---

## OP5：Abstraction

问题：

> A 和 B 是否只是某个更高层结构的两个实例？

---

## OP6：Perspective Shift

从不同主体重新理解问题：

```text
user
agent
platform
organization
market
regulator
```

---

## OP7：Second-order Consequence

不是问：

```text
A 会导致什么？
```

而是：

```text
A → B
B → C
C 又会改变 A 吗？
```

---

## OP8：Constraint Removal

问题：

> 如果去掉一个默认限制，会发生什么？

---

# 21. Operator Selector

不是每一次都跑全部 Operator。

输入：

```text
Seed Type
Current Patch
Association Type
Previous Operators
History
```

输出：

```text
recommended_operator
```

V0.1 可以使用简单 Rule + LLM 分类。

例如：

```text
发现两个远距离概念
→ Analogy / Blend

发现强默认假设
→ Counterfactual / Inversion

发现重复结构
→ Abstraction

发现明显因果链
→ Second-order
```

---

# 22. Candidate Idea

Operator 输出的结果首先叫：

```text
Candidate
```

而不是 Wonder。

Candidate 数据：

```yaml
id:
session_id:
seed_id:

candidate_type:
  - spark
  - question
  - connection
  - hypothesis

statement:
explanation:

source_items: []
operator:
path: []

scores:
status:
```

---

# 23. 两级评价机制

不要直接对所有 Candidate 使用昂贵 Agent Research。

分两级。

---

## Stage A：Cheap Filter

目标：

> 快速淘汰 70%~90% 的垃圾。

指标：

```text
Relevance
Novelty
Coherence
Non-triviality
Redundancy
Semantic distance
```

可以结合：

- embedding；
- history lookup；
- 小模型 / LLM judge；
- rule。

---

## Stage B：Deep Evaluation

只对 Top Candidates：

```text
Codex Research
+
Independent Critic
```

评估：

```text
Evidence
Counter-evidence
Existing similar idea
Practical implication
Explanatory power
Generativity
Factual risk
```

---

# 24. Wonder Score

V0.1 使用启发式评分，不声称是科学定律。

定义：

```text
WonderScore =
    w1 * Novelty
  + w2 * Surprise
  + w3 * PersonalRelevance
  + w4 * Coherence
  + w5 * Generativity
  + w6 * ExplanatoryPower
  + w7 * EvidencePotential
  + w8 * CrossDomainValue

  - p1 * Redundancy
  - p2 * Arbitrariness
  - p3 * HallucinationRisk
```

所有维度统一：

```text
0.0 ~ 1.0
```

---

## 24.1 初始权重

仅作为 V0.1 起点：

```yaml
novelty: 0.18
surprise: 0.12
personal_relevance: 0.18
coherence: 0.12
generativity: 0.14
explanatory_power: 0.10
evidence_potential: 0.08
cross_domain_value: 0.08
```

处罚项单独扣分。

后续权重主要由真实用户反馈调整。

---

# 25. Generativity

这是一个特别重要的指标。

一个 Idea 即使很新，但如果：

```text
说完就没了
```

价值有限。

Generativity 衡量：

> 这个想法还能不能进一步产生新的问题、预测或方向？

例如：

```text
“Agent 像操作系统进程”
```

Generativity 一般。

而：

```text
“如果 Agent 是 Process，
那么 Agent 平台是否最终会自然演化出
Scheduler / Memory Manager / Security Kernel / IPC？”
```

Generativity 更高。

因为它能展开整个新的问题空间。

---

# 26. Surprise 与 Randomness 必须分开

系统必须区分：

```text
Surprising
```

和：

```text
Random
```

Surprising：

```text
第一次看不明显
+
解释后合理
```

Random：

```text
没有可解释结构
```

因此高质量 Wonder 应该满足：

```text
Unexpected BEFORE explanation
+
Coherent AFTER explanation
```

---

# 27. Codex Runtime 设计

当前第一版推荐：

```text
Python Backend
     ↓
openai-codex Python SDK
     ↓
Codex Thread / Turn
```

Codex 当前适合承担：

- 多轮 Agent Thread；
- 文件读取；
- Web / Tool / MCP；
- Shell；
- Code；
- 长任务；
- Sandbox；
- Structured Output；
- Async Execution。

---

# 28. RuntimeAdapter

核心接口设计：

```python
class AgentRuntimeAdapter:
    async def start_session(...)
    async def resume_session(...)
    async def run_task(...)
    async def stream_task(...)
    async def interrupt(...)
    async def close_session(...)
```

Wander Engine 不直接 import Codex。

实现：

```text
AgentRuntimeAdapter
        ▲
        │
CodexRuntimeAdapter
```

未来：

```text
DeepAgentsRuntimeAdapter
DSHRuntimeAdapter
OtherRuntimeAdapter
```

---

# 29. ReasoningModelAdapter

纯认知操作未必需要启动完整 Agent Runtime。

例如：

- Operator Selection；
- Candidate Generation；
- Cheap Scoring；
- Text Structuring。

建议单独抽象：

```python
class ReasoningModelAdapter:
    async def generate_structured(...)
    async def embed(...)
```

这样未来可以：

```text
Local Model
OpenAI Model
Other Model
```

独立替换。

---

# 30. Codex Thread 策略

不要整个 WanderMind 共用一个 Thread。

建议：

```text
1 Wander Session
   │
   ├── Explorer Thread
   │
   ├── Evidence Thread
   │
   └── Critic Thread
```

目的：

> 减少相互 Anchoring。

其中：

### Explorer Thread

任务：

- 深入 Candidate；
- 找可能支持；
- 找历史类比。

### Evidence Thread

任务：

- 搜索事实；
- 检索来源；
- 做验证。

### Critic Thread

独立看到：

```text
Candidate + Evidence
```

但尽量不看到 Explorer 的完整思维过程。

任务：

- 反驳；
- 找陈词滥调；
- 找过度类比；
- 检查事实。

---

# 31. Codex Sandbox 策略

默认：

```text
read_only
```

用于：

- 分析；
- 搜索；
- 阅读知识库导出；
- 研究。

需要写实验：

```text
workspace_write
```

例如：

- 生成临时分析；
- 跑代码；
- 创建实验。

V0.1 不默认使用 unrestricted/full access。

---

# 32. Codex Structured Output

所有 Runtime 任务尽量要求结构化结果。

例如 Candidate Research：

```json
{
  "summary": "",
  "supporting_evidence": [],
  "counter_evidence": [],
  "similar_existing_ideas": [],
  "assumptions": [],
  "risks": [],
  "follow_up_questions": [],
  "confidence": 0.0
}
```

避免后端通过正则解析自然语言。

---

# 33. Incubation Engine

Incubation 是 WanderMind 最有区别度的能力之一。

它不针对用户当前问题运行。

而针对：

```text
历史知识
+
历史弱 Idea
+
近期新增内容
```

运行。

---

# 34. Incubation 输入

每次选择：

```text
RecentItems      5~20
OldItems         5~20
WeakIdeas        3~10
UnresolvedQs     3~10
RandomRevival    1~5
```

避免一次把整个知识库塞给模型。

---

# 35. Incubation 策略

优先寻找：

```text
new × old
old × old-but-never-connected
weak idea × new evidence
unresolved question × new knowledge
```

而不是：

```text
recent × recent
```

因为真正的孵化价值来自时间跨度。

---

# 36. Re-wonder

每个 Idea 可以拥有：

```text
last_wondered_at
wonder_count
knowledge_version
```

当出现：

```text
new related knowledge
```

可以触发：

```text
RE-WONDER
```

例如：

```text
旧 Hypothesis
+
新的论文
+
新的项目经验
↓
重新评估
```

---

# 37. 用户反馈系统

用户对 Wonder 的反馈建议：

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

---

# 38. Feedback 不是点赞系统

其目的是学习：

```text
Personal Interestingness
```

例如系统逐渐知道：

```text
用户喜欢：
跨领域结构类比

用户不喜欢：
泛哲学问题

用户喜欢：
能直接形成系统架构假设的 Idea
```

注意：

> 只学习 Wonder 偏好，不应无限推断用户人格。

---

# 39. Surface Policy

不是所有高分 Candidate 都立即打扰用户。

定义：

```text
SurfacePolicy
```

考虑：

- final_score；
- 与上次提醒时间；
- 与最近 Wonder 的相似度；
- 用户配置；
- 当前是否主动 Wander；
- 是否处于后台孵化。

默认：

```text
manual session:
0~3 wonders

background incubation:
0~1 notification
```

---

# 40. Wonder 数据结构

```yaml
id:
type:
  - spark
  - question
  - connection
  - hypothesis
  - insight

title:
statement:
why_interesting:
explanation:

seed_id:
source_items: []
wander_path: []
operators: []

supporting_evidence: []
counter_evidence: []
assumptions: []

scores:
  novelty:
  surprise:
  relevance:
  coherence:
  generativity:
  evidence:
  final:

confidence:

status:
  - candidate
  - surfaced
  - saved
  - rejected
  - exploring
  - evolved

parent_wonder_id:
created_at:
updated_at:
```

---

# 41. Wander Trace

为了调试，必须保存一次 Wandering 的完整结构化 Trace。

```yaml
session_id:
seed:
started_at:
ended_at:

states: []

patches_visited: []

steps:
  - step:
    from_item:
    to_item:
    move_type:
    distance:
    reason:
    novelty_gain:

operators_used: []

candidates_generated: []

candidates_rejected: []

final_wonders: []
```

未来很多优化都依赖这些数据。

---

# 42. Wander Budget

每个 Session 必须有预算。

例如：

```yaml
max_steps: 20
max_patch_switches: 4
max_candidates: 30
max_deep_research: 3
max_runtime_minutes: 10
max_runtime_calls: 6
```

目的：

- 防止无限循环；
- 控成本；
- 保持思维节奏；
- 易于实验比较。

---

# 43. Stop Condition

满足任一：

```text
budget exhausted
no novelty gain
candidate convergence
high-value wonder found
too much repetition
runtime cost threshold
manual stop
```

则停止。

---

# 44. API 设计

建议 V0.1 使用 REST + SSE/WebSocket streaming。

基础接口：

---

## 44.1 Seed

```text
POST /api/v1/seeds
GET  /api/v1/seeds
GET  /api/v1/seeds/{id}
```

---

## 44.2 Knowledge

```text
POST /api/v1/knowledge
GET  /api/v1/knowledge/{id}
GET  /api/v1/knowledge/search
```

---

## 44.3 Wander

```text
POST /api/v1/wander
GET  /api/v1/wander/{session_id}
GET  /api/v1/wander/{session_id}/stream
POST /api/v1/wander/{session_id}/stop
```

---

## 44.4 Wonder

```text
GET  /api/v1/wonders
GET  /api/v1/wonders/{id}
POST /api/v1/wonders/{id}/explore
POST /api/v1/wonders/{id}/rewonder
```

---

## 44.5 Feedback

```text
POST /api/v1/wonders/{id}/feedback
```

---

## 44.6 Incubation

```text
POST /api/v1/incubation/run
GET  /api/v1/incubation/history
```

---

# 45. Backend 模块建议

```text
wandermind/
│
├── api/
│   ├── seeds.py
│   ├── knowledge.py
│   ├── wander.py
│   ├── wonders.py
│   └── feedback.py
│
├── application/
│   ├── wander_service.py
│   ├── explore_service.py
│   ├── incubation_service.py
│   └── memory_service.py
│
├── cognitive/
│   ├── controller.py
│   ├── seed_selector.py
│   ├── forager.py
│   ├── patch_manager.py
│   ├── association.py
│   ├── candidate_generator.py
│   ├── scorer.py
│   └── operators/
│       ├── analogy.py
│       ├── blend.py
│       ├── counterfactual.py
│       ├── inversion.py
│       ├── abstraction.py
│       └── second_order.py
│
├── runtime/
│   ├── base.py
│   ├── codex_runtime.py
│   └── model_adapter.py
│
├── memory/
│   ├── repository.py
│   ├── embeddings.py
│   ├── graph.py
│   └── retrieval.py
│
├── evaluation/
│   ├── novelty.py
│   ├── critic.py
│   ├── evidence.py
│   └── metrics.py
│
├── models/
│   ├── knowledge.py
│   ├── wonder.py
│   ├── session.py
│   └── trace.py
│
└── infrastructure/
    ├── database.py
    ├── scheduler.py
    ├── config.py
    └── observability.py
```

---

# 46. 推荐技术栈（V0.1）

## Backend

```text
Python 3.12+
FastAPI
Pydantic
SQLAlchemy
```

---

## Data

推荐：

```text
PostgreSQL
+
pgvector
```

PostgreSQL 保存：

- KnowledgeItem；
- Edge；
- Wonder；
- Session；
- Trace；
- Feedback。

pgvector：

- semantic retrieval；
- distance bands；
- candidate similarity；
- duplicate detection。

---

## Runtime

```text
openai-codex Python SDK
```

通过 RuntimeAdapter 集成。

---

## Scheduler

V0.1：

```text
简单 asyncio / APScheduler
```

足够支持本地 incubation。

后续需要分布式可靠任务时再升级队列系统。

---

## Frontend

第一版可以：

```text
React / Next.js
```

但 UI 不是当前验证重点。

---

# 47. 最小 UI

第一版只需要四个页面。

---

## 47.1 Inbox

输入：

```text
Drop a thought...
```

支持：

- 一句话；
- 粘贴笔记；
- 上传文字材料。

---

## 47.2 Wander

展示实时 Wandering：

```text
Seed

→ Agent Runtime
→ OS Scheduler
→ Organization
→ Resource Market

Interesting collision found...
```

不需要暴露完整模型推理，只展示结构化的可解释路径。

---

## 47.3 Wonders

类似：

```text
Today your mind wandered to...

01
Agent Governance
may resemble organizational governance
more than API permission systems.

[Why?] [Continue] [Save] [Not interesting]
```

---

## 47.4 Wonder Detail

展示：

```text
Core Idea
Why Interesting
Connection Path
Evidence
Counter Evidence
Questions
Continue Exploring
```

---

# 48. 完整 Sequence Diagram

```text
User
 │
 │ new seed
 ▼
API
 │
 ▼
SeedService
 │ save
 ▼
Memory
 │
 ▼
WanderController
 │
 ├──── retrieve nearby ────▶ MemoryRetriever
 │
 ├──── retrieve remote ────▶ SemanticForager
 │
 ├──── select operator ────▶ OperatorEngine
 │
 │
 ▼
CandidateGenerator
 │
 │ 20 candidates
 ▼
CheapScorer
 │
 │ top 3
 ▼
ExploreService
 │
 ├──────────────▶ Codex Explorer Thread
 │
 ├──────────────▶ Codex Evidence Thread
 │
 ▼
Critic
 │
 └──────────────▶ Independent Critic Thread
 │
 ▼
FinalScorer
 │
 │ high score
 ▼
WonderRepository
 │
 ▼
UI
 │
 ▼
User feedback
 │
 ▼
Preference Memory
```

---

# 49. 后台 Incubation Sequence

```text
Scheduler
   │
   ▼
IncubationService
   │
   ├─ recent knowledge
   ├─ old knowledge
   ├─ unresolved questions
   └─ weak ideas
   │
   ▼
Pair / Patch Generator
   │
   ▼
Wander Engine
   │
   ▼
Candidates
   │
   ▼
Score
   │
   ▼
0 result ─────────────→ silent
   │
1 exceptional result
   ▼
Wonder
   │
   ▼
notification / inbox
```

---

# 50. Evaluation Framework

WanderMind 必须从第一天就带 Evaluation。

否则只能凭感觉调 Prompt。

---

## 50.1 Wonder Hit Rate

```text
用户认为“值得继续想”的 Wonder
/
展示给用户的 Wonder
```

这是第一核心指标。

---

## 50.2 High-value Hit Rate

```text
very_interesting + inspired_new_idea
/
surfaced wonders
```

---

## 50.3 Continue Rate

```text
点击 Continue Explore
/
surfaced wonders
```

---

## 50.4 Obvious Rate

```text
already_knew + obvious
/
surfaced wonders
```

越低越好。

---

## 50.5 Randomness Rate

```text
too_random + irrelevant
/
surfaced wonders
```

越低越好。

---

## 50.6 Redundancy Rate

系统产生的 Candidate 与历史 Idea 过度相似的比例。

---

## 50.7 Cross-domain Yield

最终高分 Wonder 中真正跨知识域的比例。

不是越高越好，但用于观察系统有没有陷入局部。

---

# 51. Offline Evaluation Dataset

除了真实用户反馈，建议自己建立测试集。

例如准备：

```text
100~500 条真实个人知识
```

人工定义：

```text
20 个 Known Obvious Connections
20 个 Interesting Hidden Connections
10 个 Nonsense Connections
```

用于比较不同算法。

---

# 52. A/B 实验

需要能比较：

```text
Nearest Retrieval
vs
Distance-band Retrieval

No Operator
vs
Analogy

One-pass Brainstorm
vs
Wander Pipeline

Same-thread Critic
vs
Independent Critic

No Incubation
vs
Cross-time Incubation
```

---

# 53. Observability

每个 Wander Session 需要记录：

```text
session time
model calls
runtime calls
token / cost
patch count
step count
candidate count
reject reason
score distribution
final wonder
user feedback
```

未来才能知道：

> 到底哪一步真正产生了好 Idea？

---

# 54. Failure Modes

这是 WanderMind 最需要警惕的部分。

---

## F1：伪深刻

例：

> “AI 与人类本质上都是信息系统。”

听起来高级，但没有新增信息。

解决：

```text
Non-triviality Check
Generativity Check
```

---

## F2：过度类比

例：

```text
Agent = human
所以人类社会的一切机制都适用于 Agent
```

解决：

Analogy 输出必须包含：

```text
where analogy breaks
```

---

## F3：随机跳跃

解决：

每一次 remote jump 必须产生：

```text
bridge explanation
```

解释：

> 为什么 A 能连接到 B？

---

## F4：不断重复同一个 Idea

解决：

```text
Idea Embedding Dedup
+
Graph lineage
+
historical novelty check
```

---

## F5：事实幻觉

解决：

Candidate 可以大胆。

Wonder 不可以。

流程：

```text
creative generation
→ evidence phase
→ confidence
```

---

## F6：用户信息越多，噪声越大

解决：

不是：

```text
retrieve everything
```

而是：

```text
patch selection
+
bounded context
+
importance
+
temporal sampling
```

---

## F7：系统太积极

每天推 30 条 Wonder。

用户两天就关掉。

原则：

> Silence is better than mediocre Wonder.

---

# 55. Privacy / Security

由于 WanderMind 会逐渐积累非常完整的个人思想资料，隐私是核心要求。

第一版原则：

```text
local-first storage when possible
minimum external context
explicit tool access
read-only runtime default
no silent data publishing
```

---

# 56. Runtime 数据最小化

发送给 Codex 的内容只包含当前任务真正需要的知识片段。

不要：

```text
把整个 Personal Knowledge Base
全部塞进 Codex Context
```

---

# 57. 数据删除

所有：

- KnowledgeItem；
- Wonder；
- Wander Session；
- Trace；
- Feedback；

必须支持显式删除。

---

# 58. 版本路线

---

## Phase 0：Simulation

目标：

> 不接 Runtime，验证 Wander 流程。

实现：

```text
Memory
Semantic Distance
3 Cognitive Operators
Candidate
Score
```

输入 100~500 条知识。

先观察：

> 有没有产生一个真正有意思的结果。

---

## Phase 1：Wander Core MVP

增加：

```text
PostgreSQL + pgvector
Semantic Foraging
6 Operators
Idea Graph
Wonder Score
Feedback
```

---

## Phase 2：Codex Explore

增加：

```text
CodexRuntimeAdapter
Explorer Thread
Evidence Thread
Critic Thread
Structured Output
```

此时 Candidate 可以真正进入：

```text
research → validation
```

---

## Phase 3：Incubation

增加：

```text
background wandering
cross-time recombination
weak idea revival
re-wonder
```

---

## Phase 4：Personal Interestingness

根据历史反馈：

```text
学习用户真正喜欢什么 Wonder
```

---

## Phase 5：External Knowledge

加入：

```text
Web
Papers
GitHub
News
Personal files
```

世界新知识不断进入 WanderMind。

---

# 59. V0.1 最小开发清单

必须完成：

- [ ] KnowledgeItem
- [ ] Seed CRUD
- [ ] Embedding
- [ ] Semantic Search
- [ ] Distance Band Retrieval
- [ ] Patch 概念
- [ ] Local / Remote Wander
- [ ] 3~6 Cognitive Operators
- [ ] Candidate 数据模型
- [ ] Cheap Scorer
- [ ] Wonder Score
- [ ] Historical Dedup
- [ ] CodexRuntimeAdapter
- [ ] Explore
- [ ] Independent Critic
- [ ] Wonder 数据模型
- [ ] Feedback
- [ ] Wander Trace
- [ ] Minimal UI
- [ ] Evaluation Metrics

---

# 60. 第一版不应该做的东西

- [ ] 不做 20 个 SubAgent
- [ ] 不做复杂 Swarm
- [ ] 不做 Neo4j 大工程
- [ ] 不做炫酷 3D Knowledge Graph
- [ ] 不做完整 PKM
- [ ] 不做几十种 Operator
- [ ] 不做“自我意识”
- [ ] 不做自动发帖
- [ ] 不做企业权限
- [ ] 不做复杂移动端
- [ ] 不先优化极限并发

---

# 61. 最重要的 Architecture Decision Records

## ADR-001：Cognitive Core 与 Runtime 解耦

决定：

```text
Wander Engine
≠
Codex Runtime
```

原因：

WanderMind 的价值是认知策略，不是 Runtime 本身。

---

## ADR-002：V0.1 使用 Codex Python SDK

原因：

- 有稳定 Python SDK；
- 支持 Thread / Turn；
- 支持异步调用；
- 支持 sandbox；
- 可做 structured output；
- runtime 自动随 SDK 管理；
- 与 Python 后端集成成本低。

app-server 可以未来作为 Remote / Desktop Integration 选项，不作为 V0.1 直接依赖。

---

## ADR-003：生成与 Critic 分离

原因：

降低 anchoring 和 self-confirmation。

---

## ADR-004：PostgreSQL + pgvector 优先

不第一阶段引入复杂多存储体系。

---

## ADR-005：允许一次 Wander 无结果

质量优先于“每次必须给答案”。

---

## ADR-006：Operator 是核心抽象，不是 Agent Persona

避免：

```text
哲学家 Agent
科学家 Agent
创业家 Agent
```

这种难以评估、难以控制的角色堆叠。

优先：

```text
Analogy
Counterfactual
Blend
Abstraction
```

这些可定义、可测试的认知操作。

---

# 62. 理论与工程模块映射

| 理论 / 研究方向 | WanderMind 模块 | 核心启发 |
|---|---|---|
| Spontaneous Thought | Cognitive State Controller | 思考可以在不同约束强度之间切换 |
| Semantic Foraging | Semantic Forager | Local exploration + patch switching |
| Associative Theory of Creativity | Remote Retrieval | 创造需要远距离但可解释的联想 |
| Conceptual Blending | Blend Operator | 不同 mental space 重组产生 emergent structure |
| Geneplore | Candidate → Explore | 先生成半成品，再探索其意义 |
| Divergent / Convergent Thinking | Generator / Critic | 发散和筛选必须分离 |
| Curiosity / Information Gain | Seed / Explore Priority | 未知本身可以成为探索驱动力 |
| Compression Progress | Interestingness | “从惊讶到理解”比纯随机更有价值 |
| Incubation / Mind Wandering | Incubation Engine | 暂时脱离当前任务可能产生新连接 |
| Discovery by Dreaming | Cross-time Recombination | 离线跨域重组可能产生新发现 |

---

# 63. 当前 Codex 集成注意事项

截至本文档版本，Codex Python SDK 已提供稳定发布，可以通过：

```text
pip install openai-codex
```

使用，并自动安装对应 runtime。

当前设计依赖的能力：

- Thread；
- multi-turn；
- resume；
- async client；
- sandbox presets；
- structured output；
- streaming / turn control。

但 WanderMind 不应依赖 Codex 内部私有协议或不稳定实现细节。

因此所有 Codex 调用必须经过：

```text
CodexRuntimeAdapter
```

---

# 64. 产品核心不变量

无论未来：

- Runtime 换掉；
- Model 换掉；
- Database 换掉；
- UI 换掉；

以下部分必须仍然属于 WanderMind 自己：

```text
Seed Selection
Semantic Wandering
Patch Switching
Cognitive Operators
Interestingness
Wonder Evaluation
Idea Lineage
Incubation
Personal Wonder Feedback
```

这才是 WanderMind 的真正产品与技术资产。

---

# 65. 最终系统心智模型

可以把 WanderMind 理解成：

```text
                  LONG-TERM MIND
                /                \
         Knowledge               Ideas
             \                    /
              \                  /
               └── Wander Engine ──┐
                        │           │
                  associative       │
                    search          │
                        │           │
                   collision        │
                        │           │
                    operator        │
                        │           │
                    candidate       │
                        │           │
                 interesting?       │
                     /   \          │
                   no    yes        │
                   │      │         │
                forget   explore    │
                           │        │
                         Codex      │
                           │        │
                        critic      │
                           │        │
                         Wonder     │
                           │        │
                         Memory ────┘
```

---

# 66. V0.1 的真正成功标准

不是：

```text
系统完成了多少模块
```

也不是：

```text
运行了多少 Agent
```

甚至不是：

```text
生成了多少 Idea
```

而是：

> 给 WanderMind 一批真实的个人知识与历史想法。

让它自主运行。

最终系统偶尔给出一条内容，让用户产生：

> **“等等，这个角度我以前确实没想到。”**

如果这种情况能够：

```text
可重复
+
可解释
+
逐渐提升
```

那么 WanderMind 的核心命题就得到第一阶段验证。

---

# 67. 下一阶段文档建议

本详细设计完成后，建议继续依次产出：

1. `WanderMind_核心认知算法设计_V0.1.md`
2. `WanderMind_数据模型与数据库设计_V0.1.md`
3. `WanderMind_Codex_Runtime接入设计_V0.1.md`
4. `WanderMind_API设计_V0.1.md`
5. `WanderMind_MVP任务拆解_V0.1.md`
6. `WanderMind_评测体系设计_V0.1.md`

其中最优先的不是数据库，而是：

> **核心认知算法设计。**

因为这个项目真正的风险不在于：

> “工程上能不能把 Agent 跑起来。”

而在于：

> **“Wandering 能不能稳定产生真正有价值的 Wonder。”**

---

# 参考实现依据

当前 Codex 集成设计参考 OpenAI Codex 官方仓库中的 Python SDK 文档，包括：

- Python SDK Getting Started
- Python SDK API Reference
- Python SDK FAQ

核心采用其稳定 Python SDK、Thread/Turn、Sandbox、Async 和结构化输出能力。

理论部分主要基于以下研究方向：

- Spontaneous Thought / Mind Wandering
- Semantic Foraging
- Associative Theory of Creativity
- Conceptual Blending
- Geneplore / Creative Cognition
- Divergent & Convergent Thinking
- Curiosity-driven Exploration
- Information Gain / Active Inference
- Compression Progress
- Incubation
- Discovery by Dreaming

本文档中的具体系统组合、状态机、Wonder Score、Patch Switching、Operator 编排以及 Wander Engine 总体架构属于 WanderMind 的工程设计，而不是任一单篇论文的直接复刻。
