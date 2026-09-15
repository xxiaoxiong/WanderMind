import type { ReactNode } from "react";

interface LayoutProps {
  activePath: string;
  children: ReactNode;
}

const navItems = [
  { href: "#/inbox", label: "Inbox", mark: "01" },
  { href: "#/wander", label: "Wander", mark: "02" },
  { href: "#/wonders", label: "Wonders", mark: "03" },
];

export function Layout({ activePath, children }: LayoutProps) {
  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <aside className="sidebar">
        <a className="brand" href="#/inbox" aria-label="WanderMind home">
          <span className="brand-orbit" aria-hidden="true">
            <span />
          </span>
          <span>
            <strong>WanderMind</strong>
            <small>cognitive field notes</small>
          </span>
        </a>
        <nav className="main-nav" aria-label="Primary navigation">
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
          <p>Local-first workspace</p>
          <small>Your knowledge stays inside your configured environment.</small>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
