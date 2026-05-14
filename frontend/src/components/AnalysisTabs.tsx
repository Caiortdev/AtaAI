import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { exportMeetingPdf, updateMeetingAnalysis } from "../api";
import type { Meeting, MeetingAnalysis, MeetingAnalysisUpdate, Priority, TaskItem } from "../types";
import { Icon } from "./ui/Icon";
import { Glass } from "./ui/Glass";
import { Button } from "./ui/Button";
import { Chip } from "./ui/Chip";
import { Field } from "./ui/Input";
import { Tabs } from "./ui/Tabs";
import { MarkdownRenderer } from "./ui/MarkdownRenderer";

const priorityLabel: Record<Priority, string> = { critical: "Critica", high: "Alta", medium: "Media", low: "Baixa" };
const priorityTone: Record<Priority, "danger" | "warn" | "solid" | undefined> = { critical: "danger", high: "warn", medium: "solid", low: undefined };
const taskStatusLabel: Record<TaskItem["status"], string> = { new: "Nova", review: "Em revisao", approved: "Aprovada" };

type AnalysisTabsProps = { meeting: Meeting };

export function AnalysisTabs({ meeting }: AnalysisTabsProps) {
  const queryClient = useQueryClient();
  const analysis = meeting.analysis;
  const [tab, setTab] = useState("minutes");
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<MeetingAnalysisUpdate | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!analysis) { setDraft(null); return; }
    setDraft(analysisToDraft(analysis));
    setIsEditing(false); setSaveError(null); setExportError(null); setExportSuccess(null);
  }, [analysis, meeting.id]);

  const saveMutation = useMutation({
    mutationFn: (payload: MeetingAnalysisUpdate) => updateMeetingAnalysis(meeting.id, payload),
    onSuccess: async () => { setIsEditing(false); setSaveError(null); await queryClient.invalidateQueries({ queryKey: ["meetings"] }); },
    onError: (err) => setSaveError(err.message),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportMeetingPdf(meeting.id),
    onSuccess: async ({ blob, filename }) => { setExportError(null); const p = await savePdf(blob, filename); setExportSuccess(p ? "PDF salvo em " + p : "PDF exportado."); },
    onError: (err) => setExportError(err.message),
  });

  if (!analysis) return null;

  function startEditing() { setDraft(analysisToDraft(analysis!)); setSaveError(null); setIsEditing(true); }
  function cancelEditing() { setDraft(analysisToDraft(analysis!)); setSaveError(null); setIsEditing(false); }
  function saveDraft() {
    if (!draft) return;
    saveMutation.mutate({ ...draft, topics: cleanList(draft.topics), decisions: cleanList(draft.decisions), risks: cleanList(draft.risks), open_questions: cleanList(draft.open_questions), tasks: draft.tasks.filter((t) => t.title.trim() || t.description.trim()) });
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 18 }}>
        <div style={{ flex: 1 }}>
          <div className="row" style={{ gap: 8, marginBottom: 8 }}>
            <Chip tone="success" icon="check-circle">Pronta</Chip>
            {meeting.client_name && <Chip icon="buildings">{meeting.client_name}</Chip>}
          </div>
          <div style={{ fontWeight: 700, fontSize: 22, letterSpacing: "-0.01em" }}>{meeting.title}</div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {isEditing ? (
            <>
              <Button variant="ghost" size="sm" onClick={cancelEditing}>Cancelar</Button>
              <Button size="sm" disabled={saveMutation.isPending} onClick={saveDraft}>{saveMutation.isPending ? "Salvando..." : "Salvar"}</Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" icon="file-pdf" disabled={exportMutation.isPending} onClick={() => exportMutation.mutate()}>{exportMutation.isPending ? "..." : "PDF"}</Button>
              <Button variant="ghost" size="sm" icon="pencil-simple" onClick={startEditing}>Revisar</Button>
            </>
          )}
        </div>
      </div>

      {exportError && <div style={{ marginBottom: 12, padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{exportError}</div>}
      {exportSuccess && <div style={{ marginBottom: 12, padding: 12, borderRadius: 10, background: "oklch(72% 0.18 155 / 0.15)", color: "var(--success)", fontSize: 13 }}>{exportSuccess}</div>}
      {saveError && <div style={{ marginBottom: 12, padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{saveError}</div>}

      <div style={{ marginBottom: 22 }}>
        <Tabs items={[
          { value: "minutes", label: "Ata", icon: "text-align-left" },
          { value: "summary", label: "Resumo", icon: "list-bullets" },
          { value: "tasks", label: "Tarefas", icon: "check-square" },
          { value: "transcript", label: "Transcricao", icon: "waveform" },
        ]} value={tab} onChange={setTab} />
      </div>

      <div>
        {tab === "minutes" && <MinutesTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />}
        {tab === "summary" && <SummaryTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />}
        {tab === "tasks" && <TasksTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />}
        {tab === "transcript" && <TranscriptTab analysis={analysis} />}
      </div>
    </div>
  );
}

function MinutesTab({ analysis, isEditing, draft, setDraft }: { analysis: MeetingAnalysis; isEditing: boolean; draft: MeetingAnalysisUpdate | null; setDraft: (d: MeetingAnalysisUpdate) => void }) {
  if (isEditing && draft) {
    return (
      <Field label="Ata em Markdown">
        <textarea className="textarea mono" style={{ minHeight: 300 }} value={draft.minutes_markdown} onChange={(e) => setDraft({ ...draft, minutes_markdown: e.target.value })} />
      </Field>
    );
  }
  return <MarkdownRenderer content={analysis.minutes_markdown} />;
}

function TranscriptTab({ analysis }: { analysis: MeetingAnalysis }) {
  return (
    <div>
      <div className="row muted" style={{ gap: 16, fontSize: 12, marginBottom: 12 }}>
        <span>Provedor: {analysis.transcript_provider}</span>
        <span>Modelo: {analysis.transcript_model}</span>
      </div>
      <pre style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6, color: "var(--text-dim)" }}>{analysis.transcript}</pre>
    </div>
  );
}

