import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMeetingsSummary } from "../../api";
import { useWorkspaceStore } from "../../store";
import type { Meeting } from "../../types";
import { Icon } from "../ui/Icon";
import { Glass } from "../ui/Glass";
import { Chip } from "../ui/Chip";

const statusLabel: Record<string, string> = {
  draft: "Rascunho", uploaded: "Enviado", recording: "Gravando",
  queued: "Na fila", processing: "Processando", completed: "Pronta", failed: "Falhou",
};
const statusTone: Record<string, "success" | "warn" | "danger" | undefined> = {
  completed: "success", processing: "warn", queued: "warn", failed: "danger",
  recording: "danger", draft: undefined, uploaded: undefined,
};

type FilterType = "all" | "completed" | "failed" | "processing";

function stepIcon(step: string): string {
  const lower = step.toLowerCase();
  if (lower.includes("erro") || lower.includes("interrompido") || lower.includes("falha")) return "warning";
  if (lower.includes("audio") || lower.includes("codec") || lower.includes("comprimido")) return "waveform";
  if (lower.includes("transcri")) return "text-aa";
  if (lower.includes("ata") || lower.includes("tarefas")) return "sparkle";
  if (lower.includes("pdf") || lower.includes("export")) return "file-pdf";
  if (lower.includes("qualidade") || lower.includes("snr")) return "chart-line-up";
  if (lower.includes("aviso")) return "info";
  if (lower.includes("enfileirado") || lower.includes("fila")) return "queue";
  if (lower.includes("gravacao")) return "record";
  return "check-circle";
}

function stepTone(step: string): string {
  const lower = step.toLowerCase();
  if (lower.includes("erro") || lower.includes("interrompido") || lower.includes("falha")) return "var(--recording)";
  if (lower.includes("aviso")) return "var(--color-warn, #e6a700)";
  return "var(--text-mute)";
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function LogsView() {
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const [filter, setFilter] = useState<FilterType>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const meetingsQuery = useQuery({
    queryKey: ["meetings-summary", accessToken],
    queryFn: listMeetingsSummary,
    enabled: Boolean(accessToken),
  });

  const meetings = meetingsQuery.data ?? [];

  const filtered = useMemo(() => {
    return meetings
      .filter((m) => {
        if (filter === "completed") return m.status === "completed";
        if (filter === "failed") return m.status === "failed";
        if (filter === "processing") return m.status === "processing" || m.status === "queued";
        return true;
      })
      .filter((m) => m.processing_steps.length > 0 || m.processing_error)
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [meetings, filter]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Logs de processamento</h1>
          <p className="page-sub">Historico detalhado de cada reuniao processada.</p>
        </div>
      </div>

      <div className="row" style={{ gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
        {([
          ["all", "Todos"],
          ["completed", "Concluidos"],
          ["failed", "Falhas"],
          ["processing", "Em andamento"],
        ] as [FilterType, string][]).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              border: "1px solid " + (filter === id ? "var(--accent)" : "var(--line)"),
              background: filter === id ? "var(--accent-soft)" : "var(--chip-bg)",
              color: filter === id ? "var(--accent)" : "var(--text-dim)",
              fontSize: 13,
              fontWeight: filter === id ? 600 : 400,
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {meetingsQuery.isLoading && (
        <p className="muted">Carregando logs...</p>
      )}

      {!meetingsQuery.isLoading && filtered.length === 0 && (
        <Glass style={{ padding: 32, textAlign: "center" }}>
          <Icon name="clipboard-text" size={32} style={{ color: "var(--text-mute)", marginBottom: 8 }} />
          <p className="muted">Nenhum log de processamento encontrado.</p>
        </Glass>
      )}

      <div className="col" style={{ gap: 12 }}>
        {filtered.map((meeting) => (
          <LogCard
            key={meeting.id}
            meeting={meeting}
            isExpanded={expanded === meeting.id}
            onToggle={() => setExpanded(expanded === meeting.id ? null : meeting.id)}
          />
        ))}
      </div>
    </div>
  );
}

function LogCard({ meeting, isExpanded, onToggle }: { meeting: Meeting; isExpanded: boolean; onToggle: () => void }) {
  return (
    <Glass style={{ padding: 0, overflow: "hidden" }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{meeting.title}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
            {formatDate(meeting.updated_at)}
            {meeting.client_name && ` · ${meeting.client_name}`}
          </div>
        </div>
        <Chip tone={statusTone[meeting.status]}>{statusLabel[meeting.status] ?? meeting.status}</Chip>
        <Icon
          name="caret-down"
          size={14}
          style={{
            transition: "transform 0.2s",
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            color: "var(--text-mute)",
          }}
        />
      </button>

      {isExpanded && (
        <div style={{ padding: "0 20px 16px", borderTop: "1px solid var(--line)" }}>
          {meeting.processing_error && (
            <div style={{
              margin: "12px 0",
              padding: 10,
              borderRadius: 8,
              background: "oklch(70% 0.22 25 / 0.1)",
              color: "var(--recording)",
              fontSize: 13,
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
            }}>
              <Icon name="warning" size={16} style={{ marginTop: 1, flexShrink: 0 }} />
              <span>{meeting.processing_error}</span>
            </div>
          )}

          {meeting.processing_steps.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {meeting.processing_steps.map((step, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "6px 0",
                    position: "relative",
                  }}
                >
                  <div style={{
                    width: 24,
                    height: 24,
                    borderRadius: 6,
                    background: "var(--chip-bg)",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}>
                    <Icon name={stepIcon(step)} size={13} style={{ color: stepTone(step) }} />
                  </div>
                  <span style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: "24px" }}>{step}</span>
                  {i < meeting.processing_steps.length - 1 && (
                    <div style={{
                      position: "absolute",
                      left: 11,
                      top: 30,
                      width: 2,
                      height: "calc(100% - 24px)",
                      background: "var(--line)",
                    }} />
                  )}
                </div>
              ))}
            </div>
          )}

          {meeting.audio_diagnostics && (
            <div style={{
              marginTop: 12,
              padding: 10,
              borderRadius: 8,
              background: "var(--chip-bg)",
              fontSize: 12,
            }}>
              <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 12 }}>Diagnostico de audio</div>
              <div className="row" style={{ gap: 16, flexWrap: "wrap" }}>
                <span>SNR: <strong>{meeting.audio_diagnostics.snr_db} dB</strong></span>
                <span>Fala: <strong>{Math.round(meeting.audio_diagnostics.speech_ratio * 100)}%</strong></span>
                <span>Volume: <strong>{meeting.audio_diagnostics.mean_volume_db} dBFS</strong></span>
                <span>Clipping: <strong>{(meeting.audio_diagnostics.clip_ratio * 100).toFixed(2)}%</strong></span>
                <Chip tone={meeting.audio_diagnostics.quality === "good" ? "success" : meeting.audio_diagnostics.quality === "unusable" ? "danger" : "warn"}>
                  {meeting.audio_diagnostics.quality}
                </Chip>
              </div>
            </div>
          )}
        </div>
      )}
    </Glass>
  );
}
