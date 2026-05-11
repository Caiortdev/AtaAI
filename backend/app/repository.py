import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain import Meeting, MeetingCreate, MeetingStatus, UploadedFileInfo


class MeetingRepository:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "meetings.json"

    def list(self) -> list[Meeting]:
        data = self._read()
        return [Meeting.model_validate(item) for item in data]

    def get(self, meeting_id: str) -> Meeting | None:
        for meeting in self.list():
            if meeting.id == meeting_id:
                return meeting
        return None

    def create(self, payload: MeetingCreate) -> Meeting:
        meeting = Meeting(**payload.model_dump())
        meetings = self.list()
        meetings.append(meeting)
        self._write(meetings)
        return meeting

    def attach_file(self, meeting_id: str, file_info: UploadedFileInfo) -> Meeting:
        meeting = self._require(meeting_id)
        meeting.file = file_info
        meeting.status = MeetingStatus.uploaded
        return self.save(meeting)

    def save(self, meeting: Meeting) -> Meeting:
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
