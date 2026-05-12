import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.domain import Meeting, MeetingCreate, MeetingStatus, UploadedFileInfo


class MeetingRepository(Protocol):
    def list(self) -> list[Meeting]: ...

    def get(self, meeting_id: str) -> Meeting | None: ...

    def create(self, payload: MeetingCreate) -> Meeting: ...

    def attach_file(self, meeting_id: str, file_info: UploadedFileInfo) -> Meeting: ...

    def save(self, meeting: Meeting) -> Meeting: ...


class JsonMeetingRepository:
    _lock = threading.RLock()

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "meetings.json"

    def list(self) -> list[Meeting]:
        with self._lock:
            data = self._read()
            return [Meeting.model_validate(item) for item in data]

    def get(self, meeting_id: str) -> Meeting | None:
        for meeting in self.list():
            if meeting.id == meeting_id:
                return meeting
        return None

    def create(self, payload: MeetingCreate) -> Meeting:
        with self._lock:
            meeting = Meeting(**payload.model_dump())
            meetings = self.list()
            meetings.append(meeting)
            self._write(meetings)
            return meeting

    def attach_file(self, meeting_id: str, file_info: UploadedFileInfo) -> Meeting:
        with self._lock:
            meeting = self._require(meeting_id)
            meeting.file = file_info
            meeting.status = MeetingStatus.uploaded
            return self.save(meeting)

    def save(self, meeting: Meeting) -> Meeting:
        with self._lock:
            meeting.updated_at = datetime.now(UTC)
            meetings = self.list()
            updated = False
            for index, current in enumerate(meetings):
                if current.id == meeting.id:
                    meetings[index] = meeting
                    updated = True
                    break
            if not updated:
                meetings.append(meeting)
            self._write(meetings)
            return meeting

    def _require(self, meeting_id: str) -> Meeting:
        meeting = self.get(meeting_id)
        if meeting is None:
            raise KeyError(meeting_id)
        return meeting

    def _read(self) -> list[dict]:
        if not self.db_path.exists():
            return []
        return json.loads(self.db_path.read_text(encoding="utf-8"))

    def _write(self, meetings: list[Meeting]) -> None:
        payload = [meeting.model_dump(mode="json") for meeting in meetings]
        self.db_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SQLiteMeetingRepository:
    _lock = threading.RLock()

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def list(self) -> list[Meeting]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM meetings ORDER BY created_at ASC"
            ).fetchall()
            return [Meeting.model_validate_json(row["payload"]) for row in rows]

    def get(self, meeting_id: str) -> Meeting | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM meetings WHERE id = ?",
                (meeting_id,),
            ).fetchone()
            if row is None:
                return None
            return Meeting.model_validate_json(row["payload"])

    def create(self, payload: MeetingCreate) -> Meeting:
        meeting = Meeting(**payload.model_dump())
        return self.save(meeting)

    def attach_file(self, meeting_id: str, file_info: UploadedFileInfo) -> Meeting:
        with self._lock:
            meeting = self._require(meeting_id)
            meeting.file = file_info
            meeting.status = MeetingStatus.uploaded
            return self.save(meeting)

    def save(self, meeting: Meeting) -> Meeting:
        with self._lock, self._connect() as connection:
            meeting.updated_at = datetime.now(UTC)
            connection.execute(
                """
                INSERT INTO meetings (
                    id, title, client_name, status, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    client_name = excluded.client_name,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    meeting.id,
                    meeting.title,
                    meeting.client_name,
                    meeting.status.value,
                    meeting.created_at.isoformat(),
                    meeting.updated_at.isoformat(),
                    meeting.model_dump_json(),
                ),
            )
            connection.commit()
            return meeting

    def _require(self, meeting_id: str) -> Meeting:
        meeting = self.get(meeting_id)
        if meeting is None:
            raise KeyError(meeting_id)
        return meeting

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    client_name TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_meetings_updated_at ON meetings(updated_at)"
            )
            connection.commit()
            self._bootstrap_from_json_if_empty(connection)

    def _bootstrap_from_json_if_empty(self, connection: sqlite3.Connection) -> None:
        existing_count = connection.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        legacy_json_path = self.database_path.parent / "meetings.json"
        if existing_count or not legacy_json_path.exists():
            return

        raw_meetings = json.loads(legacy_json_path.read_text(encoding="utf-8"))
        for raw_meeting in raw_meetings:
            meeting = Meeting.model_validate(raw_meeting)
            connection.execute(
                """
                INSERT INTO meetings (
                    id, title, client_name, status, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting.id,
                    meeting.title,
                    meeting.client_name,
                    meeting.status.value,
                    meeting.created_at.isoformat(),
                    meeting.updated_at.isoformat(),
                    meeting.model_dump_json(),
                ),
            )
        connection.commit()


def build_meeting_repository(settings: Settings) -> MeetingRepository:
    backend = settings.database_backend.lower().strip()
    if backend == "sqlite":
        return SQLiteMeetingRepository(settings.database_path)
    if backend == "json":
        return JsonMeetingRepository(settings.storage_dir)
    if backend == "postgres":
        raise RuntimeError(
            "PostgreSQL esta arquitetado como backend futuro, mas ainda nao esta ativo neste MVP. "
            "Use DATABASE_BACKEND=sqlite por enquanto."
        )
    raise RuntimeError(f"DATABASE_BACKEND desconhecido: {settings.database_backend}.")
