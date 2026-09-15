import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api";
import { Eyebrow, Notice } from "../components/Primitives";
import type { KnowledgeItem } from "../types";
import { navigate } from "../App";

export function InboxPage() {
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
    void refresh().catch(() => setKnowledge([]));
  }, []);

  const submitThought = async () => {
    if (!thought.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const seed = await api.createSeed(thought.trim());
      setThought("");
      navigate("/wander?seed=" + seed.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not capture the thought.");
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
      setMessage("Knowledge added to the field.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not save the note.");
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(file);
      setMessage(file.name + " entered the knowledge field.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not upload the document.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page inbox-page">
      <header className="page-header hero-header">
        <div>
          <Eyebrow>Unfinished thoughts belong here</Eyebrow>
          <h1>Drop a thought.<br /><em>Let it wander.</em></h1>
          <p>
            Capture a question, half-formed idea, or stubborn tension. WanderMind will connect it to
            the knowledge already in your field.
          </p>
        </div>
        <div className="field-stat">
          <strong>{String(knowledge.length).padStart(2, "0")}</strong>
          <span>knowledge fragments</span>
        </div>
      </header>

      {error ? <Notice tone="error">{error}</Notice> : null}
      {message ? <Notice tone="success">{message}</Notice> : null}

      <section className="thought-composer">
        <textarea
          aria-label="Drop a thought"
          placeholder="What keeps returning to your mind?"
          value={thought}
          onChange={(event) => setThought(event.target.value)}
        />
        <div className="composer-footer">
          <span>Seed a directed wander</span>
          <button className="button button-primary" disabled={busy || !thought.trim()} onClick={() => void submitThought()}>
            Begin wandering <span aria-hidden="true">↗</span>
          </button>
        </div>
      </section>

      <div className="inbox-grid">
        <section className="panel capture-panel">
          <div className="panel-heading">
            <div><span>Knowledge capture</span><h2>Add context to your mind</h2></div>
            <button className="icon-button" onClick={() => fileInput.current?.click()} aria-label="Upload text document">＋</button>
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
            placeholder="Optional title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            className="note-input"
            placeholder="Paste a note, observation, excerpt, or concept..."
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <button className="button" disabled={busy || !note.trim()} onClick={() => void saveNote()}>Save fragment</button>
        </section>

        <section className="panel recent-panel">
          <div className="panel-heading">
            <div><span>Recent material</span><h2>Your active knowledge field</h2></div>
            <span className="panel-count">{knowledge.length}</span>
          </div>
          <div className="knowledge-list">
            {knowledge.slice(0, 6).map((item) => (
              <article key={item.id}>
                <span>{item.type}</span>
                <div><h3>{item.title}</h3><p>{item.summary}</p></div>
                <time>{new Date(item.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</time>
              </article>
            ))}
            {!knowledge.length ? <p className="muted">No fragments yet. Add two or more to unlock wandering.</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}
