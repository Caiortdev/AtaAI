import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { exportMeetingPdf, updateMeetingAnalysis } from "../api";
import type {
  Meeting,
  MeetingAnalysis,
  MeetingAnalysisUpdate,
  Priority,
  TaskItem,
} from "../types";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Field } from "./ui/Input";
import { Panel } from "./ui/Panel";

const priorityLabel: Record<Priority, string> = {
  critical: "Critica",
  high: "Alta",
  medium: "Media",
  low: "Baixa",
};

const priorityVariant: Record<Priority, "danger" | "warning" | "accent" | "default"> = {
  critical: "danger",
  high: "warning",
  medium: "accent",
  low: "default",
};

const taskStatusLabel: Record<TaskItem["status"], string> = {
  new: "Nova",
  review: "Em revisao",
  approved: "Aprovada",
};

type TabId = "minutes" | "transcript" | "tasks" | "summary";

type AnalysisTabsProps = {
  meeting: Meeting;
};

export function AnalysisTabs({ meeting }: AnalysisTabsProps) {
  const queryClient = useQueryClient();
  const analysis = meeting.analysis;
  const [activeTab, setActiveTab] = useState<TabId>("minutes");
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<MeetingAnalysisUpdate | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!analysis) {
      setDraft(null);
      return;
    }
    setDraft(analysisToDraft(analysis));
    setIsEditing(false);
    setSaveError(null);
    setExportError(null);
    setExportSuccess(null);
  }, [analysis, meeting.id]);

  const saveMutation = useMutation({
    mutationFn: (payload: MeetingAnalysisUpdate) => updateMeetingAnalysis(meeting.id, payload),
    onSuccess: async () => {
      setIsEditing(false);
      setSaveError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => setSaveError(err.message),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportMeetingPdf(meeting.id),
    onSuccess: async ({ blob, filename }) => {
      setExportError(null);
      const savedPath = await savePdf(blob, filename);
      setExportSuccess(savedPath ? "PDF salvo em " + savedPath : "PDF exportado.");
    },
    onError: (err) => setExportError(err.message),
  });

  if (!analysis) return null;

  function startEditing() {
    setDraft(analysisToDraft(analysis!));
    setSaveError(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    setDraft(analysisToDraft(analysis!));
    setSaveError(null);
    setIsEditing(false);
  }

  function saveDraft() {
    if (!draft) return;
    saveMutation.mutate({
      ...draft,
      topics: cleanList(draft.topics),
      decisions: cleanList(draft.decisions),
      risks: cleanList(draft.risks),
      open_questions: cleanList(draft.open_questions),
      tasks: draft.tasks.filter((t) => t.title.trim() || t.description.trim()),
    });
  }

  function exportPdf() {
    setExportError(null);
    setExportSuccess(null);
    exportMutation.mutate();
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: "minutes", label: "Ata" },
    { id: "transcript", label: "Transcricao" },
    { id: "tasks", label: "Tarefas" },
    { id: "summary", label: "Resumo" },
  ];

  return (
    <Panel className="flex flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex border-b border-border">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={"relative px-4 py-2.5 text-sm font-medium transition " + (
                activeTab === tab.id
                  ? "text-accent"
                  : "text-text-secondary hover:text-text-primary"
              )}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-accent" />
              )}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          {isEditing ? (
            <>
              <Button variant="secondary" onClick={cancelEditing}>Cancelar</Button>
              <Button disabled={saveMutation.isPending} onClick={saveDraft}>
                {saveMutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" disabled={exportMutation.isPending} onClick={exportPdf}>
                {exportMutation.isPending ? "Exportando..." : "Exportar PDF"}
              </Button>
              <Button variant="secondary" onClick={startEditing}>Revisar</Button>
            </>
          )}
        </div>
      </div>

      {exportError && <AlertBox variant="danger">{exportError}</AlertBox>}
      {exportSuccess && <AlertBox variant="success">{exportSuccess}</AlertBox>}
      {saveError && <AlertBox variant="danger">{saveError}</AlertBox>}

      <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
        {activeTab === "minutes" && (
          <MinutesTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />
        )}
        {activeTab === "transcript" && <TranscriptTab analysis={analysis} />}
        {activeTab === "tasks" && (
          <TasksTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />
        )}
        {activeTab === "summary" && (
          <SummaryTab analysis={analysis} isEditing={isEditing} draft={draft} setDraft={setDraft!} />
        )}
      </div>
    </Panel>
  );
}

