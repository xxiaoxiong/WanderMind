import { useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { EmptyState, Eyebrow, LoadingOrbit, Notice, ScoreGrid, StatusPill } from "../components/Primitives";
import { usePreferences } from "../preferences";
import type { DeepExploreResponse, Wonder } from "../types";

function ListSection({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <section className="detail-section">
      <span>{title}</span>
      {items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">{empty}</p>}
    </section>
  );
}

export function WonderDetailPage({ wonderId }: { wonderId: string }) {
  const { labelCode, t } = usePreferences();
  const [wonder, setWonder] = useState<Wonder | null>(null);
  const [evaluation, setEvaluation] = useState<DeepExploreResponse["evaluation"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.getWonder(wonderId)
      .then(setWonder)
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : t("detail.loadError")))
      .finally(() => setLoading(false));
  }, [t, wonderId]);

  const explore = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await api.exploreWonder(wonderId);
      setWonder(response.wonder);
      setEvaluation(response.evaluation);
      setMessage(t("detail.exploreDone"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("detail.exploreError"));
    } finally {
      setBusy(false);
    }
  };

  const rewonder = async () => {
    setBusy(true);
    setError(null);
    try {
      const child = await api.rewonder(wonderId);
      if (child) window.location.hash = "/wonders/" + child.id;
      else setMessage(t("detail.noNewKnowledge"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("detail.rewonderError"));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.feedback(wonderId, "save_for_later");
      setWonder((current) => current ? { ...current, status: "saved" } : current);
      setMessage(t("detail.feedbackSaved"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("detail.feedbackError"));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <LoadingOrbit label={t("detail.opening")} />;
  if (!wonder) return <EmptyState title={t("detail.notFound")} body={error || t("detail.unavailable")} />;

  return (
    <div className="page detail-page">
      <a className="back-link" href="#/wonders">{t("detail.back")}</a>
      <header className="detail-hero">
        <div>
          <div className="wonder-card-meta"><Eyebrow>{labelCode(wonder.type)}</Eyebrow><StatusPill status={wonder.status} /></div>
          <h1>{wonder.statement}</h1>
          <p>{wonder.why_interesting}</p>
        </div>
        <div className="confidence-dial" style={{ "--confidence": String(wonder.confidence * 360) + "deg" } as React.CSSProperties}>
          <strong>{Math.round(wonder.confidence * 100)}</strong><span>{t("detail.confidence")}</span>
        </div>
      </header>

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}

      <div className="detail-layout">
        <div className="detail-main">
          <section className="detail-section core-idea"><span>{t("detail.coreIdea")}</span><p>{wonder.explanation}</p></section>
          <section className="detail-section">
            <span>{t("detail.connectionPath")}</span>
            <div className="connection-path">
              {wonder.connection_path.map((id, index) => <div key={id}><b>{index + 1}</b><code>{id.slice(0, 8)}</code></div>)}
            </div>
          </section>
          <ListSection title={t("detail.evidence")} items={wonder.supporting_evidence} empty={t("detail.noEvidence")} />
          <ListSection title={t("detail.counterEvidence")} items={wonder.counter_evidence} empty={t("detail.noCounterEvidence")} />
          <ListSection title={t("detail.questions")} items={wonder.questions} empty={t("detail.noQuestions")} />
          {evaluation ? (
            <section className="critic-panel">
              <div><span>{t("detail.critic")}</span><strong>{labelCode(evaluation.critic.verdict)}</strong></div>
              <p>{evaluation.critic.weakness.join(" ") || t("detail.noWeakness")}</p>
              <small>{t("detail.factualRisk", { value: Math.round(evaluation.critic.factual_risk * 100) })} · {t("detail.obviousness", { value: Math.round(evaluation.critic.obviousness * 100) })}</small>
            </section>
          ) : null}
        </div>
        <aside className="detail-aside">
          <section className="panel score-panel"><span>{t("detail.signalProfile")}</span><ScoreGrid scores={wonder.scores} /></section>
          <section className="panel action-panel">
            <span>{t("detail.nextMove")}</span>
            <button className="button button-primary" disabled={busy} onClick={() => void explore()}>{busy ? t("detail.working") : t("detail.continue")}</button>
            <button className="button" disabled={busy} onClick={() => void rewonder()}>{t("detail.rewonder")}</button>
            <button className="button-quiet" disabled={busy} onClick={() => void save()}>{t("detail.save")}</button>
          </section>
        </aside>
      </div>
    </div>
  );
}
