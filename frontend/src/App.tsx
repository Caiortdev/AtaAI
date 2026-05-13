import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { listMeetings, setAuthToken } from "./api";
import { AppShell } from "./components/AppShell";
import { AuthScreen } from "./components/AuthScreen";
import { MeetingDetail } from "./components/MeetingDetail";
import { MeetingForm } from "./components/MeetingForm";
import { MeetingList } from "./components/MeetingList";
import { PresetsPanel } from "./components/PresetsPanel";
import { DesignSystemDemo } from "./DesignSystemDemo";
import { useWorkspaceStore } from "./store";
import type { User } from "./types";

const SHOW_DESIGN_DEMO = true;

export default function App() {
  if (SHOW_DESIGN_DEMO) return <DesignSystemDemo />;
  const queryClient = useQueryClient();
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const user = useWorkspaceStore((s) => s.user);
  const selectedMeetingId = useWorkspaceStore((s) => s.selectedMeetingId);
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);
  const setSession = useWorkspaceStore((s) => s.setSession);
  const clearSession = useWorkspaceStore((s) => s.clearSession);

  const [activeView, setActiveView] = useState("meetings");
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    setAuthToken(accessToken);
  }, [accessToken]);

  useEffect(() => {
    function updateOnlineStatus() {
      setIsOnline(navigator.onLine);
    }
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  const meetingsQuery = useQuery({
    queryKey: ["meetings", accessToken],
    queryFn: listMeetings,
    enabled: Boolean(accessToken),
  });

  const meetings = meetingsQuery.data ?? [];
  const selectedMeeting = useMemo(
    () => meetings.find((m) => m.id === selectedMeetingId) ?? meetings[0],
    [meetings, selectedMeetingId],
  );

  const hasRunningMeeting = meetings.some(
    (m) => m.status === "queued" || m.status === "processing" || m.status === "recording",
  );

  useEffect(() => {
    if (!hasRunningMeeting) return undefined;
    const interval = window.setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["meetings"] });
    }, 2000);
    return () => window.clearInterval(interval);
  }, [hasRunningMeeting, queryClient]);

  function handleAuthSuccess(token: string, authenticatedUser: User) {
    setSession(token, authenticatedUser);
    void queryClient.invalidateQueries({ queryKey: ["meetings"] });
  }

  function handleLogout() {
    clearSession();
    queryClient.clear();
  }

  if (!accessToken || !user) {
    return <AuthScreen onSuccess={handleAuthSuccess} />;
  }

  return (
    <AppShell
      activeView={activeView}
      onNavigate={setActiveView}
      isOnline={isOnline}
      onLogout={handleLogout}
    >
      {activeView === "new" && <MeetingForm />}
      {activeView === "presets" && (
        <PresetsPanel selectedPresetId={selectedPresetId} onSelectPreset={setSelectedPresetId} />
      )}
      {activeView === "meetings" && (
        <div className="space-y-5">
          <MeetingList />
          {selectedMeeting && (
            <MeetingDetail meeting={selectedMeeting} selectedPresetId={selectedPresetId} />
          )}
          {!selectedMeeting && (
            <div className="rounded-lg border border-border bg-surface p-8 text-center">
              <p className="text-text-secondary">
                Selecione uma reuniao ou crie uma nova para comecar.
              </p>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
