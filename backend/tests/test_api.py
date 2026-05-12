from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.domain import MeetingCreate, PreparedAudioInfo
from app.main import app, get_processing_queue
from app.media import MediaService
from app.repository import JsonMeetingRepository, SQLiteMeetingRepository, build_meeting_repository


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
    assert presets[0]["name"] == "Ata objetiva com tarefas"


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
    assert "- Preset: Ata executiva" in processed["analysis"]["minutes_markdown"]


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
