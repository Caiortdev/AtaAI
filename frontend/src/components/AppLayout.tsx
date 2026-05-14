import type { ReactNode } from "react";
import { Icon } from "./ui/Icon";
import { useWorkspaceStore } from "../store";

type TabId = "home" | "capture" | "atas" | "estudio" | "logs" | "settings";

type AppLayoutProps = {
  activeTab: TabId;
  onNavigate: (tab: TabId) => void;
  isRecording: boolean;
  onLogout: () => void;
  children: ReactNode;
};

const ROUTES: { id: TabId; label: string; icon: string }[] = [
  { id: "home", label: "Home", icon: "house" },
  { id: "capture", label: "Captura", icon: "microphone-stage" },
  { id: "estudio", label: "Estúdio", icon: "sliders" },
  { id: "atas", label: "Atas", icon: "notebook" },
  { id: "logs", label: "Logs", icon: "list-bullets" },
  { id: "settings", label: "Config", icon: "gear" },
];

export function AppLayout({ activeTab, onNavigate, isRecording, onLogout, children }: AppLayoutProps) {
  const user = useWorkspaceStore((s) => s.user);
  const theme = useWorkspaceStore((s) => s.theme);
  const setTheme = useWorkspaceStore((s) => s.setTheme);

  function toggleTheme() {
    const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setTheme(isDark ? "light" : "dark");
  }

  const currentTheme = theme === "system"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : theme;

  return (
    <>
      <div className="bg-mesh"><div className="blob" /></div>
      <div className="grain" />

      <div className="app">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">
              <Icon name="waveform" weight="fill" />
            </div>
            <div className="brand-name">AtaAI <span>· beta</span></div>
          </div>

          <div className="top-actions">
            <button className="icon-btn" title="Buscar">
              <Icon name="magnifying-glass" />
            </button>
            <button className="icon-btn" title="Notificações" style={{ position: "relative" }}>
              <Icon name="bell" />
              {isRecording && (
                <span style={{
                  position: "absolute", top: 7, right: 7,
                  width: 8, height: 8, borderRadius: "50%",
                  background: "var(--recording)", border: "2px solid var(--bg-1)",
                }} />
              )}
            </button>
            <button
              className="icon-btn"
              title={currentTheme === "dark" ? "Tema claro" : "Tema escuro"}
              onClick={toggleTheme}
            >
              <Icon name={currentTheme === "dark" ? "sun" : "moon"} weight="duotone" />
            </button>
            <button onClick={onLogout} className="avatar-btn" title={user?.name || ""}>
              {user?.name?.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase() || "U"}
            </button>
          </div>
        </header>

        <main className="main-content">
          {children}
        </main>

        <div className="dock-wrap">
          <div className="dock">
            {ROUTES.map((r) => (
              <button
                key={r.id}
                onClick={() => onNavigate(r.id)}
                className={`dock-item ${activeTab === r.id ? "active" : ""}`}
              >
                <Icon name={r.icon} weight={activeTab === r.id ? "fill" : "duotone"} />
                <span>{r.label}</span>
                <div className="dock-tip">{r.label}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
