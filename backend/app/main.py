from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.domain import (
    HealthResponse,
    Meeting,
    MeetingAnalysisUpdate,
    MeetingCreate,
    MeetingListResponse,
    MeetingStatus,
    ProcessMeetingRequest,
    UploadedFileInfo,
)
from app.jobs import ProcessingQueue, processing_queue
from app.media import MediaService, MediaValidationError
from app.minutes import build_minutes_provider
from app.pdf_export import generate_meeting_pdf, pdf_filename
from app.processing import MeetingProcessor
from app.repository import MeetingRepository, build_meeting_repository
from app.transcription import build_transcription_provider


def get_repository(settings: Settings = Depends(get_settings)) -> MeetingRepository:
    return build_meeting_repository(settings)


def get_media_service(settings: Settings = Depends(get_settings)) -> MediaService:
    return MediaService(settings)


def get_processor(
    settings: Settings = Depends(get_settings),
    media_service: MediaService = Depends(get_media_service),
) -> MeetingProcessor:
    transcription_provider = build_transcription_provider(settings, media_service)
    minutes_provider = build_minutes_provider(settings)
    return MeetingProcessor(media_service, transcription_provider, minutes_provider)


def get_processing_queue() -> ProcessingQueue:
    return processing_queue


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
        database={
            "backend": settings.database_backend,
            "path": str(settings.database_path) if settings.database_backend == "sqlite" else "",
            "configured": database_configured(settings),
        },
        media_tools=media_service.tools_status(),
        transcription={
            "provider": settings.transcription_provider,
            "model": settings.transcription_model,
            "configured": provider_configured(
                settings.transcription_provider,
                settings,
            ),
        },
        minutes={
            "provider": settings.minutes_provider,
            "model": settings.minutes_model,
            "configured": provider_configured(settings.minutes_provider, settings),
        },
    )


def provider_configured(provider: str, settings: Settings) -> bool:
    normalized = provider.lower().strip()
    if normalized == "gemini":
        return bool(settings.gemini_api_key)
    if normalized == "openai":
        return bool(settings.openai_api_key)
    return True


def database_configured(settings: Settings) -> bool:
    backend = settings.database_backend.lower().strip()
    if backend == "postgres":
        return bool(settings.database_url)
    return backend in {"sqlite", "json"}


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
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> Meeting:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    if meeting.file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo antes de processar a reuniao.",
        )
    if meeting.status in {MeetingStatus.queued, MeetingStatus.processing}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta reuniao ja esta na fila ou em processamento.",
        )

    meeting.status = MeetingStatus.queued
    meeting.analysis_mode = payload.mode
    meeting.preset = payload.preset
    meeting.processing_error = None
    meeting.processing_steps = ["Arquivo recebido", "Processamento enfileirado"]
    queued = repository.save(meeting)
    queue.enqueue(
        meeting_id=meeting.id,
        run=lambda: run_processing_job(meeting.id, payload, repository, processor),
    )
    return queued


def run_processing_job(
    meeting_id: str,
    payload: ProcessMeetingRequest,
    repository: MeetingRepository,
    processor: MeetingProcessor,
) -> None:
    meeting = repository.get(meeting_id)
    if meeting is None:
        return

    try:
        processed = processor.process(meeting, payload)
    except Exception as exc:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = f"Erro inesperado no processamento: {exc}"
        meeting.processing_steps.append("Processamento interrompido")
        repository.save(meeting)
        return

    repository.save(processed)


@app.patch("/api/meetings/{meeting_id}/analysis", response_model=Meeting)
def update_meeting_analysis(
    meeting_id: str,
    payload: MeetingAnalysisUpdate,
    repository: MeetingRepository = Depends(get_repository),
) -> Meeting:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    if meeting.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gere uma ata antes de revisar o conteudo.",
        )

    meeting.analysis.executive_summary = payload.executive_summary
    meeting.analysis.topics = payload.topics
    meeting.analysis.decisions = payload.decisions
    meeting.analysis.tasks = payload.tasks
    meeting.analysis.risks = payload.risks
    meeting.analysis.open_questions = payload.open_questions
    meeting.analysis.minutes_markdown = payload.minutes_markdown
    return repository.save(meeting)


@app.get("/api/meetings/{meeting_id}/analysis.pdf")
def export_meeting_analysis_pdf(
    meeting_id: str,
    repository: MeetingRepository = Depends(get_repository),
) -> Response:
    meeting = repository.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    if meeting.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gere uma ata antes de exportar o PDF.",
        )

    pdf = generate_meeting_pdf(meeting)
    filename = pdf_filename(meeting)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
