import { type ReactNode, useState } from "react";

import { useWorkspaceStore } from "../store";
import { ThemeToggle } from "./ThemeToggle";

type NavItem = {
  id: string;
  label: string;
  icon: string;
};

const navItems: NavItem[] = [
  {
    id: "meetings",
    label: "Reuniões",
    icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10",
  },
  {
    id: "new",
    label: "Nova reunião",
    icon: "M12 4v16m8-8H4",
  },
  {
    id: "presets",
    label: "Presets",
    icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  },
];

type AppShellProps = {
  activeView: string;
  onNavigate: (view: string) => void;
  isOnline: boolean;
  onLogout: () => void;
  children: ReactNode;
  sidebar?: ReactNode;
};

export function AppShell({
  activeView,
  onNavigate,
  isOnline,
  onLogout,
  children,
  sidebar,
}: AppShellProps) {
  const user = useWorkspaceStore((s) => s.user);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg-primary">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded-md p-1.5 text-text-secondary transition hover:bg-bg-tertiary hover:text-text-primary lg:hidden"
            aria-label="Toggle menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-xs font-bold text-white">
              A
            </div>
            <span className="text-sm font-semibold text-text-primary">AtaAI</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <span
            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
              isOnline
                ? "border-success/30 bg-success-muted text-success"
                : "border-warning/30 bg-warning-muted text-warning"
            }`}
          >
            {isOnline ? "Online" : "Offline"}
          </span>
          {user && (
            <span className="rounded-full border border-border bg-bg-secondary px-2.5 py-1 text-xs text-text-secondary">
              {user.name}
            </span>
          )}
          <button
            onClick={onLogout}
            className="rounded-md px-2.5 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-bg-tertiary hover:text-danger"
          >
            Sair
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside
          className={`shrink-0 border-r border-border bg-bg-secondary transition-all duration-200 ${
            sidebarOpen ? "w-56" : "w-0 overflow-hidden lg:w-14"
          }`}
        >
          <nav className="flex flex-col gap-1 p-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                  activeView === item.id
                    ? "bg-accent-muted text-accent font-medium"
                    : "text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"
                }`}
                title={item.label}
              >
                <svg
                  className="h-4.5 w-4.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={item.icon} />
                </svg>
                <span className={sidebarOpen ? "" : "hidden lg:hidden"}>{item.label}</span>
              </button>
            ))}
          </nav>
          {sidebar}
        </aside>

        <main className="flex-1 overflow-y-auto p-5">{children}</main>
      </div>
    </div>
  );
}
