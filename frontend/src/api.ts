import type {
  AnalysisMode,
  AuthPayload,
  AuthSession,
  Meeting,
  MeetingAnalysisUpdate,
  MeetingCreate,
  MeetingPreset,
  MeetingPresetPayload,
  RegisterPayload,
  User,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init?.headers,
      },
    });
  } catch (error) {
    throw new Error(
      `Nao foi possivel conectar ao backend em ${API_URL}. Verifique se a API esta rodando na porta 8000.`,
    );
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
  return request<Meeting>(`/api/meetings/${meetingId}/upload${query}`, {
    method: "POST",
    body: formData,
  });
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
