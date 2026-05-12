import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.auth import (
    create_access_token,
    hash_password,
    hash_token,
    normalize_email,
    session_expiration,
    verify_password,
)
from app.config import Settings
from app.domain import (
    Meeting,
    MeetingCreate,
    MeetingPreset,
    MeetingPresetCreate,
    MeetingPresetUpdate,
    MeetingStatus,
    UploadedFileInfo,
    UserPublic,
    UserRegister,
)


class MeetingRepository(Protocol):
    def list(self, owner_id: str | None = None) -> list[Meeting]: ...

    def get(self, meeting_id: str, owner_id: str | None = None) -> Meeting | None: ...

    def create(self, payload: MeetingCreate, owner_id: str | None = None) -> Meeting: ...

    def attach_file(
        self,
        meeting_id: str,
        file_info: UploadedFileInfo,
        owner_id: str | None = None,
    ) -> Meeting: ...

    def save(self, meeting: Meeting) -> Meeting: ...


class AuthRepository(Protocol):
    def create_user(self, payload: UserRegister) -> UserPublic: ...

    def verify_credentials(self, email: str, password: str) -> UserPublic | None: ...

    def create_session(self, user_id: str, days: int) -> str: ...

    def get_user_by_token(self, token: str) -> UserPublic | None: ...

    def revoke_session(self, token: str) -> None: ...


class PresetRepository(Protocol):
    def list(self, owner_id: str) -> list[MeetingPreset]: ...

    def get(self, preset_id: str, owner_id: str) -> MeetingPreset | None: ...

    def create(self, payload: MeetingPresetCreate, owner_id: str) -> MeetingPreset: ...

    def update(
        self,
        preset_id: str,
        payload: MeetingPresetUpdate,
        owner_id: str,
    ) -> MeetingPreset | None: ...

    def delete(self, preset_id: str, owner_id: str) -> bool: ...

    def ensure_default(self, owner_id: str) -> MeetingPreset: ...


