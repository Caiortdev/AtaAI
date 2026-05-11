# Documentacao do projeto

Esta pasta organiza a documentacao do MVP como um projeto real, separando produto, fases de desenvolvimento, arquitetura e operacao.

## Estrutura

```text
docs/
  README.md                 Indice geral da documentacao
  product/                  Visao de produto e materiais de concepcao
  phases/                   Documentacao por fase de desenvolvimento
  architecture/             Decisoes tecnicas e arquitetura
  operations/               Guias de execucao, ambiente e operacao local
```

## Leitura recomendada

Para entender o projeto do zero:

1. [Product Brief](./product/project-brief.pdf)
2. [Fase 0 - Fundacao do MVP](./phases/phase-0-foundation.md)
3. [Fase 1 - Upload real e preparacao de audio](./phases/phase-1-media-upload.md)
4. [Fase 2 - Transcricao real](./phases/phase-2-transcription.md)
5. [Fase 3 - Geracao de ata e tarefas com IA](./phases/phase-3-minutes-generation.md)
6. [Stack tecnica escolhida](./architecture/stack.md)

## Status das fases

| Fase | Documento | Status | Resumo |
| --- | --- | --- | --- |
| Fase 0 | [phase-0-foundation.md](./phases/phase-0-foundation.md) | Concluida | Fundacao do MVP com backend, frontend e processamento simulado. |
| Fase 1 | [phase-1-media-upload.md](./phases/phase-1-media-upload.md) | Concluida | Upload real de audio/video e preparacao do audio com FFmpeg. |
| Fase 2 | [phase-2-transcription.md](./phases/phase-2-transcription.md) | Implementada, pendente de chave | Camada de transcricao real com Gemini e modo mock para testes. |
| Fase 3 | [phase-3-minutes-generation.md](./phases/phase-3-minutes-generation.md) | Implementada, pendente de chave | Geracao estruturada de ata, tarefas e prioridades por IA. |

## Proximas fases previstas

| Fase | Objetivo |
| --- | --- |
| Fase 4 | Criar editor de ata e tarefas para revisao humana. |
| Fase 5 | Exportar ata em PDF. |
| Fase 6 | Processamento assincrono com filas. |
| Fase 7 | Banco de dados PostgreSQL. |
| Fase 8 | Login, privacidade e controle de acesso. |
| Fase 9 | Presets personalizados de ata. |
| Fase 10 | PWA para uso em celular. |
| Fase 11 | Instalavel desktop com Tauri. |
| Fase 12 | Instalavel mobile com Capacitor. |

## Padrao dos documentos de fase

Cada documento de fase deve ser compreensivel por pessoas tecnicas e nao tecnicas.

Estrutura recomendada:

- resumo em uma frase;
- status;
- para que a fase existe;
- o que o usuario consegue fazer;
- o que foi entregue;
- o que acontece por baixo dos panos;
- configuracoes importantes;
- como testar;
- validacoes executadas;
- o que ficou fora;
- glossario rapido.

## Regra de status

- **Planejada**: ainda nao comecou.
- **Em desenvolvimento**: esta sendo implementada.
- **Implementada**: o codigo existe, mas ainda falta validacao real ou alguma configuracao externa.
- **Concluida**: foi implementada, testada e validada no fluxo real esperado.
- **Bloqueada**: depende de chave, ferramenta, decisao ou acesso externo.

## Estado atual do MVP

O MVP ja consegue receber arquivo de reuniao, preparar audio real, transcrever por provedor plugavel e gerar ata/tarefas por provedor plugavel.

O bloqueio atual para concluir operacionalmente as Fases 2 e 3 e configurar `GEMINI_API_KEY` no backend.
