# Fase 11 - Instalavel desktop com Tauri

## Resumo

Esta fase prepara o AtaAI para rodar como aplicativo desktop usando Tauri.

## Status

Implementada com bloqueio externo para gerar o instalador.

## Por que nao esta marcada como concluida

A estrutura Tauri foi criada, os scripts foram adicionados e o frontend continua compilando.

Porem, o instalador final ainda nao foi gerado nesta maquina porque o ambiente nao possui:

```text
rustc
cargo
```

Esses comandos sao obrigatorios para compilar um aplicativo Tauri.

## Para que esta fase existe

O desktop e importante porque muitas reunioes gravadas, arquivos grandes e fluxos de trabalho com clientes acontecem no computador.

Com Tauri, conseguimos reaproveitar o frontend React e criar um instalavel leve para Windows.

## O que o usuario conseguira fazer

Quando o build Tauri for executado em uma maquina com Rust instalado, o usuario podera:

- abrir o AtaAI como aplicativo desktop;
- usar a mesma interface React do navegador;
- fazer login;
- criar reunioes;
- enviar arquivos;
- gerar atas;
- revisar tarefas;
- exportar PDF.

Nesta fase, o aplicativo desktop ainda depende da API FastAPI rodando separadamente.

## O que foi entregue

### Scripts npm

Foram adicionados:

```text
npm.cmd run desktop:dev
npm.cmd run desktop:build
```

Eles usam:

```text
npx @tauri-apps/cli@2.8.4
```

### Configuracao Vite

O Vite foi ajustado para:

- funcionar com Tauri;
- usar porta fixa no desenvolvimento;
- evitar reload indevido por arquivos Rust;
- aceitar variaveis `TAURI_ENV_*`;
- gerar build compativel com WebView.

### Estrutura Tauri

Foi criada a pasta:

```text
frontend/src-tauri/
```

Com:

- `Cargo.toml`;
- `build.rs`;
- `src/main.rs`;
- `src/lib.rs`;
- `tauri.conf.json`;
- `capabilities/default.json`;
- icone SVG base.

### Seguranca inicial

O `tauri.conf.json` inclui uma CSP inicial permitindo conexao com:

```text
http://127.0.0.1:8000
http://localhost:8000
```

Isso permite que o app desktop converse com a API local.

## O que acontece por baixo dos panos

1. O Tauri inicia uma janela desktop.
2. Em desenvolvimento, a janela carrega o Vite em `127.0.0.1:5173`.
3. Em build, a janela carrega os arquivos gerados em `frontend/dist`.
4. O frontend continua chamando a API FastAPI.
5. O backend segue separado nesta etapa.

## Como testar quando Rust estiver instalado

1. Instale Rust e Cargo.
2. Abra o terminal em `frontend`.
3. Rode:

```powershell
npm.cmd install
npm.cmd run desktop:dev
```

Para gerar instalador:

```powershell
npm.cmd run desktop:build
```

## Validacoes executadas nesta fase

Foram executadas as validacoes possiveis sem Rust:

```text
npm.cmd run lint
npm.cmd run build
```

Tambem foi verificado que `rustc` e `cargo` nao estavam disponiveis no ambiente.

## O que ficou fora

Esta fase nao inclui:

- geracao real do `.exe`;
- assinatura do instalador;
- autoupdate;
- backend Python empacotado junto ao desktop;
- instalador macOS/Linux;
- icones finais em todos os formatos nativos.

## Proximo passo para concluir 100%

Instalar Rust/Cargo e executar:

```powershell
cd frontend
npm.cmd run desktop:build
```

Depois disso, testar o instalador gerado em uma maquina Windows limpa.

## Glossario rapido

- **Tauri**: ferramenta para criar apps desktop usando frontend web e backend nativo em Rust.
- **Rust**: linguagem usada pelo Tauri para compilar o aplicativo desktop.
- **Cargo**: gerenciador de pacotes e build do Rust.
- **NSIS**: formato de instalador Windows configurado nesta fase.
- **WebView2**: componente do Windows usado para exibir a interface web dentro do app desktop.
