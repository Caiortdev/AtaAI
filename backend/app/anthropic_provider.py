import json
import time

import httpx
from pydantic import ValidationError

from app.config import MINUTES_MAX_TRANSCRIPT_CHARS, MINUTES_MODEL, Settings
from app.domain import Meeting, MeetingAnalysis, Priority, TaskItem
from app.minutes import (
    GeneratedMinutesPayload,
    MinutesGenerationError,
    MinutesProvider,
    OPERATIONAL_MINUTES_INSTRUCTIONS,
    build_meeting_analysis,
    validate_coherence,
)
from app.transcription import (
    TRANSIENT_STATUS_CODES,
    TranscriptionResult,
    strip_json_fences,
)
from pathlib import Path

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_FALLBACK_MODELS = ["claude-haiku-4-20250414"]


class AnthropicMinutesProvider(MinutesProvider):
    RETRY_ATTEMPTS = 2
    RETRY_DELAY_SECONDS = 1.0
    TEMPERATURE = 0.2

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_successful_model = ANTHROPIC_MODEL

    def generate(
        self,
        meeting: Meeting,
        transcription: TranscriptionResult,
        frames: list[Path] | None = None,
    ) -> MeetingAnalysis:
        if not self.settings.anthropic_api_key:
            raise MinutesGenerationError(
                "ANTHROPIC_API_KEY nao esta configurada. Configure a chave nas "
                "configuracoes para gerar ata com Claude."
            )

        transcript = transcription.text.strip()
        if not transcript:
            raise MinutesGenerationError("A transcricao esta vazia; nao e possivel gerar a ata.")

        transcript = transcript[:MINUTES_MAX_TRANSCRIPT_CHARS]
        response = self._post_with_retries(meeting, transcript)

        output_text = self._extract_text(response.json())
        try:
            payload = GeneratedMinutesPayload.model_validate_json(strip_json_fences(output_text))
        except ValidationError as exc:
            raise MinutesGenerationError(
                "Claude retornou uma estrutura invalida para a ata."
            ) from exc

        validate_coherence(transcription.text, payload)

        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="anthropic",
            minutes_model=self._last_successful_model,
            payload=payload,
        )

    def _post_with_retries(self, meeting: Meeting, transcript: str) -> httpx.Response:
        models = self._candidate_models()
        attempts = self.RETRY_ATTEMPTS
        delay = self.RETRY_DELAY_SECONDS
        last_error = "sem detalhe retornado pelo provedor."

        for model_index, model in enumerate(models):
            for attempt in range(attempts):
                try:
                    response = httpx.post(
                        ANTHROPIC_API_URL,
                        headers={
                            "x-api-key": self.settings.anthropic_api_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                        },
                        json=self._request_payload(meeting, transcript, model),
                        timeout=180,
                    )
                except httpx.HTTPError as exc:
                    last_error = f"Falha de conexao ao gerar ata com Claude: {exc}"
                    if attempt < attempts - 1:
                        time.sleep(delay * (2**attempt))
                    continue

                if response.status_code < 400:
                    self._last_successful_model = model
                    return response

                detail = self._error_detail(response)
                last_error = f"{model}: {detail}"
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    raise MinutesGenerationError(f"Falha ao gerar ata com Claude: {detail}")

                has_more_attempts = attempt < attempts - 1
                has_more_models = model_index < len(models) - 1
                if has_more_attempts:
                    time.sleep(delay * (2**attempt))
                elif has_more_models:
                    break

        raise MinutesGenerationError(
            "Falha temporaria ao gerar ata com Claude apos tentar "
            f"{', '.join(models)}. Ultimo erro: {last_error}"
        )

    def _candidate_models(self) -> list[str]:
        models = [ANTHROPIC_MODEL, *ANTHROPIC_FALLBACK_MODELS]
        return list(dict.fromkeys(models))

    def _request_payload(self, meeting: Meeting, transcript: str, model: str) -> dict:
        metadata = {
            "titulo": meeting.title,
            "cliente": meeting.client_name or "",
            "participantes": meeting.participants,
            "observacoes": meeting.notes or "",
            "preset": meeting.preset,
            "instrucoes_do_preset": meeting.preset_instructions or "",
        }

        json_schema = json.dumps({
            "executive_summary": "string",
            "topics": ["string"],
            "decisions": ["string"],
            "tasks": [{
                "title": "string",
                "description": "string",
                "priority": "critical|high|medium|low",
                "priority_reason": "string",
                "owner": "string ou vazio",
                "due_date": "string ou vazio",
                "source_excerpt": "string ou vazio",
                "source_timestamp": "string ou vazio",
            }],
            "risks": ["string"],
            "open_questions": ["string"],
            "minutes_markdown": "string",
        }, ensure_ascii=False, indent=2)

        system_prompt = (
            f"{OPERATIONAL_MINUTES_INSTRUCTIONS}\n\n"
            "Nao invente informacoes. Quando responsavel, prazo ou timestamp nao "
            "forem citados, use string vazia. Siga as instrucoes do preset "
            "informado nos metadados.\n\n"
            "Retorne SOMENTE um JSON valido (sem markdown fences) com este schema:\n"
            f"{json_schema}"
        )

        return {
            "model": model,
            "max_tokens": 8192,
            "temperature": self.TEMPERATURE,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Metadados da reuniao:\n"
                        f"{json.dumps(metadata, ensure_ascii=False)}\n\n"
                        "Transcricao:\n"
                        f"{transcript}"
                    ),
                },
            ],
        }

    def _extract_text(self, payload: dict) -> str:
        content = payload.get("content", [])
        for block in content:
            if block.get("type") == "text":
                return block.get("text", "")
        raise MinutesGenerationError("Resposta do Claude nao contem texto.")

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(payload)
