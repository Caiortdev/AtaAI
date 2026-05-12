# Fase 7 - Persistencia SQLite e arquitetura para PostgreSQL

## Resumo em uma frase

Nesta fase, o MVP saiu da persistencia principal em arquivo JSON e passou a usar SQLite, mantendo a arquitetura preparada para migrar para PostgreSQL.

## Status

Concluida e validada localmente.

## Decisao do projeto

Vamos deixar o PostgreSQL arquitetado, mas usar SQLite por enquanto.

Essa decisao equilibra duas necessidades:

- continuar com um MVP simples de rodar localmente;
- evitar acoplar o codigo a uma persistencia fraca em JSON;
- preparar a troca futura para PostgreSQL sem reescrever a API.

## Para que esta fase existe

Antes desta fase, as reunioes eram salvas em `meetings.json`.

Isso funciona para prototipo, mas tem limites:

- concorrencia ruim;
- risco maior de corromper arquivo;
- consultas limitadas;
- dificuldade para evoluir para usuarios, permissoes e auditoria;
- pouca semelhanca com uma arquitetura de producao.

Esta fase cria uma fronteira mais real de persistencia.

## O que foi entregue

- Configuracao `DATABASE_BACKEND`.
- Configuracao `DATABASE_PATH`.
- Configuracao futura `DATABASE_URL`.
- Backend ativo usando SQLite por padrao.
- Tabela `meetings` no SQLite.
- Indices para `status` e `updated_at`.
- Importacao automatica do `meetings.json` legado quando o SQLite ainda esta vazio.
- Repositorio JSON mantido como fallback.
- Factory `build_meeting_repository`.
- Backend `postgres` reservado com erro claro enquanto o driver ainda nao esta ativo.
- Health check informando o backend de banco usado.
- Documento de arquitetura [data-model.md](../architecture/data-model.md).
- Testes automatizados cobrindo:
  - uso de SQLite;
  - fallback JSON;
  - backend PostgreSQL reservado;
  - fluxo completo do app com SQLite.

## Configuracao atual

Arquivo: `backend/.env`

```text
DATABASE_BACKEND=sqlite
DATABASE_PATH=storage/ataai.sqlite3
```

## Configuracao futura para PostgreSQL

Quando formos ativar PostgreSQL de verdade, a configuracao esperada sera:

```text
DATABASE_BACKEND=postgres
DATABASE_URL=postgresql://ataai:senha@localhost:5432/ataai
```

Nesta fase, essa opcao ainda nao executa o Postgres. Ela esta documentada e reservada para a migracao futura.

## O que acontece por baixo dos panos

1. O backend le `DATABASE_BACKEND`.
2. Se estiver como `sqlite`, usa `SQLiteMeetingRepository`.
3. Se estiver como `json`, usa `JsonMeetingRepository`.
4. Se estiver como `postgres`, retorna erro claro informando que ainda nao esta ativo.
5. Os endpoints continuam chamando apenas a interface de repositorio.
6. O restante do app nao precisa saber se os dados vem de JSON, SQLite ou PostgreSQL.

## Como isso prepara o PostgreSQL

A preparacao acontece por separacao de responsabilidades:

- endpoints nao acessam banco diretamente;
- processamento nao acessa banco diretamente;
- persistencia fica atras de uma interface de repositorio;
- configuracao escolhe o backend;
- modelo de dominio continua em Pydantic;
- payload completo da reuniao fica serializado de forma migravel.

Quando o PostgreSQL entrar, a maior parte da mudanca deve ficar concentrada em um novo `PostgresMeetingRepository`.

## Como testar

1. Configure:

```text
DATABASE_BACKEND=sqlite
DATABASE_PATH=storage/ataai.sqlite3
```

2. Inicie o backend.
3. Crie uma reuniao.
4. Envie um arquivo.
5. Gere uma ata.
6. Reinicie o backend.
7. Confirme que a reuniao continua listada.

## Validacoes executadas

- `pytest` aprovado com 16 testes.
- `ruff check` aprovado.
- `npm run build` aprovado.
- `npm run lint` aprovado.
- Teste automatizado confirmando SQLite como repositorio ativo.
- Teste automatizado confirmando fallback JSON.
- Teste automatizado confirmando importacao do JSON legado para SQLite.
- Teste automatizado confirmando que PostgreSQL ainda e uma opcao reservada.

## O que ficou fora desta fase

Esta fase nao ativa o PostgreSQL real.

Ficaram fora:

- driver PostgreSQL;
- migrations com Alembic;
- schema relacional completo;
- Docker Compose com Postgres;
- usuario e senha de banco;
- backup e restore;
- pooling de conexoes;
- deploy com banco remoto.

## Proxima evolucao para PostgreSQL

Quando formos ativar PostgreSQL, o plano recomendado e:

1. Adicionar driver `psycopg`.
2. Adicionar Alembic.
3. Criar tabela `meetings`.
4. Criar `PostgresMeetingRepository`.
5. Criar script de migracao de SQLite para PostgreSQL.
6. Adicionar Docker Compose local.
7. Rodar testes nos dois backends.

## Glossario rapido

- **SQLite**: banco local em arquivo, leve e bom para MVP.
- **PostgreSQL**: banco relacional robusto, recomendado para producao.
- **Repositorio**: camada de codigo que salva e busca dados.
- **Factory**: funcao que escolhe qual implementacao usar.
- **DATABASE_BACKEND**: variavel que define qual banco o app usa.
- **DATABASE_URL**: endereco de conexao para banco remoto ou servidor PostgreSQL.
