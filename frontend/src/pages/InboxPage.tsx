import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api";
import { Eyebrow, Notice } from "../components/Primitives";
import type { KnowledgeItem } from "../types";
import { navigate } from "../App";
import { usePreferences } from "../preferences";

export function InboxPage() {
  const { formatDate, labelCode, t } = usePreferences();
  const [thought, setThought] = useState("");
  const [note, setNote] = useState("");
  const [title, setTitle] = useState("");
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    const response = await api.listKnowledge();
    setKnowledge(response.items);
  };

  useEffect(() => {
    void refresh().catch(() => {
      setKnowledge([]);
      setError(t("inbox.loadError"));
    });
  }, [t]);

  const submitThought = async () => {
    if (!thought.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const seed = await api.createSeed(thought.trim());
      setThought("");
      navigate("/wander?seed=" + seed.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("inbox.captureError"));
    } finally {
      setBusy(false);
    }
  };

  const saveNote = async () => {
    if (!note.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createKnowledge({ title: title.trim() || undefined, content: note.trim() });
      setTitle("");
      setNote("");
      setMessage(t("inbox.saved"));
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("inbox.saveError"));
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(file);
      setMessage(t("inbox.uploaded", { file: file.name }));
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("inbox.uploadError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page inbox-page">
      <header className="page-header hero-header">
        <div>
          <Eyebrow>{t("inbox.eyebrow")}</Eyebrow>
          <h1>{t("inbox.heading")}<br /><em>{t("inbox.headingAccent")}</em></h1>
          <p>{t("inbox.intro")}</p>
        </div>
        <div className="field-stat">
          <strong>{String(knowledge.length).padStart(2, "0")}</strong>
          <span>{t("inbox.fragments")}</span>
        </div>
      </header>

      {error ? <Notice tone="error">{error}</Notice> : null}
      {message ? <Notice tone="success">{message}</Notice> : null}

      <section className="thought-composer">
        <textarea
          aria-label={t("inbox.thoughtAria")}
          placeholder={t("inbox.thoughtPlaceholder")}
          value={thought}
          onChange={(event) => setThought(event.target.value)}
        />
        <div className="composer-footer">
          <span>{t("inbox.seedHint")}</span>
          <button className="button button-primary" disabled={busy || !thought.trim()} onClick={() => void submitThought()}>
            {t("inbox.begin")} <span aria-hidden="true">↗</span>
          </button>
        </div>
      </section>

      <div className="inbox-grid">
        <section className="panel capture-panel">
          <div className="panel-heading">
            <div><span>{t("inbox.captureLabel")}</span><h2>{t("inbox.captureTitle")}</h2></div>
            <button className="icon-button" onClick={() => fileInput.current?.click()} aria-label={t("inbox.uploadAria")}>＋</button>
          </div>
          <input
            hidden
            ref={fileInput}
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
          <input
            className="line-input"
            placeholder={t("inbox.optionalTitle")}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            className="note-input"
            placeholder={t("inbox.notePlaceholder")}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <button className="button" disabled={busy || !note.trim()} onClick={() => void saveNote()}>{t("inbox.saveFragment")}</button>
        </section>

        <section className="panel recent-panel">
          <div className="panel-heading">
            <div><span>{t("inbox.recentLabel")}</span><h2>{t("inbox.recentTitle")}</h2></div>
            <span className="panel-count">{knowledge.length}</span>
          </div>
          <div className="knowledge-list">
            {knowledge.slice(0, 6).map((item) => (
              <article key={item.id}>
                <span>{labelCode(item.type)}</span>
                <div><h3>{item.title}</h3><p>{item.summary}</p></div>
                <time>{formatDate(item.created_at, { month: "short", day: "numeric" })}</time>
              </article>
            ))}
            {!knowledge.length ? <p className="muted">{t("inbox.empty")}</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}
