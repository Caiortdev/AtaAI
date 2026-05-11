import type { AnalysisMode, Meeting, MeetingCreate } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erro inesperado." }));
    throw new Error(error.detail ?? "Erro inesperado.");
  }

  return response.json() as Promise<T>;
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
