import json

from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, Settings, get_settings
from app.domain import MeetingCreate, PreparedAudioInfo
from app.main import app, get_processing_queue, initialize_database
from app.media import MediaService
from app.repository import JsonMeetingRepository, SQLiteMeetingRepository, build_meeting_repository
from app.transcription import GeminiTranscriptionProvider, parse_transcription_output


class FakeMediaService(MediaService):
    def tools_status(self) -> dict[str, bool]:
        return {"ffmpeg": True, "ffprobe": True}

    def prepare_audio(self, meeting_id, file_info):
        prepared_dir = self.settings.storage_dir / "prepared" / meeting_id
        prepared_dir.mkdir(parents=True, exist_ok=True)
        prepared_path = prepared_dir / "prepared.wav"
        prepared_path.write_bytes(b"fake wav")
        file_info.duration_seconds = 1.0
        file_info.codec_name = "mp3"
        return PreparedAudioInfo(
            stored_name="prepared.wav",
            size_bytes=prepared_path.stat().st_size,
            duration_seconds=1.0,
        )

    def transcription_chunks(self, meeting_id, prepared_audio):
        return [self.prepared_audio_path(meeting_id, prepared_audio)]


class ImmediateProcessingQueue:
    def enqueue(self, meeting_id, run):
        run()


class HoldingProcessingQueue:
    def __init__(self):
        self.jobs = []

    def enqueue(self, meeting_id, run):
        self.jobs.append((meeting_id, run))

    def run_next(self):
        meeting_id, run = self.jobs.pop(0)
        run()
        return meeting_id


