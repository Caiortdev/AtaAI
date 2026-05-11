# Fase 2 - Transcricao real

## Resumo em uma frase

Nesta fase, o sistema passou a ter uma camada real de transcricao com Gemini, capaz de enviar o audio preparado para a IA e receber o texto falado na reuniao.

## Status

Concluida e validada com Gemini em fluxo real no dia 2026-05-11.

## Para que esta fase existe

Depois que a Fase 1 prepara o audio da reuniao, o proximo passo e transformar a fala em texto.

Essa transcricao e a base para todo o resto do produto:

- gerar ata;
- identificar tarefas;
- entender pedidos do cliente;
- detectar prazos;
- apontar decisoes;
- criar resumo;
- permitir revisao humana.

Sem uma boa transcricao, a ata fica fragil.

## O que o usuario consegue fazer

O usuario consegue:

- enviar audio ou video;
- deixar o sistema preparar o audio;
- transcrever a fala da reuniao com Gemini;
- ver a transcricao completa no frontend;
- saber qual provedor e modelo foram usados;
- usar a transcricao como base para a ata.

## O que ja foi entregue

- Criacao da camada `TranscriptionProvider`.
- Provedor `gemini` como padrao do projeto.
- Provedor `mock` para testes e desenvolvimento sem custo.
- Provedor `openai` mantido como fallback opcional.
- Configuracao de:
  - provedor;
  - modelo;
  - idioma;
  - prompt de transcricao;
  - tamanho maximo de arquivo para envio;
  - duracao dos trechos quando o audio precisa ser dividido.
- Segmentacao automatica de audio quando o arquivo for maior que o limite configurado.
- Envio do audio em WAV para o Gemini usando `generateContent`.
- Resposta estruturada em JSON com o campo `text`.
- Pipeline atualizado:
  - preparar audio;
  - transcrever audio;
  - salvar transcricao;
  - gerar ata e tarefas.
- Health check informando:
  - provedor de transcricao;
  - modelo;
  - se a chave real esta configurada.
- Frontend exibindo:
  - transcricao completa;
  - provedor usado;
  - modelo usado.
- Mensagem clara quando `GEMINI_API_KEY` nao esta configurada.
- Tratamento amigavel para falhas de conexao com o provedor, evitando erro interno `500`.

## O que acontece por baixo dos panos

1. O usuario envia uma reuniao.
2. A Fase 1 prepara um arquivo WAV mono 16kHz.
3. A Fase 2 verifica qual provedor de transcricao esta configurado.
4. Se o arquivo for pequeno, ele e enviado inteiro para transcricao.
5. Se o arquivo for grande, ele e dividido em partes menores.
6. Cada parte e enviada ao Gemini.
7. O sistema junta os textos retornados.
8. A transcricao final e salva dentro da analise da reuniao.
9. A ata e as tarefas usam essa transcricao como entrada.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
TRANSCRIPTION_PROVIDER=gemini
TRANSCRIPTION_MODEL=gemini-2.5-flash
TRANSCRIPTION_LANGUAGE=pt
TRANSCRIPTION_MAX_FILE_BYTES=18874368
TRANSCRIPTION_CHUNK_SECONDS=600
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

O que cada configuracao significa:

- `TRANSCRIPTION_PROVIDER`: escolhe o provedor. Pode ser `gemini`, `openai` ou `mock`.
- `TRANSCRIPTION_MODEL`: modelo usado para transcrever.
- `TRANSCRIPTION_LANGUAGE`: idioma esperado da reuniao.
- `TRANSCRIPTION_MAX_FILE_BYTES`: tamanho maximo de cada trecho enviado ao provedor.
- `TRANSCRIPTION_CHUNK_SECONDS`: tamanho de cada trecho quando o audio precisa ser dividido.
- `GEMINI_API_KEY`: chave necessaria para usar transcricao real com Gemini.
- `GEMINI_BASE_URL`: URL base da API Gemini.

## Como testar sem chave real

Use o provedor mock:

