import { useEffect, useRef } from "react";

import { useLiveSession } from "../hooks/useLiveSession";

type LiveRecorderProps = {
  meetingId: string | null;
  onFinished: () => void;
};

export function LiveRecorder({ meetingId, onFinished }: LiveRecorderProps) {
  const { state, transcript, draft, error, elapsedSeconds, start, pause, resume, stop } =
    useLiveSession(meetingId);

  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  useEffect(() => {
    if (state === "done") {
      onFinished();
    }
  }, [state, onFinished]);

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeDisplay = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  if (state === "idle") {
    return (
      <div className="space-y-3">
        <button
          className="button-primary w-full"
          disabled={!meetingId}
          onClick={start}
        >
          Iniciar gravacao ao vivo
        </button>
        {error && (
          <p className="text-sm text-red-700">{error}</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        {state === "recording" && (
          <span className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-red-500" />
            <span className="text-sm font-medium text-red-700">Gravando</span>
          </span>
        )}
        {state === "paused" && (
          <span className="text-sm font-medium text-amber-700">Pausado</span>
        )}
        {state === "finalizing" && (
          <span className="text-sm font-medium text-sky-700">Finalizando...</span>
        )}
        <span className="ml-auto font-mono text-sm text-slate-600">{timeDisplay}</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {state === "recording" && (
          <button className="button-secondary" onClick={pause}>
            Pausar
          </button>
        )}
        {state === "paused" && (
          <button className="button-secondary" onClick={resume}>
            Retomar
          </button>
        )}
        {(state === "recording" || state === "paused") && (
          <button className="button-primary" onClick={stop}>
            Finalizar gravacao
          </button>
        )}
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="rounded-md border border-slate-200 bg-white p-3">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transcricao ao vivo
        </h4>
        <div className="max-h-48 overflow-y-auto text-sm text-slate-700">
          {transcript.length === 0 ? (
            <p className="text-slate-400">Aguardando fala...</p>
          ) : (
            transcript.map((text, index) => (
              <p key={index} className="mb-1">
                {text}
              </p>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {draft && (
        <div className="rounded-md border border-teal-200 bg-teal-50 p-3">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal-700">
            Rascunho da ata
          </h4>
          <div className="max-h-48 overflow-y-auto whitespace-pre-wrap text-sm text-slate-700">
            {draft}
          </div>
        </div>
      )}
    </div>
  );
}
