export type MeetingStatus = "draft" | "uploaded" | "recording" | "queued" | "processing" | "completed" | "failed";
export type AnalysisMode = "audio_only" | "audio_video";
export type Priority = "critical" | "high" | "medium" | "low";
export type MediaKind = "audio" | "video";

export type User = {
  id: string;
  name: string;
  email: string;
  created_at: string;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type AuthPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = AuthPayload & {
  name: string;
};

export type MeetingPreset = {
  id: string;
  owner_id: string;
  name: string;
  description?: string | null;
  instructions: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type MeetingPresetPayload = {
  name: string;
  description?: string | null;
  instructions: string;
};

export type UploadedFileInfo = {
  original_name: string;
  stored_name: string;
  extension: string;
  media_kind: MediaKind;
  content_type?: string | null;
  size_bytes: number;
  duration_seconds?: number | null;
  codec_name?: string | null;
  validation_warnings: string[];
};

export type PreparedAudioInfo = {
  stored_name: string;
  content_type: string;
  size_bytes: number;
  duration_seconds?: number | null;
  sample_rate_hz: number;
  channels: number;
};

export type TaskItem = {
  id: string;
  title: string;
  description: string;
  priority: Priority;
  priority_reason: string;
  owner?: string | null;
  due_date?: string | null;
  source_excerpt?: string | null;
  source_timestamp?: string | null;
  status: "new" | "review" | "approved";
};

export type MeetingAnalysis = {
  transcript: string;
  transcript_provider: string;
  transcript_model: string;
  transcript_language?: string | null;
  minutes_provider: string;
  minutes_model: string;
  executive_summary: string;
  topics: string[];
  decisions: string[];
  tasks: TaskItem[];
  risks: string[];
  open_questions: string[];
  minutes_markdown: string;
};

export type Meeting = {
  id: string;
  owner_id?: string | null;
  title: string;
  client_name?: string | null;
  participants: string[];
  notes?: string | null;
  consent_confirmed: boolean;
  status: MeetingStatus;
  analysis_mode?: AnalysisMode | null;
  preset: string;
  preset_id?: string | null;
  preset_instructions?: string | null;
  file?: UploadedFileInfo | null;
  prepared_audio?: PreparedAudioInfo | null;
  analysis?: MeetingAnalysis | null;
  processing_error?: string | null;
  processing_steps: string[];
  created_at: string;
  updated_at: string;
};

export type MeetingCreate = {
  title: string;
  client_name?: string | null;
  participants: string[];
  notes?: string | null;
  consent_confirmed: boolean;
};

export type MeetingAnalysisUpdate = Pick<
  MeetingAnalysis,
  | "executive_summary"
  | "topics"
  | "decisions"
  | "tasks"
  | "risks"
  | "open_questions"
  | "minutes_markdown"
>;

export type LiveSessionState = "idle" | "recording" | "paused" | "finalizing" | "done";

export type LiveMessage =
  | { type: "transcript"; text: string; is_final: boolean }
  | { type: "draft"; markdown: string }
  | { type: "status"; state: LiveSessionState }
  | { type: "error"; message: string };

export type UserSettings = {
  transcription_provider: string;
  minutes_provider: string;
  gemini_api_key_set: boolean;
  gemini_api_key_masked: string;
  openai_api_key_set: boolean;
  openai_api_key_masked: string;
  anthropic_api_key_set: boolean;
  anthropic_api_key_masked: string;
};

export type UserSettingsPayload = {
  transcription_provider?: string;
  minutes_provider?: string;
  gemini_api_key?: string;
  openai_api_key?: string;
  anthropic_api_key?: string;
};

export type ProviderInfo = {
  id: string;
  name: string;
  description: string;
};

export type ProvidersResponse = {
  transcription: ProviderInfo[];
  minutes: ProviderInfo[];
};
