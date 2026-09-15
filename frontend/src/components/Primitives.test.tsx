import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreGrid, StatusPill } from "./Primitives";

describe("presentation primitives", () => {
  it("renders readable status text", () => {
    render(<StatusPill status="not_interesting" />);
    expect(screen.getByText("not interesting")).toBeInTheDocument();
  });

  it("renders the core score profile", () => {
    render(
      <ScoreGrid
        scores={{
          novelty: 0.81,
          coherence: 0.73,
          usefulness: 0.66,
          surprise: 0.59,
          evidence_potential: 0.42,
          redundancy: 0.1,
          arbitrariness: 0.2,
          hallucination_risk: 0.15,
          total: 0.68,
        }}
      />,
    );
    expect(screen.getByText("Novelty")).toBeInTheDocument();
    expect(screen.getByText("81")).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
  });
});
