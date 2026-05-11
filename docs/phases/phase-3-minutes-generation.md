# Fase 3 - Geracao de ata e tarefas com IA

## Resumo em uma frase

Nesta fase, o sistema passou a transformar a transcricao da reuniao em uma ata estruturada com Gemini, incluindo resumo, decisoes, tarefas, prioridades, riscos e pendencias.

## Status

Concluida e validada com Gemini em fluxo real no dia 2026-05-11.

## Para que esta fase existe

A transcricao so transforma fala em texto. Ela ainda nao organiza a reuniao.

Esta fase existe para transformar o texto bruto da reuniao em informacao util:

- ata;
- resumo executivo;
- pontos discutidos;
- decisoes;
- tarefas;
- prioridades;
- responsaveis;
- prazos;
- riscos;
- duvidas abertas.

Essa e uma das fases centrais do produto, porque e aqui que a reuniao vira execucao.

## O que o usuario consegue fazer

O usuario consegue:

- enviar uma reuniao;
- gerar a transcricao;
- gerar uma ata com Gemini;
- ver as tarefas separadas automaticamente;
- revisar prioridades sugeridas;
- ver decisoes e pendencias em secoes separadas;
- usar a ata como base para follow-up com cliente ou equipe.

## O que ja foi entregue

- Criacao da camada `MinutesProvider`.
- Provedor `gemini` como padrao do projeto.
- Provedor `mock` para testes e desenvolvimento sem custo.
- Provedor `openai` mantido como fallback opcional.
- Saida estruturada com JSON Schema.
- Validacao da resposta com Pydantic.
- Geracao dos seguintes campos:
  - resumo executivo;
  - topicos;
  - decisoes;
  - tarefas;
  - prioridade de cada tarefa;
  - justificativa da prioridade;
  - responsavel, quando existir;
  - prazo, quando existir;
  - trecho de origem;
  - timestamp, quando existir;
  - riscos;
  - duvidas abertas;
  - ata em Markdown.
- Pipeline atualizado:
  - preparar audio;
  - transcrever;
  - gerar ata e tarefas;
  - salvar tudo em `MeetingAnalysis`.
- Frontend exibindo provedor e modelo usados na geracao da ata.
- Health check informando provedor/modelo da geracao de ata.
- Falha amigavel quando `GEMINI_API_KEY` nao esta configurada.
- Tratamento amigavel para falhas de conexao com o provedor, evitando erro interno `500`.

## O que acontece por baixo dos panos

1. A Fase 1 prepara o audio.
2. A Fase 2 gera a transcricao.
3. A Fase 3 recebe a transcricao.
4. O backend monta um pedido para o Gemini.
5. O pedido inclui metadados da reuniao e transcricao.
6. A IA deve responder seguindo um JSON Schema.
7. O backend valida a resposta.
8. Se a resposta for valida, ela vira `MeetingAnalysis`.
9. O frontend mostra ata, resumo, tarefas e prioridades.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
MINUTES_PROVIDER=gemini
MINUTES_MODEL=gemini-2.5-flash
MINUTES_MAX_TRANSCRIPT_CHARS=60000
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

O que cada configuracao significa:

- `MINUTES_PROVIDER`: escolhe o provedor. Pode ser `gemini`, `openai` ou `mock`.
- `MINUTES_MODEL`: modelo usado para gerar ata e tarefas.
- `MINUTES_MAX_TRANSCRIPT_CHARS`: limite de caracteres da transcricao enviados ao modelo.
- `GEMINI_API_KEY`: chave necessaria para usar a IA real com Gemini.
- `GEMINI_BASE_URL`: URL base da API Gemini.

## Como testar sem chave real

Use os provedores mock:

```text
TRANSCRIPTION_PROVIDER=mock
MINUTES_PROVIDER=mock
```

Esse modo permite testar o fluxo completo sem chamar servicos externos.

## Como testar com IA real

1. Configure a chave no arquivo `backend/.env`:

```text
GEMINI_API_KEY=sua-chave-aqui
TRANSCRIPTION_PROVIDER=gemini
MINUTES_PROVIDER=gemini
```

2. Reinicie o backend.
3. Envie um arquivo real de reuniao.
4. Clique em gerar ata.
5. Verifique se o status final fica como `completed`.
6. Confira se a transcricao corresponde ao audio.
7. Confira se a ata e as tarefas fazem sentido.

## Validacoes executadas

- Teste automatizado com transcricao mock e ata mock concluindo processamento.
- Teste automatizado com transcricao mock e ata Gemini sem chave retornando erro claro.
- Teste automatizado com Gemini sem chave na transcricao retornando erro claro.
- Teste real com audio WAV contendo fala.
- Teste real pelo contrato HTTP do backend: criar reuniao, enviar upload e processar.
- Chamada real ao Gemini `gemini-2.5-flash` para transcricao.
- Chamada real ao Gemini `gemini-2.5-flash` para geracao de ata.
- Resposta validada por Pydantic antes de salvar.
- Ata real salva com resumo, decisoes, tarefas e prioridades.
- Registro final com status `completed`.
- `ruff check` aprovado.
- `npm run build` aprovado.
- `npm run lint` aprovado.

## Resultado da validacao real

Validacao executada em 2026-05-11.

Entrada usada:

- Reuniao: `Validacao API Fase 2 e 3 com Gemini`.
- Cliente: `Acme`.
- Arquivo: audio WAV de teste com fala sintetica.
- Modo: `audio_only`.
- Provedor de ata: `gemini`.
- Modelo de ata: `gemini-2.5-flash`.

Resultado:

- Status final: `completed`.
- Upload via API: `200`.
- Resumo executivo gerado:

```text
A reuniao com o cliente Acme focou em duas solicitacoes principais: a implementacao de login com Google e a revisao do layout do painel. Foi decidido priorizar o desenvolvimento do login com Google.
```

Tarefas geradas:

| Prioridade | Tarefa | Prazo |
| --- | --- | --- |
| high | Criar login com Google | sexta-feira |
| medium | Revisar layout do painel | Nao informado |

## Resultado atual esperado sem chave

Enquanto `GEMINI_API_KEY` estiver vazia, o sistema deve falhar com uma mensagem clara quando tentar usar IA real.

Mensagem esperada na geracao de ata:

```text
GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env para gerar ata e tarefas com Gemini.
```

Isso e correto para ambientes sem chave. No ambiente local validado, a chave foi configurada e o fluxo real concluiu com sucesso.

## O que ficou fora desta fase

Esta fase ainda nao cria um editor para revisar a ata.

Ficaram fora:

- editor de ata;
- edicao de tarefas;
- exportacao PDF;
- versionamento de ata;
- atribuicao manual de responsaveis;
- envio para ferramentas externas;
- processamento assincrono em fila.

## Referencias tecnicas

- Gemini API - Structured output: `https://ai.google.dev/gemini-api/docs/structured-output`
- Gemini API - Generate content: `https://ai.google.dev/api/generate-content`

## Glossario rapido

- **LLM**: modelo de linguagem usado para interpretar texto e gerar respostas.
- **Gemini**: modelo de IA do Google usado como provedor principal neste projeto.
- **JSON Schema**: contrato que define exatamente o formato esperado da resposta.
- **Saida estruturada**: resposta da IA seguindo um schema.
- **Pydantic**: biblioteca Python usada para validar dados estruturados.
- **Markdown**: formato simples de texto usado para montar a ata.
- **Ata estruturada**: ata separada em campos claros, como resumo, decisoes e tarefas.
