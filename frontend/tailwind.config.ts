import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        glass: {
          bg: "var(--glass-bg)",
          border: "var(--glass-border)",
          highlight: "var(--glass-highlight)",
        },
        surface: "var(--color-surface)",
        overlay: "var(--color-overlay)",
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          tertiary: "var(--color-text-tertiary)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          hover: "var(--color-accent-hover)",
        },
        danger: "var(--color-danger)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
      },
      boxShadow: {
        glass: "0 2px 16px var(--glass-shadow), inset 0 1px 0 var(--glass-highlight)",
        "glass-lg": "0 8px 32px var(--glass-shadow), inset 0 1px 0 var(--glass-highlight)",
        "glass-sm": "0 1px 8px var(--glass-shadow), inset 0 0.5px 0 var(--glass-highlight)",
      },
      backdropBlur: {
        glass: "20px",
        "glass-lg": "40px",
      },
      borderRadius: {
        glass: "16px",
        "glass-sm": "12px",
        "glass-xs": "8px",
      },
    },
  },
  plugins: [],
} satisfies Config;
