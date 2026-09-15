import { useEffect, useState } from "react";

import { Layout } from "./components/Layout";
import { InboxPage } from "./pages/InboxPage";
import { WanderPage } from "./pages/WanderPage";
import { WonderDetailPage } from "./pages/WonderDetailPage";
import { WondersPage } from "./pages/WondersPage";

interface RouteState {
  path: string;
  query: URLSearchParams;
}

function readRoute(): RouteState {
  const raw = window.location.hash.slice(1) || "/inbox";
  const separator = raw.indexOf("?");
  const path = separator === -1 ? raw : raw.slice(0, separator);
  const query = new URLSearchParams(separator === -1 ? "" : raw.slice(separator + 1));
  return { path, query };
}

export function navigate(path: string): void {
  window.location.hash = path;
}

export function App() {
  const [route, setRoute] = useState(readRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  let content = <InboxPage />;
  if (route.path === "/wander") {
    content = <WanderPage seedId={route.query.get("seed")} />;
  } else if (route.path === "/wonders") {
    content = <WondersPage />;
  } else if (route.path.startsWith("/wonders/")) {
    content = <WonderDetailPage wonderId={route.path.slice("/wonders/".length)} />;
  }

  return <Layout activePath={route.path}>{content}</Layout>;
}
