import { useState } from "react";

import { api, ApiError, streamWanderTrace } from "../api";
import { Eyebrow, LoadingOrbit, Notice, StatusPill } from "../components/Primitives";
import { TraceTimeline } from "../components/TraceTimeline";
import type { WanderRunResponse, WanderStep } from "../types";

export function WanderPage({ seedId }: { seedId: string | null }) {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<WanderRunResponse | null>(null);
  const [steps, setSteps] = useState<WanderStep[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!seedId && !prompt.trim()) return;
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
      setError(caught instanceof ApiError ? caught.message : "The wander could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page wander-page">
      <header className="page-header">
        <div>
          <Eyebrow>Structured wandering, not hidden reasoning</Eyebrow>
          <h1>Follow the <em>connection path.</em></h1>
          <p>Watch the engine retrieve, collide, transform, score, and surface ideas.</p>
        </div>
        {result ? <StatusPill status={result.session.status} /> : null}
      </header>

      {error ? <Notice tone="error">{error}</Notice> : null}
      <section className="wander-console">
        <div className="wander-input-row">
          <input
            aria-label="Wander seed"
            disabled={Boolean(seedId)}
            placeholder={seedId ? "Captured seed is ready" : "Give the mind a question or tension..."}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
          <button className="button button-primary" disabled={busy || (!seedId && !prompt.trim())} onClick={() => void run()}>
            {busy ? "Wandering…" : "Run wander"}
          </button>
        </div>
        <div className="console-meta">
          <span><i /> Local + remote retrieval</span>
          <span><i /> Six cognitive operators</span>
          <span><i /> {result ? String(result.candidates.length) + " candidate" + (result.candidates.length === 1 ? "" : "s") : "Independent scoring"}</span>
        </div>
      </section>

      {busy && !result ? <LoadingOrbit /> : null}
      {result ? (
        <div className="wander-results">
          <section className="trace-section">
            <div className="section-heading">
              <div><span>Trace</span><h2>How the mind moved</h2></div>
              <strong>{steps.length || result.session.trace.steps.length} steps</strong>
            </div>
            <TraceTimeline steps={steps.length ? steps : result.session.trace.steps} />
          </section>
          <aside className="wander-outcome">
            <span className="outcome-label">Surface result</span>
            {result.wonders[0] ? (
              <>
                <h2>{result.wonders[0].statement}</h2>
                <p>{result.wonders[0].why_interesting}</p>
                <div className="signal-number">{Math.round(result.wonders[0].scores.total * 100)}<small>/100</small></div>
                <a className="button button-primary" href={"#/wonders/" + result.wonders[0].id}>Open wonder</a>
              </>
            ) : (
              <>
                <h2>No signal crossed the threshold.</h2>
                <p>The engine kept the trace but chose silence over a weak or arbitrary idea.</p>
              </>
            )}
          </aside>
        </div>
      ) : null}
    </div>
  );
}
