from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MeetingStatus(StrEnum):
    draft = "draft"
    uploaded = "uploaded"
    recording = "recording"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AnalysisMode(StrEnum):
    audio_only = "audio_only"
    audio_video = "audio_video"


class Priority(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class MediaKind(StrEnum):
    audio = "audio"
    video = "video"


class MeetingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    client_name: str | None = Field(default=None, max_length=160)
    participants: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)
    consent_confirmed: bool = False


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class AuthToken(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserPublic


class MeetingPresetBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    instructions: str = Field(min_length=20, max_length=4000)


class MeetingPresetCreate(MeetingPresetBase):
    pass


class MeetingPresetUpdate(MeetingPresetBase):
    pass


class MeetingPreset(MeetingPresetBase):
    id: str = Field(default_factory=lambda: str(uuid4()))
    owner_id: str
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MeetingPresetListResponse(BaseModel):
    items: list[MeetingPreset]


class UploadedFileInfo(BaseModel):
    original_name: str
    stored_name: str
    extension: str = ""
    media_kind: MediaKind = MediaKind.audio
    content_type: str | None = None
    size_bytes: int
    duration_seconds: float | None = None
    codec_name: str | None = None
    validation_warnings: list[str] = Field(default_factory=list)


class PreparedAudioInfo(BaseModel):
    stored_name: str
    content_type: str = "audio/wav"
    size_bytes: int
    duration_seconds: float | None = None
    sample_rate_hz: int = 16000
    channels: int = 1


class LiveSessionState(StrEnum):
    idle = "idle"
    recording = "recording"
    paused = "paused"
    finalizing = "finalizing"
    done = "done"


class TaskItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    priority: Priority
    priority_reason: str
    owner: str | None = None
    due_date: str | None = None
    source_excerpt: str | None = None
    source_timestamp: str | None = None
    status: Literal["new", "review", "approved"] = "review"


class MeetingAnalysis(BaseModel):
    transcript: str
    transcript_provider: str = "mock"
    transcript_model: str = "mock"
    transcript_language: str | None = None
    minutes_provider: str = "mock"
    minutes_model: str = "mock"
    executive_summary: str
    topics: list[str]
    decisions: list[str]
    tasks: list[TaskItem]
    risks: list[str]
    open_questions: list[str]
    minutes_markdown: str


class MeetingAnalysisUpdate(BaseModel):
    executive_summary: str = Field(min_length=1, max_length=4000)
    topics: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    minutes_markdown: str = Field(min_length=1)


class Meeting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    owner_id: str | None = None
    title: str
    client_name: str | None = None
    participants: list[str] = Field(default_factory=list)
    notes: str | None = None
    consent_confirmed: bool = False
    status: MeetingStatus = MeetingStatus.draft
    analysis_mode: AnalysisMode | None = None
    preset: str = "ata_objetiva_com_tarefas"
    preset_id: str | None = None
    preset_instructions: str | None = None
    file: UploadedFileInfo | None = None
    prepared_audio: PreparedAudioInfo | None = None
    analysis: MeetingAnalysis | None = None
    processing_error: str | None = None
    processing_steps: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessMeetingRequest(BaseModel):
    mode: AnalysisMode = AnalysisMode.audio_only
    preset: str = "ata_objetiva_com_tarefas"
    preset_id: str | None = None
    auto_metadata: bool = False


class TrimRequest(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


class MeetingListResponse(BaseModel):
    items: list[Meeting]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    database: dict[str, str | bool] = Field(default_factory=dict)
    media_tools: dict[str, bool] = Field(default_factory=dict)
    transcription: dict[str, str | bool] = Field(default_factory=dict)
    minutes: dict[str, str | bool] = Field(default_factory=dict)


VALID_TRANSCRIPTION_PROVIDERS = ("gemini", "openai")
VALID_MINUTES_PROVIDERS = ("gemini", "openai", "anthropic")


class UserSettingsUpdate(BaseModel):
    transcription_provider: str | None = None
    minutes_provider: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class UserSettingsResponse(BaseModel):
    transcription_provider: str
    minutes_provider: str
    gemini_api_key_set: bool = False
    gemini_api_key_masked: str = ""
    openai_api_key_set: bool = False
    openai_api_key_masked: str = ""
    anthropic_api_key_set: bool = False
    anthropic_api_key_masked: str = ""


class ProvidersResponse(BaseModel):
    transcription: list[dict[str, str]]
    minutes: list[dict[str, str]]
