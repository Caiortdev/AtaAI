from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.domain import PreparedAudioInfo
from app.media import MediaService


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


def make_client(tmp_path, **settings_overrides):
    gemini_api_key = settings_overrides.pop("gemini_api_key", None)
    openai_api_key = settings_overrides.pop("openai_api_key", None)
    settings = Settings(
        storage_dir=tmp_path,
        ffmpeg_binary="missing-ffmpeg-for-test",
        ffprobe_binary="missing-ffprobe-for-test",
        local_media_tools_enabled=False,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        **settings_overrides,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_health(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["media_tools"] == {"ffmpeg": False, "ffprobe": False}
    assert response.json()["transcription"]["provider"] == "gemini"
    assert response.json()["minutes"]["provider"] == "gemini"


def test_rejects_unsupported_upload(tmp_path):
    client = make_client(tmp_path)
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("documento.txt", b"conteudo", "text/plain")},
    )

    assert response.status_code == 400
    assert "Formato nao suportado" in response.json()["detail"]


def test_processing_fails_clearly_without_media_tools(tmp_path):
    client = make_client(tmp_path)
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "FFprobe" in payload["processing_error"]


def test_processing_completes_with_mock_transcription_and_minutes(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["analysis"]["transcript_provider"] == "mock"
    assert payload["analysis"]["minutes_provider"] == "mock"
    assert payload["analysis"]["transcript"]


def test_updates_generated_analysis_for_human_review(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="mock")
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    processed = client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    ).json()

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

    response = client.patch(f"/api/meetings/{meeting['id']}/analysis", json=payload)

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
    meeting = client.post(
        "/api/meetings",
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
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    response = client.get(f"/api/meetings/{meeting['id']}/analysis.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="ata-reuniao-pdf.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in response.content


def test_cannot_export_pdf_before_analysis_exists(tmp_path):
    client = make_client(tmp_path)
    meeting = client.post(
        "/api/meetings",
        json={
            "title": "Reuniao sem PDF",
            "client_name": "Cliente",
            "participants": [],
            "notes": None,
            "consent_confirmed": True,
        },
    ).json()

    response = client.get(f"/api/meetings/{meeting['id']}/analysis.pdf")

    assert response.status_code == 400
    assert "Gere uma ata" in response.json()["detail"]


def test_processing_fails_without_gemini_key_after_audio_preparation(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="gemini", gemini_api_key=None)
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "GEMINI_API_KEY" in payload["processing_error"]


def test_minutes_generation_fails_without_gemini_key_after_mock_transcription(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="gemini")
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService(
        get_settings()
    )
    meeting = client.post(
        "/api/meetings",
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
        files={"file": ("audio.mp3", b"audio simulado", "audio/mpeg")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/meetings/{meeting['id']}/process",
        json={"mode": "audio_only", "preset": "ata_objetiva_com_tarefas"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "GEMINI_API_KEY" in payload["processing_error"]


def teardown_function():
    app.dependency_overrides.clear()
