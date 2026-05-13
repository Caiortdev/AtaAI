import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

from app.config import Settings
from app.domain import PreparedAudioInfo
from app.media import MediaProcessingError, MediaService


class TranscriptionError(Exception):
    pass


TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


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
            files = {
                "file": (
                    audio_path.name,
                    audio_file,
                    self.media_service.content_type_for_path(audio_path),
                )
            }
            data = {
                "model": self.settings.transcription_model,
                "response_format": "json",
                "language": self.settings.transcription_language,
                "prompt": prompt,
            }
            try:
                response = httpx.post(
                    f"{self.settings.openai_base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    data=data,
                    files=files,
                    timeout=180,
                )
            except httpx.HTTPError as exc:
                raise TranscriptionError(f"Falha de conexao na transcricao OpenAI: {exc}") from exc

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


class GeminiTranscriptionProvider(TranscriptionProvider):
    def __init__(self, settings: Settings, media_service: MediaService) -> None:
        self.settings = settings
        self.media_service = media_service
        self._last_successful_model = settings.transcription_model

    def transcribe(self, meeting_id: str, prepared_audio: PreparedAudioInfo) -> TranscriptionResult:
        if not self.settings.gemini_api_key:
            raise TranscriptionError(
                "GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para usar transcricao real com Gemini."
            )

        try:
            chunks = self.media_service.transcription_chunks(meeting_id, prepared_audio)
        except MediaProcessingError as exc:
            raise TranscriptionError(str(exc)) from exc

        if len(chunks) == 1:
            texts = [self._transcribe_file(chunks[0], 1, 1)]
        else:
            texts = self._transcribe_parallel(chunks)

        return TranscriptionResult(
            text="\n\n".join(text for text in texts if text.strip()),
            provider="gemini",
            model=self._last_successful_model,
            language=self.settings.transcription_language,
        )

    def _transcribe_parallel(self, chunks: list[Path]) -> list[str]:
        total = len(chunks)
        results: list[str | None] = [None] * total
        errors: list[str] = []

        max_workers = min(total, 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self._transcribe_file, chunk_path, index, total): index - 1
                for index, chunk_path in enumerate(chunks, 1)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result()
                except TranscriptionError as exc:
                    errors.append(str(exc))

        if errors and all(r is None for r in results):
            raise TranscriptionError(
                f"Falha na transcricao de todos os trechos. Primeiro erro: {errors[0]}"
            )

        return [r for r in results if r is not None]

    def _transcribe_file(self, audio_path: Path, index: int, total: int) -> str:
        prompt = (
            f"{self.settings.transcription_prompt}\n"
            "Retorne somente JSON valido no schema solicitado, com o campo text contendo "
            "a transcricao completa e fiel do audio."
        )
        if total > 1:
            prompt = f"{prompt}\nEste e o trecho {index} de {total} da mesma reuniao."

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": self.media_service.content_type_for_path(audio_path),
                                "data": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": GEMINI_TRANSCRIPTION_SCHEMA,
            },
        }
        response = self._post_with_retries(payload)

        output_text = extract_gemini_text(response.json())
        return parse_transcription_output(output_text)

    def _post_with_retries(self, payload: dict) -> httpx.Response:
        models = self._candidate_models()
        attempts = max(1, self.settings.transcription_retry_attempts)
        delay = max(0.0, self.settings.transcription_retry_delay_seconds)
        last_error = "sem detalhe retornado pelo provedor."

        for model_index, model in enumerate(models):
            for attempt in range(attempts):
                try:
                    response = httpx.post(
                        self._generate_content_url(model),
                        headers={
                            "Content-Type": "application/json",
                            "x-goog-api-key": self.settings.gemini_api_key,
                        },
                        json=payload,
                        timeout=180,
                    )
                except httpx.HTTPError as exc:
                    last_error = f"Falha de conexao na transcricao Gemini: {exc}"
                    if attempt < attempts - 1:
                        self._sleep_before_retry(delay, attempt)
                    continue

                if response.status_code < 400:
                    self._last_successful_model = model
                    return response

                detail = self._error_detail(response)
                last_error = f"{model}: {detail}"
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    raise TranscriptionError(f"Falha na transcricao Gemini: {detail}")

                has_more_attempts = attempt < attempts - 1
                has_more_models = model_index < len(models) - 1
                if has_more_attempts:
                    self._sleep_before_retry(delay, attempt)
                elif has_more_models:
                    break

        raise TranscriptionError(
            "Falha temporaria na transcricao Gemini apos tentar "
            f"{', '.join(models)}. Ultimo erro: {last_error}"
        )

    def _candidate_models(self) -> list[str]:
        configured = [
            self.settings.transcription_model,
            *self.settings.transcription_fallback_models.split(","),
        ]
        models = [model.strip() for model in configured if model.strip()]
        return list(dict.fromkeys(models))

    def _sleep_before_retry(self, delay: float, attempt: int) -> None:
        if delay <= 0:
            return
        time.sleep(delay * (2**attempt))

    def _generate_content_url(self, model: str) -> str:
        return f"{self.settings.gemini_base_url}/models/{model}:generateContent"

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
    if provider == "gemini":
        return GeminiTranscriptionProvider(settings, media_service)
    if provider == "openai":
        return OpenAITranscriptionProvider(settings, media_service)
    raise TranscriptionError(f"Provedor de transcricao desconhecido: {settings.transcription_provider}.")


def extract_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise TranscriptionError("Resposta Gemini nao contem candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text

    raise TranscriptionError("Resposta Gemini nao contem texto.")


def strip_json_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def parse_transcription_output(output_text: str) -> str:
    text = strip_json_fences(output_text)
    parsed = try_parse_json_object(text)
    if parsed is not None:
        for key in ("text", "transcript", "transcription", "transcricao"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raise TranscriptionError("Resposta de transcricao Gemini nao contem campo text.")

    raw_text = text.strip()
    if raw_text:
        return raw_text

    raise TranscriptionError("Gemini retornou transcricao vazia.")


def try_parse_json_object(value: str) -> dict | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = extract_first_json_object(value)

    if parsed is None:
        return None
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, str) and parsed.strip():
        return {"text": parsed}
    return None


def extract_first_json_object(value: str) -> dict | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(value):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


GEMINI_TRANSCRIPTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "text": {"type": "STRING"},
    },
    "required": ["text"],
}
