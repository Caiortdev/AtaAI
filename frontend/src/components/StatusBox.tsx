import type { Meeting } from "../types";
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

export function StatusBox({ meeting }: { meeting: Meeting }) {
  return (
    <Panel title="Status">
      <dl className="space-y-3 text-sm">
        <StatusItem label="Etapa" value={statusLabel[meeting.status]} />
        <StatusItem label="Arquivo" value={meeting.file?.original_name || "Nenhum arquivo enviado"} />
        {meeting.file && (
          <>
            <StatusItem label="Tipo" value={meeting.file.media_kind + " " + meeting.file.extension} />
            <StatusItem label="Tamanho" value={formatBytes(meeting.file.size_bytes)} />
            <StatusItem label="Duracao" value={formatDuration(meeting.file.duration_seconds)} />
            {meeting.file.codec_name && <StatusItem label="Codec" value={meeting.file.codec_name} />}
          </>
        )}
        {meeting.prepared_audio && (
          <StatusItem
            label="Audio preparado"
            value={formatPreparedAudioLabel(meeting.prepared_audio) + " / " + formatBytes(meeting.prepared_audio.size_bytes)}
          />
        )}
        <StatusItem label="Modo" value={meeting.analysis_mode || "Nao processado"} />
        <StatusItem label="Preset" value={meeting.preset} />
      </dl>

      {meeting.file?.validation_warnings.length ? (
        <div className="mt-4 rounded-md border border-warning/30 bg-warning-muted p-3 text-xs text-warning">
          {meeting.file.validation_warnings.map((w) => <p key={w}>{w}</p>)}
        </div>
      ) : null}

      {meeting.processing_steps.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-text-secondary">Etapas</h4>
          <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-text-secondary">
            {meeting.processing_steps.map((step) => <li key={step}>{step}</li>)}
          </ol>
        </div>
      ) : null}

      {meeting.processing_error && (
        <div className="mt-4 rounded-md border border-danger/30 bg-danger-muted p-3 text-xs text-danger">
          {meeting.processing_error}
        </div>
      )}
    </Panel>
  );
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-text-secondary">{label}</dt>
      <dd className="font-medium text-text-primary">{value}</dd>
    </div>
  );
}

function formatBytes(bytes?: number | null) {
  if (!bytes) return "Nao informado";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return (value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)) + " " + units[unitIndex];
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return "Nao identificada";
  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = rounded % 60;
  if (minutes === 0) return remainingSeconds + "s";
  return minutes + "min " + remainingSeconds.toString().padStart(2, "0") + "s";
}

function formatPreparedAudioLabel(audio: Meeting["prepared_audio"]) {
  if (!audio) return "Nao preparado";
  const extension = audio.stored_name.split(".").pop()?.toUpperCase() || "Audio";
  return extension + " " + (audio.sample_rate_hz / 1000) + "kHz";
}