function MinutesTab({
  analysis,
  isEditing,
  draft,
  setDraft,
}: {
  analysis: MeetingAnalysis;
  isEditing: boolean;
  draft: MeetingAnalysisUpdate | null;
  setDraft: (d: MeetingAnalysisUpdate) => void;
}) {
  if (isEditing && draft) {
    return (
      <Field label="Ata em Markdown">
        <textarea
          className="input min-h-96 resize-y font-mono text-sm"
          value={draft.minutes_markdown}
          onChange={(e) => setDraft({ ...draft, minutes_markdown: e.target.value })}
        />
      </Field>
    );
  }
  return (
    <div className="prose-like whitespace-pre-wrap text-sm text-text-primary">
      {analysis.minutes_markdown}
    </div>
  );
}

function TranscriptTab({ analysis }: { analysis: MeetingAnalysis }) {
  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-xs text-text-secondary">
        <span>Provedor: {analysis.transcript_provider}</span>
        <span>Modelo: {analysis.transcript_model}</span>
      </div>
      <pre className="whitespace-pre-wrap font-sans text-sm text-text-primary">
        {analysis.transcript}
      </pre>
    </div>
  );
}

function TasksTab({
  analysis,
  isEditing,
  draft,
  setDraft,
}: {
  analysis: MeetingAnalysis;
  isEditing: boolean;
  draft: MeetingAnalysisUpdate | null;
  setDraft: (d: MeetingAnalysisUpdate) => void;
}) {
  if (isEditing && draft) {
    return <TaskEditor tasks={draft.tasks} onChange={(tasks) => setDraft({ ...draft, tasks })} />;
  }
  return (
    <div className="space-y-3">
      {analysis.tasks.map((task) => (
        <TaskCard task={task} key={task.id} />
      ))}
      {analysis.tasks.length === 0 && (
        <p className="text-sm text-text-secondary">Nenhuma tarefa identificada.</p>
      )}
    </div>
  );
}

