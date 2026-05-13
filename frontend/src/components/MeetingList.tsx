import { useQuery } from "@tanstack/react-query";

import { listMeetings } from "../api";
import { useWorkspaceStore } from "../store";
import type { Meeting } from "../types";
import { Badge } from "./ui/Badge";
import { Panel } from "./ui/Panel";

const statusLabel: Record<string, string> = {
  draft: "Rascunho",
  uploaded: "Arquivo enviado",
  recording: "Gravando ao vivo",
  queued: "Na fila",
  processing: "Processando",
  completed: "Concluida",
  failed: "Falhou",
};

const statusVariant: Record<string, "default" | "accent" | "success" | "warning" | "danger"> = {
  draft: "default",
  uploaded: "default",
  recording: "danger",
  queued: "warning",
  processing: "accent",
  completed: "success",
  failed: "danger",
};

export function MeetingList() {
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const selectedMeetingId = useWorkspaceStore((s) => s.selectedMeetingId);
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);

  const meetingsQuery = useQuery({
    queryKey: ["meetings", accessToken],
    queryFn: listMeetings,
    enabled: Boolean(accessToken),
  });

  const meetings = meetingsQuery.data ?? [];

  return (
    <Panel title="Reunioes">
      {meetingsQuery.isLoading ? (
        <p className="text-sm text-text-secondary">Carregando reunioes...</p>
      ) : meetings.length === 0 ? (
        <p className="text-sm text-text-secondary">Nenhuma reuniao criada ainda.</p>
      ) : (
        <div className="space-y-2">
          {meetings.map((meeting) => (
            <button
              className={"w-full rounded-md border px-3 py-2.5 text-left text-sm transition " + (
                selectedMeetingId === meeting.id
                  ? "border-accent bg-accent-muted"
                  : "border-border bg-surface hover:border-accent/50"
              )}
              key={meeting.id}
              onClick={() => selectMeeting(meeting.id)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-text-primary">{meeting.title}</span>
                <Badge variant={statusVariant[meeting.status]}>
                  {statusLabel[meeting.status]}
                </Badge>
              </div>
              <div className="mt-1 text-xs text-text-secondary">
                {meeting.client_name || "Sem cliente"}
              </div>
            </button>
          ))}
        </div>
      )}
    </Panel>
  );
}
