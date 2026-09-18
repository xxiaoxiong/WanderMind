# Changelog

## Unreleased

### Added

- Agent-backed candidate synthesis in the primary Wander flow, followed by real evidence and critic calls for promising candidates.
- Per-run Runtime proof in API/UI: configured adapter, actual provider/model, calls, failures, duration, tokens and purposes.
- Reusable real Codex App Server smoke script with strict structured-output validation and clean process shutdown.
- Persistent English/Simplified Chinese UI switching and OS-aware light/dark themes.
- OpenAI-compatible runtime with Agnes defaults, JSON Schema validation, retries, timeout handling and token usage tracking.
- Live multilingual business-flow smoke script covering exploration, evidence, critique and adversarial source invention.

### Changed

- Wander search now explores unique knowledge pairs and continues after individual quality guards instead of stopping on the first weak candidate.
- Normal budget/search exhaustion completes cleanly, and the UI retains the best candidate when no Wonder crosses the surface threshold.
- Cognitive benchmark Runtime-call metrics now come from persisted Runtime sessions instead of a constant placeholder.
- Render Blueprint now exposes the trial instance without Basic Auth by default; self-hosters can still enable the optional access gate with environment variables.

### Security

- Evidence source references are enforced against the supplied knowledge-context allowlist.

## 0.1.0 — 2026-09-15

### Added

- Controllable Wander Engine with explicit state machine, budgets, trace and silent stopping.
- Knowledge ingestion, deterministic embeddings, retrieval bands, patching and graph relations.
- Six structured cognitive operators and explainable multi-dimensional scoring.
- Swappable Mock and Codex App Server runtimes with schema validation and safe sandbox defaults.
- Independent Explorer, Evidence and Critic services.
- Incubation, recent-seed fallback, feedback and Re-Wonder lineage.
- FastAPI REST/SSE API, PostgreSQL/pgvector persistence and Alembic migration.
- React four-view UI with strict TypeScript, component tests and Playwright E2E.
- Cognitive benchmark, 120-item demo dataset, regression gate and 1000×100 performance smoke.
- Docker Compose, CI, pre-commit, operations/configuration docs and security checks.
- Multi-facet, multi-membership patches and queryable Idea Graph lineage/evidence/contradictions.
- Persistent Runtime lifecycle/cost tracking, recursive log redaction and Prometheus cognition metrics.
- Cascading deletion APIs, backup/restore scripts and reversible runtime-session migration.
- Hybrid lexical/vector retrieval and hard guards for restatement, arbitrary framing and hallucination risk.
- Optional constant-time Basic Auth gate for hosted single-user access, with an unauthenticated health probe.
- Unified production image that serves the React UI and FastAPI API from one origin and runs Alembic on startup.
- Render Blueprint with managed PostgreSQL wiring, generated access password and deployment documentation.
