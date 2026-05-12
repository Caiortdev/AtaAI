# AtaAI

AtaAI transforma gravacoes e anotacoes de reunioes em atas organizadas, com decisoes, tarefas e proximos passos reunidos em um so lugar.

MVP para capturar reunioes com clientes, processar audio/video, gerar transcricao, ata estruturada e tarefas priorizadas.

## Stack inicial

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query e Zustand.
- Desktop futuro: Tauri usando o mesmo frontend React.
- Mobile inicial: PWA; empacotamento futuro com Capacitor.
- Backend: Python, FastAPI e Pydantic.
- Processamento: fila local no MVP; Redis/Celery distribuido no futuro.
- Banco atual: SQLite.
- Banco arquitetado para migracao: PostgreSQL.
- Autenticacao atual: cadastro/login local com sessao Bearer armazenada no SQLite.
- Armazenamento futuro: storage S3-compatible.

## Estrutura

```text
backend/   API FastAPI e pipeline de processamento
frontend/  App React do MVP
docs/      Documentacao organizada do projeto
```

## Documentacao por fases

Os documentos principais ficam em [docs/README.md](docs/README.md).

Eles explicam o projeto em linguagem simples, com status, objetivo, entregas, forma de testar, stack, produto e proximos passos de cada fase.

## Como rodar em desenvolvimento

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

O frontend espera a API em `http://127.0.0.1:8000`.

## Estado atual

Esta primeira base ja inclui:

- criacao e listagem de reunioes;
- upload de arquivo;
- aviso de consentimento;
- validacao de formato e tamanho do arquivo;
- preparacao real de audio via FFmpeg/FFprobe quando os binarios estiverem configurados;
- falha amigavel quando FFmpeg/FFprobe nao estao disponiveis;
- transcricao real plugavel via Gemini quando `GEMINI_API_KEY` estiver configurada;
- transcricao mock para testes automatizados;
- geracao de ata/tarefas plugavel via Gemini quando `GEMINI_API_KEY` estiver configurada;
- geracao mock de ata/tarefas para testes automatizados;
- revisao humana da ata e das tarefas;
- exportacao da ata revisada em PDF;
- processamento em fila local para nao travar a requisicao enquanto a IA trabalha;
- persistencia em SQLite com camada preparada para migrar para PostgreSQL;
- cadastro, login e isolamento das reunioes por usuario;
- tela inicial do MVP em React.

Redis/Celery distribuido, PostgreSQL ativo, organizacoes/permissoes avancadas e storage externo serao adicionados nas proximas etapas.

## Geracao de ata e tarefas

O backend suporta geracao de ata por provedor configuravel:

```text
MINUTES_PROVIDER=gemini
MINUTES_MODEL=gemini-2.5-flash
GEMINI_API_KEY=sua-chave
```

Para testes automatizados, use `MINUTES_PROVIDER=mock`. Para geracao real de ata e tarefas, configure `GEMINI_API_KEY`.

## Dependencia de midia

Para a Fase 1 funcionar com audio/video real, instale FFmpeg e FFprobe ou configure os caminhos no `.env` do backend:

```powershell
npm.cmd install --prefix tools
```

O backend detecta automaticamente os binarios instalados em `tools/node_modules`. Se preferir apontar manualmente:

```text
FFMPEG_BINARY=C:\caminho\para\ffmpeg.exe
FFPROBE_BINARY=C:\caminho\para\ffprobe.exe
```

Sem essas ferramentas, o app aceita uploads validos, mas o processamento fica com status `failed` e mostra uma mensagem orientando a configuracao.

## Transcricao

O backend suporta transcricao por provedor configuravel:

```text
TRANSCRIPTION_PROVIDER=gemini
TRANSCRIPTION_MODEL=gemini-2.5-flash
TRANSCRIPTION_LANGUAGE=pt
GEMINI_API_KEY=sua-chave
```

Para testes automatizados, use `TRANSCRIPTION_PROVIDER=mock`. Para transcricao real, configure `GEMINI_API_KEY`.
