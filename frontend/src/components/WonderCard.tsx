import { useState } from "react";

import { api } from "../api";
import type { Wonder } from "../types";
import { usePreferences } from "../preferences";
import { StatusPill } from "./Primitives";

interface WonderCardProps {
  wonder: Wonder;
  index: number;
  onChanged?: () => void;
}

export function WonderCard({ wonder, index, onChanged }: WonderCardProps) {
  const { formatDate, labelCode, t } = usePreferences();
  const [pending, setPending] = useState<string | null>(null);

  const react = async (action: string) => {
    setPending(action);
    try {
      await api.feedback(wonder.id, action);
      onChanged?.();
    } finally {
      setPending(null);
    }
  };

  return (
    <article className="wonder-card">
      <div className="wonder-number">{String(index + 1).padStart(2, "0")}</div>
      <div className="wonder-card-body">
        <div className="wonder-card-meta">
          <span>{labelCode(wonder.type)}</span>
          <StatusPill status={wonder.status} />
          <span>{formatDate(wonder.created_at)}</span>
        </div>
        <h2>{wonder.statement}</h2>
        <p>{wonder.why_interesting}</p>
        <div className="wonder-score">
          <span>{t("wonder.signal")}</span>
          <strong>{Math.round(wonder.scores.total * 100)}</strong>
          <div><span style={{ width: String(wonder.scores.total * 100) + "%" }} /></div>
        </div>
        <div className="card-actions">
          <a className="button button-primary" href={"#/wonders/" + wonder.id}>{t("wonder.why")}</a>
          <button disabled={pending !== null} onClick={() => void react("continue_explore")}>{t("wonder.continue")}</button>
          <button disabled={pending !== null} onClick={() => void react("save_for_later")}>{t("wonder.save")}</button>
          <button
            className="button-quiet"
            disabled={pending !== null}
            onClick={() => void react("not_interesting")}
          >
            {t("wonder.notInteresting")}
          </button>
        </div>
      </div>
    </article>
  );
}
