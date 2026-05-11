import { create } from "zustand";

type WorkspaceState = {
  selectedMeetingId: string | null;
  selectMeeting: (id: string | null) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  selectedMeetingId: null,
  selectMeeting: (id) => set({ selectedMeetingId: id }),
}));
