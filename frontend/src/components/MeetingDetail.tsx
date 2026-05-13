import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { processMeeting, uploadMeetingFile } from "../api";
import type { AnalysisMode, Meeting } from "../types";
import { AnalysisTabs } from "./AnalysisTabs";
import { LiveWidget } from "./LiveWidget";
import { StatusBox } from "./StatusBox";
import { Button } from "./ui/Button";
import { Field } from "./ui/Input";
import { Panel } from "./ui/Panel";

type MeetingDetailProps = {
  meeting: Meeting;
  selectedPresetId: string | null;
};

export function MeetingDetail({ meeting, selectedPresetId }: MeetingDetailProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("audio_only");
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: ({ meetingId, file }: { meetingId: string; file: File }) =>
      uploadMeetingFile(meetingId, file),
    onSuccess: async () => {
      setSelectedFile(null);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => setError(err.message),
  });

  const processMutation = useMutation({
    mutationFn: ({ meetingId, mode }: { meetingId: string; mode: AnalysisMode }) =>
      processMeeting(meetingId, mode, selectedPresetId),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => setError(err.message),
  });

  function handleUpload() {
    if (!selectedFile) return;
    setError(null);
    uploadMutation.mutate({ meetingId: meeting.id, file: selectedFile });
  }

  function handleProcess() {
    setError(null);
    processMutation.mutate({ meetingId: meeting.id, mode: analysisMode });
  }

  return (
    <div className="space-y-5">
      {error && (
        <div className="rounded-md border border-danger/30 bg-danger-muted p-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[1fr_300px]">
        <Panel title="Processamento">
          <div className="space-y-4">
            <MeetingHeader meeting={meeting} />

            <div className="grid gap-3 md:grid-cols-2">
              <label className="option">
                <input
                  type="radio"
                  checked={analysisMode === "audio_only"}
                  onChange={() => setAnalysisMode("audio_only")}
                />
                <span>
                  <strong>Somente audio</strong>
                  <small>Extrai audio do video e ignora imagem.</small>
                </span>
              </label>
              <label className="option">
                <input
                  type="radio"
                  checked={analysisMode === "audio_video"}
                  onChange={() => setAnalysisMode("audio_video")}
                />
                <span>
                  <strong>Audio + video</strong>
                  <small>Reservado para contexto visual.</small>
                </span>
              </label>
            </div>

            <div className="rounded-md border border-border bg-bg-secondary p-4">
              <p className="mb-3 text-sm text-text-secondary">
                Formatos aceitos: mp3, wav, m4a, aac, ogg, flac, webm, mp4, mov, mkv e avi.
              </p>
              <input
                className="block w-full text-sm text-text-primary"
                type="file"
                accept="audio/*,video/*"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {(meeting.status === "queued" || meeting.status === "processing") && (
                  <span className="rounded-md border border-accent/30 bg-accent-muted px-3 py-2 text-sm font-medium text-accent">
                    Acompanhando processamento...
                  </span>
                )}
                <Button
                  variant="secondary"
                  disabled={!selectedFile || uploadMutation.isPending}
                  onClick={handleUpload}
                >
                  {uploadMutation.isPending ? "Enviando..." : "Enviar arquivo"}
                </Button>
                <Button
                  disabled={
                    !meeting.file ||
                    processMutation.isPending ||
                    meeting.status === "queued" ||
                    meeting.status === "processing"
                  }
                  onClick={handleProcess}
                >
                  {processMutation.isPending ? "Enfileirando..." : "Gerar ata"}
                </Button>
              </div>
            </div>
          </div>
        </Panel>

        <StatusBox meeting={meeting} />
      </div>

      {meeting.analysis && <AnalysisTabs meeting={meeting} />}

      <LiveWidget
        meetingId={meeting.id}
        onFinished={() => {
          void queryClient.invalidateQueries({ queryKey: ["meetings"] });
        }}
      />
    </div>
  );
}

function MeetingHeader({ meeting }: { meeting: Meeting }) {
  return (
    <div>
      <p className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
        {meeting.client_name || "Cliente nao informado"}
      </p>
      <h2 className="text-xl font-semibold text-text-primary">{meeting.title}</h2>
      <p className="mt-1 text-sm text-text-secondary">
        Participantes: {meeting.participants.length > 0 ? meeting.participants.join(", ") : "nao informado"}
      </p>
    </div>
  );
}
