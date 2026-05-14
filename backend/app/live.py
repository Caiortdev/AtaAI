import asyncio
import base64
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from app.config import (
    GEMINI_BASE_URL,
    GEMINI_LIVE_MODEL,
    LIVE_DRAFT_INTERVAL_SECONDS,
    LIVE_TRANSCRIPTION_ENABLED,
    MINUTES_MAX_TRANSCRIPT_CHARS,
    TRANSCRIPTION_LANGUAGE,
    Settings,
)
from app.domain import LiveSessionState


class LiveSessionError(Exception):
    pass


class LiveSession:
    MAX_RECONNECT_ATTEMPTS = 3
    RECONNECT_BASE_DELAY = 2.0

    def __init__(self, meeting_id: str, settings: Settings) -> None:
        self.meeting_id = meeting_id
        self.settings = settings
        self.state = LiveSessionState.idle
        self._transcript_parts: list[str] = []
        self._draft_markdown: str = ""
        self._last_draft_time: float = 0.0
        self._chunk_index: int = 0
        self._chunks_dir = settings.storage_dir / "live" / meeting_id
        self._ws_connection: object | None = None
        self._receive_task: asyncio.Task | None = None
        self._draft_task: asyncio.Task | None = None
        self._on_transcript: list = []
        self._on_draft: list = []
        self._on_status: list = []
        self._on_error: list = []
        self._reconnect_count: int = 0

    @property
    def transcript(self) -> str:
        return "\n".join(self._transcript_parts)

    @property
    def draft(self) -> str:
        return self._draft_markdown

    def on_transcript(self, callback) -> None:
        self._on_transcript.append(callback)

    def on_draft(self, callback) -> None:
        self._on_draft.append(callback)

    def on_status(self, callback) -> None:
        self._on_status.append(callback)

    def on_error(self, callback) -> None:
        self._on_error.append(callback)

    async def start(self) -> None:
        if not self.settings.gemini_api_key:
            raise LiveSessionError(
                "GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env "
                "para usar gravacao ao vivo."
            )
        if not LIVE_TRANSCRIPTION_ENABLED:
            raise LiveSessionError("Gravacao ao vivo esta desabilitada na configuracao.")

        self._chunks_dir.mkdir(parents=True, exist_ok=True)
        self.state = LiveSessionState.recording
        self._last_draft_time = time.time()
        await self._emit_status()
        await self._connect_gemini()

    async def send_audio(self, audio_bytes: bytes) -> None:
        if self.state != LiveSessionState.recording:
            return

        self._save_chunk(audio_bytes)

        if self._ws_connection is not None:
            await self._send_audio_to_gemini(audio_bytes)

    async def pause(self) -> None:
        if self.state != LiveSessionState.recording:
            return
        self.state = LiveSessionState.paused
        await self._emit_status()

    async def resume(self) -> None:
        if self.state != LiveSessionState.paused:
            return
        self.state = LiveSessionState.recording
        await self._emit_status()

    async def stop(self) -> None:
        self.state = LiveSessionState.finalizing
        await self._emit_status()
        await self._disconnect_gemini()
        if self._draft_task and not self._draft_task.done():
            self._draft_task.cancel()
            try:
                await self._draft_task
            except asyncio.CancelledError:
                pass
        self.state = LiveSessionState.done
        await self._emit_status()

    def get_chunks_dir(self) -> Path:
        return self._chunks_dir

    def _save_chunk(self, audio_bytes: bytes) -> None:
        chunk_path = self._chunks_dir / f"chunk-{self._chunk_index:05d}.webm"
        chunk_path.write_bytes(audio_bytes)
        self._chunk_index += 1

    async def _connect_gemini(self) -> None:
        try:
            import websockets
        except ImportError:
            raise LiveSessionError(
                "Pacote 'websockets' nao esta instalado. "
                "Execute: pip install websockets"
            )

        model = GEMINI_LIVE_MODEL
        api_key = self.settings.gemini_api_key
        ws_url = (
            f"wss://generativelanguage.googleapis.com/ws/"
            f"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            f"?key={api_key}"
        )

        try:
            self._ws_connection = await websockets.connect(ws_url)
        except Exception as exc:
            raise LiveSessionError(
                f"Falha ao conectar com Gemini Live API: {exc}"
            ) from exc

        setup_message = {
            "setup": {
                "model": f"models/{model}",
                "generationConfig": {
                    "responseModalities": ["TEXT"],
                    "speechConfig": {
                        "languageCode": TRANSCRIPTION_LANGUAGE,
                    },
                },
                "systemInstruction": {
                    "parts": [
                        {
                            "text": (
                                "Voce e um transcritor de reunioes. Transcreva fielmente "
                                "tudo que ouvir em portugues do Brasil. Preserve nomes, "
                                "termos tecnicos, decisoes e prazos. Retorne apenas o texto "
                                "transcrito, sem comentarios ou formatacao adicional."
                            )
                        }
                    ]
                },
            }
        }
        await self._ws_connection.send(json.dumps(setup_message))

        try:
            setup_response = await asyncio.wait_for(
                self._ws_connection.recv(), timeout=10.0
            )
            response_data = json.loads(setup_response)
            if "setupComplete" not in response_data:
                raise LiveSessionError(
                    f"Gemini Live API nao confirmou setup: {response_data}"
                )
        except asyncio.TimeoutError:
            raise LiveSessionError("Timeout aguardando confirmacao de setup do Gemini Live.")

        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _send_audio_to_gemini(self, audio_bytes: bytes) -> None:
        if self._ws_connection is None:
            return

        message = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": "audio/webm",
                        "data": base64.b64encode(audio_bytes).decode("ascii"),
                    }
                ]
            }
        }
        try:
            await self._ws_connection.send(json.dumps(message))
        except Exception as exc:
            await self._emit_error(f"Falha ao enviar audio para Gemini: {exc}")

    async def _receive_loop(self) -> None:
        if self._ws_connection is None:
            return

        try:
            async for raw_message in self._ws_connection:
                if self.state in (LiveSessionState.finalizing, LiveSessionState.done):
                    break

                try:
                    data = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue

                text = self._extract_text(data)
                if text:
                    self._transcript_parts.append(text)
                    await self._emit_transcript(text, is_final=True)
                    await self._maybe_generate_draft()

        except Exception as exc:
            if self.state in (LiveSessionState.finalizing, LiveSessionState.done):
                return
            await self._emit_error(f"Conexao com Gemini Live perdida: {exc}")
            await self._attempt_reconnect()

    def _extract_text(self, data: dict) -> str | None:
        server_content = data.get("serverContent")
        if not server_content:
            return None

        parts = server_content.get("modelTurn", {}).get("parts", [])
        texts = []
        for part in parts:
            text = part.get("text")
            if text and text.strip():
                texts.append(text.strip())

        return " ".join(texts) if texts else None

    async def _maybe_generate_draft(self) -> None:
        now = time.time()
        elapsed = now - self._last_draft_time
        if elapsed < LIVE_DRAFT_INTERVAL_SECONDS:
            return

        self._last_draft_time = now
        transcript = self.transcript
        if not transcript.strip():
            return

        if self._draft_task and not self._draft_task.done():
            return

        self._draft_task = asyncio.create_task(self._generate_draft(transcript))

    async def _generate_draft(self, transcript: str) -> None:
        try:
            draft = await self._call_gemini_draft(transcript)
            self._draft_markdown = draft
            await self._emit_draft(draft)
        except Exception as exc:
            await self._emit_error(f"Erro ao gerar rascunho: {exc}")

    async def _call_gemini_draft(self, transcript: str) -> str:
        prompt = (
            "Com base na transcricao parcial abaixo de uma reuniao em andamento, "
            "gere um rascunho curto da ata ate o momento. Inclua: pontos principais "
            "discutidos, decisoes tomadas e tarefas identificadas ate agora. "
            "Use formato markdown simples. Seja conciso.\n\n"
            f"Transcricao parcial:\n{transcript[:MINUTES_MAX_TRANSCRIPT_CHARS]}"
        )

        url = (
            f"{GEMINI_BASE_URL}/models/"
            f"{GEMINI_LIVE_MODEL}:generateContent"
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.settings.gemini_api_key,
                },
                json=payload,
                timeout=30,
            )

        if response.status_code >= 400:
            raise LiveSessionError(f"Gemini retornou erro ao gerar rascunho: {response.text[:300]}")

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        return "\n".join(texts)

    async def _attempt_reconnect(self) -> None:
        if self.state in (LiveSessionState.finalizing, LiveSessionState.done):
            return

        if self._ws_connection is not None:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

        while self._reconnect_count < self.MAX_RECONNECT_ATTEMPTS:
            self._reconnect_count += 1
            delay = self.RECONNECT_BASE_DELAY * (2 ** (self._reconnect_count - 1))
            await self._emit_error(
                f"Tentando reconectar ({self._reconnect_count}/{self.MAX_RECONNECT_ATTEMPTS}) "
                f"em {delay:.0f}s..."
            )
            await asyncio.sleep(delay)

            if self.state in (LiveSessionState.finalizing, LiveSessionState.done):
                return

            try:
                await self._connect_gemini()
                self._reconnect_count = 0
                await self._emit_error("Reconexao bem-sucedida.")
                return
            except LiveSessionError as exc:
                await self._emit_error(f"Falha na reconexao: {exc}")

        await self._emit_error(
            "Nao foi possivel reconectar ao Gemini Live apos "
            f"{self.MAX_RECONNECT_ATTEMPTS} tentativas. Sessao encerrada."
        )
        self.state = LiveSessionState.done
        await self._emit_status()

    async def _disconnect_gemini(self) -> None:
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws_connection is not None:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

    async def _emit_transcript(self, text: str, is_final: bool) -> None:
        for callback in self._on_transcript:
            await callback(text, is_final)

    async def _emit_draft(self, markdown: str) -> None:
        for callback in self._on_draft:
            await callback(markdown)

    async def _emit_status(self) -> None:
        for callback in self._on_status:
            await callback(self.state)

    async def _emit_error(self, message: str) -> None:
        for callback in self._on_error:
            await callback(message)
