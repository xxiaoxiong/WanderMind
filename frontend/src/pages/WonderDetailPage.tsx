import { useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { EmptyState, Eyebrow, LoadingOrbit, Notice, ScoreGrid, StatusPill } from "../components/Primitives";
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
  const [wonder, setWonder] = useState<Wonder | null>(null);
  const [evaluation, setEvaluation] = useState<DeepExploreResponse["evaluation"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.getWonder(wonderId)
      .then(setWonder)
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : "Could not load the wonder."))
      .finally(() => setLoading(false));
  }, [wonderId]);

  const explore = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await api.exploreWonder(wonderId);
      setWonder(response.wonder);
      setEvaluation(response.evaluation);
      setMessage("Explorer, evidence, and critic passes completed.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Deep exploration failed.");
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
      else setMessage("No sufficiently new knowledge is available yet.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Re-wonder failed.");
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
      setMessage("Feedback saved.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Feedback could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <LoadingOrbit label="Opening the connection" />;
  if (!wonder) return <EmptyState title="Wonder not found" body={error || "This connection is no longer available."} />;

  return (
    <div className="page detail-page">
      <a className="back-link" href="#/wonders">← Back to wonders</a>
      <header className="detail-hero">
        <div>
          <div className="wonder-card-meta"><Eyebrow>{wonder.type}</Eyebrow><StatusPill status={wonder.status} /></div>
          <h1>{wonder.statement}</h1>
          <p>{wonder.why_interesting}</p>
        </div>
        <div className="confidence-dial" style={{ "--confidence": String(wonder.confidence * 360) + "deg" } as React.CSSProperties}>
          <strong>{Math.round(wonder.confidence * 100)}</strong><span>confidence</span>
        </div>
      </header>

      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}

      <div className="detail-layout">
        <div className="detail-main">
          <section className="detail-section core-idea"><span>Core idea</span><p>{wonder.explanation}</p></section>
          <section className="detail-section">
            <span>Connection path</span>
            <div className="connection-path">
              {wonder.connection_path.map((id, index) => <div key={id}><b>{index + 1}</b><code>{id.slice(0, 8)}</code></div>)}
            </div>
          </section>
          <ListSection title="Evidence" items={wonder.supporting_evidence} empty="No sourced evidence has been established." />
          <ListSection title="Counter evidence" items={wonder.counter_evidence} empty="No counter evidence has been recorded." />
          <ListSection title="Open questions" items={wonder.questions} empty="Explore the wonder to generate follow-up questions." />
          {evaluation ? (
            <section className="critic-panel">
              <div><span>Independent critic</span><strong>{evaluation.critic.verdict}</strong></div>
              <p>{evaluation.critic.weakness.join(" ") || "No material weakness reported."}</p>
              <small>Factual risk {Math.round(evaluation.critic.factual_risk * 100)} · Obviousness {Math.round(evaluation.critic.obviousness * 100)}</small>
            </section>
          ) : null}
        </div>
        <aside className="detail-aside">
          <section className="panel score-panel"><span>Signal profile</span><ScoreGrid scores={wonder.scores} /></section>
          <section className="panel action-panel">
            <span>Next move</span>
            <button className="button button-primary" disabled={busy} onClick={() => void explore()}>{busy ? "Working…" : "Continue exploring"}</button>
            <button className="button" disabled={busy} onClick={() => void rewonder()}>Re-wonder with new knowledge</button>
            <button className="button-quiet" disabled={busy} onClick={() => void save()}>Save this wonder</button>
          </section>
        </aside>
      </div>
    </div>
  );
}
