import { useEffect, useState } from "react";

import { api, ApiError, streamWanderTrace } from "../api";
import { Eyebrow, LoadingOrbit, Notice, StatusPill } from "../components/Primitives";
import { TraceTimeline } from "../components/TraceTimeline";
import type { WanderRunResponse, WanderStep } from "../types";
import { usePreferences } from "../preferences";

const MINIMUM_KNOWLEDGE_ITEMS = 2;

export function WanderPage({ seedId }: { seedId: string | null }) {
  const { t } = usePreferences();
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<WanderRunResponse | null>(null);
  const [steps, setSteps] = useState<WanderStep[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [knowledgeCount, setKnowledgeCount] = useState<number | null>(null);

  useEffect(() => {
    void api.listKnowledge()
      .then((response) => setKnowledgeCount(response.items.length))
      .catch(() => setError(t("wander.knowledgeLoadError")));
  }, [t]);

  const missingKnowledge = Math.max(
    0,
    MINIMUM_KNOWLEDGE_ITEMS - (knowledgeCount ?? 0),
  );
  const knowledgeReady = knowledgeCount !== null && missingKnowledge === 0;

  const run = async () => {
    if (!knowledgeReady || (!seedId && !prompt.trim())) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setSteps([]);
    try {
      const next = await api.runWander(seedId ? { seed_id: seedId } : { content: prompt.trim() });
      setResult(next);
      await streamWanderTrace(next.session.id, (step) => {
        setSteps((current) => current.some((item) => item.id === step.id) ? current : [...current, step]);
      });
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "insufficient_knowledge") {
        setError(t("wander.knowledgeChanged"));
        void api.listKnowledge()
          .then((response) => setKnowledgeCount(response.items.length))
          .catch(() => setKnowledgeCount(null));
      } else {
        setError(caught instanceof ApiError ? caught.message : t("wander.error"));
      }
    } finally {
      setBusy(false);
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
        {result ? <StatusPill status={result.session.status} /> : null}
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
            disabled={Boolean(seedId)}
            placeholder={seedId ? t("wander.seedReady") : t("wander.seedPlaceholder")}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
          <button className="button button-primary" disabled={busy || !knowledgeReady || (!seedId && !prompt.trim())} onClick={() => void run()}>
            {busy ? t("wander.running") : t("wander.run")}
          </button>
        </div>
        <div className="console-meta">
          <span><i /> {t("wander.retrieval")}</span>
          <span><i /> {t("wander.operators")}</span>
          <span><i /> {result ? t(result.candidates.length === 1 ? "wander.candidate" : "wander.candidates", { count: result.candidates.length }) : t("wander.scoring")}</span>
        </div>
      </section>

      {busy && !result ? <LoadingOrbit /> : null}
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
            {result.wonders[0] ? (
              <>
                <h2>{result.wonders[0].statement}</h2>
                <p>{result.wonders[0].why_interesting}</p>
                <div className="signal-number">{Math.round(result.wonders[0].scores.total * 100)}<small>/100</small></div>
                <a className="button button-primary" href={"#/wonders/" + result.wonders[0].id}>{t("wander.open")}</a>
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
