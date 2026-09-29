import { afterEach, describe, expect, it, vi } from "vitest";

import { api, streamWanderTrace } from "./api";

describe("api client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("creates a seed through the versioned API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "seed-1", content: "A thought" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const seed = await api.createSeed("A thought");

    expect(seed.id).toBe("seed-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/seeds",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("preserves the backend error contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "duplicate_knowledge",
              message: "Already captured",
              details: {},
              retryable: false,
            },
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    await expect(api.createKnowledge({ content: "same" })).rejects.toMatchObject({
      code: "duplicate_knowledge",
      message: "Already captured",
      retryable: false,
    });
  });

  it("starts a persistent deep wander", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "wander-1", status: "pending" }), {
        status: 202,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.startWander({ content: "Compare these systems" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    if (typeof init.body !== "string") throw new Error("expected a JSON request body");
    const body = JSON.parse(init.body) as { budget: Record<string, unknown> };
    expect(body.budget).toMatchObject({
      min_candidates: 4,
      target_wonders: 3,
      stop_on_first_wonder: false,
      max_runtime_calls: 16,
    });
  });

  it("controls and reads the persistent Autopilot campaign", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ campaign: { status: "active" }, worker_running: true }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.getAutopilotStatus();
    await api.startAutopilot("Keep discovering testable mechanisms");
    await api.pauseAutopilot();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/autopilot/status",
      expect.objectContaining({ headers: { "content-type": "application/json" } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/autopilot/start",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ objective: "Keep discovering testable mechanisms" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/autopilot/pause",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("parses live progress and completion events", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          [
            "event: progress\ndata: {\"status\":\"running\",\"state\":\"generate\",\"candidate_count\":1,\"wonder_count\":0,\"runtime_calls_used\":1}",
            "event: wander_step\nid: 0\ndata: {\"id\":\"step-1\",\"index\":0,\"state\":\"seeding\",\"action\":\"select_seed\",\"reason\":\"seed\",\"item_ids\":[],\"operator\":null,\"novelty_gain\":null,\"relevance\":null,\"collision_score\":null,\"created_at\":\"2026-01-01T00:00:00Z\"}",
            "event: completed\ndata: {\"status\":\"completed\",\"stop_reason\":\"target_wonders_reached\",\"wonder_ids\":[],\"patch_ids\":[],\"candidate_count\":4}",
            "",
          ].join("\n\n"),
          { status: 200, headers: { "content-type": "text/event-stream" } },
        ),
      ),
    );
    const steps = vi.fn();
    const progress = vi.fn();

    const completion = await streamWanderTrace("wander-1", steps, progress);

    expect(progress).toHaveBeenCalledWith(expect.objectContaining({ candidate_count: 1 }));
    expect(steps).toHaveBeenCalledWith(expect.objectContaining({ action: "select_seed" }));
    expect(completion.stop_reason).toBe("target_wonders_reached");
  });
});
