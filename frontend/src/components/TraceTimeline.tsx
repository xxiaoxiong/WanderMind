import type { WanderStep } from "../types";

interface TraceTimelineProps {
  steps: WanderStep[];
}

export function TraceTimeline({ steps }: TraceTimelineProps) {
  return (
    <ol className="trace-timeline" aria-label="Wander trace">
      {steps.map((step, index) => (
        <li key={step.id} className="trace-step">
          <div className="trace-index">{String(index + 1).padStart(2, "0")}</div>
          <div className="trace-line" aria-hidden="true" />
          <div className="trace-card">
            <div className="trace-card-head">
              <span>{step.state}</span>
              {step.operator ? <em>{step.operator}</em> : null}
            </div>
            <h3>{step.action.replaceAll("_", " ")}</h3>
            <p>{step.reason}</p>
            <div className="trace-metrics">
              {step.novelty_gain == null ? null : (
                <span>novelty {Math.round(step.novelty_gain * 100)}</span>
              )}
              {step.collision_score == null ? null : (
                <span>collision {Math.round(step.collision_score * 100)}</span>
              )}
              {step.relevance == null ? null : (
                <span>relevance {Math.round(step.relevance * 100)}</span>
              )}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
