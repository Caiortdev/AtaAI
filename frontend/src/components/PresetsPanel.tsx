import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createPreset, deletePreset, listPresets, updatePreset } from "../api";
import { useWorkspaceStore } from "../store";
import type { MeetingPreset, MeetingPresetPayload } from "../types";
import { Icon } from "./ui/Icon";
import { Glass } from "./ui/Glass";
import { Button } from "./ui/Button";
import { Chip } from "./ui/Chip";
import { Field } from "./ui/Input";

type PresetsPanelProps = {
  selectedPresetId: string | null;
  onSelectPreset: (id: string) => void;
};

export function PresetsPanel({ selectedPresetId, onSelectPreset }: PresetsPanelProps) {
  const queryClient = useQueryClient();
  const accessToken = useWorkspaceStore((s) => s.accessToken);

  const presetsQuery = useQuery({
    queryKey: ["presets", accessToken],
    queryFn: listPresets,
    enabled: Boolean(accessToken),
  });

  const presets = presetsQuery.data ?? [];
  const selectedPreset = presets.find((p) => p.id === selectedPresetId) ?? presets[0];

  const [draft, setDraft] = useState<MeetingPresetPayload>({ name: "", description: "", instructions: "" });
  const [presetError, setPresetError] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  useEffect(() => {
    if (!presets.length || selectedPresetId) return;
    if (presets[0]) onSelectPreset(presets[0].id);
  }, [presets, selectedPresetId, onSelectPreset]);

  useEffect(() => {
    if (!selectedPreset || selectedPreset.is_default) {
      setDraft({ name: "", description: "", instructions: "" });
      return;
    }
    setDraft({ name: selectedPreset.name, description: selectedPreset.description ?? "", instructions: selectedPreset.instructions });
  }, [selectedPreset]);

  const createMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: async (preset) => { setPresetError(null); onSelectPreset(preset.id); await queryClient.invalidateQueries({ queryKey: ["presets"] }); },
    onError: (err) => setPresetError(err.message),
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: MeetingPresetPayload }) => updatePreset(id, payload),
    onSuccess: async (preset) => { setPresetError(null); onSelectPreset(preset.id); await queryClient.invalidateQueries({ queryKey: ["presets"] }); },
    onError: (err) => setPresetError(err.message),
  });
  const deleteMutation = useMutation({
    mutationFn: deletePreset,
    onSuccess: async () => { setPresetError(null); const d = presets.find((p) => p.is_default) ?? presets[0]; if (d) onSelectPreset(d.id); await queryClient.invalidateQueries({ queryKey: ["presets"] }); },
    onError: (err) => setPresetError(err.message),
  });

  function savePreset() {
    const payload = { name: draft.name.trim(), description: draft.description?.trim() || null, instructions: draft.instructions.trim() };
    if (selectedPreset && !selectedPreset.is_default) { updateMutation.mutate({ id: selectedPreset.id, payload }); return; }
    createMutation.mutate(payload);
  }

  const canEdit = Boolean(selectedPreset && !selectedPreset.is_default);
  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <Glass style={{ padding: 24 }}>
      <div className="row between" style={{ marginBottom: 16 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Preset de ata</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>Define como a IA estrutura o documento</div>
        </div>
        <Button variant="ghost" size="sm" icon="gear" onClick={() => setShowEditor(!showEditor)}>Gerenciar</Button>
      </div>

      <div className="col" style={{ gap: 8 }}>
        {presets.map((p) => {
          const active = (selectedPresetId || presets[0]?.id) === p.id;
          return (
            <div key={p.id} onClick={() => onSelectPreset(p.id)} style={{ padding: "12px 14px", borderRadius: 12, border: "1px solid " + (active ? "var(--accent)" : "var(--line)"), background: active ? "var(--accent-soft)" : "transparent", cursor: "pointer", transition: "all 0.2s var(--ease)" }}>
              <div className="row between">
                <div style={{ fontWeight: 600, fontSize: 13.5 }}>{p.name}</div>
                {active && <Icon name="check-circle" weight="fill" size={16} style={{ color: "var(--accent)" }} />}
              </div>
              {p.description && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{p.description}</div>}
            </div>
          );
        })}
      </div>

      {showEditor && (
        <div style={{ marginTop: 18, paddingTop: 18, borderTop: "1px solid var(--line)" }}>
          <div className="col" style={{ gap: 12 }}>
            <Field label={canEdit ? "Nome do preset" : "Nome do novo preset"}>
              <input className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Ata executiva" />
            </Field>
            <Field label="Descricao">
              <input className="input" value={draft.description ?? ""} onChange={(e) => setDraft({ ...draft, description: e.target.value })} placeholder="Quando usar este modelo" />
            </Field>
            <Field label="Instrucoes para IA">
              <textarea className="textarea" value={draft.instructions} onChange={(e) => setDraft({ ...draft, instructions: e.target.value })} placeholder="Ex: foque em decisoes, riscos e proximos passos." />
            </Field>
            {presetError && <div style={{ padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{presetError}</div>}
            <div className="row" style={{ gap: 8 }}>
              <Button size="sm" disabled={isPending || draft.name.trim().length < 3 || draft.instructions.trim().length < 20} onClick={savePreset}>
                {isPending ? "Salvando..." : canEdit ? "Salvar" : "Criar"}
              </Button>
              {canEdit && selectedPreset && (
                <Button variant="danger" size="sm" disabled={isPending} onClick={() => deleteMutation.mutate(selectedPreset.id)}>Remover</Button>
              )}
            </div>
          </div>
        </div>
      )}
    </Glass>
  );
}
