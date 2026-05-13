import { type FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createMeeting } from "../api";
import { useWorkspaceStore } from "../store";
import { Button } from "./ui/Button";
import { Field } from "./ui/Input";
import { Panel } from "./ui/Panel";

export function MeetingForm() {
  const queryClient = useQueryClient();
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);
  const [form, setForm] = useState({
    title: "",
    clientName: "",
    participants: "",
    notes: "",
    consent: false,
  });
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: createMeeting,
    onSuccess: async (meeting) => {
      selectMeeting(meeting.id);
      setForm({ title: "", clientName: "", participants: "", notes: "", consent: false });
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err) => setError(err.message),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    createMutation.mutate({
      title: form.title,
      client_name: form.clientName || null,
      participants: form.participants
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean),
      notes: form.notes || null,
      consent_confirmed: form.consent,
    });
  }

  return (
    <Panel title="Nova reuniao">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <Field label="Titulo">
          <input
            className="input"
            minLength={3}
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Alinhamento com cliente"
          />
        </Field>

        <Field label="Cliente">
          <input
            className="input"
            value={form.clientName}
            onChange={(e) => setForm({ ...form, clientName: e.target.value })}
            placeholder="Nome do cliente ou empresa"
          />
        </Field>

        <Field label="Participantes">
          <input
            className="input"
            value={form.participants}
            onChange={(e) => setForm({ ...form, participants: e.target.value })}
            placeholder="Ana, Bruno, Cliente X"
          />
        </Field>

        <Field label="Observacoes">
          <textarea
            className="input min-h-20 resize-y"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Contexto opcional da reuniao"
          />
        </Field>

        <label className="flex gap-3 rounded-md border border-warning/30 bg-warning-muted p-3 text-sm text-text-primary">
          <input
            className="mt-1 h-4 w-4 accent-accent"
            type="checkbox"
            checked={form.consent}
            onChange={(e) => setForm({ ...form, consent: e.target.checked })}
          />
          <span>
            Confirmo que os participantes foram cientificados sobre gravacao e processamento
            por IA para gerar ata, transcricao e tarefas.
          </span>
        </label>

        {error && (
          <div className="rounded-md border border-danger/30 bg-danger-muted p-3 text-sm text-danger">
            {error}
          </div>
        )}

        <Button className="w-full" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Criando..." : "Criar reuniao"}
        </Button>
      </form>
    </Panel>
  );
}
