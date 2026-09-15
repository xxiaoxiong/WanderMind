import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { Layout } from "./components/Layout";
import { PreferencesProvider } from "./preferences";

function renderPreferences() {
  return render(
    <PreferencesProvider>
      <Layout activePath="/inbox">
        <div>content</div>
      </Layout>
    </PreferencesProvider>,
  );
}

describe("PreferencesProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dataset.theme = "dark";
  });

  it("switches languages and persists the preference", async () => {
    renderPreferences();

    fireEvent.click(screen.getByRole("button", { name: "Switch to Chinese" }));

    expect(await screen.findByText("灵感收集")).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement.lang).toBe("zh-CN"));
    expect(window.localStorage.getItem("wandermind-language")).toBe("zh-CN");
  });

  it("switches themes and persists the preference", async () => {
    renderPreferences();

    fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    expect(window.localStorage.getItem("wandermind-theme")).toBe("light");
  });

  it("restores stored language and theme", async () => {
    window.localStorage.setItem("wandermind-language", "zh-CN");
    window.localStorage.setItem("wandermind-theme", "light");

    renderPreferences();

    expect(await screen.findByText("洞见成果")).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });
});
