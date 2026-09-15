import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { PreferencesProvider } from "./preferences";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element is missing");

createRoot(root).render(
  <StrictMode>
    <PreferencesProvider>
      <App />
    </PreferencesProvider>
  </StrictMode>,
);
