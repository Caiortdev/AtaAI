import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "./types";

type Theme = "light" | "dark" | "system";

type WorkspaceState = {
  selectedMeetingId: string | null;
  accessToken: string | null;
  user: User | null;
  theme: Theme;
  selectMeeting: (id: string | null) => void;
  setSession: (accessToken: string, user: User) => void;
  clearSession: () => void;
  setTheme: (theme: Theme) => void;
};

function applyThemeClass(theme: Theme) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = theme === "dark" || (theme === "system" && prefersDark);
  document.documentElement.classList.toggle("dark", isDark);
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      selectedMeetingId: null,
      accessToken: null,
      user: null,
      theme: "system",
      selectMeeting: (id) => set({ selectedMeetingId: id }),
      setSession: (accessToken, user) => set({ accessToken, user, selectedMeetingId: null }),
      clearSession: () => set({ accessToken: null, user: null, selectedMeetingId: null }),
      setTheme: (theme) => {
        applyThemeClass(theme);
        set({ theme });
      },
    }),
    {
      name: "ataai-workspace",
      partialize: (state) => ({ accessToken: state.accessToken, user: state.user, theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        if (state) applyThemeClass(state.theme);
      },
    },
  ),
);
