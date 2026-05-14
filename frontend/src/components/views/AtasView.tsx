import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMeetings } from "../../api";
import { useWorkspaceStore } from "../../store";
import type { Meeting } from "../../types";
import { AnalysisTabs } from "../AnalysisTabs";
import { Icon } from "../ui/Icon";
import { Glass } from "../ui/Glass";
import { Button } from "../ui/Button";
import { Chip } from "../ui/Chip";
import { Avatar } from "../ui/Avatar";
import { Tabs } from "../ui/Tabs";

const statusLabel: Record<string, string> = {
  draft: "Rascunho", uploaded: "Enviado", recording: "Gravando",
  queued: "Na fila", processing: "Processando", completed: "Pronta", failed: "Falhou",
};
const statusTone: Record<string, "success" | "warn" | "danger" | undefined> = {
  completed: "success", processing: "warn", queued: "warn", failed: "danger",
  recording: "danger", draft: undefined, uploaded: undefined,
};

export function AtasView() {
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const selectedMeetingId = useWorkspaceStore((s) => s.selectedMeetingId);
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);

  const [filter, setFilter] = useState("todas");
  const [search, setSearch] = useState("");

  const meetingsQuery = useQuery({
    queryKey: ["meetings", accessToken],
    queryFn: listMeetings,
    enabled: Boolean(accessToken),
    refetchInterval: (query) => {
      const data = query.state.data as Meeting[] | undefined;
      if (!data) return false;
      return data.some((m) => m.status === "queued" || m.status === "processing") ? 3000 : false;
    },
  });

  const meetings = meetingsQuery.data ?? [];

  const filtered = useMemo(() => {
    return meetings.filter((r) => {
      if (filter === "ready" && r.status !== "completed") return false;
      if (filter === "processing" && r.status !== "processing" && r.status !== "queued") return false;
      if (filter === "draft" && r.status !== "draft") return false;
      if (search && !r.title.toLowerCase().includes(search.toLowerCase()) && !(r.client_name || "").toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [meetings, filter, search]);

  const selectedMeeting = useMemo(
    () => meetings.find((m) => m.id === selectedMeetingId) ?? null,
    [meetings, selectedMeetingId],
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Atas</h1>
          <p className="page-sub">{filtered.length} reunioes</p>
        </div>
        <div className="row">
          <Button variant="ghost" icon="download-simple">Exportar</Button>
        </div>
      </div>

      <div className="row between" style={{ marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 320px", maxWidth: 420 }}>
          <Icon name="magnifying-glass" size={16} style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--text-mute)" }} />
          <input className="input" placeholder="Buscar por titulo, cliente..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ paddingLeft: 38 }} />
        </div>
        <Tabs value={filter} onChange={setFilter} items={[
          { value: "todas", label: "Todas" },
          { value: "ready", label: "Prontas" },
          { value: "processing", label: "Processando" },
          { value: "draft", label: "Rascunhos" },
        ]} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selectedMeetingId ? "minmax(360px, 1fr) 1.6fr" : "1fr", gap: 18, alignItems: "start" }}>
        <div className="col" style={{ gap: 12 }}>
          {filtered.map((r) => (
            <AtaListItem key={r.id} meeting={r} expanded={selectedMeetingId === r.id} onOpen={() => selectMeeting(r.id)} />
          ))}
          {filtered.length === 0 && (
            <Glass style={{ padding: 40, textAlign: "center" }}>
              <Icon name="file-magnifying-glass" weight="duotone" size={36} style={{ color: "var(--text-mute)", marginBottom: 10 }} />
              <div className="muted">Nenhuma ata encontrada.</div>
            </Glass>
          )}
        </div>
        {selectedMeeting && (
          <Glass strong style={{ padding: 28 }}>
            <MeetingContent meeting={selectedMeeting} />
          </Glass>
        )}
      </div>
    </div>
  );
}

function AtaListItem({ meeting, expanded, onOpen }: { meeting: Meeting; expanded: boolean; onOpen: () => void }) {
  return (
    <div onClick={onOpen} style={{ padding: 18, borderRadius: 14, background: expanded ? "var(--accent-soft)" : "var(--chip-bg)", border: "1px solid " + (expanded ? "var(--accent)" : "var(--line)"), cursor: "pointer", transition: "all 0.2s var(--ease)" }}>
      <div className="row between" style={{ alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row" style={{ gap: 10, marginBottom: 8 }}>
            <Chip tone={statusTone[meeting.status]} icon={meeting.status === "completed" ? "check-circle" : meeting.status === "processing" ? "circle-notch" : "pencil-simple"}>
              {statusLabel[meeting.status]}
            </Chip>
            <span className="muted mono" style={{ fontSize: 12 }}>{new Date(meeting.created_at).toLocaleDateString("pt-BR")}</span>
          </div>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>{meeting.title}</div>
          <div className="row" style={{ gap: 14, flexWrap: "wrap" }}>
            {meeting.client_name && (
              <span className="muted row" style={{ gap: 6, fontSize: 12.5 }}>
                <Icon name="buildings" weight="duotone" size={14} /> {meeting.client_name}
              </span>
            )}
            {meeting.participants && meeting.participants.length > 0 && (
              <span className="muted row" style={{ gap: 6, fontSize: 12.5 }}>
                <Icon name="users-three" weight="duotone" size={14} /> {meeting.participants.length}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MeetingContent({ meeting }: { meeting: Meeting }) {
  if (!meeting.analysis) {
    return (
      <div>
        <div className="row" style={{ gap: 8, marginBottom: 12 }}>
          <Chip tone={statusTone[meeting.status]}>{statusLabel[meeting.status]}</Chip>
          {meeting.client_name && <span className="dim" style={{ fontSize: 13 }}>{meeting.client_name}</span>}
        </div>
        <div style={{ fontWeight: 700, fontSize: 22, marginBottom: 12 }}>{meeting.title}</div>
        {(meeting.status === "queued" || meeting.status === "processing") && (
          <div style={{ padding: 20, borderRadius: 14, background: "var(--chip-bg)", textAlign: "center" }}>
            <Icon name="circle-notch" weight="duotone" size={24} style={{ animation: "spin 2s linear infinite", color: "var(--accent)", marginBottom: 8 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--accent)" }}>Processando ata...</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>A ata aparecera aqui quando finalizar.</div>
          </div>
        )}
        {meeting.status === "draft" && (
          <div className="dim" style={{ fontSize: 14 }}>Esta reuniao ainda nao foi processada.</div>
        )}
        {meeting.status === "failed" && meeting.processing_error && (
          <div style={{ padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{meeting.processing_error}</div>
        )}
      </div>
    );
  }

  return <AnalysisTabs meeting={meeting} />;
}
