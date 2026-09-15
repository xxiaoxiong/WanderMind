import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TraceTimeline } from "./TraceTimeline";

describe("TraceTimeline", () => {
  it("shows structured steps without exposing hidden chain of thought", () => {
    render(
      <TraceTimeline
        steps={[
          {
            id: "step-1",
            index: 0,
            state: "collision",
            action: "evaluate_collision",
            reason: "Compared two distant knowledge patches.",
            item_ids: ["one", "two"],
            operator: "analogy",
            novelty_gain: 0.72,
            relevance: 0.6,
            collision_score: 0.68,
            created_at: "2026-09-14T00:00:00Z",
          },
        ]}
      />,
    );
    expect(screen.getByText("evaluate collision")).toBeInTheDocument();
    expect(screen.getByText("analogy")).toBeInTheDocument();
    expect(screen.getByText("collision 68")).toBeInTheDocument();
  });
});
