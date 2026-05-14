import base64
import json
import time
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import (
    GEMINI_BASE_URL,
    MINUTES_MAX_TRANSCRIPT_CHARS,
    MINUTES_MODEL,
    OPENAI_BASE_URL,
    Settings,
)
from app.domain import Meeting, MeetingAnalysis, Priority, TaskItem
from app.transcription import (
    TRANSIENT_STATUS_CODES,
    TranscriptionResult,
    extract_gemini_text,
    strip_json_fences,
)


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


OPERATIONAL_MINUTES_INSTRUCTIONS = """
Voce transforma transcricoes de reunioes com clientes em atas operacionais para repasse ao time tecnico.
Nao faca resumo corrido de tudo que foi conversado. Extraia somente contexto, problemas, solicitacoes,
impactos, criterios de aceite, encaminhamentos e pontos a validar.

O campo minutes_markdown deve seguir este padrao:

Ata de reuniao - [tema principal]
Data da reuniao: [data citada ou Nao informado]
Cliente: [cliente/pessoa principal]
Participantes citados: [nomes citados]
Produto/processo: [produto, modulo, integracao ou processo afetado]
Objetivo informado: [objetivo da conversa]

Contexto
[um ou dois paragrafos objetivos explicando o cenario, o que a ferramenta/processo deveria fazer e
por que os problemas impedem o uso]

Tarefas levantadas
1. [verbo no infinitivo + objeto da correcao/mudanca]
Prioridade: [Critica, Alta, Media ou Baixa]
Solicitacao: [o que foi pedido, sem inventar]
Impacto: [impacto operacional/comercial citado ou inferido diretamente do contexto]
Critérios de aceite:
- [criterio verificavel]
- [criterio verificavel]

Encaminhamentos
- [responsavel/acao combinada]

Observacoes
- [alertas sobre validacao da ata, nomes, prazos, dependencias ou lacunas]

Regras:
- Nao invente nomes, datas, responsaveis, numeros, prazos, impactos ou criterios.
- Quando uma informacao nao existir na transcricao, use "Nao informado" ou "A validar".
- Prioridade Critica: operacao parada, integracao essencial indisponivel, perda grande de produtividade,
cliente bloqueado ou prazo urgente.
- Prioridade Alta: afeta fluxo principal, exige correcao na semana, envolve cliente ou dependencia relevante.
- Prioridade Media: melhoria importante, falha recorrente sem bloqueio total ou ajuste operacional.
- Cada tarefa precisa ter criterios de aceite concretos e testaveis.
- Agrupe falas repetidas em uma unica tarefa; nao duplique itens.
- Use portugues do Brasil e tom profissional.
""".strip()


class MinutesProvider:
    def generate(
        self,
        meeting: Meeting,
        transcription: TranscriptionResult,
        frames: list[Path] | None = None,
    ) -> MeetingAnalysis:
        raise NotImplementedError


