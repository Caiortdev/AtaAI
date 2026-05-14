import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createMeeting } from "../../api";
import { useLiveSession } from "../../hooks/useLiveSession";
import { useWorkspaceStore } from "../../store";
import { Icon } from "../ui/Icon";
import { Glass } from "../ui/Glass";
import { Button } from "../ui/Button";
import { Chip } from "../ui/Chip";
import { StatusDot } from "../ui/StatusDot";
import { Field } from "../ui/Input";

type CaptureViewProps = {
  onFinished: () => void;
};

function MiniWaveform({ active, bars = 60 }: { active: boolean; bars?: number }) {
  const [seed, setSeed] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setSeed((s) => s + 1), 100);
    return () => clearInterval(id);
  }, [active]);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 3, height: 42, flex: 1 }}>
      {Array.from({ length: bars }, (_, i) => {
        const t = seed * 0.18 + i * 0.22;
        const h = active ? 0.15 + Math.abs(Math.sin(t)) * 0.6 + Math.abs(Math.sin(t * 1.7)) * 0.25 : 0.1;
        return (
          <div key={i} style={{ flex: 1, height: (Math.min(100, h * 100)) + "%", borderRadius: 2, background: active ? "linear-gradient(180deg, oklch(75% 0.18 " + ((i * 4) % 60 + 250) + "), var(--accent))" : "var(--line-strong)", transition: "height 0.18s ease", minWidth: 2 }} />
        );
      })}
    </div>
  );
}

