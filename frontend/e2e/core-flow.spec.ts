import { expect, test } from "@playwright/test";

const wonder = {
  id: "wonder-1",
  candidate_id: "candidate-1",
  type: "connection",
  statement: "Backpressure in software may resemble pheromone decay in ant colonies.",
  explanation: "Both mechanisms dampen local demand before the whole system overloads.",
  why_interesting: "It suggests decentralized overload control can emerge from fading signals.",
  source_items: ["item-1", "item-2"],
  connection_path: ["item-1", "item-2"],
  supporting_evidence: [],
  counter_evidence: [],
  assumptions: [],
  questions: ["Which decay rate stabilizes each system?"],
  scores: {
    novelty: 0.82,
    coherence: 0.78,
    usefulness: 0.71,
    surprise: 0.69,
    evidence_potential: 0.64,
    redundancy: 0.1,
    arbitrariness: 0.1,
    hallucination_risk: 0.2,
    total: 0.74,
  },
  confidence: 0.71,
  status: "active",
  parent_wonder_id: null,
  metadata: {},
  created_at: "2026-09-14T00:00:00Z",
};

test("captures a seed and surfaces a structured wonder", async ({ page }) => {
  await page.route("**/api/v1/knowledge?limit=100", async (route) => {
    await route.fulfill({ json: { items: [], offset: 0, limit: 100 } });
  });
  await page.route("**/api/v1/seeds", async (route) => {
    await route.fulfill({ status: 201, json: { id: "seed-1", content: "How do systems avoid overload?" } });
  });
  await page.route("**/api/v1/wander", async (route) => {
    await route.fulfill({
      json: {
        session: {
          id: "session-1",
          seed_id: "seed-1",
          state: "surface",
          status: "completed",
          trace: {
            steps: [],
            patches: [],
            operators: ["analogy"],
            candidate_ids: ["candidate-1"],
            final_wonder_ids: ["wonder-1"],
            stop_reason: "high_value_found",
          },
          created_at: "2026-09-14T00:00:00Z",
        },
        candidates: [{ id: "candidate-1", statement: wonder.statement }],
        wonders: [wonder],
      },
    });
  });
  await page.route("**/api/v1/wander/session-1/stream", async (route) => {
    const step = {
      id: "step-1",
      index: 0,
      state: "collision",
      action: "evaluate_collision",
      reason: "Compared distant knowledge patches.",
      item_ids: ["item-1", "item-2"],
      operator: "analogy",
      novelty_gain: 0.72,
      relevance: 0.62,
      collision_score: 0.68,
      created_at: "2026-09-14T00:00:00Z",
    };
    await route.fulfill({
      contentType: "text/event-stream",
      body: "event: wander_step\ndata: " + JSON.stringify(step) + "\n\nevent: completed\ndata: {}\n\n",
    });
  });
  await page.route("**/api/v1/wonders/wonder-1/explore", async (route) => {
    await route.fulfill({
      json: {
        wonder,
        evaluation: {
          explorer: {
            expanded_idea: wonder.explanation,
            implications: ["The decay rate can be measured."],
            follow_up_questions: wonder.questions,
          },
          evidence: {
            supporting_evidence: [],
            counter_evidence: [],
            source_refs: [],
            uncertainty: 0.9,
            status: "completed",
          },
          critic: {
            weakness: ["Evidence is still local."],
            obviousness: 0.2,
            over_analogy: false,
            factual_risk: 0.3,
            alternative_explanation: [],
            verdict: "pass",
          },
        },
      },
    });
  });
  await page.route("**/api/v1/wonders/wonder-1/feedback", async (route) => {
    await route.fulfill({ status: 201, json: { id: "feedback-1" } });
  });
  await page.route("**/api/v1/wonders/wonder-1", async (route) => {
    await route.fulfill({ json: wonder });
  });

  await page.goto("/#/inbox");
  await page.getByLabel("Drop a thought").fill("How do systems avoid overload?");
  await page.getByRole("button", { name: /Begin wandering/ }).click();
  await expect(page).toHaveURL(/#\/wander\?seed=seed-1/);
  await page.getByRole("button", { name: "Run wander" }).click();
  await expect(page.getByText(wonder.statement)).toBeVisible();
  await expect(page.getByText("evaluate collision")).toBeVisible();
  await expect(page.getByText("1 candidate")).toBeVisible();
  await page.getByRole("link", { name: "Open wonder" }).click();
  await expect(page.getByText("Core idea")).toBeVisible();
  await page.getByRole("button", { name: "Continue exploring" }).click();
  await expect(page.getByText("Explorer, evidence, and critic passes completed.")).toBeVisible();
  await page.getByRole("button", { name: "Save this wonder" }).click();
  await expect(page.getByText("Feedback saved.")).toBeVisible();
});

test("lists curated wonders", async ({ page }) => {
  await page.route("**/api/v1/wonders?limit=100", async (route) => {
    await route.fulfill({ json: [wonder] });
  });
  await page.goto("/#/wonders");
  await expect(page.getByText("Today your mind")).toBeVisible();
  await expect(page.getByText(wonder.statement)).toBeVisible();
  await expect(page.getByRole("link", { name: "Why?" })).toHaveAttribute("href", "#/wonders/wonder-1");
});
