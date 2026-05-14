from app.audio_diagnostics import AudioQuality, assess_audio_quality
from app.domain import AnalysisMode, Meeting, MeetingStatus, ProcessMeetingRequest
from app.media import MediaProcessingError, MediaService
from app.minutes import MinutesGenerationError, MinutesProvider
from app.transcription import TranscriptionError, TranscriptionProvider

import re
from pathlib import Path


class MeetingProcessor:
    """Pluggable MVP processor.

    The first implementation is deterministic and local. Real FFmpeg, transcription,
    diarization and LLM calls can replace these private methods without changing API
    contracts or the frontend.
    """

    MAX_WORDS_PER_SECOND = 5.0
    REPETITION_THRESHOLD = 0.4

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
        if not meeting.preset_id:
            meeting.preset = request.preset
        meeting.processing_error = None
        if "Processamento enfileirado" in meeting.processing_steps:
            meeting.processing_steps.append("Processamento iniciado")
            meeting.processing_steps.append("Validando midia com FFprobe")
        else:
            meeting.processing_steps = ["Arquivo recebido", "Validando midia com FFprobe"]

        try:
            if meeting.file is None:
                raise MediaProcessingError("Envie um arquivo antes de processar a reuniao.")
            if meeting.prepared_audio is None:
                meeting.prepared_audio = self.media_service.prepare_audio(meeting.id, meeting.file)
                meeting.processing_steps.append("Audio preparado em MP3 mono 16k")
            else:
                meeting.processing_steps.append("Audio preparado reutilizado")

            audio_path = self.media_service.prepared_audio_path(meeting.id, meeting.prepared_audio)

            # Audio quality diagnostics (includes speech detection)
            ffmpeg_bin = self.media_service._resolve_binary(
                self.media_service.settings.ffmpeg_binary, "FFmpeg"
            )
            if ffmpeg_bin:
                diagnostics = assess_audio_quality(audio_path, ffmpeg_bin)
                meeting.audio_quality = diagnostics.quality.value
                meeting.audio_diagnostics = {
                    "snr_db": diagnostics.snr_db,
                    "clip_ratio": diagnostics.clip_ratio,
                    "speech_ratio": diagnostics.speech_ratio,
                    "mean_volume_db": diagnostics.mean_volume_db,
                    "quality": diagnostics.quality.value,
                }

                if diagnostics.quality == AudioQuality.unusable:
                    raise MediaProcessingError(
                        "Qualidade do audio insuficiente para transcricao. "
                        + " ".join(diagnostics.warnings)
                    )

                if diagnostics.warnings:
                    for warning in diagnostics.warnings:
                        meeting.processing_steps.append(f"Aviso: {warning}")

                meeting.processing_steps.append(
                    f"Qualidade do audio: {diagnostics.quality.value} "
                    f"(SNR: {diagnostics.snr_db}dB, fala: {int(diagnostics.speech_ratio * 100)}%)"
                )
            else:
                if self.media_service.detect_silence(audio_path):
                    raise MediaProcessingError(
                        "O audio nao contem fala audivel. Verifique se o arquivo possui som "
                        "ou se o microfone estava ativo durante a gravacao."
                    )
                meeting.processing_steps.append("Audio validado (contem fala)")

            transcription = self.transcription_provider.transcribe(meeting.id, meeting.prepared_audio)

            if not self._is_valid_transcription(transcription.text):
                raise TranscriptionError(
                    "A transcricao retornada esta vazia ou nao contem conteudo significativo. "
                    "Verifique se o audio possui fala clara e audivel."
                )

            if meeting.prepared_audio and meeting.prepared_audio.duration_seconds:
                self._validate_transcription_volume(
                    transcription.text, meeting.prepared_audio.duration_seconds
                )

            meeting.processing_steps.append(
                f"Transcricao gerada por {transcription.provider}/{transcription.model}"
            )

            # Extract video frames if mode is audio_video and file is a video
            frames: list[Path] = []
            if (
                request.mode == AnalysisMode.audio_video
                and meeting.file is not None
                and meeting.file.media_kind.value == "video"
            ):
                upload_path = self.media_service.upload_path(meeting.id, meeting.file.stored_name)
                if upload_path.exists():
                    try:
                        frames = self.media_service.extract_frames(meeting.id, upload_path)
                        meeting.processing_steps.append(
                            f"{len(frames)} frames extraidos para analise visual"
                        )
                    except MediaProcessingError:
                        meeting.processing_steps.append(
                            "Nao foi possivel extrair frames; continuando sem analise visual"
                        )
                else:
                    meeting.processing_steps.append(
                        "Arquivo de video nao encontrado; continuando sem analise visual"
                    )

            analysis = self.minutes_provider.generate(
                meeting=meeting, transcription=transcription, frames=frames
            )
            meeting.processing_steps.append(
                f"Ata e tarefas geradas por {analysis.minutes_provider}/{analysis.minutes_model}"
            )

            meeting.analysis = analysis
            meeting.status = MeetingStatus.completed

            if request.auto_metadata:
                self._extract_metadata(meeting)
                meeting.processing_steps.append("Metadados extraidos automaticamente da ata")

        except (MediaProcessingError, TranscriptionError, MinutesGenerationError) as exc:
            meeting.status = MeetingStatus.failed
            meeting.processing_error = str(exc)
            meeting.processing_steps.append("Processamento interrompido")
        return meeting

    def _extract_metadata(self, meeting: Meeting) -> None:
        if not meeting.analysis:
            return
        md = meeting.analysis.minutes_markdown

        title_match = re.search(r"Ata de reuniao\s*[-–—]\s*(.+)", md)
        if title_match:
            extracted_title = title_match.group(1).strip()
            if extracted_title and extracted_title.lower() != "nao informado":
                meeting.title = extracted_title

        participants_match = re.search(r"Participantes citados:\s*(.+)", md)
        if participants_match:
            raw = participants_match.group(1).strip()
            if raw.lower() != "nao informado":
                names = [n.strip() for n in raw.split(",") if n.strip()]
                if names:
                    meeting.participants = names

        client_match = re.search(r"Cliente:\s*(.+)", md)
        if client_match:
            raw = client_match.group(1).strip()
            if raw.lower() not in ("nao informado", "cliente nao informado"):
                meeting.client_name = raw

    @staticmethod
    def _is_valid_transcription(text: str) -> bool:
        """Check if transcription has meaningful content (not empty/hallucinated)."""
        cleaned = text.strip()
        if not cleaned:
            return False
        # Too short to be a real meeting transcription (less than 20 words)
        word_count = len(cleaned.split())
        if word_count < 20:
            return False
        return True

    def _validate_transcription_volume(self, text: str, duration_seconds: float) -> None:
        word_count = len(text.split())
        words_per_second = word_count / max(duration_seconds, 1.0)

        if words_per_second > self.MAX_WORDS_PER_SECOND:
            raise TranscriptionError(
                f"A transcricao parece conter conteudo inventado: {word_count} palavras "
                f"para {duration_seconds:.0f}s de audio ({words_per_second:.1f} palavras/s). "
                "Isso excede o limite de fala humana normal. Verifique a qualidade do audio."
            )

        if self._has_excessive_repetition(text):
            raise TranscriptionError(
                "A transcricao contem trechos excessivamente repetitivos, o que indica "
                "possivel alucinacao do modelo. Verifique a qualidade do audio."
            )

    @staticmethod
    def _has_excessive_repetition(text: str) -> bool:
        sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 10]
        if len(sentences) < 5:
            return False
        unique = set(sentences)
        repetition_ratio = 1.0 - (len(unique) / len(sentences))
        return repetition_ratio > MeetingProcessor.REPETITION_THRESHOLD
