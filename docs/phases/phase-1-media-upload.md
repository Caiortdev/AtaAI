# Fase 1 - Upload real e preparacao de audio

## Resumo em uma frase

Nesta fase, o sistema passou a aceitar arquivos reais de audio ou video, validar se eles podem ser usados e preparar um audio padronizado para a futura transcricao.

## Status

Concluida e validada localmente.

## Para que esta fase existe

Antes de uma IA conseguir transcrever uma reuniao, o sistema precisa receber um arquivo confiavel. Esse arquivo pode vir como audio, por exemplo `.mp3`, ou como video, por exemplo `.mp4`.

O objetivo desta fase foi garantir que o app consiga:

- receber o arquivo enviado pelo usuario;
- verificar se o formato e aceito;
- identificar se o arquivo e audio ou video;
- descobrir informacoes como duracao e codec;
- extrair o audio quando o arquivo for video;
- gerar um audio padronizado para a proxima fase.

Sem esta fase, a transcricao real seria instavel, porque cada reuniao poderia chegar em um formato diferente.

## O que o usuario consegue fazer agora

O usuario consegue:

- criar uma reuniao;
- confirmar o aviso de consentimento;
- enviar um arquivo de audio ou video;
- ver informacoes basicas do arquivo enviado;
- iniciar o processamento;
- ver se o audio foi preparado com sucesso;
- receber uma mensagem clara se algo impedir o processamento.

## O que foi entregue

- Upload real de arquivos.
- Validacao de arquivo vazio.
- Limite configuravel de tamanho por upload.
- Aceite inicial dos formatos:
  - audio: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.webm`;
  - video: `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`.
- Classificacao automatica entre audio e video.
- Instalacao local de FFmpeg e FFprobe via pacotes npm na pasta `tools`.
- Deteccao automatica dos binarios de FFmpeg e FFprobe:
  - pelo `.env`;
  - pelo PATH do sistema;
  - pela pasta local `tools`.
- Leitura de metadados com FFprobe.
- Validacao configuravel de duracao maxima da reuniao.
- Conversao do audio para MP3 mono 16kHz comprimido usando FFmpeg.
- Remocao do arquivo original apos a preparacao do audio quando FFmpeg/FFprobe estao disponiveis.
- Registro do audio preparado no modelo da reuniao.
- Status `failed` quando algo falha.
- Mensagem clara quando FFmpeg ou FFprobe nao estao disponiveis.
- Frontend exibindo:
  - nome do arquivo;
  - tipo;
  - tamanho;
  - duracao;
  - codec;
  - etapas do processamento;
  - erro, quando existir.

## O que acontece por baixo dos panos

1. O usuario envia um arquivo.
2. O backend confere se o arquivo tem tamanho valido.
3. O backend verifica a extensao do arquivo.
4. O backend recebe o upload em blocos e salva o arquivo original temporariamente em `backend/storage/uploads`.
5. O FFprobe tenta ler duracao, codec e metadados.
6. O FFmpeg gera um arquivo MP3 padronizado e comprimido.
7. O arquivo preparado fica salvo em `backend/storage/prepared`.
8. O sistema remove o arquivo original e registra esse audio preparado na reuniao.
9. A fase seguinte usa esse audio para transcricao.

## Configuracoes importantes

Arquivo: `backend/.env`

```text
MAX_UPLOAD_BYTES=5368709120
MAX_MEDIA_DURATION_SECONDS=10800
FFMPEG_BINARY=ffmpeg
FFPROBE_BINARY=ffprobe
LOCAL_MEDIA_TOOLS_ENABLED=true
```

O que cada configuracao significa:

- `MAX_UPLOAD_BYTES`: tamanho maximo permitido para upload.
- `MAX_MEDIA_DURATION_SECONDS`: duracao maxima permitida para a reuniao.
- `FFMPEG_BINARY`: caminho ou nome do executavel do FFmpeg.
- `FFPROBE_BINARY`: caminho ou nome do executavel do FFprobe.
- `LOCAL_MEDIA_TOOLS_ENABLED`: permite usar os binarios instalados localmente em `tools`.

## Como preparar o ambiente

Para instalar os binarios locais usados por esta fase:

```powershell
npm.cmd install --prefix tools
```

Depois disso, o backend consegue encontrar FFmpeg e FFprobe automaticamente.

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

3. Abra o app:

```text
http://127.0.0.1:5173
```

4. Crie uma reuniao.
5. Envie um arquivo `.mp3`, `.wav` ou `.mp4`.
6. Clique em gerar ata.
7. Verifique se o status final fica como `completed`.
8. Verifique se aparece a informacao de audio preparado.

## Validacao final executada

Foi gerado um video `.mp4` real com trilha de audio usando FFmpeg. Em seguida, o fluxo completo foi testado.

Resultado observado:

```json
{
  "status": "completed",
  "media_kind": "video",
  "extension": ".mp4",
  "duration_seconds": 3.0,
  "codec_name": "h264",
  "prepared_audio": {
    "content_type": "audio/wav",
    "sample_rate_hz": 16000,
    "channels": 1
  },
  "tasks": 3
}
```

## O que ficou fora desta fase

Esta fase nao faz transcricao real da fala. Ela apenas prepara o audio para isso.

Tambem ficaram fora:

- transcricao real;
- analise real por LLM;
- banco PostgreSQL;
- processamento assincrono com Redis/Celery;
- storage S3;
- analise visual do video.

## Glossario rapido

- **FFmpeg**: ferramenta usada para converter audio e video.
- **FFprobe**: ferramenta usada para ler informacoes tecnicas de audio e video.
- **Codec**: formato usado internamente para codificar audio ou video.
- **MP3 mono 16kHz**: formato de audio comprimido e adequado para transcricao de reunioes longas.
- **Metadados**: informacoes sobre o arquivo, como duracao, codec e tamanho.
