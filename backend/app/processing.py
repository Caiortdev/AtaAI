from app.domain import Meeting, MeetingStatus, ProcessMeetingRequest
from app.media import MediaProcessingError, MediaService
from app.minutes import MinutesGenerationError, MinutesProvider
from app.transcription import TranscriptionError, TranscriptionProvider


class MeetingProcessor:
    """Pluggable MVP processor.

    The first implementation is deterministic and local. Real FFmpeg, transcription,
    diarization and LLM calls can replace these private methods without changing API
    contracts or the frontend.
    """

    def __init__(
        self,
        media_service: MediaService,
        transcription_provider: TranscriptionProvider,
        minutes_provider: MinutesProvider,
    ) -> None:
        self.media_service = media_service
        self.transcription_provider = transcription_provider
        self.minutes_provider = minutes_provider

    def process(self, meeting: Meeting, request: ProcessMeetingRequest) -> Meeting:
        meeting.status = MeetingStatus.processing
        meeting.analysis_mode = request.mode
        meeting.preset = request.preset
        meeting.processing_error = None
        meeting.processing_steps = ["Arquivo recebido", "Validando midia com FFprobe"]

        try:
            if meeting.file is None:
                raise MediaProcessingError("Envie um arquivo antes de processar a reuniao.")
            meeting.prepared_audio = self.media_service.prepare_audio(meeting.id, meeting.file)
            meeting.processing_steps.append("Audio preparado em WAV mono 16k")

            transcription = self.transcription_provider.transcribe(meeting.id, meeting.prepared_audio)
            meeting.processing_steps.append(
                f"Transcricao gerada por {transcription.provider}/{transcription.model}"
            )
            analysis = self.minutes_provider.generate(meeting=meeting, transcription=transcription)
            meeting.processing_steps.append(
                f"Ata e tarefas geradas por {analysis.minutes_provider}/{analysis.minutes_model}"
            )

            meeting.analysis = analysis
            meeting.status = MeetingStatus.completed
        except (MediaProcessingError, TranscriptionError, MinutesGenerationError) as exc:
            meeting.status = MeetingStatus.failed
            meeting.processing_error = str(exc)
            meeting.processing_steps.append("Processamento interrompido")
        return meeting
