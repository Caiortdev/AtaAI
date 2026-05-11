# Fase 4 - Editor de ata e tarefas para revisao humana

## Resumo em uma frase

Nesta fase, o sistema passou a permitir que uma pessoa revise e salve a ata, o resumo e as tarefas geradas pela IA.

## Status

Concluida e validada localmente.

## Para que esta fase existe

A IA gera uma primeira versao da ata, mas a decisao final precisa continuar nas maos do usuario.

Esta fase existe para transformar a saida da IA em um material revisavel:

- corrigir termos;
- ajustar resumo;
- remover informacoes desnecessarias;
- mudar prioridade de tarefas;
- aprovar tarefas;
- adicionar tarefas que a IA nao identificou;
- remover tarefas que nao fazem sentido;
- salvar a versao revisada.

Sem esta fase, o MVP dependeria demais da primeira resposta da IA.

## O que o usuario consegue fazer

O usuario consegue:

- abrir uma reuniao processada;
- clicar em `Revisar ata`;
- editar a ata em Markdown;
- editar o resumo executivo;
- editar topicos, decisoes, riscos e duvidas abertas;
- editar tarefas;
- alterar prioridade da tarefa;
- alterar status da tarefa;
- preencher responsavel e prazo;
- adicionar uma nova tarefa;
- remover uma tarefa;
- salvar a revisao;
- cancelar a revisao e voltar para a versao salva.

## O que foi entregue

- Endpoint `PATCH /api/meetings/{meeting_id}/analysis`.
- Modelo `MeetingAnalysisUpdate` no backend.
- Salvamento da revisao mantendo:
  - transcricao original;
  - provedor de transcricao;
  - modelo de transcricao;
  - provedor de ata;
  - modelo de ata.
- Validacao para impedir edicao antes da ata existir.
- Teste automatizado para salvar uma revisao humana.
- Teste automatizado para bloquear revisao antes da geracao da ata.
- Frontend com modo de leitura e modo de edicao.
- Editor de ata em Markdown.
- Editor de resumo executivo.
- Editor de listas estruturadas.
- Editor de tarefas.
- Controle de status da tarefa: `Nova`, `Em revisao` e `Aprovada`.

## O que acontece por baixo dos panos

1. O usuario gera a ata nas fases anteriores.
2. O frontend mostra a ata em modo de leitura.
3. Ao clicar em `Revisar ata`, o frontend cria um rascunho local da analise.
4. O usuario altera campos da ata e das tarefas.
5. Ao salvar, o frontend envia os campos editaveis para o backend.
6. O backend valida se a reuniao existe.
7. O backend valida se a reuniao ja tem analise.
8. O backend substitui somente os campos revisaveis.
9. O backend salva a reuniao atualizada em `meetings.json`.
10. O frontend recarrega a lista e mostra a versao revisada.

## Campos editaveis

| Campo | O que representa |
| --- | --- |
| `minutes_markdown` | Texto principal da ata. |
| `executive_summary` | Resumo executivo da reuniao. |
| `topics` | Topicos discutidos. |
| `decisions` | Decisoes tomadas. |
| `tasks` | Lista de tarefas. |
| `risks` | Riscos identificados. |
| `open_questions` | Duvidas ou pendencias abertas. |

## Campos protegidos

Estes campos nao sao editados pelo endpoint da Fase 4:

- transcricao;
- provedor da transcricao;
- modelo da transcricao;
- idioma da transcricao;
- provedor da ata;
- modelo da ata;
- arquivo enviado;
- audio preparado.

Essa separacao evita que a revisao humana apague rastreabilidade tecnica do processamento.

## Como testar

1. Inicie o backend.
2. Inicie o frontend.
3. Abra uma reuniao que ja tenha ata gerada.
4. Clique em `Revisar ata`.
5. Altere o texto da ata.
6. Altere uma tarefa.
7. Mude o status da tarefa para `Aprovada`.
8. Clique em `Salvar revisao`.
9. Confirme que a tela volta para o modo de leitura com os dados revisados.

## Validacoes executadas

- `pytest` aprovado com 8 testes.
- `ruff check` aprovado.
- `npm run build` aprovado.
- `npm run lint` aprovado.
- Teste automatizado salvando uma revisao de ata.
- Teste automatizado bloqueando revisao antes da ata existir.

## O que ficou fora desta fase

Esta fase nao exporta a ata.

Ficaram fora:

- exportacao PDF;
- historico de versoes;
- comparacao entre versao da IA e versao revisada;
- editor rich text;
- comentarios por trecho;
- atribuicao de tarefas a usuarios reais;
- envio para ferramentas externas.

## Glossario rapido

- **Revisao humana**: etapa em que uma pessoa confere e ajusta a saida da IA.
- **Markdown**: formato de texto simples usado para montar a ata.
- **Rascunho local**: copia temporaria usada pelo frontend enquanto o usuario edita.
- **Campo protegido**: informacao que o editor nao altera para manter rastreabilidade.
- **Status da tarefa**: indica se a tarefa ainda e nova, esta em revisao ou ja foi aprovada.