class JsonMeetingRepository:
    _lock = threading.RLock()

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "meetings.json"

    def list(self, owner_id: str | None = None) -> list[Meeting]:
        with self._lock:
            data = self._read()
            meetings = [Meeting.model_validate(item) for item in data]
            if owner_id is None:
                return meetings
            return [meeting for meeting in meetings if meeting.owner_id == owner_id]

    def get(self, meeting_id: str, owner_id: str | None = None) -> Meeting | None:
        for meeting in self.list(owner_id):
            if meeting.id == meeting_id:
                return meeting
        return None

    def create(self, payload: MeetingCreate, owner_id: str | None = None) -> Meeting:
        with self._lock:
            meeting = Meeting(**payload.model_dump(), owner_id=owner_id)
            meetings = self.list()
            meetings.append(meeting)
            self._write(meetings)
            return meeting

    def attach_file(
        self,
        meeting_id: str,
        file_info: UploadedFileInfo,
        owner_id: str | None = None,
    ) -> Meeting:
        with self._lock:
            meeting = self._require(meeting_id, owner_id)
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

    def _require(self, meeting_id: str, owner_id: str | None = None) -> Meeting:
        meeting = self.get(meeting_id, owner_id)
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

    def list(self, owner_id: str | None = None) -> list[Meeting]:
        with self._lock, self._connect() as connection:
            if owner_id is None:
                rows = connection.execute(
                    "SELECT payload FROM meetings ORDER BY created_at ASC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM meetings WHERE owner_id = ? ORDER BY created_at ASC",
                    (owner_id,),
                ).fetchall()
            return [Meeting.model_validate_json(row["payload"]) for row in rows]

    def get(self, meeting_id: str, owner_id: str | None = None) -> Meeting | None:
        with self._lock, self._connect() as connection:
            query = "SELECT payload FROM meetings WHERE id = ?"
            params: tuple[str, ...] = (meeting_id,)
            if owner_id is not None:
                query += " AND owner_id = ?"
                params = (meeting_id, owner_id)
            row = connection.execute(
                query,
                params,
            ).fetchone()
            if row is None:
                return None
            return Meeting.model_validate_json(row["payload"])

    def create(self, payload: MeetingCreate, owner_id: str | None = None) -> Meeting:
        meeting = Meeting(**payload.model_dump(), owner_id=owner_id)
        return self.save(meeting)

    def attach_file(
        self,
        meeting_id: str,
        file_info: UploadedFileInfo,
        owner_id: str | None = None,
    ) -> Meeting:
        with self._lock:
            meeting = self._require(meeting_id, owner_id)
            meeting.file = file_info
            meeting.status = MeetingStatus.uploaded
            return self.save(meeting)

    def save(self, meeting: Meeting) -> Meeting:
        with self._lock, self._connect() as connection:
            meeting.updated_at = datetime.now(UTC)
            connection.execute(
                """
                INSERT INTO meetings (
                    id, owner_id, title, client_name, status, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    title = excluded.title,
                    client_name = excluded.client_name,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    meeting.id,
                    meeting.owner_id,
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

    def _require(self, meeting_id: str, owner_id: str | None = None) -> Meeting:
        meeting = self.get(meeting_id, owner_id)
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
                    owner_id TEXT,
                    title TEXT NOT NULL,
                    client_name TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            self._ensure_column(connection, "meetings", "owner_id", "TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_meetings_owner_id ON meetings(owner_id)"
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
                    id, owner_id, title, client_name, status, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting.id,
                    meeting.owner_id,
                    meeting.title,
                    meeting.client_name,
                    meeting.status.value,
                    meeting.created_at.isoformat(),
                    meeting.updated_at.isoformat(),
                    meeting.model_dump_json(),
                ),
            )
        connection.commit()

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if column_name in {column["name"] for column in columns}:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


class SQLiteAuthRepository:
    _lock = threading.RLock()

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def create_user(self, payload: UserRegister) -> UserPublic:
        now = datetime.now(UTC)
        user_id = self._new_id()
        email = normalize_email(payload.email)
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO users (id, name, email, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        payload.name.strip(),
                        email,
                        hash_password(payload.password),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("Este e-mail ja esta cadastrado.") from exc
            return UserPublic(id=user_id, name=payload.name.strip(), email=email, created_at=now)

    def verify_credentials(self, email: str, password: str) -> UserPublic | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (normalize_email(email),),
            ).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                return None
            return self._user_from_row(row)

    def create_session(self, user_id: str, days: int) -> str:
        token = create_access_token()
        now = datetime.now(UTC)
        expires_at = session_expiration(days)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self._new_id(),
                    user_id,
                    hash_token(token),
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            connection.commit()
        return token

    def get_user_by_token(self, token: str) -> UserPublic | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.* FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (hash_token(token), datetime.now(UTC).isoformat()),
            ).fetchone()
            if row is None:
                return None
            return self._user_from_row(row)

    def revoke_session(self, token: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
            )
            connection.commit()

    def _user_from_row(self, row: sqlite3.Row) -> UserPublic:
        return UserPublic(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _new_id(self) -> str:
        from uuid import uuid4

        return str(uuid4())


class SQLitePresetRepository:
    _lock = threading.RLock()

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def list(self, owner_id: str) -> list[MeetingPreset]:
        self.ensure_default(owner_id)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM meeting_presets
                WHERE owner_id = ?
                ORDER BY is_default DESC, updated_at DESC
                """,
                (owner_id,),
            ).fetchall()
            return [MeetingPreset.model_validate_json(row["payload"]) for row in rows]

    def get(self, preset_id: str, owner_id: str) -> MeetingPreset | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM meeting_presets WHERE id = ? AND owner_id = ?",
                (preset_id, owner_id),
            ).fetchone()
            if row is None:
                return None
            return MeetingPreset.model_validate_json(row["payload"])

    def create(self, payload: MeetingPresetCreate, owner_id: str) -> MeetingPreset:
        preset = MeetingPreset(**payload.model_dump(), owner_id=owner_id)
        return self._save(preset)

    def update(
        self,
        preset_id: str,
        payload: MeetingPresetUpdate,
        owner_id: str,
    ) -> MeetingPreset | None:
        preset = self.get(preset_id, owner_id)
        if preset is None or preset.is_default:
            return None
        preset.name = payload.name
        preset.description = payload.description
        preset.instructions = payload.instructions
        return self._save(preset)

    def delete(self, preset_id: str, owner_id: str) -> bool:
        preset = self.get(preset_id, owner_id)
        if preset is None or preset.is_default:
            return False
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM meeting_presets WHERE id = ? AND owner_id = ?",
                (preset_id, owner_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def ensure_default(self, owner_id: str) -> MeetingPreset:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM meeting_presets WHERE owner_id = ? AND is_default = 1",
                (owner_id,),
            ).fetchone()
            if row is not None:
                return MeetingPreset.model_validate_json(row["payload"])

        default = MeetingPreset(
            owner_id=owner_id,
            name="Ata objetiva com tarefas",
            description="Modelo padrao para reunioes com clientes e demandas acionaveis.",
            instructions=(
                "Gere uma ata objetiva em portugues do Brasil. Separe resumo executivo, "
                "topicos discutidos, decisoes, riscos, duvidas abertas e tarefas. Para cada "
                "tarefa, defina prioridade de acordo com urgencia, impacto no cliente, bloqueio "
                "operacional e prazo citado na reuniao. Nao invente responsaveis ou prazos."
            ),
            is_default=True,
        )
        return self._save(default)

    def _save(self, preset: MeetingPreset) -> MeetingPreset:
        with self._lock, self._connect() as connection:
            preset.updated_at = datetime.now(UTC)
            connection.execute(
                """
                INSERT INTO meeting_presets (
                    id, owner_id, name, is_default, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    preset.id,
                    preset.owner_id,
                    preset.name,
                    int(preset.is_default),
                    preset.created_at.isoformat(),
                    preset.updated_at.isoformat(),
                    preset.model_dump_json(),
                ),
            )
            connection.commit()
            return preset

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS meeting_presets (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_meeting_presets_owner_id "
                "ON meeting_presets(owner_id)"
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


def build_auth_repository(settings: Settings) -> AuthRepository:
    backend = settings.database_backend.lower().strip()
    if backend == "sqlite":
        return SQLiteAuthRepository(settings.database_path)
    if backend == "postgres":
        raise RuntimeError(
            "PostgreSQL esta arquitetado como backend futuro, mas ainda nao esta ativo neste MVP. "
            "Use DATABASE_BACKEND=sqlite por enquanto."
        )
    raise RuntimeError("Autenticacao local exige DATABASE_BACKEND=sqlite neste MVP.")


def build_preset_repository(settings: Settings) -> PresetRepository:
    backend = settings.database_backend.lower().strip()
    if backend == "sqlite":
        return SQLitePresetRepository(settings.database_path)
    if backend == "postgres":
        raise RuntimeError(
            "PostgreSQL esta arquitetado como backend futuro, mas ainda nao esta ativo neste MVP. "
            "Use DATABASE_BACKEND=sqlite por enquanto."
        )
    raise RuntimeError("Presets personalizados exigem DATABASE_BACKEND=sqlite neste MVP.")
