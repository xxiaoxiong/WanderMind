import type { ReactNode } from "react";

import { usePreferences } from "../preferences";

interface LayoutProps {
  activePath: string;
  children: ReactNode;
}

export function Layout({ activePath, children }: LayoutProps) {
  const { language, setLanguage, setTheme, t, theme } = usePreferences();
  const navItems = [
    { href: "#/inbox", label: t("nav.inbox"), mark: "01" },
    { href: "#/wander", label: t("nav.wander"), mark: "02" },
    { href: "#/wonders", label: t("nav.wonders"), mark: "03" },
  ];

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="preference-controls" aria-label={t("preferences.aria")}>
        <button
          className="preference-button"
          aria-label={language === "en" ? t("preferences.chinese") : t("preferences.english")}
          title={language === "en" ? t("preferences.chinese") : t("preferences.english")}
          onClick={() => setLanguage(language === "en" ? "zh-CN" : "en")}
        >
          {language === "en" ? "中" : "EN"}
        </button>
        <button
          className="preference-button"
          aria-label={theme === "dark" ? t("preferences.light") : t("preferences.dark")}
          title={theme === "dark" ? t("preferences.light") : t("preferences.dark")}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
        </button>
      </div>
      <aside className="sidebar">
        <a className="brand" href="#/inbox" aria-label={t("app.home")}>
          <span className="brand-orbit" aria-hidden="true">
            <span />
          </span>
          <span>
            <strong>WanderMind</strong>
            <small>{t("app.tagline")}</small>
          </span>
        </a>
        <nav className="main-nav" aria-label={t("nav.aria")}>
          {navItems.map((item) => {
            const active =
              item.href === "#/wonders"
                ? activePath.startsWith("/wonders")
                : activePath === item.href.slice(1);
            return (
              <a className={active ? "active" : ""} href={item.href} key={item.href}>
                <span>{item.mark}</span>
                {item.label}
              </a>
            );
          })}
        </nav>
        <div className="sidebar-note">
          <span className="live-dot" />
          <p>{t("workspace.title")}</p>
          <small>{t("workspace.body")}</small>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
