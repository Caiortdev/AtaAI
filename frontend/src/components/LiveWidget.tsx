import { useEffect, useRef, useState } from "react";

import { useLiveSession } from "../hooks/useLiveSession";

type LiveWidgetProps = {
  meetingId: string | null;
  onFinished: () => void;
};

export function LiveWidget({ meetingId, onFinished }: LiveWidgetProps) {
  const { state, transcript, draft, error, elapsedSeconds, start, pause, resume, stop } =
    useLiveSession(meetingId);
  const [expanded, setExpanded] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (expanded) transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript, expanded]);

  useEffect(() => {
    if (state === "done") onFinished();
  }, [state, onFinished]);

  useEffect(() => {
    if (state === "recording" || state === "paused" || state === "finalizing") {
      setExpanded(true);
    }
  }, [state]);

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeDisplay = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  const isActive = state === "recording" || state === "paused" || state === "finalizing";

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-accent shadow-elevated transition hover:bg-accent-hover"
        title="Gravação ao vivo"
        aria-label="Abrir painel de gravação"
      >
        <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        {isActive && (
          <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-bg-primary bg-danger animate-pulse" />
        )}
      </button>
    );
  }

  return (
    <aside className="fixed bottom-0 right-0 top-14 z-40 flex w-80 flex-col border-l border-border bg-surface shadow-elevated transition-transform">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          {state === "recording" && (
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-danger" />
              <span className="text-xs font-medium text-danger">REC</span>
            </span>
          )}
          {state === "paused" && (
            <span className="text-xs font-medium text-warning">Pausado</span>
          )}
          {state === "finalizing" && (
            <span className="text-xs font-medium text-accent">Finalizando...</span>
          )}
          {state === "idle" && (
            <span className="text-xs font-medium text-text-secondary">Pronto</span>
          )}
          {isActive && (
            <span className="font-mono text-sm text-text-secondary">{timeDisplay}</span>
          )}
        </div>
        <button
          onClick={() => setExpanded(false)}
          className="rounded-md p-1 text-text-secondary transition hover:bg-bg-tertiary hover:text-text-primary"
          aria-label="Minimizar gravação"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-border px-4 py-3">
        {state === "idle" && (
          <button className="button-primary w-full text-sm" disabled={!meetingId} onClick={start}>
            Iniciar gravação
          </button>
        )}
        {state === "recording" && (
          <>
            <button className="button-secondary flex-1 text-sm" onClick={pause}>
              Pausar
            </button>
            <button className="button-primary flex-1 text-sm" onClick={stop}>
              Finalizar
            </button>
          </>
        )}
        {state === "paused" && (
          <>
            <button className="button-secondary flex-1 text-sm" onClick={resume}>
              Retomar
            </button>
            <button className="button-primary flex-1 text-sm" onClick={stop}>
              Finalizar
            </button>
          </>
        )}
      </div>

      {error && (
        <div className="mx-4 mt-3 rounded-md border border-danger/30 bg-danger-muted p-2 text-xs text-danger">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          Transcrição ao vivo
        </h4>
        <div className="space-y-1 text-sm text-text-primary">
          {transcript.length === 0 ? (
            <p className="text-text-secondary">Aguardando fala...</p>
          ) : (
            transcript.map((text, index) => (
              <p key={index}>{text}</p>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {draft && (
        <div className="border-t border-border px-4 py-3">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-accent">
            Rascunho da ata
          </h4>
          <div className="max-h-32 overflow-y-auto whitespace-pre-wrap text-sm text-text-primary">
            {draft}
          </div>
        </div>
      )}
    </aside>
  );
}
