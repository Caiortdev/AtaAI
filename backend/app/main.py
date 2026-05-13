from contextlib import asynccontextmanager
from uuid import uuid4
import asyncio
import base64
import json

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.domain import (
    AuthToken,
    HealthResponse,
    LiveSessionState,
    Meeting,
    MeetingAnalysisUpdate,
    MeetingCreate,
    MeetingListResponse,
    MeetingPreset,
    MeetingPresetCreate,
    MeetingPresetListResponse,
    MeetingPresetUpdate,
    MeetingStatus,
    ProcessMeetingRequest,
    UploadedFileInfo,
    UserLogin,
    UserPublic,
    UserRegister,
)
from app.jobs import ProcessingQueue, processing_queue
from app.live import LiveSession, LiveSessionError
from app.media import MediaProcessingError, MediaService, MediaValidationError
from app.minutes import build_minutes_provider
from app.pdf_export import generate_meeting_pdf, pdf_filename
from app.processing import MeetingProcessor
from app.repository import (
    AuthRepository,
    MeetingRepository,
    PresetRepository,
    build_auth_repository,
    build_meeting_repository,
    build_preset_repository,
)
from app.transcription import build_transcription_provider


bearer_scheme = HTTPBearer(auto_error=False)
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024


def cors_origins(settings: Settings) -> list[str]:
    configured_origins = [
        origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()
    ]
    default_origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ]
    return list(dict.fromkeys([*configured_origins, *default_origins]))


def initialize_database(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.database_backend.lower().strip() != "sqlite":
        return
    build_auth_repository(settings)
    build_meeting_repository(settings)
    build_preset_repository(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


def get_repository(settings: Settings = Depends(get_settings)) -> MeetingRepository:
    return build_meeting_repository(settings)


def get_auth_repository(settings: Settings = Depends(get_settings)) -> AuthRepository:
    return build_auth_repository(settings)


def get_preset_repository(settings: Settings = Depends(get_settings)) -> PresetRepository:
    return build_preset_repository(settings)


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_repository: AuthRepository = Depends(get_auth_repository),
) -> UserPublic:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faca login para acessar esta area.",
        )
    user = auth_repository.get_user_by_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida ou expirada.",
        )
    return user


app = FastAPI(
    title="Gerador de Ata de Reuniao por IA",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings),
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


@app.post("/api/auth/register", response_model=AuthToken, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegister,
    settings: Settings = Depends(get_settings),
    auth_repository: AuthRepository = Depends(get_auth_repository),
) -> AuthToken:
    try:
        user = auth_repository.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    token = auth_repository.create_session(user.id, settings.auth_session_days)
    return AuthToken(access_token=token, user=user)


@app.post("/api/auth/login", response_model=AuthToken)
def login_user(
    payload: UserLogin,
    settings: Settings = Depends(get_settings),
    auth_repository: AuthRepository = Depends(get_auth_repository),
) -> AuthToken:
    user = auth_repository.verify_credentials(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha invalidos.",
        )
    token = auth_repository.create_session(user.id, settings.auth_session_days)
    return AuthToken(access_token=token, user=user)


@app.get("/api/auth/me", response_model=UserPublic)
def get_me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user


@app.post("/api/auth/logout")
def logout_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_repository: AuthRepository = Depends(get_auth_repository),
) -> dict[str, str]:
    if credentials is not None:
        auth_repository.revoke_session(credentials.credentials)
    return {"status": "ok"}


@app.get("/api/presets", response_model=MeetingPresetListResponse)
def list_presets(
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
) -> MeetingPresetListResponse:
    return MeetingPresetListResponse(items=preset_repository.list(current_user.id))


@app.post("/api/presets", response_model=MeetingPreset, status_code=status.HTTP_201_CREATED)
def create_preset(
    payload: MeetingPresetCreate,
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
) -> MeetingPreset:
    return preset_repository.create(payload, current_user.id)


@app.patch("/api/presets/{preset_id}", response_model=MeetingPreset)
def update_preset(
    preset_id: str,
    payload: MeetingPresetUpdate,
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
) -> MeetingPreset:
    preset = preset_repository.update(preset_id, payload, current_user.id)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset nao encontrado ou protegido contra edicao.",
        )
    return preset


@app.delete("/api/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    preset_id: str,
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
) -> Response:
    deleted = preset_repository.delete(preset_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset nao encontrado ou protegido contra exclusao.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/meetings", response_model=MeetingListResponse)
def list_meetings(
    repository: MeetingRepository = Depends(get_repository),
    current_user: UserPublic = Depends(get_current_user),
) -> MeetingListResponse:
    return MeetingListResponse(items=repository.list(owner_id=current_user.id))


@app.post("/api/meetings", response_model=Meeting, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate,
    repository: MeetingRepository = Depends(get_repository),
    current_user: UserPublic = Depends(get_current_user),
) -> Meeting:
    if not payload.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirme que os participantes foram cientificados antes de processar a reuniao.",
        )
    return repository.create(payload, owner_id=current_user.id)


