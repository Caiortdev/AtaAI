# Fase 9 - Presets personalizados de ata

## Resumo

Esta fase permite que cada usuario crie modelos proprios de ata para orientar a IA.

## Status

Concluida.

## Para que esta fase existe

Nem toda reuniao precisa da mesma ata.

Uma reuniao comercial pode precisar destacar dores do cliente, objecoes e proximos passos. Uma reuniao tecnica pode precisar destacar bugs, dependencias, riscos e decisoes de arquitetura. Uma reuniao executiva pode precisar de um resumo curto, riscos e impacto financeiro.

Antes desta fase, o app usava sempre um preset fixo. Agora o usuario pode criar presets conforme o tipo de reuniao.

## O que o usuario consegue fazer

Com esta fase, o usuario consegue:

- ver um preset padrao criado automaticamente;
- criar presets personalizados;
- editar presets personalizados;
- remover presets personalizados;
- escolher qual preset sera usado no processamento da reuniao;
- manter presets separados por usuario;
- gerar uma ata com instrucoes especificas para aquele tipo de reuniao.

## O que foi entregue

### Backend

Foram adicionados endpoints protegidos:

```text
GET    /api/presets
POST   /api/presets
PATCH  /api/presets/{preset_id}
DELETE /api/presets/{preset_id}
```

Todos exigem usuario autenticado.

O processamento de reuniao agora aceita:

```json
{
  "mode": "audio_only",
  "preset_id": "id-do-preset"
}
```

Se nenhum `preset_id` for enviado, o backend usa o preset padrao do usuario.

### Banco de dados

Foi adicionada a tabela:

```text
meeting_presets
```

Cada preset tem:

- dono;
- nome;
- descricao;
- instrucoes para IA;
- indicador de preset padrao;
- datas de criacao e atualizacao;
- payload completo em JSON.

O preset padrao e criado automaticamente por usuario e nao pode ser editado ou removido neste MVP.

### Frontend

O app recebeu um painel de presets na lateral.

Nele, o usuario pode:

- selecionar o modelo usado na geracao;
- criar um novo preset;
- editar um preset personalizado;
- remover um preset personalizado.

## O que acontece por baixo dos panos

1. O usuario entra na conta.
2. O frontend busca os presets daquele usuario.
3. O backend garante que exista pelo menos um preset padrao.
4. O usuario seleciona um preset no painel.
5. Ao processar a reuniao, o frontend envia o `preset_id`.
6. O backend valida se o preset pertence ao usuario.
7. A reuniao guarda o nome, o id e as instrucoes do preset usado.
8. A IA recebe essas instrucoes junto com os metadados e a transcricao.

Guardar as instrucoes na reuniao e importante porque preserva o historico. Se o usuario editar o preset depois, atas antigas continuam mostrando o modelo que foi usado na epoca.

## Exemplo de preset

```text
Nome:
Ata executiva

Descricao:
Modelo para reunioes com diretoria.

Instrucoes:
Gere um resumo executivo curto. Destaque decisoes estrategicas,
riscos, impacto financeiro e proximos passos com responsaveis.
Evite detalhes operacionais que nao afetem a decisao.
```

## Regras de privacidade

Presets sao privados por usuario.

Um usuario nao consegue:

- listar presets de outro usuario;
- editar presets de outro usuario;
- remover presets de outro usuario;
- usar um preset que nao pertence a ele no processamento.

## Como testar manualmente

1. Inicie backend e frontend.
2. Entre com uma conta.
3. Crie um preset chamado `Ata executiva`.
4. Crie ou selecione uma reuniao.
5. Escolha o preset no painel.
6. Envie um arquivo e gere a ata.
7. Verifique no status que o preset usado foi `Ata executiva`.
8. Saia da conta.
9. Entre com outra conta.
10. Verifique que o preset da primeira conta nao aparece.

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
22 testes passaram no backend
Ruff sem erros
TypeScript sem erros
Build do frontend concluido
```

## O que ficou fora

Esta fase nao inclui:

- biblioteca publica de templates;
- compartilhamento de presets entre usuarios;
- presets por organizacao;
- importacao/exportacao de presets;
- versionamento visual de presets;
- comparacao entre atas geradas por presets diferentes.

Esses pontos fazem sentido depois que houver organizacoes, permissoes avancadas e uso mais amplo do app.

## Glossario rapido

- **Preset**: modelo de instrucao que diz para a IA como montar a ata.
- **Preset padrao**: modelo inicial criado automaticamente para cada usuario.
- **Instrucoes para IA**: texto que orienta o foco da ata, os blocos esperados e o criterio de prioridade.
- **Historico preservado**: a reuniao guarda o preset usado no momento do processamento.
