# Fase 8 - Login, privacidade e controle de acesso

## Resumo

Esta fase adiciona cadastro, login e isolamento das reunioes por usuario.

## Status

Concluida.

## Para que esta fase existe

Ate a fase anterior, o app ja conseguia salvar reunioes em SQLite. O problema era que todas as reunioes ficavam no mesmo espaco de trabalho.

Para um produto que processa reunioes com clientes, isso nao e aceitavel. Atas, transcricoes, tarefas, nomes de clientes e arquivos enviados precisam pertencer a uma pessoa ou conta.

Esta fase cria a primeira camada de privacidade do MVP.

## O que o usuario consegue fazer

Com esta fase, o usuario consegue:

- criar uma conta com nome, e-mail e senha;
- entrar no app com e-mail e senha;
- manter uma sessao local;
- sair da conta;
- criar reunioes vinculadas ao proprio usuario;
- ver somente as proprias reunioes;
- impedir que outro usuario acesse uma reuniao que nao pertence a ele.

## O que foi entregue

### Backend

Foram adicionados endpoints de autenticacao:

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout
```

As rotas de reuniao agora exigem token Bearer:

```text
GET   /api/meetings
POST  /api/meetings
GET   /api/meetings/{meeting_id}
POST  /api/meetings/{meeting_id}/upload
POST  /api/meetings/{meeting_id}/process
PATCH /api/meetings/{meeting_id}/analysis
GET   /api/meetings/{meeting_id}/analysis.pdf
```

### Banco de dados

O SQLite recebeu tabelas para:

- usuarios;
- sessoes;
- reunioes com dono.

As senhas nao sao salvas em texto puro. O backend salva apenas um hash PBKDF2.

Os tokens de sessao tambem nao sao salvos em texto puro. O backend salva o hash do token e entrega o token original somente ao cliente no momento do login/cadastro.

### Frontend

O app React recebeu:

- tela de login;
- tela de cadastro;
- persistencia local da sessao;
- envio automatico do token nas chamadas da API;
- botao de sair;
- listagem de reunioes filtrada pelo usuario autenticado.

## O que acontece por baixo dos panos

1. O usuario cria uma conta ou faz login.
2. O backend valida os dados.
3. O backend gera um token de sessao.
4. O frontend guarda o token localmente.
5. A cada chamada protegida, o frontend envia:

```text
Authorization: Bearer <token>
```

6. O backend identifica o usuario pelo token.
7. Toda busca ou alteracao de reuniao usa o `owner_id` do usuario autenticado.

Isso evita que um usuario veja ou edite reunioes de outro usuario.

## Configuracoes importantes

No `.env` do backend:

```text
AUTH_SESSION_DAYS=30
DATABASE_BACKEND=sqlite
DATABASE_PATH=storage/ataai.sqlite3
```

`AUTH_SESSION_DAYS` define por quantos dias a sessao local fica valida.

## Decisao tecnica

Para o MVP, foi escolhida autenticacao local com token de sessao opaco.

Isso foi escolhido porque:

- e simples de testar;
- nao depende de provedor externo;
- funciona localmente;
- evita adicionar complexidade antes da necessidade real;
- prepara o caminho para permissoes e organizacoes no futuro.

Em uma versao de producao, ainda sera necessario avaliar:

- recuperacao de senha;
- confirmacao de e-mail;
- MFA;
- OAuth;
- politicas de senha;
- auditoria de acesso;
- organizacoes e papeis de usuario.

## Como testar manualmente

1. Inicie o backend.
2. Inicie o frontend.
3. Abra o app.
4. Crie uma conta.
5. Crie uma reuniao.
6. Saia da conta.
7. Crie outra conta.
8. Verifique que a reuniao da primeira conta nao aparece.
9. Volte para a primeira conta.
10. Verifique que a reuniao aparece novamente.

## Validacoes executadas

Foram executadas as validacoes:

```text
python -m pytest -q
python -m ruff check .
npm.cmd run lint
npm.cmd run build
```

Resultado:

```text
19 testes passaram no backend
Ruff sem erros
TypeScript sem erros
Build do frontend concluido
```

## O que ficou fora

Esta fase nao inclui:

- recuperacao de senha;
- convite de usuarios;
- organizacoes;
- papeis como administrador, membro e cliente;
- tela de perfil;
- auditoria detalhada;
- refresh token separado;
- expiracao visual da sessao no frontend.

Esses pontos fazem mais sentido depois que o MVP tiver presets, uso mobile e uma decisao mais clara sobre multiusuario/empresa.

## Glossario rapido

- **Autenticacao**: confirmar quem e o usuario.
- **Autorizacao**: decidir o que esse usuario pode acessar.
- **Token Bearer**: chave temporaria enviada pelo frontend para provar que o usuario esta logado.
- **Hash de senha**: versao transformada da senha, usada para comparacao segura sem armazenar a senha pura.
- **Owner ID**: campo que indica quem e o dono de uma reuniao.
