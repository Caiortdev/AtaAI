export type MeetingStatus = "draft" | "uploaded" | "processing" | "completed" | "failed";
export type AnalysisMode = "audio_only" | "audio_video";
export type Priority = "critical" | "high" | "medium" | "low";
export type MediaKind = "audio" | "video";

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
  title: string;
  client_name?: string | null;
  participants: string[];
  notes?: string | null;
  consent_confirmed: boolean;
  status: MeetingStatus;
  analysis_mode?: AnalysisMode | null;
  preset: string;
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
