from pathlib import Path

import httpx

from app.config import Settings
from app.domain import PreparedAudioInfo
from app.media import MediaProcessingError, MediaService


class TranscriptionError(Exception):
    pass


class TranscriptionResult:
    def __init__(self, text: str, provider: str, model: str, language: str | None) -> None:
        self.text = text
        self.provider = provider
        self.model = model
        self.language = language


class TranscriptionProvider:
    def transcribe(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> TranscriptionResult:
        raise NotImplementedError


class MockTranscriptionProvider(TranscriptionProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> TranscriptionResult:
        duration = (
            f"{prepared_audio.duration_seconds:.1f}s"
            if prepared_audio.duration_seconds
            else "duracao nao identificada"
        )
        return TranscriptionResult(
            text=(
                f"Transcricao mock do audio preparado ({duration}).\n\n"
                "Cliente informou que precisa corrigir o fluxo de envio de relatorios ainda esta semana, "
                "pois a equipe operacional esta bloqueada. Tambem solicitou melhorar a tela de acompanhamento "
                "para facilitar a visualizacao dos status. Ficou combinado validar os requisitos com o time "
                "interno e retornar com prazo estimado. O cliente mencionou que a melhoria visual pode ficar "
                "para um segundo momento, sem urgencia imediata."
            ),
            provider="mock",
            model="mock-transcriber",
            language=self.settings.transcription_language,
        )


class OpenAITranscriptionProvider(TranscriptionProvider):
    def __init__(self, settings: Settings, media_service: MediaService) -> None:
        self.settings = settings
        self.media_service = media_service

    def transcribe(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> TranscriptionResult:
        if not self.settings.openai_api_key:
            raise TranscriptionError(
                "OPENAI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para usar transcricao real."
            )

        try:
            chunks = self.media_service.transcription_chunks(meeting_id, prepared_audio)
        except MediaProcessingError as exc:
            raise TranscriptionError(str(exc)) from exc

        texts = [self._transcribe_file(chunk_path, index, len(chunks)) for index, chunk_path in enumerate(chunks, 1)]
        return TranscriptionResult(
            text="\n\n".join(text for text in texts if text.strip()),
            provider="openai",
            model=self.settings.transcription_model,
            language=self.settings.transcription_language,
        )

    def _transcribe_file(self, audio_path: Path, index: int, total: int) -> str:
        prompt = self.settings.transcription_prompt
        if total > 1:
            prompt = f"{prompt}\nEste e o trecho {index} de {total} da mesma reuniao."

        with audio_path.open("rb") as audio_file:
            files = {"file": (audio_path.name, audio_file, "audio/wav")}
            data = {
                "model": self.settings.transcription_model,
                "response_format": "json",
                "language": self.settings.transcription_language,
                "prompt": prompt,
            }
            response = httpx.post(
                f"{self.settings.openai_base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                data=data,
                files=files,
                timeout=180,
            )

        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise TranscriptionError(f"Falha na transcricao OpenAI: {detail}")

        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise TranscriptionError("Resposta de transcricao nao contem campo text.")
        return text

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(payload)


def build_transcription_provider(
    settings: Settings,
    media_service: MediaService,
) -> TranscriptionProvider:
    provider = settings.transcription_provider.lower().strip()
    if provider == "mock":
        return MockTranscriptionProvider(settings)
    if provider == "openai":
        return OpenAITranscriptionProvider(settings, media_service)
    raise TranscriptionError(f"Provedor de transcricao desconhecido: {settings.transcription_provider}.")
