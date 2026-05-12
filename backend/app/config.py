from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gerador de Ata de Reuniao por IA"
    app_env: str = "development"
    frontend_origin: str = "http://127.0.0.1:5173"
    storage_dir: Path = Path("storage")
    database_backend: str = "sqlite"
    database_path: Path = Path("storage/ataai.sqlite3")
    database_url: str | None = None
    max_upload_bytes: int = 500 * 1024 * 1024
    max_media_duration_seconds: int = 3 * 60 * 60
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    local_media_tools_enabled: bool = True
    transcription_provider: str = "gemini"
    transcription_model: str = "gemini-2.5-flash"
    transcription_language: str = "pt"
    transcription_prompt: str = (
        "Transcreva em portugues do Brasil. Preserve termos tecnicos, nomes de pessoas, "
        "nomes de empresas, tarefas, prazos e decisoes mencionadas na reuniao."
    )
    transcription_max_file_bytes: int = 18 * 1024 * 1024
    transcription_chunk_seconds: int = 10 * 60
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    minutes_provider: str = "gemini"
    minutes_model: str = "gemini-2.5-flash"
    minutes_max_transcript_chars: int = 60000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
