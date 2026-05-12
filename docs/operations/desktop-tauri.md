# Desktop com Tauri

Este guia explica como rodar e gerar o instalavel desktop do AtaAI com Tauri.

## Estado atual

O projeto ja possui configuracao Tauri em:

```text
frontend/src-tauri/
```

O frontend continua sendo React/Vite. O Tauri empacota esse mesmo frontend dentro de uma janela desktop.

O instalador Windows ja foi gerado em:

```text
frontend/src-tauri/target/release/bundle/nsis/AtaAI_0.1.0_x64-setup.exe
```

## Requisitos

Para gerar o instalavel, a maquina precisa ter:

- Node.js;
- dependencias npm do frontend;
- Rust;
- Cargo;
- WebView2 Runtime no Windows;
- CLI do Tauri, usado via `npx`.

Verifique Rust e Cargo:

```powershell
rustc --version
cargo --version
```

Se esses comandos nao existirem, instale Rust pelo site oficial:

```text
https://www.rust-lang.org/tools/install
```

No Windows, tambem pode ser necessario instalar as ferramentas C++ do Visual Studio Build Tools.

## Rodar em desenvolvimento

Em um terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run desktop:dev
```

O Tauri vai iniciar o Vite e abrir uma janela desktop apontando para:

```text
http://127.0.0.1:5173
```

## Gerar instalavel

```powershell
cd frontend
npm.cmd run desktop:build
```

No Windows, o alvo configurado inicialmente e NSIS.

O instalador deve sair em uma pasta semelhante a:

```text
frontend/src-tauri/target/release/bundle/nsis/
```

## API do backend

O desktop ainda depende da API FastAPI rodando em:

```text
http://127.0.0.1:8000
```

Isso significa que, nesta fase, o instalavel desktop empacota a interface, mas nao empacota o backend Python junto.

Para usar:

1. Inicie o backend.
2. Abra o app desktop.
3. O app desktop conversa com a API local.

Em uma fase futura, existem tres caminhos:

- empacotar o backend junto com o app;
- rodar backend em servidor/cloud;
- transformar partes do processamento em comandos nativos do Tauri.

## Variavel de API

Se a API estiver em outro endereco, gere o frontend com:

```powershell
$env:VITE_API_URL="https://api.seudominio.com"
npm.cmd run desktop:build
```

## Icones

O projeto possui icones base em:

```text
frontend/src-tauri/icons/icon.svg
frontend/src-tauri/icons/icon.ico
```

Antes de publicar um instalador final, gere o conjunto completo de icones do Tauri:

```powershell
cd frontend
npx @tauri-apps/cli@2.8.4 icon public/icon.svg
```

Isso cria arquivos PNG/ICO/ICNS usados pelos empacotadores.

## Limitacoes atuais

O instalador desktop empacota a interface, mas nao empacota o backend Python.

O que ainda precisa evoluir:

- testar o instalador em uma maquina Windows limpa;
- assinar o instalador;
- definir autoupdate;
- decidir se o backend sera empacotado junto ou hospedado em servidor;
- gerar icones finais em todos os formatos recomendados pelo Tauri.
