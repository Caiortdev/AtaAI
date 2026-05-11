# Fase 3 - Geracao de ata e tarefas com IA

## Resumo em uma frase

Nesta fase, o sistema passou a transformar a transcricao da reuniao em uma ata estruturada, com resumo, decisoes, tarefas, prioridades, riscos e pendencias.

## Status

Implementada no codigo, mas pendente de validacao real com OpenAI porque falta configurar `OPENAI_API_KEY`.

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

## O que o usuario conseguira fazer quando a chave estiver configurada

O usuario conseguira:

- enviar uma reuniao;
- gerar a transcricao;
- gerar uma ata com IA real;
- ver as tarefas separadas automaticamente;
- revisar prioridades sugeridas;
- ver decisoes e pendencias em secoes separadas;
- usar a ata como base para follow-up com cliente ou equipe.

## O que ja foi entregue

- Criacao da camada `MinutesProvider`.
- Provedor `openai` para gerar ata real.
- Provedor `mock` para testes e desenvolvimento sem custo.
- Saida estruturada com JSON Schema.
- Validacao da resposta com Pydantic.
- Geração dos seguintes campos:
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
- Falha amigavel quando `OPENAI_API_KEY` nao esta configurada.

## O que acontece por baixo dos panos

1. A Fase 1 prepara o audio.
2. A Fase 2 gera a transcricao.
3. A Fase 3 recebe a transcricao.
4. O backend monta um pedido para o modelo de IA.
5. O pedido inclui metadados da reuniao e transcricao.
6. A IA deve responder seguindo um JSON Schema.
7. O backend valida a resposta.
8. Se a resposta for valida, ela vira `MeetingAnalysis`.
9. O frontend mostra ata, resumo, tarefas e prioridades.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
MINUTES_PROVIDER=openai
MINUTES_MODEL=gpt-4o-mini
MINUTES_MAX_TRANSCRIPT_CHARS=60000
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

O que cada configuracao significa:

- `MINUTES_PROVIDER`: escolhe o provedor. Pode ser `openai` ou `mock`.
- `MINUTES_MODEL`: modelo usado para gerar ata e tarefas.
- `MINUTES_MAX_TRANSCRIPT_CHARS`: limite de caracteres da transcricao enviados ao modelo.
- `OPENAI_API_KEY`: chave necessaria para usar a IA real.
- `OPENAI_BASE_URL`: URL base da API usada pelo provedor.

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
OPENAI_API_KEY=sua-chave-aqui
TRANSCRIPTION_PROVIDER=openai
MINUTES_PROVIDER=openai
```

2. Reinicie o backend.
3. Envie um arquivo real de reuniao.
4. Clique em gerar ata.
5. Verifique se o status final fica como `completed`.
6. Confira se a transcricao corresponde ao audio.
7. Confira se a ata e as tarefas fazem sentido.

## Validacoes executadas

- Teste automatizado com transcricao mock e ata mock concluindo processamento.
- Teste automatizado com transcricao mock e ata OpenAI sem chave retornando erro claro.
- Teste automatizado com OpenAI sem chave na transcricao retornando erro claro.
- `ruff check` aprovado.
- `npm run build` aprovado.
- `npm run lint` aprovado.

## Resultado atual esperado sem chave

Enquanto `OPENAI_API_KEY` estiver vazia, o sistema deve falhar com uma mensagem clara quando tentar usar IA real.

Mensagem esperada na geracao de ata:

```text
OPENAI_API_KEY nao esta configurada. Configure a chave no backend/.env para gerar ata e tarefas com IA real.
```

Isso e correto. Significa que a integracao esta pronta no codigo, mas nao pode chamar o provedor real.

## O que falta para concluir operacionalmente

- Configurar `OPENAI_API_KEY`.
- Reiniciar a API.
- Rodar o fluxo com uma reuniao real.
- Confirmar que a transcricao real foi gerada.
- Confirmar que a ata real foi gerada.
- Confirmar que tarefas e prioridades fazem sentido.
- Marcar a fase como concluida e validada.

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

- OpenAI Structured Outputs: `https://platform.openai.com/docs/guides/structured-outputs`
- OpenAI Responses API: `https://platform.openai.com/docs/api-reference/responses`

## Glossario rapido

- **LLM**: modelo de linguagem usado para interpretar texto e gerar respostas.
- **JSON Schema**: contrato que define exatamente o formato esperado da resposta.
- **Structured Outputs**: recurso que faz o modelo responder seguindo um schema.
- **Pydantic**: biblioteca Python usada para validar dados estruturados.
- **Markdown**: formato simples de texto usado para montar a ata.
- **Ata estruturada**: ata separada em campos claros, como resumo, decisoes e tarefas.
