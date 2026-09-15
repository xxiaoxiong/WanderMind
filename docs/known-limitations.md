# V0.1 已知限制

1. 默认 Hash Embedding 为可复现基线，不等于生产级语义模型。
2. `POST /wander` 同步执行；SSE 是 Trace 回放，不是实时推理 token 流。
3. Scheduler 只适合单 leader；没有分布式锁、队列或任务租约。
4. Runtime Session 已记录生命周期、关联 ID 和成本，但 V0.1 不支持进程重启后恢复正在执行的 Codex turn。
5. 仅支持 UTF-8 文本上传，不解析 PDF、Office、网页或图片。
6. 可选 Basic Auth 仅提供单用户访问门；仍无账号体系、细粒度权限、租户隔离与公网速率限制。
7. pgvector schema 固定 96 维；修改维度需要迁移与重新嵌入。
8. Knowledge Graph 支持邻居、血缘、证据与矛盾查询，但 V0.1 没有图谱可视化与自动关系批量抽取。
9. 用户偏好只保存显式 Feedback，尚未训练个性化排序器。
10. 自动 benchmark 是 proxy；人工 UX 与认知价值评分必须由仓库所有者完成。
11. `render.yaml` 的免费 PostgreSQL 仅适合试用，会在创建 30 天后到期；长期使用必须升级数据库并配置备份。
12. OpenAI-compatible Runtime 当前面向 `/chat/completions` 协议；不同供应商的专有参数、Responses API、工具调用和原生流式 token 尚未适配。
13. 双语切换覆盖产品 UI 与模型深探提示，用户导入的知识、历史 Wonder 和 API 错误正文不会被自动翻译。
