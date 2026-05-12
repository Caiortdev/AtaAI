# Fase 10 - PWA para uso no celular

## Resumo

Esta fase transforma o frontend em uma PWA instalavel, com manifesto, icone, service worker e suporte offline basico.

## Status

Concluida.

## Para que esta fase existe

O objetivo e permitir que o AtaAI seja usado no celular antes de criar aplicativos nativos com Capacitor.

Uma PWA nao precisa passar pela Play Store ou App Store para ser testada. O usuario abre a URL no navegador e pode adicionar o app a tela inicial.

Isso ajuda a validar:

- se a interface funciona bem em telas pequenas;
- se o fluxo de login e reunioes faz sentido no celular;
- se vale a pena investir depois em Android/iOS empacotado.

## O que o usuario consegue fazer

Com esta fase, o usuario consegue:

- abrir o AtaAI pelo navegador do celular;
- adicionar o app a tela inicial;
- ver nome, icone e cor de tema do app;
- abrir a interface mesmo sem conexao depois do primeiro carregamento;
- visualizar um indicador simples de estado online/offline.

## O que foi entregue

### Manifesto PWA

Arquivo:

```text
frontend/public/manifest.webmanifest
```

Ele define:

- nome do app;
- nome curto;
- descricao;
- icone;
- modo de exibicao standalone;
- cor de tema;
- escopo e URL inicial.

### Service worker

Arquivo:

```text
frontend/public/service-worker.js
```

Ele faz cache basico do app shell:

- rota inicial;
- `index.html`;
- manifesto;
- icone;
- pagina offline.

Tambem tenta buscar recursos pela rede e usa cache quando a conexao falha.

### Pagina offline

Arquivo:

```text
frontend/public/offline.html
```

Ela explica que a interface pode abrir offline, mas login, upload, transcricao e geracao de ata ainda precisam da API.

### Registro no React

Arquivo:

```text
frontend/src/pwa.ts
```

O frontend registra o service worker quando o app carrega.

### Metadados mobile

Arquivo:

```text
frontend/index.html
```

Foram adicionados:

- `theme-color`;
- link para o manifesto;
- icone;
- metadados para comportamento em iOS.

## O que acontece por baixo dos panos

1. O usuario abre o app no navegador.
2. O navegador le o manifesto PWA.
3. O app registra o service worker.
4. O service worker salva arquivos essenciais em cache.
5. Em acessos futuros, se a rede falhar, o navegador tenta usar os arquivos em cache.
6. O app mostra se o navegador esta online ou offline.

## Limites importantes

A PWA atual nao torna todo o produto offline.

Ainda precisam de conexao:

- login;
- cadastro;
- upload de audio/video;
- transcricao;
- geracao de ata;
- exportacao conectada ao backend;
- sincronizacao de reunioes.

O suporte offline desta fase e propositalmente basico: ele garante que a interface abra e informe o estado de conexao.

## Como instalar no Android

1. Abra a URL do app no Chrome.
2. Toque no menu do navegador.
3. Escolha `Adicionar a tela inicial` ou `Instalar app`.
4. Confirme o nome `AtaAI`.

## Como instalar no iPhone

1. Abra a URL do app no Safari.
2. Toque no botao de compartilhar.
3. Escolha `Adicionar a Tela de Inicio`.
4. Confirme o nome `AtaAI`.

## Como testar localmente

1. Rode o frontend.
2. Abra o app no navegador.
3. Verifique se o manifesto existe em:

```text
http://127.0.0.1:5173/manifest.webmanifest
```

4. Verifique se o service worker existe em:

```text
http://127.0.0.1:5173/service-worker.js
```

5. Rode o build de producao.
6. Abra o app em uma rede local ou deploy HTTPS.
7. Teste adicionar a tela inicial no celular.

## Validacoes executadas

Foram executadas as validacoes:

```text
npm.cmd run lint
npm.cmd run build
```

Resultado:

```text
TypeScript sem erros
Build do frontend concluido
```

## O que ficou fora

Esta fase nao inclui:

- sincronizacao offline de reunioes;
- fila local de uploads offline;
- cache de dados privados;
- notificacoes push;
- prompt customizado de instalacao;
- icones PNG em varios tamanhos;
- empacotamento Android/iOS com Capacitor.

Esses pontos entram melhor depois que o fluxo mobile for validado com usuarios reais.

## Glossario rapido

- **PWA**: aplicativo web que pode se comportar como app instalado.
- **Manifesto**: arquivo que descreve nome, icone, tema e forma de abertura do app.
- **Service worker**: script do navegador que pode interceptar requisicoes e usar cache.
- **App shell**: arquivos minimos para abrir a interface do app.
- **Standalone**: modo em que o app abre sem parecer uma aba comum do navegador.
