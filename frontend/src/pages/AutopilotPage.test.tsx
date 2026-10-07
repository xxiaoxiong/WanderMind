import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  accepted_generated_knowledge_count: 5,
  rejected_generated_knowledge_count: 1,
  worker_running: true,
};

describe("AutopilotPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => vi.useRealTimers());

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

  it("preserves an edited objective during polling and saves it without resuming", async () => {
    vi.useFakeTimers();
    const pausedSnapshot = {
      ...snapshot,
      campaign: snapshot.campaign ? { ...snapshot.campaign, status: "paused" as const } : null,
    };
    const getStatus = vi.spyOn(api, "getAutopilotStatus").mockResolvedValue(pausedSnapshot);
    const updateObjective = vi.spyOn(api, "updateAutopilotObjective").mockImplementation(
      (objective) => Promise.resolve({
        ...pausedSnapshot,
        campaign: pausedSnapshot.campaign ? { ...pausedSnapshot.campaign, objective } : null,
      }),
    );
    render(
      <PreferencesProvider>
        <AutopilotPage />
      </PreferencesProvider>,
    );

    await act(async () => Promise.resolve());
    const objective = screen.getByRole("textbox", {
      name: "Persistent exploration objective",
    });
    fireEvent.change(objective, {
      target: { value: "Design resilient, high-quality agent architectures" },
    });
    await act(async () => vi.advanceTimersByTimeAsync(3_000));

    expect(getStatus).toHaveBeenCalledTimes(2);
    expect(objective).toHaveValue("Design resilient, high-quality agent architectures");

    fireEvent.click(screen.getByRole("button", { name: "Save objective" }));
    await act(async () => Promise.resolve());
    expect(updateObjective).toHaveBeenCalledWith(
      "Design resilient, high-quality agent architectures",
    );
    expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();
  });

  it("submits the edited objective when resuming", async () => {
    const pausedSnapshot = {
      ...snapshot,
      campaign: snapshot.campaign ? { ...snapshot.campaign, status: "paused" as const } : null,
    };
    vi.spyOn(api, "getAutopilotStatus").mockResolvedValue(pausedSnapshot);
    const start = vi.spyOn(api, "startAutopilot").mockImplementation((objective) => Promise.resolve({
      ...pausedSnapshot,
      campaign: pausedSnapshot.campaign
        ? { ...pausedSnapshot.campaign, objective: objective ?? "", status: "active" as const }
        : null,
    }));
    const resume = vi.spyOn(api, "resumeAutopilot");

    render(
      <PreferencesProvider>
        <AutopilotPage />
      </PreferencesProvider>,
    );

    const objective = await screen.findByRole("textbox", {
      name: "Persistent exploration objective",
    });
    fireEvent.change(objective, {
      target: { value: "Design observable, testable agent architectures" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Resume" }));

    await waitFor(() => {
      expect(start).toHaveBeenCalledWith("Design observable, testable agent architectures");
    });
    expect(resume).not.toHaveBeenCalled();
  });
});
