import { useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { EmptyState, Eyebrow, LoadingOrbit, Notice } from "../components/Primitives";
import { WonderCard } from "../components/WonderCard";
import type { Wonder } from "../types";
import { usePreferences } from "../preferences";

export function WondersPage() {
  const { t } = usePreferences();
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
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : t("wonders.loadError")))
      .finally(() => setLoading(false));
  }, [t]);

  const incubate = async () => {
    setIncubating(true);
    setError(null);
    try {
      const outcome = await api.runIncubation();
      setMessage(outcome.surfaced ? t("wonders.surfaced") : t("wonders.quiet"));
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("wonders.incubationError"));
    } finally {
      setIncubating(false);
    }
  };

  return (
    <div className="page wonders-page">
      <header className="page-header hero-header">
        <div>
          <Eyebrow>{t("wonders.eyebrow")}</Eyebrow>
          <h1>{t("wonders.heading")}<br /><em>{t("wonders.headingAccent")}</em></h1>
          <p>{t("wonders.intro")}</p>
        </div>
        <button className="button" disabled={incubating} onClick={() => void incubate()}>{incubating ? t("wonders.incubating") : t("wonders.runIncubation")}</button>
      </header>
      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      {loading ? <LoadingOrbit label={t("wonders.loading")} /> : null}
      {!loading && !wonders.length ? (
        <EmptyState title={t("wonders.emptyTitle")} body={t("wonders.emptyBody")} />
      ) : null}
      <div className="wonder-list">
        {wonders.map((wonder, index) => (
          <WonderCard wonder={wonder} index={index} key={wonder.id} onChanged={() => void refresh()} />
        ))}
      </div>
    </div>
  );
}
