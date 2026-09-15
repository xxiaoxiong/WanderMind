import { useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { EmptyState, Eyebrow, LoadingOrbit, Notice } from "../components/Primitives";
import { WonderCard } from "../components/WonderCard";
import type { Wonder } from "../types";

export function WondersPage() {
  const [wonders, setWonders] = useState<Wonder[]>([]);
  const [loading, setLoading] = useState(true);
  const [incubating, setIncubating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setWonders(await api.listWonders());
  };

  useEffect(() => {
    void refresh()
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : "Could not load wonders."))
      .finally(() => setLoading(false));
  }, []);

  const incubate = async () => {
    setIncubating(true);
    setError(null);
    try {
      const outcome = await api.runIncubation();
      setMessage(outcome.surfaced ? "A cross-time connection surfaced." : "No idea was strong enough to interrupt you.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Incubation failed.");
    } finally {
      setIncubating(false);
    }
  };

  return (
    <div className="page wonders-page">
      <header className="page-header hero-header">
        <div>
          <Eyebrow>Curated, not continuous</Eyebrow>
          <h1>Today your mind<br /><em>wandered to…</em></h1>
          <p>Only connections that clear the quality threshold arrive here.</p>
        </div>
        <button className="button" disabled={incubating} onClick={() => void incubate()}>{incubating ? "Incubating…" : "Run incubation"}</button>
      </header>
      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      {loading ? <LoadingOrbit label="Gathering surfaced wonders" /> : null}
      {!loading && !wonders.length ? (
        <EmptyState title="The field is quiet" body="Add knowledge, run a wander, and strong connections will collect here." />
      ) : null}
      <div className="wonder-list">
        {wonders.map((wonder, index) => (
          <WonderCard wonder={wonder} index={index} key={wonder.id} onChanged={() => void refresh()} />
        ))}
      </div>
    </div>
  );
}
