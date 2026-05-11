# Fase 2 - Transcricao real

## Resumo em uma frase

Nesta fase, o sistema passou a ter uma camada real de transcricao, capaz de enviar o audio preparado para um provedor externo e receber o texto falado na reuniao.

## Status

Implementada no codigo, mas ainda pendente de validacao real com OpenAI porque falta configurar `OPENAI_API_KEY`.

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

## O que o usuario conseguira fazer quando a chave estiver configurada

O usuario conseguira:

- enviar audio ou video;
- deixar o sistema preparar o audio;
- transcrever a fala da reuniao;
- ver a transcricao completa no frontend;
- saber qual provedor e modelo foram usados;
- usar a transcricao como base para a ata.

## O que ja foi entregue

- Criacao da camada `TranscriptionProvider`.
- Provedor `openai` para transcricao real.
- Provedor `mock` para testes e desenvolvimento sem custo.
- Configuracao de:
  - provedor;
  - modelo;
  - idioma;
  - prompt de transcricao;
  - tamanho maximo de arquivo para envio;
  - duracao dos trechos quando o audio precisa ser dividido.
- Segmentacao automatica de audio quando o arquivo for maior que o limite configurado.
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
- Mensagem clara quando `OPENAI_API_KEY` nao esta configurada.

## O que acontece por baixo dos panos

1. O usuario envia uma reuniao.
2. A Fase 1 prepara um arquivo WAV mono 16kHz.
3. A Fase 2 verifica qual provedor de transcricao esta configurado.
4. Se o arquivo for pequeno, ele e enviado inteiro para transcricao.
5. Se o arquivo for grande, ele e dividido em partes menores.
6. Cada parte e enviada ao provedor.
7. O sistema junta os textos retornados.
8. A transcricao final e salva dentro da analise da reuniao.
9. A ata e as tarefas usam essa transcricao como entrada.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
TRANSCRIPTION_PROVIDER=openai
TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
TRANSCRIPTION_LANGUAGE=pt
TRANSCRIPTION_MAX_FILE_BYTES=25165824
TRANSCRIPTION_CHUNK_SECONDS=600
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

O que cada configuracao significa:

- `TRANSCRIPTION_PROVIDER`: escolhe o provedor. Pode ser `openai` ou `mock`.
- `TRANSCRIPTION_MODEL`: modelo usado para transcrever.
- `TRANSCRIPTION_LANGUAGE`: idioma esperado da reuniao.
- `TRANSCRIPTION_MAX_FILE_BYTES`: tamanho maximo de cada arquivo enviado ao provedor.
- `TRANSCRIPTION_CHUNK_SECONDS`: tamanho de cada trecho quando o audio precisa ser dividido.
- `OPENAI_API_KEY`: chave necessaria para usar transcricao real da OpenAI.
- `OPENAI_BASE_URL`: URL base da API usada pelo provedor.

## Como testar sem chave real

Use o provedor mock:

```text
TRANSCRIPTION_PROVIDER=mock
```

Esse modo nao chama servico externo. Ele serve para testar o fluxo do app sem gastar credito e sem depender de internet.

## Como testar com transcricao real

1. Configure a chave no arquivo `backend/.env`:

```text
OPENAI_API_KEY=sua-chave-aqui
TRANSCRIPTION_PROVIDER=openai
```

2. Reinicie o backend.
3. Envie um arquivo real de reuniao.
4. Clique em gerar ata.
5. Verifique se o status final fica como `completed`.
6. Abra a secao de transcricao no frontend.
7. Confirme se o texto retornado corresponde ao audio.

## Validacoes executadas

- Teste automatizado com provedor `mock` concluindo processamento.
- Teste automatizado com provedor `openai` sem chave retornando erro claro.
- Teste de build do frontend.
- Teste de tipos do frontend.
- Verificacao de lint do backend.
- Verificacao visual basica da interface no navegador.

## Resultado atual esperado sem chave

Enquanto `OPENAI_API_KEY` estiver vazia, o sistema deve:

1. aceitar o upload;
2. preparar o audio com FFmpeg;
3. tentar iniciar a transcricao;
4. parar com status `failed`;
5. mostrar uma mensagem clara pedindo a chave.

Mensagem esperada:

```text
OPENAI_API_KEY nao esta configurada. Configure a chave no backend/.env para usar transcricao real.
```

Isso e correto. Significa que a fase esta pronta no codigo, mas ainda nao pode chamar o provedor real.

## O que falta para concluir operacionalmente

- Configurar `OPENAI_API_KEY`.
- Reiniciar a API.
- Rodar teste com audio real.
- Confirmar que o provedor retorna uma transcricao real.
- Confirmar que a transcricao aparece no frontend.
- Marcar a fase como concluida e validada.

## O que ficou fora desta fase

Esta fase nao cria uma ata inteligente real. A ata ainda usa uma analise simulada.

Ficaram fora:

- analise real por LLM;
- identificacao real de tarefas com IA;
- resumo real baseado em prompt;
- diarizacao, ou seja, separar quem falou cada trecho;
- timestamps detalhados por frase;
- processamento assincrono em fila.

## Referencia tecnica

- OpenAI Audio Transcriptions: `https://platform.openai.com/docs/api-reference/audio/createTranscription`

## Glossario rapido

- **Transcricao**: transformar fala em texto.
- **Provedor**: servico usado para executar a transcricao.
- **Modelo**: IA especifica usada pelo provedor.
- **Mock**: modo de teste que simula uma resposta sem chamar servico real.
- **Chunk**: pedaco menor de um arquivo grande.
- **Prompt de transcricao**: instrucao enviada ao modelo para melhorar a forma como ele transcreve.
