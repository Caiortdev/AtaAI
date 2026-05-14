import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", "[data-theme='dark']"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        bg: { 0: "var(--bg-0)", 1: "var(--bg-1)" },
        text: { DEFAULT: "var(--text)", dim: "var(--text-dim)", mute: "var(--text-mute)" },
        line: { DEFAULT: "var(--line)", strong: "var(--line-strong)" },
        accent: { DEFAULT: "var(--accent)", soft: "var(--accent-soft)", glow: "var(--accent-glow)" },
        recording: "var(--recording)",
        success: "var(--success)",
        warning: "var(--warning)",
      },
      borderRadius: {
        glass: "var(--radius)",
        "glass-lg": "var(--radius-lg)",
        "glass-sm": "var(--radius-sm)",
      },
    },
  },
  plugins: [],
} satisfies Config;
