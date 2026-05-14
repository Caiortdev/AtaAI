import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


logger = logging.getLogger(__name__)

JobCallable = Callable[[], None]


@dataclass(frozen=True)
class ProcessingJob:
    id: str
    meeting_id: str
    created_at: datetime
    run: JobCallable = field(repr=False)


class ProcessingQueue:
    def __init__(self) -> None:
        self._jobs: queue.Queue[ProcessingJob] = queue.Queue()
        self._worker = threading.Thread(target=self._work, name="meeting-processing", daemon=True)
        self._worker.start()

    def enqueue(self, meeting_id: str, run: JobCallable) -> ProcessingJob:
        job = ProcessingJob(
            id=str(uuid4()),
            meeting_id=meeting_id,
            created_at=datetime.now(UTC),
            run=run,
        )
        self._jobs.put(job)
        return job

    def size(self) -> int:
        return self._jobs.qsize()

    def _work(self) -> None:
        while True:
            job = self._jobs.get()
            try:
                job.run()
            except Exception:
                logger.exception(
                    "Unexpected error in processing job %s (meeting %s)",
                    job.id,
                    job.meeting_id,
                )
            finally:
                self._jobs.task_done()


processing_queue = ProcessingQueue()
