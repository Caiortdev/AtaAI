import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { createMeeting, uploadMeetingFile, processMeeting } from "../../api";
import { useWorkspaceStore } from "../../store";
import type { AnalysisMode } from "../../types";
import { Icon } from "../ui/Icon";
import { Glass } from "../ui/Glass";
import { Button } from "../ui/Button";
import { Chip } from "../ui/Chip";
import { Field } from "../ui/Input";
import { PresetsPanel } from "../PresetsPanel";

export function EstudioView() {
  const queryClient = useQueryClient();
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);

  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [clientName, setClientName] = useState("");
  const [participants, setParticipants] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("audio_only");
  const [phase, setPhase] = useState<"ready" | "processing" | "done">("ready");
  const [progress, setProgress] = useState(0);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (phase !== "processing") return;
    const id = setInterval(() => setProgress((p) => {
      const n = p + Math.random() * 6;
      if (n >= 100) { clearInterval(id); setPhase("done"); return 100; }
      return n;
    }), 280);
    return () => clearInterval(id);
  }, [phase]);

  async function handleProcess() {
    if (!file || !title.trim()) return;
    setError(null);
    setPhase("processing");
    try {
      const meeting = await createMeeting({ title: title.trim(), client_name: clientName || null, participants: participants.split(",").map((p) => p.trim()).filter(Boolean), notes: notes || null, consent_confirmed: true });
      await uploadMeetingFile(meeting.id, file);
      await processMeeting(meeting.id, analysisMode, selectedPreset);
      selectMeeting(meeting.id);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
      setPhase("done");
    } catch (err: any) {
      setError(err.message || "Erro ao processar");
      setPhase("ready");
    }
  }

  const steps = [
    { label: "Preparando audio", icon: "waveform", min: 0, max: 20 },
    { label: "Transcrevendo", icon: "text-aa", min: 20, max: 55 },
    { label: "Identificando falantes", icon: "users-three", min: 55, max: 75 },
    { label: "Gerando ata", icon: "sparkle", min: 75, max: 100 },
  ];

  if (phase === "done") {
    return (
      <div className="page" style={{ maxWidth: 520, margin: "60px auto", textAlign: "center" }}>
        <Glass strong style={{ padding: 40 }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", margin: "0 auto 16px", background: "oklch(72% 0.18 155 / 0.2)", color: "var(--success)", display: "grid", placeItems: "center" }}>
            <Icon name="check-circle" weight="fill" size={36} />
          </div>
          <div style={{ fontWeight: 700, fontSize: 20 }}>Ata gerada com sucesso</div>
          <div className="dim" style={{ fontSize: 14, marginTop: 8 }}>Sua reuniao foi processada e a ata esta pronta para revisao.</div>
          <Button style={{ marginTop: 24 }} icon="notebook" onClick={() => setActiveTab("atas")}>Ver ata</Button>
        </Glass>
      </div>
    );
  }

  if (phase === "processing") {
    return (
      <div className="page" style={{ maxWidth: 520, margin: "60px auto" }}>
        <Glass strong style={{ padding: 36 }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ fontWeight: 700, fontSize: 20 }}>Processando reuniao</div>
            <div className="dim" style={{ fontSize: 14, marginTop: 6 }}>{file?.name}</div>
          </div>
          <div style={{ marginBottom: 20, height: 6, borderRadius: 4, background: "var(--chip-bg)", overflow: "hidden" }}>
            <div style={{ width: progress + "%", height: "100%", background: "linear-gradient(90deg, var(--accent), oklch(60% 0.22 calc(var(--accent-h) + 40)))", borderRadius: 4, transition: "width 0.3s" }} />
          </div>
          <div className="col" style={{ gap: 10 }}>
            {steps.map((s) => {
              const active = progress >= s.min && progress < s.max;
              const done = progress >= s.max;
              return (
                <div key={s.label} className="row" style={{ gap: 12, opacity: done || active ? 1 : 0.4 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 9, background: done ? "oklch(72% 0.18 155 / 0.2)" : active ? "var(--accent-soft)" : "var(--chip-bg)", color: done ? "var(--success)" : active ? "var(--accent)" : "var(--text-mute)", display: "grid", placeItems: "center" }}>
                    <Icon name={done ? "check" : s.icon} weight={done ? "bold" : "duotone"} size={16} />
                  </div>
                  <span style={{ fontSize: 14, fontWeight: active ? 600 : 400 }}>{s.label}</span>
                  {active && <Icon name="circle-notch" size={14} style={{ animation: "spin 1.5s linear infinite", color: "var(--accent)" }} />}
                </div>
              );
            })}
          </div>
        </Glass>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Estudio</h1>
          <p className="page-sub">Suba um arquivo de audio ou video. A IA cuida do resto.</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, alignItems: "start" }}>
        <Glass strong style={{ padding: 28 }}>
          {/* Dropzone */}
          <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }} onClick={() => document.getElementById("file-input")?.click()} style={{ border: "1.5px dashed " + (drag ? "var(--accent)" : "var(--line-strong)"), borderRadius: 16, padding: 28, textAlign: "center", background: drag ? "var(--accent-soft)" : "var(--chip-bg)", cursor: "pointer", transition: "all 0.2s var(--ease)", marginBottom: 20 }}>
            <input id="file-input" type="file" accept="audio/*,video/*" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            {file ? (
              <div className="row" style={{ justifyContent: "center", gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, background: "var(--accent)", color: "white", display: "grid", placeItems: "center" }}>
                  <Icon name="file-audio" weight="fill" size={22} />
                </div>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontWeight: 600 }}>{file.name}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{(file.size / 1024 / 1024).toFixed(1)} MB</div>
                </div>
                <button className="icon-btn" onClick={(e) => { e.stopPropagation(); setFile(null); }}><Icon name="x" size={16} /></button>
              </div>
            ) : (
              <>
                <div style={{ width: 56, height: 56, borderRadius: 16, margin: "0 auto 14px", background: "var(--accent-soft)", color: "var(--accent)", display: "grid", placeItems: "center" }}>
                  <Icon name="cloud-arrow-up" weight="duotone" size={28} />
                </div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Arraste um arquivo ou clique para selecionar</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>MP3, WAV, M4A, MP4, MOV — ate 500MB</div>
              </>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Field label="Titulo da reuniao">
              <input className="input" placeholder="Ex.: Kickoff Magalu Cloud" value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Cliente">
              <input className="input" placeholder="Ex.: Magazine Luiza" value={clientName} onChange={(e) => setClientName(e.target.value)} />
            </Field>
          </div>
          <div style={{ marginTop: 14 }}>
            <Field label="Participantes" hint="Separe por virgula.">
              <input className="input" placeholder="Camila Rios, Bruno Tanaka..." value={participants} onChange={(e) => setParticipants(e.target.value)} />
            </Field>
          </div>
          <div style={{ marginTop: 14 }}>
            <Field label="Observacoes para a IA">
              <textarea className="textarea" placeholder="Contexto, jargao do cliente..." value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>
          </div>

          {/* Mode selector */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 18 }}>
            <button onClick={() => setAnalysisMode("audio_only")} style={{ padding: 14, borderRadius: 12, border: "1px solid " + (analysisMode === "audio_only" ? "var(--accent)" : "var(--line)"), background: analysisMode === "audio_only" ? "var(--accent-soft)" : "var(--chip-bg)", textAlign: "left", cursor: "pointer" }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: analysisMode === "audio_only" ? "var(--accent)" : "var(--text)" }}>Somente audio</div>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>Extrai audio do video</div>
            </button>
            <button onClick={() => setAnalysisMode("audio_video")} style={{ padding: 14, borderRadius: 12, border: "1px solid " + (analysisMode === "audio_video" ? "var(--accent)" : "var(--line)"), background: analysisMode === "audio_video" ? "var(--accent-soft)" : "var(--chip-bg)", textAlign: "left", cursor: "pointer" }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: analysisMode === "audio_video" ? "var(--accent)" : "var(--text)" }}>Audio + video</div>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>Contexto visual incluso</div>
            </button>
          </div>

          {error && <div style={{ marginTop: 14, padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{error}</div>}

          <label className="row" style={{ gap: 10, marginTop: 18, padding: 12, borderRadius: 10, background: "var(--chip-bg)", border: "1px solid var(--line)", cursor: "pointer", fontSize: 13, color: "var(--text-dim)" }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ accentColor: "var(--accent)", width: 16, height: 16 }} />
            <span>Confirmo que os participantes foram cientificados sobre gravacao e processamento por IA.</span>
          </label>

          <div className="row between" style={{ marginTop: 22 }}>
            <div className="muted row" style={{ fontSize: 12, gap: 6 }}>
              <Icon name="shield-check" weight="duotone" size={16} />
              Processado em conformidade com a LGPD.
            </div>
            <Button icon="play" disabled={!file || !title.trim() || !consent} onClick={handleProcess}>Processar reuniao</Button>
          </div>
        </Glass>

        <div className="col" style={{ gap: 20 }}>
          <PresetsPanel selectedPresetId={selectedPreset} onSelectPreset={setSelectedPreset} />
        </div>
      </div>
    </div>
  );
}
