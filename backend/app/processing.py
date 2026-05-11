from app.domain import (
    Meeting,
    MeetingAnalysis,
    MeetingStatus,
    Priority,
    ProcessMeetingRequest,
    TaskItem,
)
from app.media import MediaProcessingError, MediaService
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
    ) -> None:
        self.media_service = media_service
        self.transcription_provider = transcription_provider

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
            analysis = self._analyze_placeholder(
                meeting=meeting,
                transcript=transcription.text,
                transcript_provider=transcription.provider,
                transcript_model=transcription.model,
                transcript_language=transcription.language,
            )

            meeting.analysis = analysis
            meeting.status = MeetingStatus.completed
            meeting.processing_steps.append("Ata e tarefas geradas")
        except (MediaProcessingError, TranscriptionError) as exc:
            meeting.status = MeetingStatus.failed
            meeting.processing_error = str(exc)
            meeting.processing_steps.append("Processamento interrompido")
        return meeting

    def _analyze_placeholder(
        self,
        meeting: Meeting,
        transcript: str,
        transcript_provider: str,
        transcript_model: str,
        transcript_language: str | None,
    ) -> MeetingAnalysis:
        tasks = [
            TaskItem(
                title="Corrigir fluxo de envio de relatorios",
                description=(
                    "Investigar e corrigir o problema no fluxo de envio de relatorios citado pelo cliente."
                ),
                priority=Priority.critical,
                priority_reason=(
                    "O cliente indicou bloqueio operacional e necessidade de resolucao ainda esta semana."
                ),
                owner="A definir",
                due_date="Esta semana",
                source_excerpt="a equipe operacional esta bloqueada",
                source_timestamp="00:00:18",
            ),
            TaskItem(
                title="Melhorar tela de acompanhamento de status",
                description=(
                    "Revisar a tela de acompanhamento para tornar os status mais claros para o cliente."
                ),
                priority=Priority.medium,
                priority_reason="Solicitacao relevante, mas sem bloqueio imediato informado.",
                owner="A definir",
                due_date=None,
                source_excerpt="melhorar a tela de acompanhamento",
                source_timestamp="00:00:32",
            ),
            TaskItem(
                title="Validar requisitos com o time interno",
                description="Confirmar escopo tecnico e retornar ao cliente com prazo estimado.",
                priority=Priority.high,
                priority_reason="E um proximo passo combinado durante a reuniao.",
                owner="A definir",
                due_date="Antes do retorno ao cliente",
                source_excerpt="validar os requisitos com o time interno",
                source_timestamp="00:00:45",
            ),
        ]

        minutes = self._build_minutes(meeting, tasks)
        return MeetingAnalysis(
            transcript=transcript,
            transcript_provider=transcript_provider,
            transcript_model=transcript_model,
            transcript_language=transcript_language,
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
            tasks=tasks,
            risks=[
                "Bloqueio operacional do cliente caso o fluxo de relatorios nao seja corrigido.",
                "Prazo ainda indefinido ate validacao tecnica interna.",
            ],
            open_questions=[
                "Qual e a causa exata do bloqueio no envio de relatorios?",
                "Quem sera o responsavel final por cada tarefa?",
            ],
            minutes_markdown=minutes,
        )

    def _build_minutes(self, meeting: Meeting, tasks: list[TaskItem]) -> str:
        client = meeting.client_name or "Cliente nao informado"
        participants = ", ".join(meeting.participants) if meeting.participants else "Nao informado"
        task_lines = "\n".join(
            f"- [{task.priority.value.upper()}] {task.title}: {task.description}"
            for task in tasks
        )
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
{task_lines}

## Pendencias
- Confirmar responsaveis.
- Confirmar prazo tecnico apos analise interna.
"""
