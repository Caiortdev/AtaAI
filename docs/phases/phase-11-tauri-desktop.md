# Fase 11 - Instalavel desktop com Tauri

## Resumo

Esta fase prepara o AtaAI para rodar como aplicativo desktop usando Tauri.

## Status

Concluida.

## Para que esta fase existe

O desktop e importante porque muitas reunioes gravadas, arquivos grandes e fluxos de trabalho com clientes acontecem no computador.

Com Tauri, conseguimos reaproveitar o frontend React e criar um instalavel leve para Windows.

## O que o usuario consegue fazer

Com o instalador gerado, o usuario pode:

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
- icone SVG base;
- icone ICO obrigatorio para Windows;
- `Cargo.lock` para travar as dependencias Rust do aplicativo.

### Instalador Windows

Foi gerado o instalador:

```text
frontend/src-tauri/target/release/bundle/nsis/AtaAI_0.1.0_x64-setup.exe
```

Tambem foi gerado o executavel:

```text
frontend/src-tauri/target/release/ataai.exe
```

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

## Como testar

Abra o terminal em `frontend` e rode:

```powershell
npm.cmd install
npm.cmd run desktop:dev
```

Para gerar instalador:

```powershell
npm.cmd run desktop:build
```

## Validacoes executadas nesta fase

Foram executadas as validacoes:

```text
npm.cmd run lint
npm.cmd run build
npm.cmd run desktop:build
rustc --version
cargo --version
```

Resultado:

```text
Frontend TypeScript sem erros
Build web concluido
Build Tauri release concluido
Instalador NSIS gerado
rustc 1.95.0
cargo 1.95.0
```

## O que ficou fora

Esta fase nao inclui:

- assinatura do instalador;
- autoupdate;
- backend Python empacotado junto ao desktop;
- instalador macOS/Linux;
- icones finais em todos os formatos nativos.

## Proximo passo de melhoria

Testar o instalador em uma maquina Windows limpa:

- instalar o app;
- iniciar o backend;
- abrir o AtaAI desktop;
- fazer login;
- criar uma reuniao;
- gerar e exportar uma ata.

## Glossario rapido

- **Tauri**: ferramenta para criar apps desktop usando frontend web e backend nativo em Rust.
- **Rust**: linguagem usada pelo Tauri para compilar o aplicativo desktop.
- **Cargo**: gerenciador de pacotes e build do Rust.
- **NSIS**: formato de instalador Windows configurado nesta fase.
- **WebView2**: componente do Windows usado para exibir a interface web dentro do app desktop.
