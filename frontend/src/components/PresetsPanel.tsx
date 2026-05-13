import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createPreset, deletePreset, listPresets, updatePreset } from "../api";
import { useWorkspaceStore } from "../store";
import type { MeetingPreset, MeetingPresetPayload } from "../types";
import { Button } from "./ui/Button";
import { Field } from "./ui/Input";
import { Panel } from "./ui/Panel";

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

  const [draft, setDraft] = useState<MeetingPresetPayload>({
    name: "",
    description: "",
    instructions: "",
  });
  const [presetError, setPresetError] = useState<string | null>(null);

  useEffect(() => {
    if (!presets.length || selectedPresetId) return;
    if (presets[0]) onSelectPreset(presets[0].id);
  }, [presets, selectedPresetId, onSelectPreset]);

  useEffect(() => {
    if (!selectedPreset || selectedPreset.is_default) {
      setDraft({ name: "", description: "", instructions: "" });
      return;
    }
    setDraft({
      name: selectedPreset.name,
      description: selectedPreset.description ?? "",
      instructions: selectedPreset.instructions,
    });
  }, [selectedPreset]);

  const createMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: async (preset) => {
      setPresetError(null);
      onSelectPreset(preset.id);
      await queryClient.invalidateQueries({ queryKey: ["presets"] });
    },
    onError: (err) => setPresetError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: MeetingPresetPayload }) =>
      updatePreset(id, payload),
    onSuccess: async (preset) => {
      setPresetError(null);
      onSelectPreset(preset.id);
      await queryClient.invalidateQueries({ queryKey: ["presets"] });
    },
    onError: (err) => setPresetError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePreset,
    onSuccess: async () => {
      setPresetError(null);
      const defaultPreset = presets.find((p) => p.is_default) ?? presets[0];
      if (defaultPreset) onSelectPreset(defaultPreset.id);
      await queryClient.invalidateQueries({ queryKey: ["presets"] });
    },
    onError: (err) => setPresetError(err.message),
  });

  function savePreset() {
    const payload = {
      name: draft.name.trim(),
      description: draft.description?.trim() || null,
      instructions: draft.instructions.trim(),
    };
    if (selectedPreset && !selectedPreset.is_default) {
      updateMutation.mutate({ id: selectedPreset.id, payload });
      return;
    }
    createMutation.mutate(payload);
  }

  const canEditSelected = Boolean(selectedPreset && !selectedPreset.is_default);
  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <Panel title="Presets de ata">
      <div className="space-y-4">
        <Field label="Modelo usado na geracao">
          <select
            className="input"
            value={selectedPreset?.id ?? ""}
            onChange={(e) => onSelectPreset(e.target.value)}
          >
            {presets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name}
              </option>
            ))}
          </select>
        </Field>

        {selectedPreset?.description && (
          <p className="rounded-md border border-border bg-bg-secondary p-3 text-sm text-text-secondary">
            {selectedPreset.description}
          </p>
        )}

        <div className="space-y-3 border-t border-border pt-4">
          <Field label={canEditSelected ? "Nome do preset" : "Nome do novo preset"}>
            <input
              className="input"
              minLength={3}
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              placeholder="Ata executiva"
            />
          </Field>
          <Field label="Descricao">
            <input
              className="input"
              value={draft.description ?? ""}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              placeholder="Quando usar este modelo"
            />
          </Field>
          <Field label="Instrucoes para IA">
            <textarea
              className="input min-h-28 resize-y"
              value={draft.instructions}
              onChange={(e) => setDraft({ ...draft, instructions: e.target.value })}
              placeholder="Ex: foque em decisoes, riscos e proximos passos executivos."
            />
          </Field>

          {presetError && (
            <div className="rounded-md border border-danger/30 bg-danger-muted p-3 text-sm text-danger">
              {presetError}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={isPending || draft.name.trim().length < 3 || draft.instructions.trim().length < 20}
              onClick={savePreset}
            >
              {isPending ? "Salvando..." : canEditSelected ? "Salvar preset" : "Criar preset"}
            </Button>
            {canEditSelected && selectedPreset && (
              <Button
                variant="danger"
                disabled={isPending}
                onClick={() => deleteMutation.mutate(selectedPreset.id)}
              >
                Remover
              </Button>
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
