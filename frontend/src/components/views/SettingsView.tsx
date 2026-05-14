import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { getUserSettings, updateUserSettings, getProviders } from "../../api";
import { useWorkspaceStore } from "../../store";
import { Glass } from "../ui/Glass";
import { Button } from "../ui/Button";
import { Field, Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Icon } from "../ui/Icon";

import type { UserSettingsPayload } from "../../types";

export function SettingsView() {
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["user-settings", accessToken],
    queryFn: getUserSettings,
    enabled: Boolean(accessToken),
  });

  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
    enabled: Boolean(accessToken),
  });

  const [transcriptionProvider, setTranscriptionProvider] = useState("");
  const [minutesProvider, setMinutesProvider] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (settingsQuery.data) {
      setTranscriptionProvider(settingsQuery.data.transcription_provider);
      setMinutesProvider(settingsQuery.data.minutes_provider);
    }
  }, [settingsQuery.data]);

  const mutation = useMutation({
    mutationFn: updateUserSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-settings"] });
      setSaved(true);
      setError("");
      setGeminiKey("");
      setOpenaiKey("");
      setAnthropicKey("");
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: Error) => {
      setError(err.message);
      setSaved(false);
    },
  });

  function handleSave() {
    const payload: UserSettingsPayload = {};

    if (transcriptionProvider && transcriptionProvider !== settingsQuery.data?.transcription_provider) {
      payload.transcription_provider = transcriptionProvider;
    }
    if (minutesProvider && minutesProvider !== settingsQuery.data?.minutes_provider) {
      payload.minutes_provider = minutesProvider;
    }
    if (geminiKey) payload.gemini_api_key = geminiKey;
    if (openaiKey) payload.openai_api_key = openaiKey;
    if (anthropicKey) payload.anthropic_api_key = anthropicKey;

    if (Object.keys(payload).length === 0) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      return;
    }

    mutation.mutate(payload);
  }

  const settings = settingsQuery.data;
  const providers = providersQuery.data;

  if (settingsQuery.isLoading) {
    return (
      <div className="page" style={{ maxWidth: 720 }}>
        <p className="muted">Carregando configuracoes...</p>
      </div>
    );
  }

  return (
    <div className="page" style={{ maxWidth: 720 }}>
      <h1 className="page-title" style={{ fontSize: 28, marginBottom: 8 }}>Configuracoes</h1>
      <p className="page-sub" style={{ fontSize: 14, marginBottom: 32 }}>
        Configure suas chaves de API e escolha os provedores de IA para transcricao e geracao de ata.
      </p>

      <Glass style={{ padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Provedores</h2>

        <Field label="Transcricao" hint="Provedor usado para converter audio em texto">
          <Select
            value={transcriptionProvider}
            onChange={(e) => setTranscriptionProvider(e.target.value)}
          >
            {providers?.transcription.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            )) ?? (
              <>
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI Whisper</option>
              </>
            )}
          </Select>
        </Field>

        <Field label="Geracao de ata" hint="Provedor usado para gerar a ata estruturada a partir da transcricao">
          <Select
            value={minutesProvider}
            onChange={(e) => setMinutesProvider(e.target.value)}
          >
            {providers?.minutes.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            )) ?? (
              <>
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic Claude</option>
              </>
            )}
          </Select>
        </Field>
      </Glass>

      <Glass style={{ padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Chaves de API</h2>
        <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
          Suas chaves sao criptografadas e armazenadas com seguranca. Preencha apenas as chaves dos provedores que deseja usar.
        </p>

        <Field
          label="Google Gemini API Key"
          hint={settings?.gemini_api_key_set ? `Configurada: ${settings.gemini_api_key_masked}` : "Nao configurada"}
        >
          <Input
            type="password"
            placeholder={settings?.gemini_api_key_set ? "Manter chave atual" : "Cole sua chave aqui"}
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            autoComplete="off"
          />
        </Field>

        <Field
          label="OpenAI API Key"
          hint={settings?.openai_api_key_set ? `Configurada: ${settings.openai_api_key_masked}` : "Nao configurada"}
        >
          <Input
            type="password"
            placeholder={settings?.openai_api_key_set ? "Manter chave atual" : "Cole sua chave aqui"}
            value={openaiKey}
            onChange={(e) => setOpenaiKey(e.target.value)}
            autoComplete="off"
          />
        </Field>

        <Field
          label="Anthropic API Key"
          hint={settings?.anthropic_api_key_set ? `Configurada: ${settings.anthropic_api_key_masked}` : "Nao configurada"}
        >
          <Input
            type="password"
            placeholder={settings?.anthropic_api_key_set ? "Manter chave atual" : "Cole sua chave aqui"}
            value={anthropicKey}
            onChange={(e) => setAnthropicKey(e.target.value)}
            autoComplete="off"
          />
        </Field>
      </Glass>

      {error && (
        <div style={{ color: "var(--color-error)", fontSize: 13, marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Button onClick={handleSave} disabled={mutation.isPending}>
          {mutation.isPending ? "Salvando..." : "Salvar configuracoes"}
        </Button>
        {saved && (
          <span style={{ color: "var(--color-success)", fontSize: 13 }}>
            Configuracoes salvas
          </span>
        )}
      </div>
    </div>
  );
}