@app.get("/api/meetings/{meeting_id}", response_model=Meeting)
def get_meeting(
    meeting_id: str,
    repository: MeetingRepository = Depends(get_repository),
    current_user: UserPublic = Depends(get_current_user),
) -> Meeting:
    meeting = repository.get(meeting_id, owner_id=current_user.id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")
    return meeting


@app.post("/api/meetings/{meeting_id}/upload", response_model=Meeting)
async def upload_meeting_file(
    meeting_id: str,
    file: UploadFile = File(...),
    auto_process: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    repository: MeetingRepository = Depends(get_repository),
    media_service: MediaService = Depends(get_media_service),
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> Meeting:
    meeting = repository.get(meeting_id, owner_id=current_user.id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reuniao nao encontrada.")

    uploads_dir = settings.storage_dir / "uploads" / meeting_id
    uploads_dir.mkdir(parents=True, exist_ok=True)

    try:
        extension, media_kind = media_service.validate_upload_type(file.filename)
    except MediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stored_name = f"{uuid4()}{extension}"
    target_path = uploads_dir / stored_name
    size_bytes = 0
    try:
        with target_path.open("wb") as output:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > settings.max_upload_bytes:
                    raise MediaValidationError(
                        f"O arquivo excede o limite de {settings.max_upload_bytes // (1024 * 1024)} MB."
                    )
                output.write(chunk)
        media_service.validate_upload_size(size_bytes)
    except MediaValidationError as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    validation_warnings = []
    media_tools = media_service.tools_status()
    if not media_tools["ffprobe"]:
        validation_warnings.append(
            "FFprobe nao esta configurado; duracao e codec serao validados no processamento."
        )
    if not media_tools["ffmpeg"]:
        validation_warnings.append(
            "FFmpeg nao esta configurado; o arquivo original sera mantido ate o processamento."
        )

    file_info = UploadedFileInfo(
        original_name=file.filename or stored_name,
        stored_name=stored_name,
        extension=extension,
        media_kind=media_kind,
        content_type=file.content_type,
        size_bytes=size_bytes,
        validation_warnings=validation_warnings,
    )
    prepared_audio = None
    if media_tools["ffmpeg"] and media_tools["ffprobe"]:
        try:
            prepared_audio = media_service.prepare_audio(meeting_id, file_info)
        except MediaProcessingError as exc:
            target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        media_service.delete_upload(meeting_id, file_info)
        file_info.validation_warnings.append(
            "Arquivo original removido apos gerar audio comprimido para processamento."
        )

    updated = repository.attach_file(meeting_id, file_info, owner_id=current_user.id)
    if prepared_audio is not None:
        updated.prepared_audio = prepared_audio
        updated.processing_steps.append("Audio comprimido preparado no upload")
        updated = repository.save(updated)

    if auto_process and updated.prepared_audio is not None:
        preset = preset_repository.ensure_default(current_user.id)
        request = ProcessMeetingRequest(preset_id=preset.id)
        updated.status = MeetingStatus.queued
        updated.preset = preset.name
        updated.preset_id = preset.id
        updated.preset_instructions = preset.instructions
        updated.processing_steps.append("Processamento enfileirado automaticamente")
        updated = repository.save(updated)

        transcription_provider = build_transcription_provider(settings, media_service)
        minutes_prov = build_minutes_provider(settings)
        processor = MeetingProcessor(media_service, transcription_provider, minutes_prov)
        queue.enqueue(
            meeting_id=updated.id,
            run=lambda: run_processing_job(updated.id, request, repository, processor),
        )

    return updated


@app.post("/api/meetings/{meeting_id}/process", response_model=Meeting)
def process_meeting(
    meeting_id: str,
    payload: ProcessMeetingRequest,
    repository: MeetingRepository = Depends(get_repository),
    processor: MeetingProcessor = Depends(get_processor),
    queue: ProcessingQueue = Depends(get_processing_queue),
    current_user: UserPublic = Depends(get_current_user),
    preset_repository: PresetRepository = Depends(get_preset_repository),
) -> Meeting:
    meeting = repository.get(meeting_id, owner_id=current_user.id)
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

    preset = resolve_processing_preset(payload, current_user.id, preset_repository)

    meeting.status = MeetingStatus.queued
    meeting.analysis_mode = payload.mode
    meeting.preset = preset.name
    meeting.preset_id = preset.id
    meeting.preset_instructions = preset.instructions
    meeting.processing_error = None
    meeting.processing_steps = ["Arquivo recebido", "Processamento enfileirado"]
    queued = repository.save(meeting)
    queue.enqueue(
        meeting_id=meeting.id,
        run=lambda: run_processing_job(meeting.id, payload, repository, processor),
    )
    return queued


def resolve_processing_preset(
    payload: ProcessMeetingRequest,
    owner_id: str,
    preset_repository: PresetRepository,
) -> MeetingPreset:
    if payload.preset_id:
        preset = preset_repository.get(payload.preset_id, owner_id)
        if preset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset nao encontrado.")
        return preset

    return preset_repository.ensure_default(owner_id)


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
    current_user: UserPublic = Depends(get_current_user),
) -> Meeting:
    meeting = repository.get(meeting_id, owner_id=current_user.id)
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
    current_user: UserPublic = Depends(get_current_user),
) -> Response:
    meeting = repository.get(meeting_id, owner_id=current_user.id)
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


def authenticate_ws_token(token: str, auth_repository: AuthRepository) -> UserPublic | None:
    if not token:
        return None
    return auth_repository.get_user_by_token(token)


@app.websocket("/ws/live/{meeting_id}")
async def live_session_ws(
    websocket: WebSocket,
    meeting_id: str,
) -> None:
    settings = get_settings()
    auth_repository = build_auth_repository(settings)
    repository = build_meeting_repository(settings)

    token = websocket.query_params.get("token", "")
    user = authenticate_ws_token(token, auth_repository)
    if user is None:
        await websocket.close(code=4001, reason="Autenticacao necessaria.")
        return

    meeting = repository.get(meeting_id, owner_id=user.id)
    if meeting is None:
        await websocket.close(code=4004, reason="Reuniao nao encontrada.")
        return

    await websocket.accept()

    session = LiveSession(meeting_id, settings)
    _ws_open = True

    async def _safe_send(data: dict) -> None:
        if not _ws_open:
            return
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    async def on_transcript(text: str, is_final: bool) -> None:
        await _safe_send({"type": "transcript", "text": text, "is_final": is_final})

    async def on_draft(markdown: str) -> None:
        await _safe_send({"type": "draft", "markdown": markdown})

    async def on_status(state) -> None:
        await _safe_send({"type": "status", "state": str(state)})

    async def on_error(message: str) -> None:
        await _safe_send({"type": "error", "message": message})

    session.on_transcript(on_transcript)
    session.on_draft(on_draft)
    session.on_status(on_status)
    session.on_error(on_error)

    try:
        await session.start()

        meeting.status = MeetingStatus.recording
        repository.save(meeting)

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")

            if msg_type == "audio":
                data = message.get("data", "")
                if data:
                    audio_bytes = base64.b64decode(data)
                    await session.send_audio(audio_bytes)

            elif msg_type == "pause":
                await session.pause()

            elif msg_type == "resume":
                await session.resume()

            elif msg_type == "stop":
                await session.stop()
                await _finalize_live_recording(session, meeting, settings, repository)
                break

    except WebSocketDisconnect:
        _ws_open = False
        if session.state not in (LiveSessionState.done, LiveSessionState.finalizing):
            await session.stop()
            await _finalize_live_recording(session, meeting, settings, repository)
    except LiveSessionError as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=4000, reason=str(exc))
        except Exception:
            pass
        _ws_open = False
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": f"Erro inesperado: {exc}"})
            await websocket.close(code=4000)
        except Exception:
            pass
        _ws_open = False


async def _finalize_live_recording(
    session: LiveSession,
    meeting: Meeting,
    settings: Settings,
    repository: MeetingRepository,
) -> None:
    media_service = MediaService(settings)
    chunks_dir = session.get_chunks_dir()

    loop = asyncio.get_event_loop()
    prepared_audio = await loop.run_in_executor(
        None, media_service.concatenate_live_chunks, meeting.id, chunks_dir
    )
    if prepared_audio is not None:
        meeting.prepared_audio = prepared_audio
        meeting.status = MeetingStatus.queued
        meeting.processing_steps = ["Gravacao ao vivo finalizada", "Processamento enfileirado"]
        repository.save(meeting)

        transcription_provider = build_transcription_provider(settings, media_service)
        minutes_provider = build_minutes_provider(settings)
        processor = MeetingProcessor(media_service, transcription_provider, minutes_provider)
        request = ProcessMeetingRequest()
        queue = get_processing_queue()
        queue.enqueue(
            meeting_id=meeting.id,
            run=lambda: run_processing_job(meeting.id, request, repository, processor),
        )
    else:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = "Nenhum audio foi gravado durante a sessao ao vivo."
        repository.save(meeting)
