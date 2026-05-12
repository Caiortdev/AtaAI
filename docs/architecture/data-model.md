# Modelo de dados

## Estado atual

O MVP usa SQLite como banco ativo.

Arquivo padrao:

```text
backend/storage/ataai.sqlite3
```

Tabela atual:

```text
users
sessions
meetings
```

### `users`

| Campo | Tipo | Uso |
| --- | --- | --- |
| `id` | TEXT | Identificador do usuario. |
| `name` | TEXT | Nome exibido no app. |
| `email` | TEXT | E-mail normalizado em minusculas. |
| `password_hash` | TEXT | Hash PBKDF2 da senha. A senha pura nao e armazenada. |
| `created_at` | TEXT | Data de criacao em ISO 8601. |
| `updated_at` | TEXT | Ultima atualizacao em ISO 8601. |

### `sessions`

| Campo | Tipo | Uso |
| --- | --- | --- |
| `id` | TEXT | Identificador da sessao. |
| `user_id` | TEXT | Usuario dono da sessao. |
| `token_hash` | TEXT | Hash SHA-256 do token de acesso. |
| `created_at` | TEXT | Data de criacao em ISO 8601. |
| `expires_at` | TEXT | Data de expiracao da sessao. |

### `meetings`

| Campo | Tipo | Uso |
| --- | --- | --- |
| `id` | TEXT | Identificador da reuniao. |
| `owner_id` | TEXT | Usuario dono da reuniao. |
| `title` | TEXT | Titulo da reuniao para listagem e busca futura. |
| `client_name` | TEXT | Nome do cliente. |
| `status` | TEXT | Estado atual: draft, uploaded, queued, processing, completed ou failed. |
| `created_at` | TEXT | Data de criacao em ISO 8601. |
| `updated_at` | TEXT | Ultima atualizacao em ISO 8601. |
| `payload` | TEXT | JSON completo da reuniao serializada pelo Pydantic. |

Indices:

```text
idx_users_email
idx_sessions_token_hash
idx_sessions_user_id
idx_meetings_owner_id
idx_meetings_status
idx_meetings_updated_at
```

## Por que payload JSON no SQLite

Nesta etapa, manter o payload completo em JSON reduz a chance de quebrar o MVP enquanto o modelo ainda muda rapido.

O backend ja possui uma camada de repositorio. Isso permite trocar a implementacao interna sem alterar os endpoints principais.

## Caminho para PostgreSQL

Quando ativarmos PostgreSQL, existem dois caminhos possiveis:

1. **Primeira migracao simples**: manter uma tabela `meetings` com colunas principais e `payload JSONB`.
2. **Migracao relacional completa**: separar reunioes, arquivos, analises, tarefas e eventos em tabelas proprias.

Para o proximo passo real de producao, o caminho recomendado e comecar com `payload JSONB`, porque:

- reduz risco;
- preserva compatibilidade com o modelo Pydantic;
- permite consultas por colunas importantes;
- facilita uma migracao posterior para tabelas mais granulares.

## Modelo PostgreSQL inicial sugerido

```sql
CREATE TABLE meetings (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  client_name TEXT,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

CREATE INDEX idx_meetings_owner_id ON meetings(owner_id);
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_updated_at ON meetings(updated_at);
CREATE INDEX idx_meetings_payload_gin ON meetings USING GIN(payload);
```

## Modelo relacional futuro

Depois que login e organizacoes entrarem, o modelo pode evoluir para:

- `users`;
- `organizations`;
- `clients`;
- `meetings`;
- `meeting_files`;
- `meeting_analyses`;
- `meeting_tasks`;
- `meeting_exports`;
- `audit_events`.

Essa separacao sera mais importante quando houver:

- varios usuarios;
- permissoes;
- auditoria;
- filtros por cliente;
- relatorios;
- historico de versoes;
- tarefas atribuidas a pessoas.
