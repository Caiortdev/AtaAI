import json
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.domain import Meeting, MeetingAnalysis, Priority, TaskItem
from app.transcription import TranscriptionResult, extract_gemini_text, strip_json_fences


class MinutesGenerationError(Exception):
    pass


class GeneratedTask(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Priority
    priority_reason: str = Field(min_length=1)
    owner: str = ""
    due_date: str = ""
    source_excerpt: str = ""
    source_timestamp: str = ""


class GeneratedMinutesPayload(BaseModel):
    executive_summary: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    tasks: list[GeneratedTask] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    minutes_markdown: str = Field(min_length=1)


class MinutesProvider:
    def generate(self, meeting: Meeting, transcription: TranscriptionResult) -> MeetingAnalysis:
        raise NotImplementedError


class MockMinutesProvider(MinutesProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, meeting: Meeting, transcription: TranscriptionResult) -> MeetingAnalysis:
        payload = GeneratedMinutesPayload(
            executive_summary=(
                "A reuniao tratou de ajustes solicitados pelo cliente, com foco principal em um "
                "bloqueio no envio de relatorios e melhorias na visibilidade dos status."
            ),
            topics=[
                "Fluxo de envio de relatorios",
                "Acompanhamento de status",
                "Validacao interna de requisitos",
            ],
            decisions=[
                "Priorizar a correcao do fluxo de envio de relatorios.",
                "Validar requisitos internamente antes de confirmar prazo ao cliente.",
            ],
            tasks=[
                GeneratedTask(
                    title="Corrigir fluxo de envio de relatorios",
                    description=(
                        "Investigar e corrigir o problema no fluxo de envio de relatorios citado "
                        "pelo cliente."
                    ),
                    priority=Priority.critical,
                    priority_reason=(
                        "O cliente indicou bloqueio operacional e necessidade de resolucao ainda "
                        "esta semana."
                    ),
                    owner="A definir",
                    due_date="Esta semana",
                    source_excerpt="a equipe operacional esta bloqueada",
                    source_timestamp="00:00:18",
                ),
                GeneratedTask(
                    title="Melhorar tela de acompanhamento de status",
                    description=(
                        "Revisar a tela de acompanhamento para tornar os status mais claros para "
                        "o cliente."
                    ),
                    priority=Priority.medium,
                    priority_reason="Solicitacao relevante, mas sem bloqueio imediato informado.",
                    owner="A definir",
                    source_excerpt="melhorar a tela de acompanhamento",
                    source_timestamp="00:00:32",
                ),
                GeneratedTask(
                    title="Validar requisitos com o time interno",
                    description="Confirmar escopo tecnico e retornar ao cliente com prazo estimado.",
                    priority=Priority.high,
                    priority_reason="E um proximo passo combinado durante a reuniao.",
                    owner="A definir",
                    due_date="Antes do retorno ao cliente",
                    source_excerpt="validar os requisitos com o time interno",
                    source_timestamp="00:00:45",
                ),
            ],
            risks=[
                "Bloqueio operacional do cliente caso o fluxo de relatorios nao seja corrigido.",
                "Prazo ainda indefinido ate validacao tecnica interna.",
            ],
            open_questions=[
                "Qual e a causa exata do bloqueio no envio de relatorios?",
                "Quem sera o responsavel final por cada tarefa?",
            ],
            minutes_markdown=self._build_minutes(meeting),
        )
        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="mock",
            minutes_model="mock-minutes",
            payload=payload,
        )

    def _build_minutes(self, meeting: Meeting) -> str:
        client = meeting.client_name or "Cliente nao informado"
        participants = ", ".join(meeting.participants) if meeting.participants else "Nao informado"
        return f"""# Ata da reuniao: {meeting.title}

## Informacoes gerais
- Cliente: {client}
- Participantes: {participants}
- Preset: {meeting.preset}

## Resumo executivo
A reuniao registrou solicitacoes do cliente e proximos passos para transformar os pontos discutidos em tarefas executaveis.

## Decisoes
- Priorizar itens que bloqueiam a operacao do cliente.
- Validar requisitos tecnicos antes de confirmar prazos finais.

## Tarefas
- [CRITICAL] Corrigir fluxo de envio de relatorios.
- [HIGH] Validar requisitos com o time interno.
- [MEDIUM] Melhorar tela de acompanhamento de status.

## Pendencias
- Confirmar responsaveis.
- Confirmar prazo tecnico apos analise interna.
"""


