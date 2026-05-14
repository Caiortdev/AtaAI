import json
import shutil
from pathlib import Path

from app.config import Settings


class LocalStorageService:
    _config_filename = "storage_config.json"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._config_path = settings.storage_dir / self._config_filename
        self._base = self._load_or_default(settings)

    def _load_or_default(self, settings: Settings) -> Path:
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                saved_path = data.get("path")
                if saved_path:
                    resolved = Path(saved_path)
                    if resolved.exists():
                        self._ensure_subdirs(resolved)
                        return resolved
            except (json.JSONDecodeError, OSError):
                pass

        if settings.local_export_dir:
            base = Path(settings.local_export_dir)
        else:
            base = Path.home() / "Documents" / "AtaAI"
        self._ensure_subdirs(base)
        return base

    def _ensure_subdirs(self, base: Path) -> None:
        base.mkdir(parents=True, exist_ok=True)
        (base / "recordings").mkdir(exist_ok=True)
        (base / "atas").mkdir(exist_ok=True)

    def _persist_config(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps({"path": str(self._base)}, ensure_ascii=False),
            encoding="utf-8",
        )

    @property
    def base_dir(self) -> Path:
        return self._base

    def save_recording(self, meeting, source_path: Path) -> Path:
        safe_title = self._safe_filename(meeting.title)
        short_id = meeting.id[:8]
        suffix = source_path.suffix or ".webm"
        dest = self._base / "recordings" / f"{safe_title}_{short_id}{suffix}"
        shutil.copy2(source_path, dest)
        return dest

    def save_ata_pdf(self, meeting, pdf_bytes: bytes) -> Path:
        safe_title = self._safe_filename(meeting.title)
        short_id = meeting.id[:8]
        dest = self._base / "atas" / f"{safe_title}_{short_id}.pdf"
        dest.write_bytes(pdf_bytes)
        return dest

    def get_config(self) -> dict:
        return {
            "enabled": self.settings.local_export_enabled,
            "path": str(self._base),
        }

    def update_path(self, new_path: str) -> dict:
        resolved = Path(new_path)
        self._ensure_subdirs(resolved)
        self._base = resolved
        self._persist_config()
        return {
            "enabled": self.settings.local_export_enabled,
            "path": str(self._base),
        }

    def _safe_filename(self, name: str) -> str:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
        return safe.strip()[:60] or "reuniao"
