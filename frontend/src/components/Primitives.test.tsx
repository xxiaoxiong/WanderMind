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
          surprise: 0.59,
          personal_relevance: 0.66,
          coherence: 0.73,
          generativity: 0.61,
          explanatory_power: 0.64,
          evidence_potential: 0.42,
          cross_domain_value: 0.7,
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
    expect(screen.queryByText("NaN")).not.toBeInTheDocument();
  });
});
