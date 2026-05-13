import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.domain import MediaKind, PreparedAudioInfo, UploadedFileInfo


class MediaProcessingError(Exception):
    pass


class MediaValidationError(Exception):
    pass


class MediaService:
    audio_extensions = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"}
    video_extensions = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    content_types = {
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_upload_type(self, filename: str | None) -> tuple[str, MediaKind]:
        extension = Path(filename or "").suffix.lower()
        if extension in self.audio_extensions:
            return extension, MediaKind.audio
        if extension in self.video_extensions:
            return extension, MediaKind.video

        accepted = ", ".join(sorted(self.audio_extensions | self.video_extensions))
        raise MediaValidationError(f"Formato nao suportado. Envie um destes formatos: {accepted}.")

    def validate_upload_size(self, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise MediaValidationError("O arquivo enviado esta vazio.")
        if size_bytes > self.settings.max_upload_bytes:
            max_mb = self.settings.max_upload_bytes // (1024 * 1024)
            raise MediaValidationError(f"O arquivo excede o limite de {max_mb} MB.")

    def validate_upload(self, filename: str | None, size_bytes: int) -> tuple[str, MediaKind]:
        extension, media_kind = self.validate_upload_type(filename)
        self.validate_upload_size(size_bytes)
        return extension, media_kind

    def probe(self, source_path: Path) -> dict:
        ffprobe = self._require_binary(self.settings.ffprobe_binary, "FFprobe")
        command = [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(source_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode != 0:
            detail = result.stderr.strip() or "Nao foi possivel ler metadados da midia."
            raise MediaProcessingError(detail)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MediaProcessingError("FFprobe retornou metadados invalidos.") from exc

    def enrich_file_info(self, file_info: UploadedFileInfo, source_path: Path) -> UploadedFileInfo:
        probe = self.probe(source_path)
        duration = self._duration_from_probe(probe)
        if duration and duration > self.settings.max_media_duration_seconds:
            max_minutes = self.settings.max_media_duration_seconds // 60
            raise MediaProcessingError(f"A reuniao excede o limite de {max_minutes} minutos.")

        stream = self._first_stream(probe, file_info.media_kind)
        file_info.duration_seconds = duration
        file_info.codec_name = stream.get("codec_name") if stream else None
        return file_info

    def prepare_audio(self, meeting_id: str, file_info: UploadedFileInfo) -> PreparedAudioInfo:
        source_path = self.upload_path(meeting_id, file_info.stored_name)
        self.enrich_file_info(file_info, source_path)

        ffmpeg = self._require_binary(self.settings.ffmpeg_binary, "FFmpeg")
        prepared_dir = self.settings.storage_dir / "prepared" / meeting_id
        prepared_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{uuid4()}.mp3"
        target_path = prepared_dir / target_name

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "32k",
            str(target_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
        if result.returncode != 0:
            detail = result.stderr.strip() or "Nao foi possivel preparar o audio com FFmpeg."
            raise MediaProcessingError(detail)

        probe = self.probe(target_path)
        duration = self._duration_from_probe(probe)
        return PreparedAudioInfo(
            stored_name=target_name,
            content_type=self.content_type_for_path(target_path),
            size_bytes=target_path.stat().st_size,
            duration_seconds=duration,
        )

    def prepared_audio_path(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> Path:
        return self.settings.storage_dir / "prepared" / meeting_id / prepared_audio.stored_name

    def transcription_chunks(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> list[Path]:
        source_path = self.prepared_audio_path(meeting_id, prepared_audio)
        if source_path.stat().st_size <= self.settings.transcription_max_file_bytes:
            return [source_path]

        ffmpeg = self._require_binary(self.settings.ffmpeg_binary, "FFmpeg")
        chunks_dir = self.settings.storage_dir / "chunks" / meeting_id
        chunks_dir.mkdir(parents=True, exist_ok=True)
        for stale_chunk in chunks_dir.glob("chunk-*"):
            stale_chunk.unlink()

        extension = source_path.suffix or ".mp3"
        target_pattern = chunks_dir / f"chunk-%03d{extension}"
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(source_path),
            "-f",
            "segment",
            "-segment_time",
            str(self.settings.transcription_chunk_seconds),
            "-c",
            "copy",
            str(target_pattern),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
        if result.returncode != 0:
            detail = result.stderr.strip() or "Nao foi possivel segmentar o audio para transcricao."
            raise MediaProcessingError(detail)

        chunks = sorted(chunks_dir.glob("chunk-*.wav"))
        if not chunks:
            chunks = sorted(chunks_dir.glob(f"chunk-*{extension}"))
        if not chunks:
            raise MediaProcessingError("FFmpeg nao gerou trechos de audio para transcricao.")
        return chunks

    def upload_path(self, meeting_id: str, stored_name: str) -> Path:
        return self.settings.storage_dir / "uploads" / meeting_id / stored_name

    def delete_upload(self, meeting_id: str, file_info: UploadedFileInfo) -> None:
        source_path = self.upload_path(meeting_id, file_info.stored_name)
        source_path.unlink(missing_ok=True)

    def content_type_for_path(self, path: Path) -> str:
        return self.content_types.get(path.suffix.lower(), "application/octet-stream")

    def concatenate_live_chunks(self, meeting_id: str, chunks_dir: Path) -> PreparedAudioInfo | None:
        chunks = sorted(chunks_dir.glob("chunk-*.webm"))
        if not chunks:
            return None

        ffmpeg = self._require_binary(self.settings.ffmpeg_binary, "FFmpeg")
        prepared_dir = self.settings.storage_dir / "prepared" / meeting_id
        prepared_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{uuid4()}.mp3"
        target_path = prepared_dir / target_name

        concat_list = chunks_dir / "concat.txt"
        with concat_list.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                safe_path = str(chunk.resolve()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "32k",
            str(target_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
        concat_list.unlink(missing_ok=True)

        if result.returncode != 0:
            detail = result.stderr.strip() or "Nao foi possivel concatenar os chunks de audio ao vivo."
            raise MediaProcessingError(detail)

        probe = self.probe(target_path)
        duration = self._duration_from_probe(probe)
        return PreparedAudioInfo(
            stored_name=target_name,
            content_type=self.content_type_for_path(target_path),
            size_bytes=target_path.stat().st_size,
            duration_seconds=duration,
        )

    def tools_status(self) -> dict[str, bool]:
        return {
            "ffmpeg": self._resolve_binary(self.settings.ffmpeg_binary, "FFmpeg") is not None,
            "ffprobe": self._resolve_binary(self.settings.ffprobe_binary, "FFprobe") is not None,
        }

    def _require_binary(self, binary: str, label: str) -> str:
        resolved = self._resolve_binary(binary, label)
        if resolved:
            return resolved
        raise MediaProcessingError(
            f"{label} nao esta instalado ou nao foi encontrado no PATH. "
            f"Configure {label.upper()}_BINARY no .env ou instale a ferramenta."
        )

    def _resolve_binary(self, binary: str, label: str) -> str | None:
        if Path(binary).exists():
            return binary

        path_binary = shutil.which(binary)
        if path_binary:
            return path_binary

        if self.settings.local_media_tools_enabled:
            local_binary = self._local_tool_path(label)
            if local_binary.exists():
                return str(local_binary)
        return None

    def _local_tool_path(self, label: str) -> Path:
        project_root = Path(__file__).resolve().parents[2]
        if label == "FFmpeg":
            return (
                project_root
                / "tools"
                / "node_modules"
                / "@ffmpeg-installer"
                / "win32-x64"
                / "ffmpeg.exe"
            )
        return (
            project_root
            / "tools"
            / "node_modules"
            / "@ffprobe-installer"
            / "win32-x64"
            / "ffprobe.exe"
        )

    def _duration_from_probe(self, probe: dict) -> float | None:
        raw_duration = probe.get("format", {}).get("duration")
        if raw_duration is None:
            return None
        try:
            return float(raw_duration)
        except (TypeError, ValueError):
            return None

    def _first_stream(self, probe: dict, media_kind: MediaKind) -> dict | None:
        target_type = "audio" if media_kind == MediaKind.audio else "video"
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == target_type:
                return stream
        return None