function TasksTab({ analysis, isEditing, draft, setDraft }: { analysis: MeetingAnalysis; isEditing: boolean; draft: MeetingAnalysisUpdate | null; setDraft: (d: MeetingAnalysisUpdate) => void }) {
  if (isEditing && draft) {
    return <TaskEditor tasks={draft.tasks} onChange={(tasks) => setDraft({ ...draft, tasks })} />;
  }
  return (
    <div className="col" style={{ gap: 10 }}>
      {analysis.tasks.map((task) => <TaskCard task={task} key={task.id} />)}
      {analysis.tasks.length === 0 && <div className="muted" style={{ fontSize: 13 }}>Nenhuma tarefa identificada.</div>}
    </div>
  );
}

function SummaryTab({ analysis, isEditing, draft, setDraft }: { analysis: MeetingAnalysis; isEditing: boolean; draft: MeetingAnalysisUpdate | null; setDraft: (d: MeetingAnalysisUpdate) => void }) {
  if (isEditing && draft) {
    return (
      <div className="col" style={{ gap: 14 }}>
        <Field label="Resumo executivo"><textarea className="textarea" value={draft.executive_summary} onChange={(e) => setDraft({ ...draft, executive_summary: e.target.value })} /></Field>
        <Field label="Topicos (um por linha)"><textarea className="textarea" value={draft.topics.join("\n")} onChange={(e) => setDraft({ ...draft, topics: e.target.value.split("\n") })} /></Field>
        <Field label="Decisoes (uma por linha)"><textarea className="textarea" value={draft.decisions.join("\n")} onChange={(e) => setDraft({ ...draft, decisions: e.target.value.split("\n") })} /></Field>
        <Field label="Riscos (um por linha)"><textarea className="textarea" value={draft.risks.join("\n")} onChange={(e) => setDraft({ ...draft, risks: e.target.value.split("\n") })} /></Field>
        <Field label="Duvidas abertas (uma por linha)"><textarea className="textarea" value={draft.open_questions.join("\n")} onChange={(e) => setDraft({ ...draft, open_questions: e.target.value.split("\n") })} /></Field>
      </div>
    );
  }
  return (
    <div className="col" style={{ gap: 18 }}>
      <div>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Resumo executivo</div>
        <div style={{ fontSize: 14, lineHeight: 1.6, color: "var(--text-dim)" }}>{analysis.executive_summary}</div>
      </div>
      {analysis.decisions.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>Decisoes</div>
          <div className="col" style={{ gap: 8 }}>
            {analysis.decisions.map((d, i) => (
              <div key={i} className="row" style={{ gap: 12, padding: 12, borderRadius: 10, background: "var(--chip-bg)", border: "1px solid var(--line)" }}>
                <div style={{ width: 24, height: 24, borderRadius: 7, background: "var(--accent-soft)", color: "var(--accent)", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 11, flexShrink: 0 }}>{i + 1}</div>
                <div style={{ fontSize: 14, lineHeight: 1.5 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {analysis.risks.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Riscos</div>
          <div className="col" style={{ gap: 6 }}>
            {analysis.risks.map((r, i) => <div key={i} style={{ fontSize: 14, color: "var(--text-dim)", paddingLeft: 12, borderLeft: "2px solid var(--warning)" }}>{r}</div>)}
          </div>
        </div>
      )}
    </div>
  );
}

function TaskCard({ task }: { task: TaskItem }) {
  return (
    <div className="row" style={{ gap: 14, padding: 14, borderRadius: 12, background: "var(--chip-bg)", border: "1px solid var(--line)" }}>
      <div style={{ width: 22, height: 22, borderRadius: 7, background: task.status === "approved" ? "var(--success)" : "transparent", border: "1.5px solid " + (task.status === "approved" ? "var(--success)" : "var(--line-strong)"), display: "grid", placeItems: "center", color: "white" }}>
        {task.status === "approved" && <Icon name="check" weight="bold" size={13} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 600, textDecoration: task.status === "approved" ? "line-through" : "none" }}>{task.title}</div>
        {task.description && <div className="dim" style={{ fontSize: 13, marginTop: 4 }}>{task.description}</div>}
        <div className="row" style={{ gap: 10, marginTop: 6 }}>
          {task.owner && <span className="muted" style={{ fontSize: 12 }}>{task.owner}</span>}
          {task.due_date && <span className="muted" style={{ fontSize: 12 }}>{task.due_date}</span>}
        </div>
      </div>
      <Chip tone={priorityTone[task.priority]}>{priorityLabel[task.priority]}</Chip>
    </div>
  );
}

function TaskEditor({ tasks, onChange }: { tasks: TaskItem[]; onChange: (tasks: TaskItem[]) => void }) {
  function updateTask(index: number, patch: Partial<TaskItem>) { onChange(tasks.map((t, i) => (i === index ? { ...t, ...patch } : t))); }
  function removeTask(index: number) { onChange(tasks.filter((_, i) => i !== index)); }
  function addTask() {
    onChange([...tasks, { id: window.crypto.randomUUID(), title: "", description: "", priority: "medium", priority_reason: "", owner: null, due_date: null, source_excerpt: null, source_timestamp: null, status: "review" }]);
  }
  return (
    <div className="col" style={{ gap: 12 }}>
      {tasks.map((task, index) => (
        <div key={task.id} style={{ padding: 16, borderRadius: 12, background: "var(--chip-bg)", border: "1px solid var(--line)" }}>
          <div className="row between" style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Tarefa {index + 1}</span>
            <Button variant="ghost" size="sm" onClick={() => removeTask(index)}>Remover</Button>
          </div>
          <div className="col" style={{ gap: 10 }}>
            <Field label="Titulo"><input className="input" value={task.title} onChange={(e) => updateTask(index, { title: e.target.value })} /></Field>
            <Field label="Descricao"><textarea className="textarea" value={task.description} onChange={(e) => updateTask(index, { description: e.target.value })} /></Field>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Field label="Prioridade">
                <select className="input" value={task.priority} onChange={(e) => updateTask(index, { priority: e.target.value as Priority })}>
                  <option value="critical">Critica</option><option value="high">Alta</option><option value="medium">Media</option><option value="low">Baixa</option>
                </select>
              </Field>
              <Field label="Status">
                <select className="input" value={task.status} onChange={(e) => updateTask(index, { status: e.target.value as TaskItem["status"] })}>
                  <option value="new">Nova</option><option value="review">Em revisao</option><option value="approved">Aprovada</option>
                </select>
              </Field>
            </div>
          </div>
        </div>
      ))}
      <Button variant="ghost" icon="plus" onClick={addTask} style={{ width: "100%", justifyContent: "center" }}>Adicionar tarefa</Button>
    </div>
  );
}

function analysisToDraft(analysis: MeetingAnalysis): MeetingAnalysisUpdate {
  return { executive_summary: analysis.executive_summary, topics: analysis.topics, decisions: analysis.decisions, tasks: analysis.tasks, risks: analysis.risks, open_questions: analysis.open_questions, minutes_markdown: analysis.minutes_markdown };
}
function cleanList(items: string[]) { return items.map((item) => item.trim()).filter(Boolean); }

async function savePdf(blob: Blob, filename: string): Promise<string | null> {
  const tauriInvoke = (window as any).__TAURI_INTERNALS__?.invoke;
  if (tauriInvoke) {
    const bytes = Array.from(new Uint8Array(await blob.arrayBuffer()));
    return tauriInvoke("save_pdf_to_downloads", { payload: { filename, bytes } });
  }
  downloadBlob(blob, filename);
  return null;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
