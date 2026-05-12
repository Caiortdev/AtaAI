from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MeetingStatus(StrEnum):
    draft = "draft"
    uploaded = "uploaded"
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
    title: str
    client_name: str | None = None
    participants: list[str] = Field(default_factory=list)
    notes: str | None = None
    consent_confirmed: bool = False
    status: MeetingStatus = MeetingStatus.draft
    analysis_mode: AnalysisMode | None = None
    preset: str = "ata_objetiva_com_tarefas"
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


class MeetingListResponse(BaseModel):
    items: list[Meeting]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    media_tools: dict[str, bool] = Field(default_factory=dict)
    transcription: dict[str, str | bool] = Field(default_factory=dict)
    minutes: dict[str, str | bool] = Field(default_factory=dict)
