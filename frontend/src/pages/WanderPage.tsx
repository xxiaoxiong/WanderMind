import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError, streamWanderTrace } from "../api";
import { Eyebrow, LoadingOrbit, Notice, StatusPill } from "../components/Primitives";
import { TraceTimeline } from "../components/TraceTimeline";
import { usePreferences } from "../preferences";
import type {
  Candidate,
  WanderProgress,
  WanderRunResponse,
  WanderStep,
} from "../types";

const MINIMUM_KNOWLEDGE_ITEMS = 2;
const ACTIVE_SESSION_KEY = "wandermind.active-wander-session";

function selectBestCandidate(candidates: Candidate[]): Candidate | null {
  const first = candidates[0];
  if (!first) return null;
  return candidates.slice(1).reduce((best, candidate) => (
    (candidate.scores?.total ?? 0) > (best.scores?.total ?? 0) ? candidate : best
  ), first);
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export function WanderPage({ seedId }: { seedId: string | null }) {
  const { t } = usePreferences();
  const recoveryStarted = useRef(false);
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<WanderRunResponse | null>(null);
  const [steps, setSteps] = useState<WanderStep[]>([]);
  const [progress, setProgress] = useState<WanderProgress | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [knowledgeCount, setKnowledgeCount] = useState<number | null>(null);

  useEffect(() => {
    void api.listKnowledge()
      .then((response) => setKnowledgeCount(response.items.length))
      .catch(() => setError(t("wander.knowledgeLoadError")));
  }, [t]);

  useEffect(() => {
    if (!busy) {
      setElapsedSeconds(0);
      return undefined;
    }
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [busy]);

  const followSession = useCallback(async (sessionId: string) => {
    setBusy(true);
    setActiveSessionId(sessionId);
    setError(null);
    let lastStepIndex = -1;
    let reconnects = 0;
    try {
      while (true) {
        try {
          await streamWanderTrace(
            sessionId,
            (step) => {
              lastStepIndex = Math.max(lastStepIndex, step.index);
              setSteps((current) => (
                current.some((item) => item.id === step.id)
                  ? current
                  : [...current, step].sort((left, right) => left.index - right.index)
              ));
            },
            setProgress,
            lastStepIndex,
          );
          break;
        } catch (caught) {
          if (!(caught instanceof ApiError) || !caught.retryable || reconnects >= 8) {
            throw caught;
          }
          reconnects += 1;
          await wait(Math.min(500 * 2 ** reconnects, 8_000));
        }
      }
      const completed = await api.getWanderResult(sessionId);
      setResult(completed);
      setProgress((current) => current ? { ...current, status: completed.session.status } : null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("wander.error"));
    } finally {
      window.localStorage.removeItem(ACTIVE_SESSION_KEY);
      setActiveSessionId(null);
      setStopping(false);
      setBusy(false);
    }
  }, [t]);

  useEffect(() => {
    if (recoveryStarted.current) return;
    recoveryStarted.current = true;
    const sessionId = window.localStorage.getItem(ACTIVE_SESSION_KEY);
    if (sessionId) {
      void followSession(sessionId);
    }
  }, [followSession]);

  const missingKnowledge = Math.max(
    0,
    MINIMUM_KNOWLEDGE_ITEMS - (knowledgeCount ?? 0),
  );
  const knowledgeReady = knowledgeCount !== null && missingKnowledge === 0;
  const bestCandidate = selectBestCandidate(result?.candidates ?? []);
  const candidateCount = result?.candidates.length ?? progress?.candidate_count ?? 0;
  const currentStatus = result?.session.status ?? progress?.status;

  const run = async () => {
    if (!knowledgeReady || (!seedId && !prompt.trim())) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setProgress(null);
    setSteps([]);
    try {
      const session = await api.startWander(
        seedId ? { seed_id: seedId } : { content: prompt.trim() },
      );
      window.localStorage.setItem(ACTIVE_SESSION_KEY, session.id);
      await followSession(session.id);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "insufficient_knowledge") {
        setError(t("wander.knowledgeChanged"));
        void api.listKnowledge()
          .then((response) => setKnowledgeCount(response.items.length))
          .catch(() => setKnowledgeCount(null));
      } else {
        setError(caught instanceof ApiError ? caught.message : t("wander.error"));
      }
      setBusy(false);
    }
  };

  const stop = async () => {
    if (!activeSessionId || stopping) return;
    setStopping(true);
    try {
      await api.stopWander(activeSessionId);
    } catch (caught) {
      setStopping(false);
      setError(caught instanceof ApiError ? caught.message : t("wander.error"));
    }
  };

  return (
    <div className="page wander-page">
      <header className="page-header">
        <div>
          <Eyebrow>{t("wander.eyebrow")}</Eyebrow>
          <h1>{t("wander.heading")} <em>{t("wander.headingAccent")}</em></h1>
          <p>{t("wander.intro")}</p>
        </div>
        {currentStatus ? <StatusPill status={currentStatus} /> : null}
      </header>

      {error ? <Notice tone="error">{error}</Notice> : null}
      {knowledgeCount !== null && !knowledgeReady ? (
        <Notice>
          {t("wander.knowledgeRequired", { count: missingKnowledge })}{" "}
          <a href="#/inbox">{t("wander.addKnowledge")}</a>
        </Notice>
      ) : null}
      <section className="wander-console">
        <div className="wander-input-row">
          <input
            aria-label={t("wander.seedAria")}
            disabled={Boolean(seedId) || busy}
            placeholder={seedId ? t("wander.seedReady") : t("wander.seedPlaceholder")}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
          {busy ? (
            <button className="button button-ghost" disabled={stopping} onClick={() => void stop()}>
              {stopping ? t("wander.stopping") : t("wander.stop")}
            </button>
          ) : (
            <button className="button button-primary" disabled={!knowledgeReady || (!seedId && !prompt.trim())} onClick={() => void run()}>
              {t("wander.run")}
            </button>
          )}
        </div>
        <div className="console-meta">
          <span><i /> {t("wander.retrieval")}</span>
          <span><i /> {t("wander.deepMode")}</span>
          <span><i /> {candidateCount > 0 ? t(candidateCount === 1 ? "wander.candidate" : "wander.candidates", { count: candidateCount }) : t("wander.scoring")}</span>
        </div>
      </section>

      {busy ? (
        <section className="live-wander">
          <LoadingOrbit label={`${t("wander.agentRunning")} · ${elapsedSeconds}s`} />
          <div className="live-progress">
            <strong>{t("wander.liveProgress")}</strong>
            <span>{candidateCount} / 8 {t("wander.candidateUnit")}</span>
            <span>{progress?.wonder_count ?? 0} / 3 {t("wander.wonderUnit")}</span>
            <span>{progress?.runtime_calls_used ?? 0} / 16 {t("wander.callUnit")}</span>
          </div>
          {steps.length ? <TraceTimeline steps={steps} /> : null}
        </section>
      ) : null}
      {result ? (
        <div className="wander-results">
          <section className="trace-section">
            <div className="section-heading">
              <div><span>{t("wander.trace")}</span><h2>{t("wander.traceTitle")}</h2></div>
              <strong>{t("wander.steps", { count: steps.length || result.session.trace.steps.length })}</strong>
            </div>
            <TraceTimeline steps={steps.length ? steps : result.session.trace.steps} />
          </section>
          <aside className="wander-outcome">
            <span className="outcome-label">{t("wander.outcome")}</span>
            <div className={"runtime-proof " + (result.runtime.verified ? "runtime-verified" : "runtime-missing")}>
              <strong>
                {result.runtime.verified ? t("wander.runtimeVerified") : t("wander.runtimeUnavailable")}
              </strong>
              <span>{[result.runtime.provider, result.runtime.model].filter(Boolean).join(" · ") || result.runtime.configured_adapter}</span>
              <small>
                {t("wander.runtimeCalls", {
                  count: result.runtime.completed_calls,
                  seconds: result.runtime.duration_seconds.toFixed(1),
                })}
                {result.runtime.total_tokens > 0 ? " · " + t("wander.runtimeTokens", { count: result.runtime.total_tokens }) : ""}
              </small>
            </div>
            {result.wonders[0] ? (
              <>
                <h2>{result.wonders[0].statement}</h2>
                <p>{result.wonders[0].why_interesting}</p>
                <div className="signal-number">{Math.round(result.wonders[0].scores.total * 100)}<small>/100</small></div>
                <a className="button button-primary" href={"#/wonders/" + result.wonders[0].id}>{t("wander.open")}</a>
                {result.wonders.length > 1 ? (
                  <div className="ranked-wonders">
                    <strong>{t("wander.alternatives")}</strong>
                    {result.wonders.slice(1).map((wonder, index) => (
                      <a href={"#/wonders/" + wonder.id} key={wonder.id}>
                        <span>0{index + 2}</span>{wonder.statement}
                      </a>
                    ))}
                  </div>
                ) : null}
              </>
            ) : bestCandidate ? (
              <>
                <span className="candidate-label">{t("wander.bestCandidate")}</span>
                <h2>{bestCandidate.statement}</h2>
                <p>{bestCandidate.explanation}</p>
                {bestCandidate.scores ? (
                  <div className="signal-number">{Math.round(bestCandidate.scores.total * 100)}<small>/100</small></div>
                ) : null}
                <StatusPill status={bestCandidate.status} />
                <p className="stop-reason">
                  {t("wander.stopReason", {
                    reason: (result.session.trace.stop_reason ?? "search_space_exhausted").replaceAll("_", " "),
                  })}
                </p>
              </>
            ) : (
              <>
                <h2>{t("wander.noSignal")}</h2>
                <p>{t("wander.silence")}</p>
              </>
            )}
          </aside>
        </div>
      ) : null}
    </div>
  );
}
