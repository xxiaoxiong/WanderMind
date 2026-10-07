import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api";
import { Eyebrow, LoadingOrbit, Notice, StatusPill } from "../components/Primitives";
import { TraceTimeline } from "../components/TraceTimeline";
import { WonderCard } from "../components/WonderCard";
import { usePreferences } from "../preferences";
import type { AutopilotSnapshot } from "../types";

const DEFAULT_OBJECTIVE =
  "聚焦高质量智能体架构设计，持续研究认知与决策分层、规划执行闭环、记忆与知识治理、工具调用、多智能体协作、上下文工程、可观测性、评估、安全和成本效能；产出可验证、可实施、有反证路径且不重复既有成果的架构原则、设计模式、失败模式与演进方案。";

export function AutopilotPage() {
  const { formatDate, language } = usePreferences();
  const copy = language === "zh-CN" ? chinese : english;
  const [snapshot, setSnapshot] = useState<AutopilotSnapshot | null>(null);
  const [objective, setObjective] = useState(DEFAULT_OBJECTIVE);
  const [objectiveDirty, setObjectiveDirty] = useState(false);
  const objectiveDirtyRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const value = await api.getAutopilotStatus();
      setSnapshot(value);
      if (value.campaign?.objective && !objectiveDirtyRef.current) {
        setObjective(value.campaign.objective);
      }
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : copy.loadError);
    }
  }, [copy.loadError]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const control = async (action: "start" | "resume" | "pause" | "stop") => {
    setBusy(true);
    setError(null);
    try {
      const submitsObjective = action === "start" || action === "resume";
      const next = submitsObjective
        ? await api.startAutopilot(objective.trim() || DEFAULT_OBJECTIVE)
        : action === "pause"
          ? await api.pauseAutopilot()
          : await api.stopAutopilot();
      setSnapshot(next);
      if (submitsObjective && next.campaign?.objective) {
        objectiveDirtyRef.current = false;
        setObjectiveDirty(false);
        setObjective(next.campaign.objective);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : copy.controlError);
    } finally {
      setBusy(false);
    }
  };

  const saveObjective = async () => {
    const nextObjective = objective.trim();
    if (!nextObjective) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.updateAutopilotObjective(nextObjective);
      setSnapshot(next);
      objectiveDirtyRef.current = false;
      setObjectiveDirty(false);
      setObjective(next.campaign?.objective ?? nextObjective);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : copy.saveError);
    } finally {
      setBusy(false);
    }
  };

  const campaign = snapshot?.campaign;
  const current = snapshot?.current_session;
  const running = campaign?.status === "active";
  const currentCandidateCount = current?.trace.candidate_ids.length ?? 0;
  const currentWonderCount = current?.trace.final_wonder_ids.length ?? 0;
  const currentMode = snapshot?.current_seed?.metadata.mode;

  return (
    <div className="page autopilot-page">
      <header className="page-header hero-header">
        <div>
          <Eyebrow>{copy.eyebrow}</Eyebrow>
          <h1>{copy.heading}<br /><em>{copy.headingAccent}</em></h1>
          <p>{copy.intro}</p>
        </div>
        {campaign ? <StatusPill status={campaign.status} /> : null}
      </header>

      {error ? <Notice tone="error">{error}</Notice> : null}
      {!snapshot ? <LoadingOrbit label={copy.loading} /> : null}

      {snapshot ? (
        <>
          <section className="autopilot-command">
            <label htmlFor="autopilot-objective">{copy.objective}</label>
            <textarea
              id="autopilot-objective"
              disabled={running}
              value={objective}
              onChange={(event) => {
                objectiveDirtyRef.current = true;
                setObjectiveDirty(true);
                setObjective(event.target.value);
              }}
            />
            <div className="autopilot-actions">
              {campaign && !running ? (
                <button
                  className="button"
                  disabled={busy || !objectiveDirty || !objective.trim()}
                  onClick={() => void saveObjective()}
                >
                  {copy.saveObjective}
                </button>
              ) : null}
              {!campaign || campaign.status === "stopped" ? (
                <button className="button button-primary" disabled={busy} onClick={() => void control("start")}>{copy.start}</button>
              ) : null}
              {campaign?.status === "paused" ? (
                <button className="button button-primary" disabled={busy} onClick={() => void control("resume")}>{copy.resume}</button>
              ) : null}
              {running ? (
                <button className="button" disabled={busy} onClick={() => void control("pause")}>{copy.pause}</button>
              ) : null}
              {campaign && campaign.status !== "stopped" ? (
                <button className="button button-quiet" disabled={busy} onClick={() => void control("stop")}>{copy.stop}</button>
              ) : null}
              <span className={snapshot.worker_running ? "worker-online" : "worker-offline"}>
                <i /> {snapshot.worker_running ? copy.workerOnline : copy.workerOffline}
              </span>
            </div>
          </section>

          <section className="autopilot-metrics" aria-label={copy.metrics}>
            <Metric label={copy.cycles} value={campaign?.cycles_completed ?? 0} />
            <Metric label={copy.candidates} value={campaign?.total_candidates ?? 0} />
            <Metric label={copy.wonders} value={campaign?.total_wonders ?? 0} />
            <Metric label={copy.runtimeCalls} value={campaign?.total_runtime_calls ?? 0} />
            <Metric label={copy.promoted} value={snapshot.accepted_generated_knowledge_count} />
            <Metric label={copy.knowledge} value={snapshot.knowledge_count} />
          </section>

          <section className="autopilot-current">
            <div className="section-heading">
              <div><span>{copy.currentLabel}</span><h2>{copy.currentTitle}</h2></div>
              <strong>{campaign?.cycles_started ?? 0} {copy.cycleUnit}</strong>
            </div>
            {current ? (
              <>
                <div className="live-progress">
                  <strong>{typeof currentMode === "string" ? currentMode : copy.exploring}</strong>
                  <span>{current.trace.steps.length} {copy.steps}</span>
                  <span>{currentCandidateCount} {copy.candidates}</span>
                  <span>{currentWonderCount} {copy.wonders}</span>
                  <span>{snapshot.current_runtime.calls} {copy.runtimeCalls}</span>
                </div>
                {snapshot.current_seed ? <p className="autopilot-seed">{snapshot.current_seed.content}</p> : null}
                {current.trace.steps.length ? <TraceTimeline steps={current.trace.steps.slice(-10)} /> : null}
              </>
            ) : (
              <div className="autopilot-idle">
                <strong>{running ? copy.betweenCycles : copy.notRunning}</strong>
                {campaign?.last_cycle_completed_at ? (
                  <span>{copy.lastCompleted} {formatDate(campaign.last_cycle_completed_at, { dateStyle: "medium", timeStyle: "medium" })}</span>
                ) : null}
                {campaign?.last_error ? <span className="autopilot-error">{campaign.last_error}</span> : null}
              </div>
            )}
          </section>

          <section className="autopilot-results">
            <div className="section-heading">
              <div><span>{copy.accumulated}</span><h2>{copy.latestTitle}</h2></div>
              <strong>
                {snapshot.accepted_generated_knowledge_count} {copy.generatedKnowledge}
                {snapshot.rejected_generated_knowledge_count
                  ? ` · ${snapshot.rejected_generated_knowledge_count} ${copy.quarantinedKnowledge}`
                  : ""}
              </strong>
            </div>
            <div className="wonder-list">
              {snapshot.latest_wonders.map((wonder, index) => (
                <WonderCard wonder={wonder} index={index} key={wonder.id} onChanged={() => void refresh()} />
              ))}
            </div>
            {!snapshot.latest_wonders.length ? <p className="autopilot-empty">{copy.noWonders}</p> : null}
          </section>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div><strong>{value}</strong><span>{label}</span></div>;
}

const english = {
  eyebrow: "Unsupervised cumulative discovery",
  heading: "Let the field keep",
  headingAccent: "thinking while you are away.",
  intro: "Autopilot runs deep research cycles, survives restarts, feeds verified discoveries back into the knowledge field, and continues from the expanded frontier.",
  loading: "Reading the persistent exploration state",
  loadError: "Could not load Autopilot status.",
  controlError: "Could not change Autopilot state.",
  saveError: "Could not save the exploration objective.",
  objective: "Persistent exploration objective",
  saveObjective: "Save objective",
  start: "Start continuous exploration",
  resume: "Resume",
  pause: "Pause after checkpoint",
  stop: "Stop Autopilot",
  workerOnline: "supervisor online",
  workerOffline: "supervisor unavailable",
  metrics: "Cumulative exploration metrics",
  cycles: "cycles completed",
  candidates: "candidates",
  wonders: "verified wonders",
  runtimeCalls: "runtime calls",
  promoted: "insights fed back",
  knowledge: "knowledge items",
  currentLabel: "Live checkpoint",
  currentTitle: "What the system is exploring now",
  cycleUnit: "cycles started",
  exploring: "deep exploration",
  steps: "steps",
  betweenCycles: "The previous cycle is committed. The next frontier will start automatically.",
  notRunning: "Autopilot is not currently running.",
  lastCompleted: "Last committed:",
  accumulated: "Cumulative discoveries",
  latestTitle: "High-quality results that survived review",
  generatedKnowledge: "generated knowledge items",
  quarantinedKnowledge: "quality-quarantined",
  noWonders: "No result has crossed the quality threshold yet. The trace and rejected candidates remain auditable while exploration continues.",
} as const;

const chinese = {
  eyebrow: "无人监督的累积式发现",
  heading: "离开以后，也让知识场",
  headingAccent: "继续思考和生长。",
  intro: "自动驾驶会持续运行深度探索批次，在重启后恢复，把通过独立审查的成果回灌为新知识，再从扩展后的知识边界继续探索。",
  loading: "正在读取持久化探索状态",
  loadError: "无法加载持续探索状态。",
  controlError: "无法切换持续探索状态。",
  saveError: "无法保存长期探索目标。",
  objective: "长期探索目标",
  saveObjective: "保存目标",
  start: "启动持续探索",
  resume: "继续运行",
  pause: "在检查点暂停",
  stop: "停止自动驾驶",
  workerOnline: "主管循环在线",
  workerOffline: "主管循环不可用",
  metrics: "累计探索指标",
  cycles: "已完成轮次",
  candidates: "候选",
  wonders: "已验证洞见",
  runtimeCalls: "模型调用",
  promoted: "回灌洞见",
  knowledge: "知识总量",
  currentLabel: "实时检查点",
  currentTitle: "系统当前正在探索什么",
  cycleUnit: "轮已启动",
  exploring: "深度探索",
  steps: "步",
  betweenCycles: "上一轮已经持久化，下一轮会自动从新边界继续。",
  notRunning: "自动驾驶当前没有运行。",
  lastCompleted: "最近一次持久化：",
  accumulated: "累积发现",
  latestTitle: "通过质量审查的高价值结果",
  generatedKnowledge: "条自动生成知识",
  quarantinedKnowledge: "条质量隔离",
  noWonders: "暂时没有结果越过质量阈值。探索会继续，轨迹和被淘汰候选仍保留供审计。",
} satisfies Record<keyof typeof english, string>;
