import type {
  AnalysisMode,
  AuthPayload,
  AuthSession,
  Meeting,
  MeetingAnalysisUpdate,
  MeetingCreate,
  RegisterPayload,
  User,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
let accessToken: string | null = null;

export function setAuthToken(token: string | null) {
  accessToken = token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erro inesperado." }));
    throw new Error(error.detail ?? "Erro inesperado.");
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

export async function createMeeting(payload: MeetingCreate): Promise<Meeting> {
  return request<Meeting>("/api/meetings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadMeetingFile(meetingId: string, file: File): Promise<Meeting> {
  const formData = new FormData();
  formData.append("file", file);

  return request<Meeting>(`/api/meetings/${meetingId}/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function processMeeting(
  meetingId: string,
  mode: AnalysisMode,
  preset = "ata_objetiva_com_tarefas",
): Promise<Meeting> {
  return request<Meeting>(`/api/meetings/${meetingId}/process`, {
    method: "POST",
    body: JSON.stringify({ mode, preset }),
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

export async function exportMeetingPdf(meetingId: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_URL}/api/meetings/${meetingId}/analysis.pdf`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erro inesperado." }));
    throw new Error(error.detail ?? "Erro inesperado.");
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] ?? "ata-reuniao.pdf",
  };
}