function SummaryTab({
  analysis,
  isEditing,
  draft,
  setDraft,
}: {
  analysis: MeetingAnalysis;
  isEditing: boolean;
  draft: MeetingAnalysisUpdate | null;
  setDraft: (d: MeetingAnalysisUpdate) => void;
}) {
  if (isEditing && draft) {
    return (
      <div className="space-y-4">
        <Field label="Resumo executivo">
          <textarea
            className="input min-h-24 resize-y"
            value={draft.executive_summary}
            onChange={(e) => setDraft({ ...draft, executive_summary: e.target.value })}
          />
        </Field>
        <Field label="Topicos (um por linha)">
          <textarea
            className="input min-h-24 resize-y"
            value={draft.topics.join("\n")}
            onChange={(e) => setDraft({ ...draft, topics: e.target.value.split("\n") })}
          />
        </Field>
        <Field label="Decisoes (uma por linha)">
          <textarea
            className="input min-h-24 resize-y"
            value={draft.decisions.join("\n")}
            onChange={(e) => setDraft({ ...draft, decisions: e.target.value.split("\n") })}
          />
        </Field>
        <Field label="Riscos (um por linha)">
          <textarea
            className="input min-h-20 resize-y"
            value={draft.risks.join("\n")}
            onChange={(e) => setDraft({ ...draft, risks: e.target.value.split("\n") })}
          />
        </Field>
        <Field label="Duvidas abertas (uma por linha)">
          <textarea
            className="input min-h-20 resize-y"
            value={draft.open_questions.join("\n")}
            onChange={(e) => setDraft({ ...draft, open_questions: e.target.value.split("\n") })}
          />
        </Field>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-text-primary">Resumo executivo</h3>
        <p className="mt-1 text-sm text-text-secondary">{analysis.executive_summary}</p>
      </div>
      {analysis.decisions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Decisoes</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {analysis.decisions.map((d) => <li key={d}>{d}</li>)}
          </ul>
        </div>
      )}
      {analysis.risks.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Riscos</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {analysis.risks.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}
      {analysis.open_questions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Duvidas abertas</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {analysis.open_questions.map((q) => <li key={q}>{q}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function TaskCard({ task }: { task: TaskItem }) {
  return (
    <article className="rounded-md border border-border bg-bg-secondary p-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-text-primary">{task.title}</h3>
        <Badge variant={priorityVariant[task.priority]}>{priorityLabel[task.priority]}</Badge>
      </div>
      <p className="mt-2 text-sm text-text-secondary">{task.description}</p>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-text-secondary">
        <span>Status: {taskStatusLabel[task.status]}</span>
        {task.owner && <span>Resp: {task.owner}</span>}
        {task.due_date && <span>Prazo: {task.due_date}</span>}
      </div>
    </article>
  );
}

function TaskEditor({
  tasks,
  onChange,
}: {
  tasks: TaskItem[];
  onChange: (tasks: TaskItem[]) => void;
}) {
  function updateTask(index: number, patch: Partial<TaskItem>) {
    onChange(tasks.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  }

  function removeTask(index: number) {
    onChange(tasks.filter((_, i) => i !== index));
  }

  function addTask() {
    onChange([
      ...tasks,
      {
        id: window.crypto.randomUUID(),
        title: "",
        description: "",
        priority: "medium",
        priority_reason: "",
        owner: null,
        due_date: null,
        source_excerpt: null,
        source_timestamp: null,
        status: "review",
      },
    ]);
  }

  return (
    <div className="space-y-3">
      {tasks.map((task, index) => (
        <article className="rounded-md border border-border p-3" key={task.id}>
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-semibold text-text-primary">Tarefa {index + 1}</span>
            <Button variant="ghost" className="text-xs" onClick={() => removeTask(index)}>
              Remover
            </Button>
          </div>
          <div className="space-y-3">
            <Field label="Titulo">
              <input className="input" value={task.title} onChange={(e) => updateTask(index, { title: e.target.value })} />
            </Field>
            <Field label="Descricao">
              <textarea className="input min-h-16 resize-y" value={task.description} onChange={(e) => updateTask(index, { description: e.target.value })} />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Prioridade">
                <select className="input" value={task.priority} onChange={(e) => updateTask(index, { priority: e.target.value as Priority })}>
                  <option value="critical">Critica</option>
                  <option value="high">Alta</option>
                  <option value="medium">Media</option>
                  <option value="low">Baixa</option>
                </select>
              </Field>
              <Field label="Status">
                <select className="input" value={task.status} onChange={(e) => updateTask(index, { status: e.target.value as TaskItem["status"] })}>
                  <option value="new">Nova</option>
                  <option value="review">Em revisao</option>
                  <option value="approved">Aprovada</option>
                </select>
              </Field>
            </div>
          </div>
        </article>
      ))}
      <Button variant="secondary" className="w-full" onClick={addTask}>
        Adicionar tarefa
      </Button>
    </div>
  );
}

function AlertBox({ variant, children }: { variant: "danger" | "success"; children: React.ReactNode }) {
  const styles = variant === "danger"
    ? "border-danger/30 bg-danger-muted text-danger"
    : "border-success/30 bg-success-muted text-success";
  return (
    <div className={"mb-3 rounded-md border p-3 text-sm " + styles}>{children}</div>
  );
}

function analysisToDraft(analysis: MeetingAnalysis): MeetingAnalysisUpdate {
  return {
    executive_summary: analysis.executive_summary,
    topics: analysis.topics,
    decisions: analysis.decisions,
    tasks: analysis.tasks,
    risks: analysis.risks,
    open_questions: analysis.open_questions,
    minutes_markdown: analysis.minutes_markdown,
  };
}

function cleanList(items: string[]) {
  return items.map((item) => item.trim()).filter(Boolean);
}

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