def make_client(tmp_path, **settings_overrides):
    gemini_api_key = settings_overrides.pop("gemini_api_key", None)
    openai_api_key = settings_overrides.pop("openai_api_key", None)
    settings = Settings(
        storage_dir=tmp_path,
        ffmpeg_binary="missing-ffmpeg-for-test",
        ffprobe_binary="missing-ffprobe-for-test",
        local_media_tools_enabled=False,
        database_backend="sqlite",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        **settings_overrides,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def auth_headers(client, email="caio@example.com"):
    response = client.post(
        "/api/auth/register",
        json={"name": "Caio Torres", "email": email, "password": "senha-segura-123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def use_immediate_processing_queue():
    queue = ImmediateProcessingQueue()
    app.dependency_overrides[get_processing_queue] = lambda: queue
    return queue


def test_health(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"]["backend"] == "sqlite"
    assert response.json()["database"]["configured"] is True
    assert response.json()["media_tools"] == {"ffmpeg": False, "ffprobe": False}
    assert response.json()["transcription"]["provider"] == "gemini"
    assert response.json()["minutes"]["provider"] == "gemini"


def test_uses_sqlite_repository_by_default(tmp_path):
    settings = Settings(
        storage_dir=tmp_path,
        database_backend="sqlite",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=None,
        openai_api_key=None,
    )

    repository = build_meeting_repository(settings)

    assert isinstance(repository, SQLiteMeetingRepository)


def test_default_runtime_paths_are_backend_relative():
    settings = Settings(gemini_api_key=None, openai_api_key=None)

    assert settings.storage_dir == BACKEND_DIR / "storage"
    assert settings.database_path == BACKEND_DIR / "storage" / "ataai.sqlite3"
    assert settings.max_upload_bytes == 5 * 1024 * 1024 * 1024


def test_json_repository_remains_available_as_fallback(tmp_path):
    settings = Settings(
        storage_dir=tmp_path,
        database_backend="json",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=None,
        openai_api_key=None,
    )

    repository = build_meeting_repository(settings)

    assert isinstance(repository, JsonMeetingRepository)


def test_sqlite_repository_imports_legacy_json_when_empty(tmp_path):
    legacy_repository = JsonMeetingRepository(tmp_path)
    created = legacy_repository.create(
        MeetingCreate(
            title="Reuniao legado",
            client_name="Cliente",
            participants=[],
            notes=None,
            consent_confirmed=True,
        )
    )

    repository = SQLiteMeetingRepository(tmp_path / "ataai.sqlite3")

    imported = repository.get(created.id)
    assert imported is not None
    assert imported.title == "Reuniao legado"


def test_database_initialization_creates_all_sqlite_tables(tmp_path):
    settings = Settings(
        storage_dir=tmp_path,
        database_backend="sqlite",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=None,
        openai_api_key=None,
    )

    initialize_database(settings)

    import sqlite3

    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"users", "sessions", "meetings", "meeting_presets"}.issubset(tables)


def test_tauri_origin_is_allowed_for_auth_requests(tmp_path):
    client = make_client(tmp_path)

    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_postgres_backend_is_reserved_until_driver_is_added(tmp_path):
    settings = Settings(
        storage_dir=tmp_path,
        database_backend="postgres",
        database_url="postgresql://ataai:senha@localhost:5432/ataai",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=None,
        openai_api_key=None,
    )

    try:
        build_meeting_repository(settings)
    except RuntimeError as exc:
        assert "PostgreSQL" in str(exc)
    else:
        raise AssertionError("PostgreSQL backend should be explicit about not being active yet.")


def test_registers_and_authenticates_user(tmp_path):
    client = make_client(tmp_path)

    register = client.post(
        "/api/auth/register",
        json={"name": "Caio Torres", "email": "caio@example.com", "password": "senha-segura-123"},
    )

    assert register.status_code == 201
    payload = register.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == "caio@example.com"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {payload['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "caio@example.com"


def test_rejects_meetings_without_login(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/meetings")

    assert response.status_code == 401
    assert "login" in response.json()["detail"]


def test_meetings_are_isolated_by_user(tmp_path):
    client = make_client(tmp_path)
    caio_headers = auth_headers(client, "caio@example.com")
    maria_headers = auth_headers(client, "maria@example.com")

    created = client.post(
        "/api/meetings",
        headers=caio_headers,
        json={
            "title": "Reuniao privada",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    )

    assert created.status_code == 201
    assert created.json()["owner_id"]
    assert client.get("/api/meetings", headers=maria_headers).json()["items"] == []
    assert client.get(f"/api/meetings/{created.json()['id']}", headers=maria_headers).status_code == 404


def test_lists_default_preset_for_authenticated_user(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)

    response = client.get("/api/presets", headers=headers)

    assert response.status_code == 200
    presets = response.json()["items"]
    assert len(presets) == 1
    assert presets[0]["is_default"] is True
    assert presets[0]["name"] == "Ata operacional com solicitações de mudança"
    assert "Tarefas levantadas" in presets[0]["instructions"]


def test_existing_default_preset_is_upgraded_to_operational_minutes(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)
    old_default = client.get("/api/presets", headers=headers).json()["items"][0]

    import sqlite3

    with sqlite3.connect(tmp_path / "ataai.sqlite3") as connection:
        payload = {
            **old_default,
            "name": "Ata objetiva com tarefas",
            "description": "Modelo antigo.",
            "instructions": "Gere uma ata objetiva em portugues do Brasil.",
        }
        connection.execute(
            """
            UPDATE meeting_presets
            SET name = ?, payload = ?
            WHERE id = ?
            """,
            ("Ata objetiva com tarefas", json.dumps(payload), old_default["id"]),
        )
        connection.commit()

    upgraded = client.get("/api/presets", headers=headers).json()["items"][0]

    assert upgraded["name"] == "Ata operacional com solicitações de mudança"
    assert "Critérios de aceite" in upgraded["instructions"]


def test_custom_presets_are_isolated_by_user(tmp_path):
    client = make_client(tmp_path)
    caio_headers = auth_headers(client, "caio@example.com")
    maria_headers = auth_headers(client, "maria@example.com")

    created = client.post(
        "/api/presets",
        headers=caio_headers,
        json={
            "name": "Ata comercial",
            "description": "Modelo para reunioes de vendas.",
            "instructions": "Foque em dores do cliente, oportunidades, proximos passos e objecoes.",
        },
    )

    assert created.status_code == 201
    assert len(client.get("/api/presets", headers=caio_headers).json()["items"]) == 2
    maria_presets = client.get("/api/presets", headers=maria_headers).json()["items"]
    assert len(maria_presets) == 1
    assert maria_presets[0]["is_default"] is True
    assert client.patch(
        f"/api/presets/{created.json()['id']}",
        headers=maria_headers,
        json={
            "name": "Tentativa externa",
            "description": None,
            "instructions": "Esta alteracao nao deve ser permitida por outro usuario.",
        },
    ).status_code == 404


def test_processing_uses_custom_preset(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    preset = client.post(
        "/api/presets",
        headers=headers,
        json={
            "name": "Ata executiva",
            "description": "Modelo para diretoria.",
            "instructions": (
                "Gere um resumo executivo curto, destaque decisoes estrategicas e liste riscos "
                "com impacto financeiro."
            ),
        },
    ).json()
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Comite executivo",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset_id": preset["id"]},
    )

    assert response.status_code == 200
    processed = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert processed["preset"] == "Ata executiva"
    assert processed["preset_id"] == preset["id"]
    assert "resumo executivo curto" in processed["preset_instructions"]
    assert "Tarefas levantadas" in processed["analysis"]["minutes_markdown"]


def test_rejects_unsupported_upload(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()

    response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("documento.txt", b"conteudo", "text/plain")},
    )

    assert response.status_code == 400
    assert "Formato nao suportado" in response.json()["detail"]


def test_upload_prepares_audio_and_removes_original_when_tools_are_available(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path)
    headers = auth_headers(client)
    media_settings = Settings(
        storage_dir=tmp_path,
        database_backend="sqlite",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key=None,
        openai_api_key=None,
    )
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(media_settings)
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao com video grande",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()

    response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("gravacao.mp4", b"video simulado", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prepared_audio"]["stored_name"] == "prepared.wav"
    assert "Audio comprimido preparado no upload" in payload["processing_steps"]
    assert any(
        "Arquivo original removido" in warning
        for warning in payload["file"]["validation_warnings"]
    )
    original_path = tmp_path / "uploads" / meeting["id"] / payload["file"]["stored_name"]
    assert not original_path.exists()


def test_processing_fails_clearly_without_media_tools(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)
    use_immediate_processing_queue()
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    upload_response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert payload["status"] == "failed"
    assert "FFprobe" in payload["processing_error"]


def test_processing_completes_with_mock_transcription_and_minutes(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    upload_response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    payload = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert payload["status"] == "completed"
    assert payload["analysis"]["transcript_provider"] == "mock"
    assert payload["analysis"]["minutes_provider"] == "mock"
    assert payload["analysis"]["transcript"]
    assert "Processamento enfileirado" in payload["processing_steps"]


def test_processing_returns_queued_before_background_job_runs(tmp_path):
    from app.main import get_media_service

    queue = HoldingProcessingQueue()
    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    app.dependency_overrides[get_processing_queue] = lambda: queue
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["processing_steps"] == ["Arquivo recebido", "Processamento enfileirado"]
    assert len(queue.jobs) == 1

    queue.run_next()
    processed = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert processed["status"] == "completed"
    assert processed["analysis"]["minutes_provider"] == "mock"


def test_rejects_duplicate_processing_while_queued(tmp_path):
    from app.main import get_media_service

    queue = HoldingProcessingQueue()
    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    app.dependency_overrides[get_processing_queue] = lambda: queue
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 409
    assert "ja esta na fila" in response.json()["detail"]


def test_updates_generated_analysis_for_human_review(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    processed = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )
    assert processed.status_code == 200
    processed = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()

    analysis = processed["analysis"]
    first_task = analysis["tasks"][0]
    first_task["title"] = "Tarefa revisada pelo usuario"
    first_task["priority"] = "high"
    first_task["status"] = "approved"
    payload = {
        "executive_summary": "Resumo revisado pelo usuario.",
        "topics": ["Topico revisado"],
        "decisions": ["Decisao revisada"],
        "tasks": [first_task],
        "risks": ["Risco revisado"],
        "open_questions": ["Pergunta revisada"],
        "minutes_markdown": "# Ata revisada\n\nConteudo revisado.",
    }

    response = client.patch(f"/api/meetings/{meeting['id']}/analysis", headers=headers, json=payload)

    assert response.status_code == 200
    updated = response.json()
    assert updated["analysis"]["executive_summary"] == "Resumo revisado pelo usuario."
    assert updated["analysis"]["minutes_markdown"].startswith("# Ata revisada")
    assert updated["analysis"]["tasks"][0]["title"] == "Tarefa revisada pelo usuario"
    assert updated["analysis"]["tasks"][0]["priority"] == "high"
    assert updated["analysis"]["tasks"][0]["status"] == "approved"
    assert updated["analysis"]["transcript"] == analysis["transcript"]


def test_cannot_update_analysis_before_generation(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao sem ata",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()

    response = client.patch(
        f"/api/meetings/{meeting['id']}/analysis",
        headers=headers,
        json={
            "executive_summary": "Resumo",
            "topics": [],
            "decisions": [],
            "tasks": [],
            "risks": [],
            "open_questions": [],
            "minutes_markdown": "# Ata",
        },
    )

    assert response.status_code == 400
    assert "Gere uma ata" in response.json()["detail"]


def test_exports_generated_analysis_as_pdf(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao PDF",
            "client_name": "Cliente",
            "participants": ["Caio", "Cliente"],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    response = client.get(f"/api/meetings/{meeting['id']}/analysis.pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="ata-reuniao-pdf.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in response.content


def test_cannot_export_pdf_before_analysis_exists(tmp_path):
    client = make_client(tmp_path)
    headers = auth_headers(client)
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao sem PDF",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()

    response = client.get(f"/api/meetings/{meeting['id']}/analysis.pdf", headers=headers)

    assert response.status_code == 400
    assert "Gere uma ata" in response.json()["detail"]


def test_processing_fails_without_gemini_key_after_audio_preparation(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="gemini", gemini_api_key=None)
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    upload_response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert payload["status"] == "failed"
    assert "GEMINI_API_KEY" in payload["processing_error"]


def test_gemini_transcription_falls_back_after_transient_model_error(tmp_path, monkeypatch):
    settings = Settings(
        storage_dir=tmp_path,
        database_backend="sqlite",
        database_path=tmp_path / "ataai.sqlite3",
        gemini_api_key="test-key",
        transcription_model="gemini-2.5-flash",
        transcription_fallback_models="gemini-2.5-flash-lite,gemini-2.0-flash",
        transcription_retry_attempts=1,
        transcription_retry_delay_seconds=0,
        openai_api_key=None,
    )
    audio_dir = tmp_path / "prepared" / "meeting-1"
    audio_dir.mkdir(parents=True)
    (audio_dir / "prepared.mp3").write_bytes(b"audio")
    provider = GeminiTranscriptionProvider(settings, MediaService(settings))
    attempted_urls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

    def fake_post(url, **kwargs):
        attempted_urls.append(url)
        if "gemini-2.5-flash:" in url:
            return FakeResponse(
                503,
                {"error": {"message": "This model is currently experiencing high demand."}},
            )
        return FakeResponse(
            200,
            {"candidates": [{"content": {"parts": [{"text": "{\"text\":\"ok\"}"}]}}]},
        )

    monkeypatch.setattr("app.transcription.httpx.post", fake_post)

    result = provider.transcribe(
        "meeting-1",
        PreparedAudioInfo(stored_name="prepared.mp3", content_type="audio/mpeg", size_bytes=5),
    )

    assert result.text == "ok"
    assert result.model == "gemini-2.5-flash-lite"
    assert any("gemini-2.5-flash:" in url for url in attempted_urls)
    assert any("gemini-2.5-flash-lite:" in url for url in attempted_urls)


def test_gemini_transcription_accepts_plain_text_output():
    output = "Cliente pediu correcao do fluxo de documentos e retorno com prazo."

    assert parse_transcription_output(output) == output


def test_gemini_transcription_extracts_json_embedded_in_text():
    output = 'Resultado:\n{"text": "Transcricao extraida com sucesso."}\nFim.'

    assert parse_transcription_output(output) == "Transcricao extraida com sucesso."


def test_minutes_generation_fails_without_gemini_key_after_mock_transcription(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="gemini")
    headers = auth_headers(client)
    use_immediate_processing_queue()
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
        headers=headers,
        json={
            "title": "Reuniao teste",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()
    upload_response = client.post(
        f"/api/meetings/{meeting['id']}/upload",
        headers=headers,
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        headers=headers,
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = client.get(f"/api/meetings/{meeting['id']}", headers=headers).json()
    assert payload["status"] == "failed"
    assert "GEMINI_API_KEY" in payload["processing_error"]


def teardown_function():
    app.dependency_overrides.clear()
