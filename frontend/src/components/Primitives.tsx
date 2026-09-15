import type { ReactNode } from "react";

import type { WonderScores } from "../types";

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

export function LoadingOrbit({ label = "Thinking across the edges" }: { label?: string }) {
  return (
    <div className="loading-orbit" role="status">
      <span className="orbit-ring"><span /></span>
      <p>{label}</p>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  return <span className={"status-pill status-" + status}>{status.replaceAll("_", " ")}</span>;
}

const scoreLabels: Array<[keyof WonderScores, string]> = [
  ["novelty", "Novelty"],
  ["coherence", "Coherence"],
  ["usefulness", "Usefulness"],
  ["surprise", "Surprise"],
  ["evidence_potential", "Evidence"],
];

export function ScoreGrid({ scores }: { scores: WonderScores }) {
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
