import {
  Bell,
  Camera,
  Gauge,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  Users,
} from "lucide-react";

import type { Role, User } from "../types";
import { canWrite } from "../utils/format";

export type ActivePage = "overview" | "cameras" | "events" | "people" | "settings";

const navItems: Array<{ id: ActivePage; label: string; icon: typeof LayoutDashboard; writeOnly?: boolean }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "cameras", label: "Cameras", icon: Camera },
  { id: "events", label: "Events", icon: Bell },
  { id: "people", label: "People", icon: Users, writeOnly: true },
  { id: "settings", label: "Settings", icon: Settings },
];

type AppShellProps = {
  activePage: ActivePage;
  children: React.ReactNode;
  loading: boolean;
  user: User;
  onNavigate: (page: ActivePage) => void;
  onRefresh: () => void;
  onLogout: () => void;
};

function visibleNavItems(role: Role) {
  return navItems.filter((item) => !item.writeOnly || canWrite(role));
}

export function AppShell({ activePage, children, loading, user, onNavigate, onRefresh, onLogout }: AppShellProps) {
  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <span>AI Camera</span>
        </div>

        <nav className="nav-list">
          {visibleNavItems(user.role).map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={`nav-item ${activePage === item.id ? "nav-item--active" : ""}`}
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>Operations Dashboard</h1>
            <p>Local MVP - one camera - person-only detection</p>
          </div>
          <div className="topbar-actions">
            <div className="role-chip">
              <Gauge aria-hidden="true" />
              <span>{user.username}</span>
              <strong>{user.role}</strong>
            </div>
            <button className="secondary-button" type="button" onClick={onRefresh} disabled={loading}>
              {loading ? "Refreshing" : "Refresh"}
            </button>
            <button className="icon-button" type="button" onClick={onLogout} aria-label="Sign out">
              <LogOut aria-hidden="true" />
            </button>
          </div>
        </header>

        {children}
      </section>
    </main>
  );
}
