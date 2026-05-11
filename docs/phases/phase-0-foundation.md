# Fase 0 - Fundacao do MVP

## Resumo em uma frase

Nesta fase, criamos a base inicial do produto: backend, frontend, estrutura de pastas, fluxo visual e processamento simulado.

## Status

Concluida.

## Para que esta fase existe

Antes de implementar transcricao, IA e processamento real, o projeto precisava de uma estrutura inicial funcionando.

O objetivo foi criar uma primeira versao navegavel do app, com as principais partes do fluxo:

- criar reuniao;
- confirmar consentimento;
- enviar arquivo;
- iniciar processamento;
- ver uma ata gerada;
- ver tarefas priorizadas.

Mesmo com processamento simulado, essa fase ajudou a validar se a experiencia principal fazia sentido.

## O que o usuario consegue fazer

O usuario consegue:

- acessar o app no navegador;
- criar uma reuniao;
- informar cliente e participantes;
- confirmar o aviso de consentimento;
- enviar um arquivo;
- clicar em gerar ata;
- ver um resultado simulado de ata;
- ver tarefas simuladas com prioridade.

## O que foi entregue

- Estrutura inicial do projeto.
- Pasta `backend` com FastAPI.
- Pasta `frontend` com React, TypeScript e Vite.
- Configuracao inicial de Tailwind CSS.
- API para:
  - criar reunioes;
  - listar reunioes;
  - buscar uma reuniao;
  - fazer upload;
  - iniciar processamento.
- Armazenamento local simples em JSON.
- Tela inicial do MVP.
- Fluxo de consentimento antes do processamento.
- Processamento simulado.
- Geracao simulada de:
  - transcricao;
  - resumo;
  - ata;
  - tarefas;
  - prioridades;
  - decisoes;
  - riscos;
  - pendencias.
- README inicial com instrucoes para rodar o projeto.

## O que acontece por baixo dos panos

1. O usuario cria uma reuniao no frontend.
2. O frontend envia os dados para a API FastAPI.
3. O backend salva a reuniao em um arquivo JSON local.
4. O usuario envia um arquivo.
5. O backend salva o arquivo em uma pasta local.
6. O usuario pede para processar.
7. O backend gera uma resposta simulada.
8. O frontend mostra a ata e as tarefas.

## Como testar manualmente

1. Suba o backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Suba o frontend:

```powershell
cd frontend
npm.cmd run dev
```

3. Abra:

```text
http://127.0.0.1:5173
```

4. Crie uma reuniao.
5. Confirme o consentimento.
6. Envie um arquivo.
7. Gere a ata.

## Validacoes executadas

- Teste automatizado basico da API.
- Build do frontend.
- Verificacao de tipos do frontend.
- Verificacao visual basica no navegador.

## O que ficou fora desta fase

- Validacao real de audio e video.
- FFmpeg e FFprobe.
- Transcricao real.
- IA real para gerar ata.
- Banco de dados real.
- Login.
- Exportacao PDF.
- Processamento assincrono.
- Instalavel desktop ou mobile.

## Glossario rapido

- **MVP**: primeira versao util do produto, com foco no valor principal.
- **Backend**: parte do sistema que processa dados e fornece API.
- **Frontend**: interface visual usada pelo usuario.
- **API**: ponte de comunicacao entre frontend e backend.
- **Processamento simulado**: resposta falsa ou fixa usada enquanto a integracao real ainda nao existe.
