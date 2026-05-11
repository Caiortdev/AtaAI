from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.domain import (
    HealthResponse,
    Meeting,
    MeetingCreate,
    MeetingListResponse,
    ProcessMeetingRequest,
    UploadedFileInfo,
)
from app.media import MediaService, MediaValidationError
from app.processing import MeetingProcessor
from app.repository import MeetingRepository
from app.transcription import build_transcription_provider


def get_repository(settings: Settings = Depends(get_settings)) -> MeetingRepository:
    return MeetingRepository(settings.storage_dir)


def get_media_service(settings: Settings = Depends(get_settings)) -> MediaService:
    return MediaService(settings)


def get_processor(
    settings: Settings = Depends(get_settings),
    media_service: MediaService = Depends(get_media_service),
) -> MeetingProcessor:
    transcription_provider = build_transcription_provider(settings, media_service)
    return MeetingProcessor(media_service, transcription_provider)


app = FastAPI(title="Gerador de Ata de Reuniao por IA", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings),
    media_service: MediaService = Depends(get_media_service),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        media_tools=media_service.tools_status(),
        transcription={
            "provider": settings.transcription_provider,
            "model": settings.transcription_model,
            "configured": bool(settings.openai_api_key)
            if settings.transcription_provider == "openai"
            else True,
        },
    )


@app.get("/api/meetings", response_model=MeetingListResponse)
def list_meetings(repository: MeetingRepository = Depends(get_repository)) -> MeetingListResponse:
    return MeetingListResponse(items=repository.list())


@app.post("/api/meetings", response_model=Meeting, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate,
    repository: MeetingRepository = Depends(get_repository),
) -> Meeting:
    if not payload.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirme que os participantes foram cientificados antes de processar a reuniao.",
        )
    return repository.create(payload)


@app.get("/api/meetings/{meeting_id}", response_model=Meeting)
def get_meeting(
    meeting_id: str,
    repository: MeetingRepository = Depends(get_repository),
) -> Meeting:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    return meeting


@app.post("/api/meetings/{meeting_id}/upload", response_model=Meeting)
async def upload_meeting_file(
    meeting_id: str,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    repository: MeetingRepository = Depends(get_repository),
    media_service: MediaService = Depends(get_media_service),
) -> Meeting:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")

    uploads_dir = settings.storage_dir / "uploads" / meeting_id
    uploads_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    try:
        extension, media_kind = media_service.validate_upload(file.filename, len(content))
    except MediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stored_name = f"{uuid4()}{extension}"
    target_path = uploads_dir / stored_name
    target_path.write_bytes(content)

    validation_warnings = []
    if not media_service.tools_status()["ffprobe"]:
        validation_warnings.append(
            "FFprobe nao esta configurado; duracao e codec serao validados no processamento."
        )

    file_info = UploadedFileInfo(
        original_name=file.filename or stored_name,
        stored_name=stored_name,
        extension=extension,
        media_kind=media_kind,
        content_type=file.content_type,
        size_bytes=len(content),
        validation_warnings=validation_warnings,
    )
    return repository.attach_file(meeting_id, file_info)


@app.post("/api/meetings/{meeting_id}/process", response_model=Meeting)
def process_meeting(
    meeting_id: str,
    payload: ProcessMeetingRequest,
    repository: MeetingRepository = Depends(get_repository),
    processor: MeetingProcessor = Depends(get_processor),
) -> Meeting:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    if meeting.file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo antes de processar a reuniao.",
        )

    processed = processor.process(meeting, payload)
    return repository.save(processed)