class OpenAIMinutesProvider(MinutesProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, meeting: Meeting, transcription: TranscriptionResult) -> MeetingAnalysis:
        if not self.settings.openai_api_key:
            raise MinutesGenerationError(
                "OPENAI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para gerar ata e tarefas com IA real."
            )

        transcript = transcription.text.strip()
        if not transcript:
            raise MinutesGenerationError("A transcricao esta vazia; nao e possivel gerar a ata.")

        transcript = transcript[: self.settings.minutes_max_transcript_chars]
        try:
            response = httpx.post(
                f"{self.settings.openai_base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=self._request_payload(meeting, transcript),
                timeout=180,
            )
        except httpx.HTTPError as exc:
            raise MinutesGenerationError(f"Falha de conexao ao gerar ata com OpenAI: {exc}") from exc

        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise MinutesGenerationError(f"Falha ao gerar ata com OpenAI: {detail}")

        output_text = self._extract_output_text(response.json())
        try:
            payload = GeneratedMinutesPayload.model_validate_json(output_text)
        except ValidationError as exc:
            raise MinutesGenerationError(
                "A IA retornou uma estrutura invalida para a ata."
            ) from exc

        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="openai",
            minutes_model=self.settings.minutes_model,
            payload=payload,
        )

    def _request_payload(self, meeting: Meeting, transcript: str) -> dict:
        metadata = {
            "titulo": meeting.title,
            "cliente": meeting.client_name or "",
            "participantes": meeting.participants,
            "observacoes": meeting.notes or "",
            "preset": meeting.preset,
        }
        return {
            "model": self.settings.minutes_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Voce transforma transcricoes de reunioes com clientes em atas "
                        "objetivas, tarefas acionaveis e prioridades justificadas. "
                        "Nao invente informacoes. Quando responsavel, prazo ou timestamp nao "
                        "forem citados, use string vazia."
                    ),
                },
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
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "meeting_minutes_analysis",
                    "strict": True,
                    "schema": MINUTES_JSON_SCHEMA,
                }
            },
        }

    def _extract_output_text(self, payload: dict) -> str:
        direct_text = payload.get("output_text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text

        for output in payload.get("output", []):
            for content in output.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return str(content["text"])

        raise MinutesGenerationError("Resposta da IA nao contem texto estruturado.")

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(payload)


class GeminiMinutesProvider(MinutesProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, meeting: Meeting, transcription: TranscriptionResult) -> MeetingAnalysis:
        if not self.settings.gemini_api_key:
            raise MinutesGenerationError(
                "GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para gerar ata e tarefas com Gemini."
            )

        transcript = transcription.text.strip()
        if not transcript:
            raise MinutesGenerationError("A transcricao esta vazia; nao e possivel gerar a ata.")

        transcript = transcript[: self.settings.minutes_max_transcript_chars]
        try:
            response = httpx.post(
                self._generate_content_url(self.settings.minutes_model),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.settings.gemini_api_key,
                },
                json=self._request_payload(meeting, transcript),
                timeout=180,
            )
        except httpx.HTTPError as exc:
            raise MinutesGenerationError(f"Falha de conexao ao gerar ata com Gemini: {exc}") from exc

        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise MinutesGenerationError(f"Falha ao gerar ata com Gemini: {detail}")

        output_text = extract_gemini_text(response.json())
        try:
            payload = GeneratedMinutesPayload.model_validate_json(strip_json_fences(output_text))
        except ValidationError as exc:
            raise MinutesGenerationError(
                "Gemini retornou uma estrutura invalida para a ata."
            ) from exc

        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="gemini",
            minutes_model=self.settings.minutes_model,
            payload=payload,
        )

    def _request_payload(self, meeting: Meeting, transcript: str) -> dict:
        metadata = {
            "titulo": meeting.title,
            "cliente": meeting.client_name or "",
            "participantes": meeting.participants,
            "observacoes": meeting.notes or "",
            "preset": meeting.preset,
        }
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Voce transforma transcricoes de reunioes com clientes em atas "
                                "objetivas, tarefas acionaveis e prioridades justificadas. "
                                "Nao invente informacoes. Quando responsavel, prazo ou timestamp "
                                "nao forem citados, use string vazia. Retorne somente JSON valido "
                                "no schema solicitado.\n\n"
                                "Metadados da reuniao:\n"
                                f"{json.dumps(metadata, ensure_ascii=False)}\n\n"
                                "Transcricao:\n"
                                f"{transcript}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": GEMINI_MINUTES_JSON_SCHEMA,
            },
        }

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