class MockMinutesProvider(MinutesProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        meeting: Meeting,
        transcription: TranscriptionResult,
        frames: list[Path] | None = None,
    ) -> MeetingAnalysis:
        payload = GeneratedMinutesPayload(
            executive_summary="Foram levantadas solicitacoes de mudanca e problemas operacionais para priorizacao tecnica.",
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
        return f"""Ata de reuniao - Solicitacoes de mudanca
Data da reuniao: Nao informado
Cliente: {client}
Participantes citados: {participants}
Produto/processo: Nao informado
Objetivo informado: coletar problemas e mudancas para priorizar correcoes

Contexto
A reuniao registrou solicitacoes do cliente e proximos passos para transformar os pontos discutidos em tarefas executaveis. A ata deve ser validada pela equipe antes do envio formal.

Tarefas levantadas
1. Corrigir fluxo de envio de relatorios
Prioridade: Critica
Solicitacao: Investigar e corrigir o problema no fluxo de envio de relatorios citado pelo cliente.
Impacto: O cliente indicou bloqueio operacional.
Critérios de aceite:
- O fluxo de envio deve voltar a funcionar sem bloqueio operacional.
- A causa do problema deve ser identificada e registrada.

2. Validar requisitos com o time interno
Prioridade: Alta
Solicitacao: Confirmar escopo tecnico e retornar ao cliente com prazo estimado.
Impacto: O cliente depende do retorno para acompanhar a resolucao.
Critérios de aceite:
- Requisitos validados com o time interno.
- Prazo estimado comunicado ao cliente.

Encaminhamentos
- Validar requisitos tecnicos antes de confirmar prazos finais.
- Confirmar responsaveis por cada tarefa.

Observacoes
- Ata gerada a partir de transcricao automatica.
- Recomenda-se validar nomes proprios e prazos antes de enviar formalmente ao cliente.
"""


class OpenAIMinutesProvider(MinutesProvider):
    RETRY_ATTEMPTS = 2
    RETRY_DELAY_SECONDS = 1.0
    TEMPERATURE = 0.2

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        meeting: Meeting,
        transcription: TranscriptionResult,
        frames: list[Path] | None = None,
    ) -> MeetingAnalysis:
        if not self.settings.openai_api_key:
            raise MinutesGenerationError(
                "OPENAI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para gerar ata e tarefas com IA real."
            )

        transcript = transcription.text.strip()
        if not transcript:
            raise MinutesGenerationError("A transcricao esta vazia; nao e possivel gerar a ata.")

        transcript = transcript[: MINUTES_MAX_TRANSCRIPT_CHARS]
        response = self._post_with_retries(meeting, transcript)

        output_text = self._extract_output_text(response.json())
        try:
            payload = GeneratedMinutesPayload.model_validate_json(output_text)
        except ValidationError as exc:
            raise MinutesGenerationError(
                "A IA retornou uma estrutura invalida para a ata."
            ) from exc

        validate_coherence(transcription.text, payload)

        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="openai",
            minutes_model=MINUTES_MODEL,
            payload=payload,
        )

    def _post_with_retries(self, meeting: Meeting, transcript: str) -> httpx.Response:
        attempts = self.RETRY_ATTEMPTS
        delay = self.RETRY_DELAY_SECONDS
        last_error = "sem detalhe retornado pelo provedor."

        for attempt in range(attempts):
            try:
                response = httpx.post(
                    f"{OPENAI_BASE_URL}/responses",
                    headers={
                        "Authorization": f"Bearer {self.settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=self._request_payload(meeting, transcript),
                    timeout=180,
                )
            except httpx.HTTPError as exc:
                last_error = f"Falha de conexao ao gerar ata com OpenAI: {exc}"
                if attempt < attempts - 1:
                    time.sleep(delay * (2**attempt))
                continue

            if response.status_code < 400:
                return response

            detail = self._error_detail(response)
            last_error = detail
            if response.status_code not in TRANSIENT_STATUS_CODES:
                raise MinutesGenerationError(f"Falha ao gerar ata com OpenAI: {detail}")

            if attempt < attempts - 1:
                time.sleep(delay * (2**attempt))

        raise MinutesGenerationError(
            f"Falha temporaria ao gerar ata com OpenAI apos {attempts} tentativas. "
            f"Ultimo erro: {last_error}"
        )

    def _request_payload(self, meeting: Meeting, transcript: str) -> dict:
        metadata = {
            "titulo": meeting.title,
            "cliente": meeting.client_name or "",
            "participantes": meeting.participants,
            "observacoes": meeting.notes or "",
            "preset": meeting.preset,
            "instrucoes_do_preset": meeting.preset_instructions or "",
        }
        return {
            "model": MINUTES_MODEL,
            "input": [
                {
                    "role": "system",
                    "content": (
                        f"{OPERATIONAL_MINUTES_INSTRUCTIONS}\n\n"
                        "Nao invente informacoes. Quando responsavel, prazo ou timestamp nao "
                        "forem citados, use string vazia. Siga as instrucoes do preset "
                        "informado nos metadados."
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
            "temperature": self.TEMPERATURE,
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
    FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-2.0-flash"]
    RETRY_ATTEMPTS = 2
    RETRY_DELAY_SECONDS = 1.0
    TEMPERATURE = 0.2

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_successful_model = MINUTES_MODEL

    def generate(
        self,
        meeting: Meeting,
        transcription: TranscriptionResult,
        frames: list[Path] | None = None,
    ) -> MeetingAnalysis:
        if not self.settings.gemini_api_key:
            raise MinutesGenerationError(
                "GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para gerar ata e tarefas com Gemini."
            )

        transcript = transcription.text.strip()
        if not transcript:
            raise MinutesGenerationError("A transcricao esta vazia; nao e possivel gerar a ata.")

        transcript = transcript[: MINUTES_MAX_TRANSCRIPT_CHARS]
        request_payload = self._request_payload(meeting, transcript, frames or [])
        response = self._post_with_retries(request_payload)

        output_text = extract_gemini_text(response.json())
        try:
            payload = GeneratedMinutesPayload.model_validate_json(strip_json_fences(output_text))
        except ValidationError as exc:
            raise MinutesGenerationError(
                "Gemini retornou uma estrutura invalida para a ata."
            ) from exc

        validate_coherence(transcription.text, payload)

        return build_meeting_analysis(
            meeting=meeting,
            transcription=transcription,
            minutes_provider="gemini",
            minutes_model=self._last_successful_model,
            payload=payload,
        )

    def _post_with_retries(self, payload: dict) -> httpx.Response:
        models = self._candidate_models()
        attempts = self.RETRY_ATTEMPTS
        delay = self.RETRY_DELAY_SECONDS
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
                    last_error = f"Falha de conexao ao gerar ata com Gemini: {exc}"
                    if attempt < attempts - 1:
                        self._sleep_before_retry(delay, attempt)
                    continue

                if response.status_code < 400:
                    self._last_successful_model = model
                    return response

                detail = self._error_detail(response)
                last_error = f"{model}: {detail}"
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    raise MinutesGenerationError(f"Falha ao gerar ata com Gemini: {detail}")

                has_more_attempts = attempt < attempts - 1
                has_more_models = model_index < len(models) - 1
                if has_more_attempts:
                    self._sleep_before_retry(delay, attempt)
                elif has_more_models:
                    break

        raise MinutesGenerationError(
            "Falha temporaria ao gerar ata com Gemini apos tentar "
            f"{', '.join(models)}. Ultimo erro: {last_error}"
        )

    def _candidate_models(self) -> list[str]:
        configured = [MINUTES_MODEL, *self.FALLBACK_MODELS]
        models = [model.strip() for model in configured if model.strip()]
        return list(dict.fromkeys(models))

    def _sleep_before_retry(self, delay: float, attempt: int) -> None:
        if delay <= 0:
            return
        time.sleep(delay * (2**attempt))

    def _request_payload(self, meeting: Meeting, transcript: str, frames: list[Path]) -> dict:
        metadata = {
            "titulo": meeting.title,
            "cliente": meeting.client_name or "",
            "participantes": meeting.participants,
            "observacoes": meeting.notes or "",
            "preset": meeting.preset,
            "instrucoes_do_preset": meeting.preset_instructions or "",
        }

        visual_instruction = ""
        if frames:
            visual_instruction = (
                "\n\nAlem da transcricao, analise as imagens/frames do video anexados. "
                "Identifique e descreva: slides apresentados, telas compartilhadas, diagramas, "
                "quadros brancos ou qualquer conteudo visual relevante para a ata. "
                "Inclua na ata uma secao 'Conteudo visual identificado' com os pontos principais "
                "extraidos das imagens. Se nao houver conteudo visual relevante, omita essa secao."
            )

        parts: list[dict] = [
            {
                "text": (
                    f"{OPERATIONAL_MINUTES_INSTRUCTIONS}\n\n"
                    "Nao invente informacoes. Quando responsavel, prazo ou timestamp "
                    "nao forem citados, use string vazia. Siga as instrucoes do preset "
                    "informado nos metadados. Retorne somente JSON valido no schema "
                    f"solicitado.{visual_instruction}\n\n"
                    "Metadados da reuniao:\n"
                    f"{json.dumps(metadata, ensure_ascii=False)}\n\n"
                    "Transcricao:\n"
                    f"{transcript}"
                )
            }
        ]

        # Append video frames as inline images
        for frame_path in frames[:20]:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": base64.b64encode(frame_path.read_bytes()).decode("ascii"),
                }
            })

        return {
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": GEMINI_MINUTES_JSON_SCHEMA,
                "temperature": self.TEMPERATURE,
            },
        }

    def _generate_content_url(self, model: str) -> str:
        return f"{GEMINI_BASE_URL}/models/{model}:generateContent"

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(payload)


def _extract_keywords(text: str, min_length: int = 4) -> set[str]:
    words = set()
    for word in text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if len(cleaned) >= min_length:
            words.add(cleaned)
    return words


def validate_coherence(transcript: str, payload: GeneratedMinutesPayload) -> None:
    transcript_keywords = _extract_keywords(transcript)
    if not transcript_keywords:
        return

    ata_text = " ".join([
        payload.executive_summary,
        " ".join(t.title + " " + t.description for t in payload.tasks),
        " ".join(payload.topics),
        " ".join(payload.decisions),
    ])
    ata_keywords = _extract_keywords(ata_text)
    if not ata_keywords:
        raise MinutesGenerationError(
            "A ata gerada nao contem conteudo significativo. Tente novamente."
        )

    overlap = ata_keywords & transcript_keywords
    ratio = len(overlap) / len(ata_keywords) if ata_keywords else 0.0

    if ratio < 0.15:
        raise MinutesGenerationError(
            "A ata gerada parece nao corresponder a transcricao (baixa coerencia). "
            "Isso pode indicar alucinacao da IA. Tente processar novamente."
        )


def build_meeting_analysis(
    meeting: Meeting,
    transcription: TranscriptionResult,
    minutes_provider: Literal["mock", "openai", "gemini", "anthropic"],
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


def build_minutes_provider(
    settings: Settings,
    provider_override: str | None = None,
    api_key_override: str | None = None,
) -> MinutesProvider:
    provider = (provider_override or settings.minutes_provider).lower().strip()
    effective_settings = settings
    if api_key_override:
        effective_settings = settings.model_copy()
        if provider == "gemini":
            effective_settings.gemini_api_key = api_key_override
        elif provider == "openai":
            effective_settings.openai_api_key = api_key_override
        elif provider == "anthropic":
            effective_settings.anthropic_api_key = api_key_override

    if provider == "mock":
        return MockMinutesProvider(effective_settings)
    if provider == "gemini":
        return GeminiMinutesProvider(effective_settings)
    if provider == "openai":
        return OpenAIMinutesProvider(effective_settings)
    if provider == "anthropic":
        from app.anthropic_provider import AnthropicMinutesProvider
        return AnthropicMinutesProvider(effective_settings)
    raise MinutesGenerationError(f"Provedor de ata desconhecido: {provider}.")


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