```text
TRANSCRIPTION_PROVIDER=mock
```

Esse modo nao chama servico externo. Ele serve para testar o fluxo do app sem gastar credito e sem depender de internet.

## Como testar com transcricao real

1. Configure a chave no arquivo `backend/.env`:

```text
GEMINI_API_KEY=sua-chave-aqui
TRANSCRIPTION_PROVIDER=gemini
```

2. Reinicie o backend.
3. Envie um arquivo real de reuniao.
4. Clique em gerar ata.
5. Verifique se o status final fica como `completed`.
6. Abra a secao de transcricao no frontend.
7. Confirme se o texto retornado corresponde ao audio.

## Validacoes executadas

- Teste automatizado com provedor `mock` concluindo processamento.
- Teste automatizado com provedor `gemini` sem chave retornando erro claro.
- Teste real com audio WAV contendo fala.
- Teste real pelo contrato HTTP do backend: criar reuniao, enviar upload e processar.
- Preparacao real do audio via FFmpeg para WAV mono 16kHz.
- Chamada real ao Gemini `gemini-2.5-flash`.
- Transcricao real salva na analise da reuniao.
- Registro final com status `completed`.
- Teste de build do frontend.
- Teste de tipos do frontend.
- Verificacao de lint do backend.
- Verificacao visual basica da interface no navegador.

## Resultado da validacao real

Validacao executada em 2026-05-11.

Entrada usada:

- Reuniao: `Validacao API Fase 2 e 3 com Gemini`.
- Cliente: `Acme`.
- Arquivo: audio WAV de teste com fala sintetica.
- Modo: `audio_only`.
- Provedor: `gemini`.
- Modelo: `gemini-2.5-flash`.

Resultado:

- Status final: `completed`.
- Upload via API: `200`.
- Etapas registradas:
  - `Arquivo recebido`;
  - `Validando midia com FFprobe`;
  - `Audio preparado em WAV mono 16k`;
  - `Transcricao gerada por gemini/gemini-2.5-flash`;
  - `Ata e tarefas geradas por gemini/gemini-2.5-flash`.

Trecho da transcricao real retornada:

```text
Reuniao com cliente Acme. O cliente pediu criar login com Google com prioridade alta para entregar sexta-feira. Tambem pediu revisar o layout do painel com prioridade media. A decisao foi iniciar pelo login com Google.
```

## Resultado atual esperado sem chave

Enquanto `GEMINI_API_KEY` estiver vazia, o sistema deve:

1. aceitar o upload;
2. preparar o audio com FFmpeg;
3. tentar iniciar a transcricao;
4. parar com status `failed`;
5. mostrar uma mensagem clara pedindo a chave.

Mensagem esperada:

```text
GEMINI_API_KEY nao esta configurada. Configure a chave no backend/.env para usar transcricao real com Gemini.
```

Isso e correto para ambientes sem chave. No ambiente local validado, a chave foi configurada e o fluxo real concluiu com sucesso.

## O que ficou fora desta fase

Esta fase nao cria uma ata inteligente real. A ata ainda depende da fase seguinte.

Ficaram fora:

- analise real por LLM;
- identificacao real de tarefas com IA;
- resumo real baseado em prompt;
- diarizacao, ou seja, separar quem falou cada trecho;
- timestamps detalhados por frase;
- processamento assincrono em fila.

## Referencia tecnica

- Gemini API - Audio understanding: `https://ai.google.dev/gemini-api/docs/audio`
- Gemini API - Generate content: `https://ai.google.dev/api/generate-content`

## Glossario rapido

- **Transcricao**: transformar fala em texto.
- **Gemini**: modelo de IA do Google usado como provedor principal neste projeto.
- **Provedor**: servico usado para executar a transcricao.
- **Modelo**: IA especifica usada pelo provedor.
- **Mock**: modo de teste que simula uma resposta sem chamar servico real.
- **Chunk**: pedaco menor de um arquivo grande.
- **Prompt de transcricao**: instrucao enviada ao modelo para melhorar a forma como ele transcreve.
