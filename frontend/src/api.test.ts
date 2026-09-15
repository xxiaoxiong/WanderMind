import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

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
});
