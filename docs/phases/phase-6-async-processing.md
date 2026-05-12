# Fase 6 - Processamento assincrono com fila local

## Resumo em uma frase

Nesta fase, o processamento da reuniao passou a ser enfileirado e executado em background, sem prender a requisicao HTTP ate a IA terminar.

## Status

Concluida e validada localmente.

## Para que esta fase existe

Processar uma reuniao pode demorar.

O backend precisa preparar audio, chamar transcricao, chamar geracao de ata e salvar o resultado. Quando esse fluxo acontece dentro da mesma requisicao, o usuario fica esperando a chamada terminar e o navegador pode parecer travado.

Esta fase existe para separar duas coisas:

- pedido do usuario para iniciar o processamento;
- execucao real do processamento.

Com isso, o app consegue responder rapido e atualizar o status enquanto o trabalho acontece.

## O que o usuario consegue fazer

O usuario consegue:

- clicar em `Gerar ata`;
- receber resposta rapida do backend;
- ver a reuniao com status `Na fila`;
- acompanhar a mudanca para `Processando`;
- ver a mudanca final para `Concluida` ou `Falhou`;
- continuar usando a tela enquanto o processamento acontece.

## O que foi entregue

- Novo status de reuniao: `queued`.
- Fila local `ProcessingQueue` no backend.
- Worker em background para executar jobs.
- Endpoint `/api/meetings/{meeting_id}/process` agora enfileira o job.
- Protecao contra duplo processamento enquanto a reuniao ja esta na fila ou em processamento.
- Salvamento inicial do status `queued`.
- Atualizacao posterior para `processing`, `completed` ou `failed`.
- Frontend reconhecendo o status `Na fila`.
- Frontend atualizando a lista automaticamente enquanto houver reuniao na fila ou em processamento.
- Teste automatizado validando resposta `queued` antes do job rodar.
- Teste automatizado validando conclusao do job em background.
- Teste automatizado bloqueando processamento duplicado.

## O que acontece por baixo dos panos

1. O usuario clica em `Gerar ata`.
2. O backend valida se a reuniao existe.
3. O backend valida se existe arquivo enviado.
4. O backend verifica se a reuniao ja esta `queued` ou `processing`.
5. O backend salva a reuniao como `queued`.
6. O backend adiciona o job na fila local.
7. A resposta HTTP volta rapidamente para o frontend.
8. O worker em background pega o job.
9. O worker executa o processamento real.
10. O backend salva o status final.
11. O frontend consulta a lista periodicamente e mostra a atualizacao.

## Decisao tecnica

Para o MVP, foi criada uma fila local em memoria usando recursos nativos do Python.

Motivos:

- reduzir complexidade operacional;
- evitar instalar Redis antes de validar a experiencia;
- manter o app simples para rodar localmente;
- entregar o comportamento assincrono que o usuario percebe;
- preparar o codigo para trocar a fila local por Redis/Celery depois.

Essa decisao e adequada para desenvolvimento local e MVP inicial. Para producao com muitos usuarios, o ideal e evoluir para uma fila persistente.

## Como testar

1. Inicie o backend.
2. Inicie o frontend.
3. Abra uma reuniao com arquivo enviado.
4. Clique em `Gerar ata`.
5. Verifique se o status muda para `Na fila`.
6. Aguarde a tela atualizar.
7. Confirme se o status final vira `Concluida` ou `Falhou`.

## Validacoes executadas

- `pytest` aprovado com 12 testes.
- `ruff check` aprovado.
- `npm run build` aprovado.
- `npm run lint` aprovado.
- Teste automatizado garantindo retorno `queued`.
- Teste automatizado executando o job em background.
- Teste automatizado bloqueando processamento duplicado.

## O que ficou fora desta fase

Esta fase nao implementa uma fila distribuida.

Ficaram fora:

- Redis;
- Celery;
- retry automatico;
- persistencia dos jobs;
- painel administrativo da fila;
- multiplos workers;
- prioridade entre jobs;
- cancelamento de processamento;
- progresso percentual.

## Glossario rapido

- **Fila**: lista de trabalhos esperando execucao.
- **Job**: trabalho individual, neste caso processar uma reuniao.
- **Worker**: processo ou thread que pega jobs da fila e executa.
- **Background**: execucao fora da requisicao principal.
- **Fila local**: fila em memoria dentro do proprio backend.
- **Fila distribuida**: fila externa, como Redis, que pode ser usada por varios workers.
