import type { ReactNode } from "react";

import type { WonderScores } from "../types";
import { usePreferences } from "../preferences";

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="eyebrow">{children}</p>;
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: string }) {
  return <div className={"notice notice-" + tone}>{children}</div>;
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <span className="empty-orbit" aria-hidden="true" />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

export function LoadingOrbit({ label }: { label?: string }) {
  const { t } = usePreferences();
  return (
    <div className="loading-orbit" role="status">
      <span className="orbit-ring"><span /></span>
      <p>{label ?? t("loading.default")}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const { labelCode } = usePreferences();
  return <span className={"status-pill status-" + status}>{labelCode(status)}</span>;
}

export function ScoreGrid({ scores }: { scores: WonderScores }) {
  const { t } = usePreferences();
  const scoreLabels: Array<[keyof WonderScores, string]> = [
    ["novelty", t("score.novelty")],
    ["coherence", t("score.coherence")],
    ["personal_relevance", t("score.usefulness")],
    ["surprise", t("score.surprise")],
    ["evidence_potential", t("score.evidence")],
  ];
  return (
    <div className="score-grid">
      {scoreLabels.map(([key, label]) => (
        <div className="score-row" key={key}>
          <span>{label}</span>
          <div className="score-track">
            <span style={{ width: String(Math.round(scores[key] * 100)) + "%" }} />
          </div>
          <strong>{Math.round(scores[key] * 100)}</strong>
        </div>
      ))}
    </div>
  );
}
