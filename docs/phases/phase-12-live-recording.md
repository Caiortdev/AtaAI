# Fase 12 - Reuniao ao vivo e rascunho em tempo real

## Resumo em uma frase

Nesta fase, o sistema passou a permitir gravacao direta do microfone no navegador, transcricao em tempo real via Gemini Live API, e geracao automatica de rascunhos parciais da ata enquanto a reuniao acontece.

## Status

Em desenvolvimento.

## Para que esta fase existe

Ate agora, o usuario precisava gravar a reuniao externamente, salvar o arquivo, e depois enviar para processamento. Isso cria atrito e atraso entre a reuniao e a ata.

Com esta fase, o usuario pode:

- gravar diretamente do microfone no navegador ou desktop;
- ver a transcricao aparecendo em tempo real;
- receber rascunhos parciais da ata a cada 30 segundos;
- pausar e retomar a gravacao;
- ao finalizar, ter a ata completa gerada automaticamente.

## O que o usuario consegue fazer

- Criar uma reuniao e clicar em "Iniciar gravacao ao vivo".
- Falar no microfone e ver o texto transcrito aparecendo na tela.
- Ver um rascunho parcial da ata sendo atualizado automaticamente.
- Pausar a gravacao quando necessario e retomar depois.
- Finalizar a gravacao e aguardar a ata completa ser gerada.
- Continuar usando o fluxo de upload de arquivo normalmente.

## O que foi entregue

- Configuracoes novas no backend:
  - `LIVE_TRANSCRIPTION_ENABLED`: habilita/desabilita gravacao ao vivo.
  - `LIVE_DRAFT_INTERVAL_SECONDS`: intervalo para gerar rascunho parcial.
  - `GEMINI_LIVE_MODEL`: modelo usado na transcricao ao vivo.
- Novo status de reuniao: `recording`.
- Novo enum `LiveSessionState`: idle, recording, paused, finalizing, done.
- Modulo `backend/app/live.py`:
  - Classe `LiveSession` gerenciando conexao com Gemini Live API.
  - Streaming bidirecional de audio via WebSocket.
  - Acumulacao de transcricao parcial.
  - Geracao automatica de rascunho a cada 30s.
  - Salvamento de chunks de audio em disco.
- Endpoint WebSocket `ws/live/{meeting_id}` no backend.
- Protocolo de mensagens JSON sobre WebSocket:
  - Client envia: audio (base64), pause, resume, stop.
  - Server envia: transcript, draft, status, error.
- Concatenacao de chunks de audio ao vivo em MP3 via FFmpeg.
- Finalizacao automatica: ao parar a gravacao, o audio e consolidado e o processamento completo e disparado.
- Frontend:
  - Tipos `LiveSessionState` e `LiveMessage`.
  - Helper `createLiveWebSocket` para conexao autenticada.
  - Hook `useLiveSession` gerenciando MediaRecorder + WebSocket.
  - Componente `LiveRecorder` com UI completa.
  - Integracao na tela principal como alternativa ao upload.

## O que acontece por baixo dos panos

1. O usuario clica em "Iniciar gravacao ao vivo".
2. O navegador pede permissao de microfone.
3. O frontend abre um WebSocket autenticado para o backend.
4. O backend abre uma conexao WebSocket com a Gemini Live API.
5. O MediaRecorder captura audio em chunks de 1 segundo (WebM/Opus).
6. Cada chunk e enviado em base64 para o backend via WebSocket.
7. O backend repassa o audio para o Gemini Live.
8. O Gemini retorna texto transcrito em tempo real.
9. O backend envia a transcricao parcial para o frontend.
10. A cada 30 segundos de nova transcricao, o backend gera um rascunho parcial da ata.
11. Ao finalizar, o backend concatena todos os chunks em MP3 mono 16kHz.
12. O processamento completo (transcricao final + ata + tarefas) e disparado.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
LIVE_TRANSCRIPTION_ENABLED=true
LIVE_DRAFT_INTERVAL_SECONDS=30
GEMINI_LIVE_MODEL=gemini-2.5-flash
GEMINI_API_KEY=sua-chave
```

## Dependencias adicionadas

- `websockets>=13.0` no backend (para conexao com Gemini Live API).

## Como testar

1. Configure `GEMINI_API_KEY` no `backend/.env`.
2. Instale a dependencia: `pip install websockets`.
3. Suba o backend: `python -m uvicorn app.main:app --reload --port 8000`.
4. Suba o frontend: `npm run dev`.
5. Abra o app, crie uma reuniao.
6. Na secao de processamento, clique em "Iniciar gravacao ao vivo".
7. Permita acesso ao microfone.
8. Fale e observe a transcricao aparecendo.
9. Aguarde ~30s para ver o rascunho parcial.
10. Teste pausar e retomar.
11. Clique em "Finalizar gravacao".
12. Aguarde o processamento completo e verifique a ata gerada.

## O que ficou fora desta fase

- Diarizacao (separar quem falou cada trecho).
- Timestamps detalhados por frase na transcricao ao vivo.
- Indicador visual de nivel de audio/volume.
- Gravacao de audio do sistema (apenas microfone).
- Modo offline para gravacao ao vivo.

## Referencia tecnica

- Gemini Live API: `https://ai.google.dev/gemini-api/docs/live`
- MediaRecorder API: `https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder`
- WebSocket FastAPI: `https://fastapi.tiangolo.com/advanced/websockets/`

## Glossario rapido

- **Gemini Live API**: API de streaming bidirecional do Google para interacao em tempo real.
- **MediaRecorder**: API do navegador para capturar audio/video do microfone.
- **WebSocket**: protocolo de comunicacao bidirecional persistente.
- **Chunk**: pedaco de audio capturado a cada segundo.
- **Rascunho parcial**: versao preliminar da ata gerada durante a reuniao.
