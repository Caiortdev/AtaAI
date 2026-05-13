import { useWorkspaceStore } from "../store";

const themes = ["light", "dark", "system"] as const;

const icons: Record<(typeof themes)[number], string> = {
  light: "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z",
  dark: "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z",
  system: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
};

const labels: Record<(typeof themes)[number], string> = {
  light: "Claro",
  dark: "Escuro",
  system: "Sistema",
};

export function ThemeToggle() {
  const theme = useWorkspaceStore((s) => s.theme);
  const setTheme = useWorkspaceStore((s) => s.setTheme);

  function cycle() {
    const currentIndex = themes.indexOf(theme);
    const next = themes[(currentIndex + 1) % themes.length];
    setTheme(next);
  }

  return (
    <button
      onClick={cycle}
      className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-text-secondary transition hover:bg-bg-tertiary hover:text-text-primary"
      title={`Tema: ${labels[theme]}`}
      aria-label={`Alternar tema. Atual: ${labels[theme]}`}
    >
      <svg
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={icons[theme]} />
      </svg>
      <span className="hidden sm:inline">{labels[theme]}</span>
    </button>
  );
}
