from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]

APP_NAME = "Gerador de Ata de Reuniao por IA"
AUTH_SESSION_DAYS = 30
MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
MAX_MEDIA_DURATION_SECONDS = 3 * 60 * 60  # 3 hours
TRANSCRIPTION_MODEL = "gemini-2.5-flash"
TRANSCRIPTION_FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-2.0-flash"]
TRANSCRIPTION_RETRY_ATTEMPTS = 2
TRANSCRIPTION_RETRY_DELAY_SECONDS = 1.0
TRANSCRIPTION_LANGUAGE = "pt"
TRANSCRIPTION_PROMPT = (
    "Transcreva em portugues do Brasil. Preserve termos tecnicos, nomes de pessoas, "
    "nomes de empresas, tarefas, prazos e decisoes mencionadas na reuniao. "
    "Se o audio nao contiver fala humana audivel (silencio, ruido, musica sem voz), "
    "retorne o campo text como string vazia. Nao invente conteudo."
)
TRANSCRIPTION_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
TRANSCRIPTION_CHUNK_SECONDS = 10 * 60  # 10 minutes
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
OPENAI_BASE_URL = "https://api.openai.com/v1"
MINUTES_MODEL = "gemini-2.5-flash"
MINUTES_MAX_TRANSCRIPT_CHARS = 60000
LIVE_TRANSCRIPTION_ENABLED = True
LIVE_DRAFT_INTERVAL_SECONDS = 30
GEMINI_LIVE_MODEL = "gemini-2.5-flash"
LOCAL_EXPORT_ENABLED = True


def resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_origin: str = "http://127.0.0.1:5173"
    storage_dir: Path = Path("storage")
    database_backend: str = "sqlite"
    database_path: Path = Path("storage/ataai.sqlite3")
    database_url: str | None = None
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    transcription_provider: str = "gemini"
    minutes_provider: str = "gemini"
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    encryption_key: str = ""
    local_export_dir: str = ""

    @model_validator(mode="after")
    def resolve_runtime_paths(self) -> "Settings":
        self.storage_dir = resolve_backend_path(self.storage_dir)
        self.database_path = resolve_backend_path(self.database_path)
        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.encryption_key:
        from app.crypto import generate_encryption_key

        settings.encryption_key = generate_encryption_key()
        _persist_encryption_key(settings.encryption_key)
    else:
        _validate_encryption_key(settings.encryption_key)
    return settings


def _validate_encryption_key(key: str) -> None:
    from cryptography.fernet import Fernet, InvalidToken

    try:
        fernet = Fernet(key.encode())
        fernet.decrypt(fernet.encrypt(b"test"))
    except (InvalidToken, ValueError, Exception) as exc:
        raise RuntimeError(
            "ENCRYPTION_KEY no .env e invalida ou esta corrompida. "
            "As API keys dos usuarios nao poderao ser descriptografadas. "
            f"Erro: {exc}"
        ) from exc


def _persist_encryption_key(key: str) -> None:
    env_path = BACKEND_DIR / ".env"
    line = f"\nENCRYPTION_KEY={key}\n"
    try:
        with env_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as exc:
        raise RuntimeError(
            f"Nao foi possivel salvar ENCRYPTION_KEY no arquivo {env_path}. "
            "Sem essa chave persistida, as API keys dos usuarios serao perdidas "
            f"na proxima reinicializacao. Erro: {exc}"
        ) from exc
