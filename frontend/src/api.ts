import type {
  AnalysisMode,
  AuthPayload,
  AuthSession,
  Meeting,
  MeetingAnalysisUpdate,
  MeetingCreate,
  MeetingPreset,
  MeetingPresetPayload,
  ProvidersResponse,
  RegisterPayload,
  User,
  UserSettings,
  UserSettingsPayload,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
let accessToken: string | null = null;

export function setAuthToken(token: string | null) {
  accessToken = token;
}

function formatApiError(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String(item.msg);
        }
        return String(item);
      })
      .filter(Boolean)
      .join(" ");
  }

  return "Erro inesperado.";
}

async function parseError(response: Response): Promise<string> {
  const error = await response.json().catch(() => ({ detail: "Erro inesperado." }));
  return formatApiError((error as { detail?: unknown }).detail);
}

let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(callback: () => void) {
  onUnauthorized = callback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init?.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("A requisicao excedeu o tempo limite. Verifique se o backend esta respondendo.");
    }
    throw new Error(
      `Nao foi possivel conectar ao backend em ${API_URL}. Verifique se a API esta rodando na porta 8000.`,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401 && accessToken && !path.includes("/api/auth/")) {
    if (onUnauthorized) onUnauthorized();
    throw new Error("Sessao expirada. Faca login novamente.");
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function registerUser(payload: RegisterPayload): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginUser(payload: AuthPayload): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser(): Promise<User> {
  return request<User>("/api/auth/me");
}

export async function logoutUser(): Promise<void> {
  await request<{ status: string }>("/api/auth/logout", { method: "POST" });
  setAuthToken(null);
}

export async function listMeetings(): Promise<Meeting[]> {
  const data = await request<{ items: Meeting[] }>("/api/meetings");
  return data.items;
}

export async function listMeetingsSummary(): Promise<Meeting[]> {
  const data = await request<{ items: Meeting[] }>("/api/meetings/summary");
  return data.items;
}

export async function getMeeting(meetingId: string): Promise<Meeting> {
  return request<Meeting>(`/api/meetings/${meetingId}`);
}

export async function listPresets(): Promise<MeetingPreset[]> {
  const data = await request<{ items: MeetingPreset[] }>("/api/presets");
  return data.items;
}

export async function createPreset(payload: MeetingPresetPayload): Promise<MeetingPreset> {
  return request<MeetingPreset>("/api/presets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updatePreset(
  presetId: string,
  payload: MeetingPresetPayload,
): Promise<MeetingPreset> {
  return request<MeetingPreset>(`/api/presets/${presetId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deletePreset(presetId: string): Promise<void> {
  await request<void>(`/api/presets/${presetId}`, { method: "DELETE" });
}

export async function createMeeting(payload: MeetingCreate): Promise<Meeting> {
  return request<Meeting>("/api/meetings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadMeetingFile(
  meetingId: string,
  file: File,
  autoProcess = false,
): Promise<Meeting> {
  const formData = new FormData();
  formData.append("file", file);

  const query = autoProcess ? "?auto_process=true" : "";
  const timeoutMs = Math.max(300000, Math.ceil(file.size / (1024 * 1024)) * 1000);
  let response: Response;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    response = await fetch(`${API_URL}/api/meetings/${meetingId}/upload${query}`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("O upload excedeu o tempo limite. Verifique sua conexao.");
    }
    throw new Error(
      `Nao foi possivel conectar ao backend em ${API_URL}. Verifique se a API esta rodando na porta 8000.`,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401 && accessToken) {
    if (onUnauthorized) onUnauthorized();
    throw new Error("Sessao expirada. Faca login novamente.");
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json() as Promise<Meeting>;
}

export async function processMeeting(
  meetingId: string,
  mode: AnalysisMode,
  presetId?: string | null,
): Promise<Meeting> {
  return request<Meeting>(`/api/meetings/${meetingId}/process`, {
    method: "POST",
    body: JSON.stringify({ mode, preset_id: presetId }),
  });
}

export async function updateMeetingAnalysis(
  meetingId: string,
  payload: MeetingAnalysisUpdate,
): Promise<Meeting> {
  return request<Meeting>(`/api/meetings/${meetingId}/analysis`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createLiveWebSocket(meetingId: string): WebSocket {
  const wsBase = API_URL.replace(/^http/, "ws");
  const token = accessToken ?? "";
  return new WebSocket(`${wsBase}/ws/live/${meetingId}?token=${encodeURIComponent(token)}`);
}

export async function quickProcessMeeting(
  file: File,
  presetId?: string,
  mode: "audio_only" | "audio_video" = "audio_only",
): Promise<Meeting> {
  const formData = new FormData();
  formData.append("file", file);
  if (presetId) formData.append("preset_id", presetId);
  if (mode !== "audio_only") formData.append("mode", mode);

  return request<Meeting>("/api/meetings/quick", {
    method: "POST",
    body: formData,
  });
}

export async function trimMeeting(
  meetingId: string,
  startSeconds: number,
  endSeconds: number,
): Promise<{ duration_seconds: number; size_bytes: number }> {
  return request<{ duration_seconds: number; size_bytes: number }>(
    `/api/meetings/${meetingId}/trim`,
    {
      method: "POST",
      body: JSON.stringify({ start_seconds: startSeconds, end_seconds: endSeconds }),
    },
  );
}

export async function getStorageConfig(): Promise<{ enabled: boolean; path: string }> {
  return request<{ enabled: boolean; path: string }>("/api/storage/config");
}

export async function updateStorageConfig(path: string): Promise<{ enabled: boolean; path: string }> {
  return request<{ enabled: boolean; path: string }>("/api/storage/config", {
    method: "PUT",
    body: JSON.stringify({ path }),
  });
}

export async function exportMeetingPdf(meetingId: string): Promise<{ blob: Blob; filename: string }> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/meetings/${meetingId}/analysis.pdf`, {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
  } catch (error) {
    throw new Error(
      `Nao foi possivel conectar ao backend em ${API_URL}. Verifique se a API esta rodando na porta 8000.`,
    );
  }
  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] ?? "ata-reuniao.pdf",
  };
}

export async function getUserSettings(): Promise<UserSettings> {
  return request<UserSettings>("/api/settings");
}

export async function updateUserSettings(payload: UserSettingsPayload): Promise<UserSettings> {
  return request<UserSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getProviders(): Promise<ProvidersResponse> {
  return request<ProvidersResponse>("/api/settings/providers");
}
