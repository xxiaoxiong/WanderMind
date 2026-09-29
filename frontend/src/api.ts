import type {
  AutopilotSnapshot,
  ApiErrorEnvelope,
  DeepExploreResponse,
  KnowledgeItem,
  Seed,
  WanderRunResponse,
  WanderCompletion,
  WanderProgress,
  WanderSession,
  WanderStep,
  Wonder,
} from "./types";

const configuredApiRoot: unknown = import.meta.env.VITE_API_URL;
const API_ROOT = typeof configuredApiRoot === "string" ? configuredApiRoot : "/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly retryable: boolean;

  constructor(message: string, code = "request_failed", retryable = false) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = retryable;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_ROOT + path, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "content-type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let envelope: ApiErrorEnvelope;
    try {
      envelope = (await response.json()) as ApiErrorEnvelope;
    } catch {
      throw new ApiError("The server returned an unreadable response.");
    }
    throw new ApiError(
      envelope.error.message,
      envelope.error.code,
      envelope.error.retryable,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  getAutopilotStatus(): Promise<AutopilotSnapshot> {
    return request("/autopilot/status");
  },
  startAutopilot(objective?: string): Promise<AutopilotSnapshot> {
    return request("/autopilot/start", {
      method: "POST",
      body: JSON.stringify({ objective: objective || null }),
    });
  },
  resumeAutopilot(): Promise<AutopilotSnapshot> {
    return request("/autopilot/resume", { method: "POST" });
  },
  pauseAutopilot(): Promise<AutopilotSnapshot> {
    return request("/autopilot/pause", { method: "POST" });
  },
  stopAutopilot(): Promise<AutopilotSnapshot> {
    return request("/autopilot/stop", { method: "POST" });
  },
  createKnowledge(payload: {
    title?: string;
    content: string;
    type?: string;
    source_ref?: string;
  }): Promise<KnowledgeItem> {
    return request("/knowledge", { method: "POST", body: JSON.stringify(payload) });
  },
  uploadDocument(file: File): Promise<KnowledgeItem> {
    const body = new FormData();
    body.append("file", file);
    return request("/knowledge/document", { method: "POST", body });
  },
  listKnowledge(): Promise<{ items: KnowledgeItem[]; offset: number; limit: number }> {
    return request("/knowledge?limit=100");
  },
  createSeed(content: string): Promise<Seed> {
    return request("/seeds", { method: "POST", body: JSON.stringify({ content }) });
  },
  runWander(payload: { seed_id?: string; content?: string }): Promise<WanderRunResponse> {
    return request("/wander", {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        budget: {
          max_steps: 12,
          max_patch_switches: 3,
          max_candidates: 4,
          max_runtime_calls: 4,
          time_budget_seconds: 100,
        },
      }),
    });
  },
  startWander(payload: { seed_id?: string; content?: string }): Promise<WanderSession> {
    return request("/wander/start", {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        budget: {
          max_steps: 24,
          max_patch_switches: 8,
          max_candidates: 8,
          min_candidates: 4,
          target_wonders: 3,
          max_stagnant_candidates: 5,
          stop_on_first_wonder: false,
          max_runtime_calls: 16,
          time_budget_seconds: 900,
        },
      }),
    });
  },
  getWanderResult(id: string): Promise<WanderRunResponse> {
    return request("/wander/" + id + "/result");
  },
  stopWander(id: string): Promise<WanderSession> {
    return request("/wander/" + id + "/stop", { method: "POST" });
  },
  listWonders(): Promise<Wonder[]> {
    return request("/wonders?limit=100");
  },
  getWonder(id: string): Promise<Wonder> {
    return request("/wonders/" + id);
  },
  exploreWonder(id: string): Promise<DeepExploreResponse> {
    return request("/wonders/" + id + "/explore", { method: "POST" });
  },
  rewonder(id: string): Promise<Wonder | null> {
    return request("/wonders/" + id + "/rewonder", { method: "POST" });
  },
  feedback(id: string, action: string, note?: string): Promise<void> {
    return request("/wonders/" + id + "/feedback", {
      method: "POST",
      body: JSON.stringify({ action, note: note || null }),
    });
  },
  runIncubation(): Promise<{ surfaced: boolean; wonder: Wonder | null }> {
    return request("/incubation/run", { method: "POST" });
  },
};

export async function streamWanderTrace(
  sessionId: string,
  onStep: (step: WanderStep) => void,
  onProgress?: (progress: WanderProgress) => void,
  after = -1,
): Promise<WanderCompletion> {
  const response = await fetch(
    API_ROOT + "/wander/" + sessionId + "/stream?after=" + after,
  );
  if (!response.ok || !response.body) {
    throw new ApiError("The wander trace could not be streamed.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const result = await reader.read();
    if (result.done) break;
    buffer += decoder.decode(result.value, { stream: true }).replaceAll("\r\n", "\n");
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = parseEvent(chunk);
      if (event.name === "wander_step" && event.data) {
        onStep(JSON.parse(event.data) as WanderStep);
      }
      if (event.name === "progress" && event.data) {
        onProgress?.(JSON.parse(event.data) as WanderProgress);
      }
      if (event.name === "completed" && event.data) {
        return JSON.parse(event.data) as WanderCompletion;
      }
    }
  }
  throw new ApiError("The wander trace ended before the task completed.", "stream_interrupted", true);
}

function parseEvent(chunk: string): { name: string; data: string } {
  let name = "message";
  const data: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) name = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  return { name, data: data.join("\n") };
}
