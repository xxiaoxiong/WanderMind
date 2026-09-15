# WanderMind V0.1 认知评估报告

日期：2026-09-14  
环境：Python 3.12.14，Mock Runtime，确定性 Hash Embedding，内存 Repository

## 数据

- `data/demo_knowledge.jsonl`：120 条。
- 领域：Ecology、Distributed Systems、Urban Design、Learning Science、Economics、Biology、Organizations、Music、Psychology、Climate Adaptation、Craft、Governance。
- `data/known_connections.json`：12 个 case；interesting 6、obvious 2、nonsense 2、duplicate 2。

## Baseline V1

| 指标 | 结果 | 回归门 |
|---|---:|---:|
| Wonder Hit proxy | 1.000 | ≥ 0.450 |
| High-value proxy | 0.833 | ≥ 0.250 |
| Obvious Rate | 0.000 | ≤ 0.100 |
| Randomness Rate | 0.000 | ≤ 0.100 |
| Duplicate Rate | 0.000 | ≤ 0.100 |
| Mean surfaced redundancy | 0.218 | ≤ 0.350 |
| Cross-domain Yield | 1.000 | ≥ 0.450 |
| Average Candidates | 1.000 | 记录项 |
| Runtime calls | 0 | Mock core baseline |

命令：

```bash
cd backend
.venv/bin/python scripts/run_benchmark.py
```

每个 case 的 seed、session、path、patch count、operators、candidate count、top score 与 wonder count 保存到 `reports/benchmark_latest.json`。

## 解释

- 六个 interesting case 全部达到 Surface 门，其中五个达到 0.65 high-value proxy 门。
- obvious、nonsense、duplicate 均未被呈现，说明显式冗余与绝对因果风险门有效。
- 当前 High-value proxy 依赖轻量 Hash Embedding，尚不能代表真实语义模型上限。
- 每次运行构建 218 个多维 Patch，覆盖 domain、topic、project/temporal（存在时）与 embedding cluster；Item 可多归属。

## Scale Smoke

```text
KnowledgeItems:       1000
Wander Sessions:      100
Completed sessions:   5
Surfaced wonders:     5
Unique wonders:       5
p50:                  0.5012 s
p95:                  0.5149 s
mean:                 0.4960 s
peak traced memory:   6.11 MB
```

重复 Seed 受历史 Wonder 冗余惩罚，后续 95 次选择静默；没有 duplicate explosion、session/runtime leak。测试启用 `tracemalloc`；多维 Patch 的质心计算是当前最慢阶段，但 V0.1 p95 仍低于 0.52 秒。

## 变更门

以下任一变化必须重跑 benchmark：Prompt、Operator、Embedding、Model、Retrieval、Score weights、Patch strategy、Critic。`data/baseline_v1.json` 是机器可执行阈值。

## 人工评估

模板位于 `data/human_evaluation_template.csv`，评分 0–5。自动评估不替代人工“是否真的值得继续想”的判断；正式发布前由产品所有者完成至少 10 次真实 Seed 验收。
