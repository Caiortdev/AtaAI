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
    settings = Settings(
        storage_dir=tmp_path,
        ffmpeg_binary="missing-ffmpeg-for-test",
        ffprobe_binary="missing-ffprobe-for-test",
        local_media_tools_enabled=False,
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
    assert response.json()["transcription"]["provider"] == "openai"
    assert response.json()["minutes"]["provider"] == "openai"


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


def test_processing_fails_without_openai_key_after_audio_preparation(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="openai", openai_api_key=None)
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
    assert "OPENAI_API_KEY" in payload["processing_error"]


def test_minutes_generation_fails_without_openai_key_after_mock_transcription(tmp_path):
    from app.main import get_media_service

    client = make_client(tmp_path, transcription_provider="mock", minutes_provider="openai")
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
    assert "gerar ata e tarefas" in payload["processing_error"]


def teardown_function():
    app.dependency_overrides.clear()
