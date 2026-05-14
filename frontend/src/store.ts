import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "./types";

type Theme = "light" | "dark" | "system";
type TabId = "home" | "capture" | "atas" | "estudio" | "settings";

type WorkspaceState = {
  selectedMeetingId: string | null;
  accessToken: string | null;
  user: User | null;
  theme: Theme;
  activeTab: TabId;
  isRecording: boolean;
  selectMeeting: (id: string | null) => void;
  setSession: (accessToken: string, user: User) => void;
  clearSession: () => void;
  setTheme: (theme: Theme) => void;
  setActiveTab: (tab: TabId) => void;
  setIsRecording: (recording: boolean) => void;
};

function applyThemeClass(theme: Theme) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = theme === "dark" || (theme === "system" && prefersDark);
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
}

const VALID_TABS: TabId[] = ["home", "capture", "atas", "estudio", "settings"];

function isValidTab(tab: unknown): tab is TabId {
  return typeof tab === "string" && VALID_TABS.includes(tab as TabId);
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      selectedMeetingId: null,
      accessToken: null,
      user: null,
      theme: "system",
      activeTab: "home",
      isRecording: false,
      selectMeeting: (id) => set({ selectedMeetingId: id }),
      setSession: (accessToken, user) => set({ accessToken, user, selectedMeetingId: null }),
      clearSession: () => set({ accessToken: null, user: null, selectedMeetingId: null }),
      setTheme: (theme) => {
        applyThemeClass(theme);
        set({ theme });
      },
      setActiveTab: (tab) => set({ activeTab: tab }),
      setIsRecording: (recording) => set({ isRecording: recording }),
    }),
    {
      name: "ataai-workspace",
      partialize: (state) => ({ accessToken: state.accessToken, user: state.user, theme: state.theme, activeTab: state.activeTab }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyThemeClass(state.theme);
          if (!isValidTab(state.activeTab)) {
            state.activeTab = "home";
          }
        }
      },
    },
  ),
);