export function CaptureView({ onFinished }: CaptureViewProps) {
  const queryClient = useQueryClient();
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);

  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [consent, setConsent] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  const { state, transcript, draft, error, elapsedSeconds, start, pause, resume, stop } =
    useLiveSession(meetingId);

  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [transcript]);

  useEffect(() => {
    if (state === "done" && meetingId) {
      selectMeeting(meetingId);
      void queryClient.invalidateQueries({ queryKey: ["meetings"] });
      onFinished();
    }
  }, [state, meetingId, selectMeeting, queryClient, onFinished]);

  const createMutation = useMutation({
    mutationFn: createMeeting,
    onSuccess: (meeting) => { setMeetingId(meeting.id); setSetupError(null); },
    onError: (err) => setSetupError(err.message),
  });

  function handleSetup() {
    if (!title.trim() || !consent) return;
    createMutation.mutate({ title: title.trim(), client_name: null, participants: [], notes: "Captura em tempo real", consent_confirmed: true });
  }

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeDisplay = String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
  const isActive = state === "recording" || state === "paused" || state === "finalizing";
  const isRec = state === "recording";

  if (!meetingId) {
    return (
      <div className="page" style={{ maxWidth: 480, margin: "60px auto" }}>
        <Glass strong style={{ padding: 36 }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ width: 64, height: 64, borderRadius: 18, margin: "0 auto 16px", background: "linear-gradient(135deg, var(--accent), oklch(60% 0.22 calc(var(--accent-h) + 30)))", color: "white", display: "grid", placeItems: "center", boxShadow: "0 12px 30px -6px var(--accent-glow)" }}>
              <Icon name="microphone-stage" weight="fill" size={30} />
            </div>
            <div style={{ fontWeight: 700, fontSize: 20 }}>Iniciar captura ao vivo</div>
            <div className="dim" style={{ fontSize: 14, marginTop: 6 }}>Crie uma reuniao para iniciar a gravacao com transcricao em tempo real.</div>
          </div>
          <Field label="Titulo da reuniao">
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Reuniao de alinhamento" />
          </Field>
          {setupError && <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{setupError}</div>}
          <label className="row" style={{ gap: 10, marginTop: 16, padding: 12, borderRadius: 10, background: "var(--chip-bg)", border: "1px solid var(--line)", cursor: "pointer", fontSize: 13, color: "var(--text-dim)" }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ accentColor: "var(--accent)", width: 16, height: 16 }} />
            <span>Confirmo que os participantes foram cientificados sobre gravacao e processamento por IA.</span>
          </label>
          <Button style={{ width: "100%", justifyContent: "center", marginTop: 20 }} icon="play" disabled={createMutation.isPending || title.trim().length < 3 || !consent} onClick={handleSetup}>
            {createMutation.isPending ? "Criando..." : "Preparar gravacao"}
          </Button>
        </Glass>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="row" style={{ gap: 10, marginBottom: 8 }}>
            <Chip tone={isRec ? "danger" : "warn"} icon={isRec ? "record" : "pause"}>
              <StatusDot tone={isRec ? "danger" : "warn"} />
              {isRec ? "GRAVANDO AO VIVO" : state === "paused" ? "PAUSADO" : "PRONTO"}
            </Chip>
          </div>
          <h1 className="page-title">Sessao ao vivo</h1>
          <p className="page-sub">Transcricao em tempo real</p>
        </div>
        <div className="row">
          <Button variant="danger" icon="stop" onClick={stop} disabled={!isActive}>Encerrar sessao</Button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, alignItems: "start" }}>
        <div className="col" style={{ gap: 20 }}>
          <Glass strong style={{ padding: 18 }}>
            {/* Audio visualization area */}
            <div style={{ aspectRatio: "16 / 9", borderRadius: 18, overflow: "hidden", position: "relative", background: "radial-gradient(circle at 50% 50%, oklch(40% 0.15 280), oklch(15% 0.08 280))", display: "grid", placeItems: "center" }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{ position: "absolute", width: 200 + i * 120, height: 200 + i * 120, borderRadius: "50%", border: "1px solid rgba(255,255,255,0.08)", animation: isRec ? "pulse-ring 3s ease-out " + i + "s infinite" : "none" }} />
              ))}
              <div style={{ width: 130, height: 130, borderRadius: "50%", background: "var(--glass-bg-strong)", backdropFilter: "blur(20px)", display: "grid", placeItems: "center", boxShadow: isRec ? "0 0 0 8px var(--accent-soft), 0 20px 50px -10px var(--accent-glow)" : "0 0 0 4px rgba(255,255,255,0.05)", transition: "all 0.3s", color: "white", position: "relative", zIndex: 2 }}>
                <Icon name="microphone" weight="fill" size={56} />
              </div>
            </div>

            {/* Controls HUD */}
            <div className="row between" style={{ marginTop: 16, gap: 16 }}>
              <div className="row" style={{ gap: 14, flex: 1 }}>
                <div>
                  <div className="muted" style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: 0.06, textTransform: "uppercase" }}>Decorrido</div>
                  <div className="mono" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 2 }}>{timeDisplay}</div>
                </div>
                <div style={{ width: 1, height: 36, background: "var(--line)" }} />
                <MiniWaveform active={isRec} />
              </div>
              <div className="row" style={{ gap: 8 }}>
                {state === "idle" && <Button icon="play" onClick={start}>Iniciar</Button>}
                {state === "recording" && <button className="icon-btn" onClick={pause}><Icon name="pause" weight="duotone" size={18} /></button>}
                {state === "paused" && <button className="icon-btn" onClick={resume}><Icon name="play" weight="duotone" size={18} /></button>}
                {isActive && (
                  <button onClick={stop} style={{ width: 48, height: 48, borderRadius: "50%", background: "var(--recording)", color: "white", display: "grid", placeItems: "center", boxShadow: "0 0 0 4px oklch(70% 0.22 25 / 0.18), inset 0 1px 0 rgba(255,255,255,0.3)", border: "none", animation: isRec ? "pulse 1.6s ease-in-out infinite" : "none" }}>
                    <Icon name="stop" weight="fill" size={18} />
                  </button>
                )}
              </div>
            </div>
          </Glass>
          {error && <div style={{ padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{error}</div>}
        </div>

        {/* Right column: transcript + draft */}
        <div className="col" style={{ gap: 20 }}>
          <Glass style={{ padding: 22 }}>
            <div className="row between" style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>Transcricao em tempo real</div>
              <Chip icon="waveform">{transcript.length} segmentos</Chip>
            </div>
            <div ref={transcriptRef} style={{ maxHeight: 260, overflowY: "auto", paddingRight: 4 }}>
              {transcript.length === 0 ? (
                <div className="muted" style={{ fontSize: 13 }}>Aguardando fala...</div>
              ) : (
                <div className="col" style={{ gap: 10 }}>
                  {transcript.map((text, i) => (
                    <div key={i} style={{ fontSize: 14, lineHeight: 1.55, color: "var(--text-dim)" }}>{text}</div>
                  ))}
                </div>
              )}
            </div>
          </Glass>

          <Glass style={{ padding: 22 }}>
            <div className="row between" style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>Rascunho da ata</div>
              <Icon name="sparkle" weight="duotone" size={18} style={{ color: "var(--accent)" }} />
            </div>
            <div style={{ maxHeight: 260, overflowY: "auto" }}>
              {draft ? (
                <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6, color: "var(--text-dim)" }}>{draft}</div>
              ) : (
                <div className="muted" style={{ fontSize: 13 }}>O rascunho aparecera aqui conforme a reuniao avanca...</div>
              )}
            </div>
          </Glass>
        </div>
      </div>
    </div>
  );
}
