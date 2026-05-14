import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { setAuthToken, setOnUnauthorized } from "./api";
import { AppLayout } from "./components/AppLayout";
import { AuthScreen } from "./components/AuthScreen";
import { AtasView } from "./components/views/AtasView";
import { CaptureView } from "./components/views/CaptureView";
import { EstudioView } from "./components/views/EstudioView";
import { HomeView } from "./components/views/HomeView";
import { SettingsView } from "./components/views/SettingsView";
import { useWorkspaceStore } from "./store";
import type { User } from "./types";

export default function App() {
  const queryClient = useQueryClient();
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const user = useWorkspaceStore((s) => s.user);
  const activeTab = useWorkspaceStore((s) => s.activeTab);
  const isRecording = useWorkspaceStore((s) => s.isRecording);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
  const setSession = useWorkspaceStore((s) => s.setSession);
  const clearSession = useWorkspaceStore((s) => s.clearSession);

  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);

  useEffect(() => {
    setAuthToken(accessToken);
  }, [accessToken]);

  useEffect(() => {
    setOnUnauthorized(() => {
      clearSession();
      queryClient.clear();
    });
  }, [clearSession, queryClient]);

  function handleAuthSuccess(token: string, authenticatedUser: User) {
    setAuthToken(token);
    setSession(token, authenticatedUser);
    void queryClient.invalidateQueries({ queryKey: ["meetings"] });
  }

  function handleLogout() {
    clearSession();
    queryClient.clear();
  }

  const navigateToAtas = useCallback(() => {
    setActiveTab("atas");
  }, [setActiveTab]);

  if (!accessToken || !user) {
    return <AuthScreen onSuccess={handleAuthSuccess} />;
  }

  return (
    <AppLayout
      activeTab={activeTab}
      onNavigate={setActiveTab}
      isRecording={isRecording}
      onLogout={handleLogout}
    >
      {activeTab === "home" && (
        <HomeView
          selectedPresetId={selectedPresetId}
          onSelectPreset={setSelectedPresetId}
          onNavigateToAtas={navigateToAtas}
        />
      )}
      {activeTab === "capture" && (
        <CaptureView onFinished={navigateToAtas} />
      )}
      {activeTab === "estudio" && <EstudioView />}
      {activeTab === "atas" && <AtasView />}
      {activeTab === "settings" && <SettingsView />}
    </AppLayout>
  );
}
