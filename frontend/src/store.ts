import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "./types";

type WorkspaceState = {
  selectedMeetingId: string | null;
  accessToken: string | null;
  user: User | null;
  selectMeeting: (id: string | null) => void;
  setSession: (accessToken: string, user: User) => void;
  clearSession: () => void;
};

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      selectedMeetingId: null,
      accessToken: null,
      user: null,
      selectMeeting: (id) => set({ selectedMeetingId: id }),
      setSession: (accessToken, user) => set({ accessToken, user, selectedMeetingId: null }),
      clearSession: () => set({ accessToken: null, user: null, selectedMeetingId: null }),
    }),
    {
      name: "ataai-workspace",
      partialize: (state) => ({ accessToken: state.accessToken, user: state.user }),
    },
  ),
);