def build_meeting_analysis(
    meeting: Meeting,
    transcription: TranscriptionResult,
    minutes_provider: Literal["mock", "openai", "gemini"],
    minutes_model: str,
    payload: GeneratedMinutesPayload,
) -> MeetingAnalysis:
    tasks = [
        TaskItem(
            title=task.title,
            description=task.description,
            priority=task.priority,
            priority_reason=task.priority_reason,
            owner=task.owner or None,
            due_date=task.due_date or None,
            source_excerpt=task.source_excerpt or None,
            source_timestamp=task.source_timestamp or None,
        )
        for task in payload.tasks
    ]
    return MeetingAnalysis(
        transcript=transcription.text,
        transcript_provider=transcription.provider,
        transcript_model=transcription.model,
        transcript_language=transcription.language,
        minutes_provider=minutes_provider,
        minutes_model=minutes_model,
        executive_summary=payload.executive_summary,
        topics=payload.topics,
        decisions=payload.decisions,
        tasks=tasks,
        risks=payload.risks,
        open_questions=payload.open_questions,
        minutes_markdown=payload.minutes_markdown,
    )


def build_minutes_provider(settings: Settings) -> MinutesProvider:
    provider = settings.minutes_provider.lower().strip()
    if provider == "mock":
        return MockMinutesProvider(settings)
    if provider == "gemini":
        return GeminiMinutesProvider(settings)
    if provider == "openai":
        return OpenAIMinutesProvider(settings)
    raise MinutesGenerationError(f"Provedor de ata desconhecido: {settings.minutes_provider}.")


TASK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
        "priority_reason": {"type": "string"},
        "owner": {"type": "string"},
        "due_date": {"type": "string"},
        "source_excerpt": {"type": "string"},
        "source_timestamp": {"type": "string"},
    },
    "required": [
        "title",
        "description",
        "priority",
        "priority_reason",
        "owner",
        "due_date",
        "source_excerpt",
        "source_timestamp",
    ],
}

MINUTES_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "executive_summary": {"type": "string"},
        "topics": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "tasks": {"type": "array", "items": TASK_SCHEMA},
        "risks": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "minutes_markdown": {"type": "string"},
    },
    "required": [
        "executive_summary",
        "topics",
        "decisions",
        "tasks",
        "risks",
        "open_questions",
        "minutes_markdown",
    ],
}

GEMINI_TASK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "priority": {"type": "STRING", "enum": ["critical", "high", "medium", "low"]},
        "priority_reason": {"type": "STRING"},
        "owner": {"type": "STRING"},
        "due_date": {"type": "STRING"},
        "source_excerpt": {"type": "STRING"},
        "source_timestamp": {"type": "STRING"},
    },
    "required": [
        "title",
        "description",
        "priority",
        "priority_reason",
        "owner",
        "due_date",
        "source_excerpt",
        "source_timestamp",
    ],
}

GEMINI_MINUTES_JSON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "executive_summary": {"type": "STRING"},
        "topics": {"type": "ARRAY", "items": {"type": "STRING"}},
        "decisions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tasks": {"type": "ARRAY", "items": GEMINI_TASK_SCHEMA},
        "risks": {"type": "ARRAY", "items": {"type": "STRING"}},
        "open_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "minutes_markdown": {"type": "STRING"},
    },
    "required": [
        "executive_summary",
        "topics",
        "decisions",
        "tasks",
        "risks",
        "open_questions",
        "minutes_markdown",
    ],
}
