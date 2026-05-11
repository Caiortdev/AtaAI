import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  createMeeting,
  listMeetings,
  processMeeting,
  updateMeetingAnalysis,
  uploadMeetingFile,
} from "./api";
import { useWorkspaceStore } from "./store";
import type { AnalysisMode, Meeting, MeetingAnalysis, MeetingAnalysisUpdate, Priority, TaskItem } from "./types";

const priorityLabel: Record<Priority, string> = {
  critical: "Critica",
  high: "Alta",
  medium: "Media",
  low: "Baixa",
};

const priorityClass: Record<Priority, string> = {
  critical: "border-red-200 bg-red-50 text-red-800",
  high: "border-amber-200 bg-amber-50 text-amber-800",
  medium: "border-sky-200 bg-sky-50 text-sky-800",
  low: "border-slate-200 bg-slate-50 text-slate-700",
};

const statusLabel: Record<string, string> = {
  draft: "Rascunho",
  uploaded: "Arquivo enviado",
  processing: "Processando",
  completed: "Concluida",
  failed: "Falhou",
};

const taskStatusLabel: Record<TaskItem["status"], string> = {
  new: "Nova",
  review: "Em revisao",
  approved: "Aprovada",
};

export default function App() {
  const queryClient = useQueryClient();
  const selectedMeetingId = useWorkspaceStore((state) => state.selectedMeetingId);
  const selectMeeting = useWorkspaceStore((state) => state.selectMeeting);
  const [form, setForm] = useState({
    title: "",
    clientName: "",
    participants: "",
    notes: "",
    consent: false,
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("audio_only");
  const [error, setError] = useState<string | null>(null);

  const meetingsQuery = useQuery({
    queryKey: ["meetings"],
    queryFn: listMeetings,
  });

  const meetings = meetingsQuery.data ?? [];
  const selectedMeeting = useMemo(
    () => meetings.find((meeting) => meeting.id === selectedMeetingId) ?? meetings[0],
    [meetings, selectedMeetingId],
  );

  const createMutation = useMutation({
    mutationFn: createMeeting,
    onSuccess: async (meeting) => {
      selectMeeting(meeting.id);
      setForm({ title: "", clientName: "", participants: "", notes: "", consent: false });
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (mutationError) => setError(mutationError.message),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ meetingId, file }: { meetingId: string; file: File }) =>
      uploadMeetingFile(meetingId, file),
    onSuccess: async (meeting) => {
      selectMeeting(meeting.id);
      setSelectedFile(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (mutationError) => setError(mutationError.message),
  });

  const processMutation = useMutation({
    mutationFn: ({ meetingId, mode }: { meetingId: string; mode: AnalysisMode }) =>
      processMeeting(meetingId, mode),
    onSuccess: async (meeting) => {
      selectMeeting(meeting.id);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (mutationError) => setError(mutationError.message),
  });

  function handleCreateMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createMutation.mutate({
      title: form.title,
      client_name: form.clientName || null,
      participants: form.participants
        .split(",")
        .map((participant) => participant.trim())
        .filter(Boolean),
      notes: form.notes || null,
      consent_confirmed: form.consent,
    });
  }

  function handleUpload() {
    if (!selectedMeeting || !selectedFile) return;
    setError(null);
    uploadMutation.mutate({ meetingId: selectedMeeting.id, file: selectedFile });
  }

  function handleProcess() {
    if (!selectedMeeting) return;
    setError(null);
    processMutation.mutate({ meetingId: selectedMeeting.id, mode: analysisMode });
  }

  return (
    <main className="min-h-screen bg-cloud text-ink">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-lagoon">MVP</p>
            <h1 className="text-2xl font-semibold">Ata de reuniao por IA</h1>
          </div>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-600">
            React + FastAPI
          </span>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-5 lg:grid-cols-[380px_1fr]">
        <section className="space-y-5">
          <Panel title="Nova reuniao">
            <form className="space-y-4" onSubmit={handleCreateMeeting}>
              <Field label="Titulo">
                <input
                  className="input"
                  minLength={3}
                  required
                  value={form.title}
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                  placeholder="Alinhamento com cliente"
                />
              </Field>

              <Field label="Cliente">
                <input
                  className="input"
                  value={form.clientName}
                  onChange={(event) => setForm({ ...form, clientName: event.target.value })}
                  placeholder="Nome do cliente ou empresa"
                />
              </Field>

              <Field label="Participantes">
                <input
                  className="input"
                  value={form.participants}
                  onChange={(event) => setForm({ ...form, participants: event.target.value })}
                  placeholder="Ana, Bruno, Cliente X"
                />
              </Field>

              <Field label="Observacoes">
                <textarea
                  className="input min-h-20 resize-y"
                  value={form.notes}
                  onChange={(event) => setForm({ ...form, notes: event.target.value })}
                  placeholder="Contexto opcional da reuniao"
                />
              </Field>

              <label className="flex gap-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <input
                  className="mt-1 h-4 w-4"
                  type="checkbox"
                  checked={form.consent}
                  onChange={(event) => setForm({ ...form, consent: event.target.checked })}
                />
                <span>
                  Confirmo que os participantes foram cientificados sobre gravacao e processamento
                  por IA para gerar ata, transcricao e tarefas.
                </span>
              </label>

              <button className="button-primary w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Criando..." : "Criar reuniao"}
              </button>
            </form>
          </Panel>

          <Panel title="Reunioes">
            {meetingsQuery.isLoading ? (
              <p className="text-sm text-slate-500">Carregando reunioes...</p>
            ) : meetings.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhuma reuniao criada ainda.</p>
            ) : (
              <div className="space-y-2">
                {meetings.map((meeting) => (
                  <button
                    className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                      selectedMeeting?.id === meeting.id
                        ? "border-lagoon bg-teal-50"
                        : "border-slate-200 bg-white hover:border-slate-300"
                    }`}
                    key={meeting.id}
                    onClick={() => selectMeeting(meeting.id)}
                  >
                    <div className="font-medium">{meeting.title}</div>
                    <div className="text-xs text-slate-500">
                      {meeting.client_name || "Sem cliente"} / {statusLabel[meeting.status]}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Panel>
        </section>

        <section className="space-y-5">
          {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

          <Panel title="Processamento">
            {selectedMeeting ? (
              <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
                <div className="space-y-4">
                  <MeetingHeader meeting={selectedMeeting} />
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="option">
                      <input
                        type="radio"
                        checked={analysisMode === "audio_only"}
                        onChange={() => setAnalysisMode("audio_only")}
                      />
                      <span>
                        <strong>Somente audio</strong>
                        <small>Extrai audio do video e ignora imagem.</small>
                      </span>
                    </label>
                    <label className="option">
                      <input
                        type="radio"
                        checked={analysisMode === "audio_video"}
                        onChange={() => setAnalysisMode("audio_video")}
                      />
                      <span>
                        <strong>Audio + video</strong>
                        <small>Reservado para contexto visual.</small>
                      </span>
                    </label>
                  </div>

                  <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                    <p className="mb-3 text-sm text-slate-600">
                      Formatos aceitos: mp3, wav, m4a, aac, ogg, flac, webm, mp4, mov,
                      mkv e avi.
                    </p>
                    <input
                      className="block w-full text-sm"
                      type="file"
                      accept="audio/*,video/*"
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="button-secondary"
                        disabled={!selectedFile || uploadMutation.isPending}
                        onClick={handleUpload}
                      >
                        {uploadMutation.isPending ? "Enviando..." : "Enviar arquivo"}
                      </button>
                      <button
                        className="button-primary"
                        disabled={!selectedMeeting.file || processMutation.isPending}
                        onClick={handleProcess}
                      >
                        {processMutation.isPending ? "Processando..." : "Gerar ata"}
                      </button>
                    </div>
                  </div>
                </div>

                <StatusBox meeting={selectedMeeting} />
              </div>
            ) : (
              <p className="text-sm text-slate-500">Crie uma reuniao para iniciar o processamento.</p>
            )}
          </Panel>

          {selectedMeeting?.analysis ? <AnalysisView meeting={selectedMeeting} /> : null}
        </section>
      </div>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-panel">
      <h2 className="mb-4 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}

function MeetingHeader({ meeting }: { meeting: Meeting }) {
  return (
    <div>
      <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {meeting.client_name || "Cliente nao informado"}
      </p>
      <h2 className="text-xl font-semibold">{meeting.title}</h2>
      <p className="mt-1 text-sm text-slate-500">
        Participantes: {meeting.participants.length > 0 ? meeting.participants.join(", ") : "nao informado"}
      </p>
    </div>
  );
}

function StatusBox({ meeting }: { meeting: Meeting }) {
  return (
    <aside className="rounded-md border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold">Status</h3>
      <dl className="mt-3 space-y-3 text-sm">
        <div>
          <dt className="text-slate-500">Etapa</dt>
          <dd className="font-medium">{statusLabel[meeting.status]}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Arquivo</dt>
          <dd className="font-medium">{meeting.file?.original_name || "Nenhum arquivo enviado"}</dd>
        </div>
        {meeting.file ? (
          <>
            <div>
              <dt className="text-slate-500">Tipo</dt>
              <dd className="font-medium">
                {meeting.file.media_kind} {meeting.file.extension}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Tamanho</dt>
              <dd className="font-medium">{formatBytes(meeting.file.size_bytes)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Duracao</dt>
              <dd className="font-medium">{formatDuration(meeting.file.duration_seconds)}</dd>
            </div>
            {meeting.file.codec_name ? (
              <div>
                <dt className="text-slate-500">Codec</dt>
                <dd className="font-medium">{meeting.file.codec_name}</dd>
              </div>
            ) : null}
          </>
        ) : null}
        {meeting.prepared_audio ? (
          <div>
            <dt className="text-slate-500">Audio preparado</dt>
            <dd className="font-medium">
              WAV {meeting.prepared_audio.sample_rate_hz / 1000}kHz /{" "}
              {formatBytes(meeting.prepared_audio.size_bytes)}
            </dd>
          </div>
        ) : null}
        <div>
          <dt className="text-slate-500">Modo</dt>
          <dd className="font-medium">{meeting.analysis_mode || "Nao processado"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Preset</dt>
          <dd className="font-medium">{meeting.preset}</dd>
        </div>
      </dl>
      {meeting.file?.validation_warnings.length ? (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          {meeting.file.validation_warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      {meeting.processing_steps.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Etapas</h4>
          <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-slate-600">
            {meeting.processing_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      ) : null}
      {meeting.processing_error ? (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          {meeting.processing_error}
        </div>
      ) : null}
    </aside>
  );
}

function AnalysisView({ meeting }: { meeting: Meeting }) {
  const queryClient = useQueryClient();
  const analysis = meeting.analysis;
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<MeetingAnalysisUpdate | null>(
    analysis ? analysisToDraft(analysis) : null,
  );
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysis) {
      setDraft(null);
      return;
    }
    setDraft(analysisToDraft(analysis));
    setIsEditing(false);
    setSaveError(null);
  }, [analysis, meeting.id]);

  const saveMutation = useMutation({
    mutationFn: (payload: MeetingAnalysisUpdate) => updateMeetingAnalysis(meeting.id, payload),
    onSuccess: async () => {
      setIsEditing(false);
      setSaveError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (mutationError) => setSaveError(mutationError.message),
  });

  if (!analysis) return null;
  const currentAnalysis = analysis;

  function startEditing() {
    setDraft(analysisToDraft(currentAnalysis));
    setSaveError(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    setDraft(analysisToDraft(currentAnalysis));
    setSaveError(null);
    setIsEditing(false);
  }

  function saveDraft() {
    if (!draft) return;
    setSaveError(null);
    saveMutation.mutate({
      ...draft,
      topics: cleanList(draft.topics),
      decisions: cleanList(draft.decisions),
      risks: cleanList(draft.risks),
      open_questions: cleanList(draft.open_questions),
      tasks: draft.tasks.filter((task) => task.title.trim() || task.description.trim()),
    });
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <Panel title="Ata gerada">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <dl className="grid grid-cols-2 gap-3 text-xs text-slate-600">
            <div>
              <dt className="font-semibold text-slate-500">Provedor</dt>
              <dd>{analysis.minutes_provider}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-500">Modelo</dt>
              <dd>{analysis.minutes_model}</dd>
            </div>
          </dl>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <button className="button-secondary" onClick={cancelEditing}>
                  Cancelar
                </button>
                <button className="button-primary" disabled={saveMutation.isPending} onClick={saveDraft}>
                  {saveMutation.isPending ? "Salvando..." : "Salvar revisao"}
                </button>
              </>
            ) : (
              <button className="button-secondary" onClick={startEditing}>
                Revisar ata
              </button>
            )}
          </div>
        </div>
        {saveError ? (
          <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {saveError}
          </div>
        ) : null}
        {isEditing && draft ? (
          <div className="space-y-4">
            <Field label="Ata em Markdown">
              <textarea
                className="input min-h-96 resize-y font-mono"
                value={draft.minutes_markdown}
                onChange={(event) => setDraft({ ...draft, minutes_markdown: event.target.value })}
              />
            </Field>
            <Field label="Resumo executivo">
              <textarea
                className="input min-h-24 resize-y"
                value={draft.executive_summary}
                onChange={(event) => setDraft({ ...draft, executive_summary: event.target.value })}
              />
            </Field>
          </div>
        ) : (
          <div className="prose-like whitespace-pre-wrap">{analysis.minutes_markdown}</div>
        )}
      </Panel>

      <div className="space-y-5">
        <Panel title="Transcricao">
          <dl className="mb-3 grid grid-cols-2 gap-3 text-xs text-slate-600">
            <div>
              <dt className="font-semibold text-slate-500">Provedor</dt>
              <dd>{analysis.transcript_provider}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-500">Modelo</dt>
              <dd>{analysis.transcript_model}</dd>
            </div>
          </dl>
          <div className="max-h-72 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <pre className="whitespace-pre-wrap font-sans">{analysis.transcript}</pre>
          </div>
        </Panel>

        <Panel title="Tarefas">
          {isEditing && draft ? (
            <TaskEditor
              tasks={draft.tasks}
              onChange={(tasks) => setDraft({ ...draft, tasks })}
            />
          ) : (
            <div className="space-y-3">
              {analysis.tasks.map((task) => (
                <TaskCard task={task} key={task.id} />
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Resumo">
          {isEditing && draft ? (
            <div className="space-y-4">
              <Field label="Topicos">
                <textarea
                  className="input min-h-24 resize-y"
                  value={draft.topics.join("\n")}
                  onChange={(event) => setDraft({ ...draft, topics: linesToList(event.target.value) })}
                />
              </Field>
              <Field label="Decisoes">
                <textarea
                  className="input min-h-24 resize-y"
                  value={draft.decisions.join("\n")}
                  onChange={(event) => setDraft({ ...draft, decisions: linesToList(event.target.value) })}
                />
              </Field>
              <Field label="Riscos">
                <textarea
                  className="input min-h-20 resize-y"
                  value={draft.risks.join("\n")}
                  onChange={(event) => setDraft({ ...draft, risks: linesToList(event.target.value) })}
                />
              </Field>
              <Field label="Duvidas abertas">
                <textarea
                  className="input min-h-20 resize-y"
                  value={draft.open_questions.join("\n")}
                  onChange={(event) => setDraft({ ...draft, open_questions: linesToList(event.target.value) })}
                />
              </Field>
            </div>
          ) : (
            <>
              <p className="text-sm text-slate-700">{analysis.executive_summary}</p>
              <h3 className="mt-4 text-sm font-semibold">Decisoes</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {analysis.decisions.map((decision) => (
                  <li key={decision}>{decision}</li>
                ))}
              </ul>
              {analysis.risks.length ? (
                <>
                  <h3 className="mt-4 text-sm font-semibold">Riscos</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                    {analysis.risks.map((risk) => (
                      <li key={risk}>{risk}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: TaskItem }) {
  return (
    <article className="rounded-md border border-slate-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold">{task.title}</h3>
        <span className={`rounded-full border px-2 py-0.5 text-xs ${priorityClass[task.priority]}`}>
          {priorityLabel[task.priority]}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600">{task.description}</p>
      <dl className="mt-3 grid gap-2 text-xs text-slate-500">
        <div>
          <dt className="font-semibold">Status</dt>
          <dd>{taskStatusLabel[task.status]}</dd>
        </div>
        {task.owner ? (
          <div>
            <dt className="font-semibold">Responsavel</dt>
            <dd>{task.owner}</dd>
          </div>
        ) : null}
        {task.due_date ? (
          <div>
            <dt className="font-semibold">Prazo</dt>
            <dd>{task.due_date}</dd>
          </div>
        ) : null}
      </dl>
      <p className="mt-2 text-xs text-slate-500">{task.priority_reason}</p>
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
    onChange(tasks.map((task, currentIndex) => (currentIndex === index ? { ...task, ...patch } : task)));
  }

  function removeTask(index: number) {
    onChange(tasks.filter((_, currentIndex) => currentIndex !== index));
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
        <article className="rounded-md border border-slate-200 p-3" key={task.id}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">Tarefa {index + 1}</h3>
            <button className="button-secondary px-3 py-1" onClick={() => removeTask(index)}>
              Remover
            </button>
          </div>
          <div className="space-y-3">
            <Field label="Titulo">
              <input
                className="input"
                value={task.title}
                onChange={(event) => updateTask(index, { title: event.target.value })}
              />
            </Field>
            <Field label="Descricao">
              <textarea
                className="input min-h-20 resize-y"
                value={task.description}
                onChange={(event) => updateTask(index, { description: event.target.value })}
              />
            </Field>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Prioridade">
                <select
                  className="input"
                  value={task.priority}
                  onChange={(event) => updateTask(index, { priority: event.target.value as Priority })}
                >
                  <option value="critical">Critica</option>
                  <option value="high">Alta</option>
                  <option value="medium">Media</option>
                  <option value="low">Baixa</option>
                </select>
              </Field>
              <Field label="Status">
                <select
                  className="input"
                  value={task.status}
                  onChange={(event) => updateTask(index, { status: event.target.value as TaskItem["status"] })}
                >
                  <option value="new">Nova</option>
                  <option value="review">Em revisao</option>
                  <option value="approved">Aprovada</option>
                </select>
              </Field>
            </div>
            <Field label="Justificativa da prioridade">
              <textarea
                className="input min-h-20 resize-y"
                value={task.priority_reason}
                onChange={(event) => updateTask(index, { priority_reason: event.target.value })}
              />
            </Field>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Responsavel">
                <input
                  className="input"
                  value={task.owner ?? ""}
                  onChange={(event) => updateTask(index, { owner: event.target.value || null })}
                />
              </Field>
              <Field label="Prazo">
                <input
                  className="input"
                  value={task.due_date ?? ""}
                  onChange={(event) => updateTask(index, { due_date: event.target.value || null })}
                />
              </Field>
            </div>
          </div>
        </article>
      ))}
      <button className="button-secondary w-full" onClick={addTask}>
        Adicionar tarefa
      </button>
    </div>
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

function linesToList(value: string) {
  return value.split("\n");
}

function cleanList(items: string[]) {
  return items.map((item) => item.trim()).filter(Boolean);
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
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return "Nao identificada";
  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = rounded % 60;
  if (minutes === 0) return `${remainingSeconds}s`;
  return `${minutes}min ${remainingSeconds.toString().padStart(2, "0")}s`;
}
