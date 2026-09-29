import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { PreferencesProvider } from "../preferences";
import type { AutopilotSnapshot } from "../types";
import { AutopilotPage } from "./AutopilotPage";

const snapshot: AutopilotSnapshot = {
  campaign: {
    id: "campaign-1",
    objective: "Keep testing hidden assumptions",
    status: "active",
    current_session_id: null,
    cycles_started: 8,
    cycles_completed: 7,
    total_candidates: 41,
    total_wonders: 9,
    total_runtime_calls: 56,
    promoted_knowledge_count: 6,
    consecutive_failures: 0,
    started_at: "2026-09-29T00:00:00Z",
    last_cycle_started_at: "2026-09-29T00:07:00Z",
    last_cycle_completed_at: "2026-09-29T00:08:00Z",
    next_cycle_at: "2026-09-29T00:09:00Z",
    last_error: null,
    metadata: {},
  },
  current_session: null,
  current_seed: null,
  current_runtime: {
    configured_adapter: "openai",
    provider: null,
    model: null,
    calls: 0,
    completed_calls: 0,
    failed_calls: 0,
    duration_seconds: 0,
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    purposes: [],
    verified: false,
  },
  latest_wonders: [],
  knowledge_count: 28,
  generated_knowledge_count: 6,
  worker_running: true,
};

describe("AutopilotPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("shows cumulative progress and pauses through the persistent API", async () => {
    vi.spyOn(api, "getAutopilotStatus").mockResolvedValue(snapshot);
    const pause = vi.spyOn(api, "pauseAutopilot").mockResolvedValue({
      ...snapshot,
      campaign: snapshot.campaign ? { ...snapshot.campaign, status: "paused" } : null,
    });

    render(
      <PreferencesProvider>
        <AutopilotPage />
      </PreferencesProvider>,
    );

    expect(await screen.findByText("41")).toBeInTheDocument();
    expect(screen.getByText("supervisor online")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pause after checkpoint" }));

    await waitFor(() => expect(pause).toHaveBeenCalledOnce());
    expect(await screen.findByRole("button", { name: "Resume" })).toBeInTheDocument();
  });
});
