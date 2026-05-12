# Stack tecnica escolhida

Este documento resume as decisoes de stack do MVP.

## Frontend

Usaremos React com TypeScript e Vite. React permite criar uma interface rica para upload, editor de ata, tarefas e estados de processamento. TypeScript ajuda a manter contratos confiaveis entre frontend e backend. Vite deixa o desenvolvimento rapido e tambem funciona bem como base para Tauri, PWA e Capacitor.

Para estilo, usaremos Tailwind CSS. A interface deve ser pratica e operacional, sem parecer uma landing page. Componentes podem ser proprios ou baseados em shadcn/ui quando isso acelerar a entrega.

Para dados vindos da API, usaremos TanStack Query. Para estado local simples, usaremos Zustand.

## Desktop

Usaremos Tauri em fase posterior para gerar instalaveis desktop leves. A decisao favorece Windows primeiro, reaproveitando o mesmo frontend React.

## Mobile

O mobile comeca como PWA responsiva e instalavel. Isso permite validar o uso no celular antes de entrar em assinatura, distribuicao e builds nativos.

A PWA atual usa manifesto web, service worker manual, icone do app, tema mobile e tela offline basica. Ela nao substitui uma aplicacao nativa, mas permite abrir o AtaAI pelo navegador e adicionar o app a tela inicial em Android e iOS.

Depois, usaremos Capacitor para empacotar Android e iOS. Android pode ser distribuido por APK assinado fora da Play Store. iOS deve seguir TestFlight, App Store, Ad Hoc ou distribuicao empresarial.

## Backend

Usaremos Python com FastAPI. O backend precisa receber arquivos grandes, controlar jobs, extrair audio, chamar transcricao, chamar LLM, salvar resultados e gerar PDF.

No MVP local, a persistencia ativa usa SQLite para reduzir complexidade de instalacao. A camada de repositorio ja foi separada por backend para permitir migracao futura para PostgreSQL sem reescrever endpoints, processamento ou frontend.

A autenticacao atual tambem usa SQLite. O backend cria usuarios, sessoes e reunioes com dono. Essa escolha e suficiente para validar o MVP localmente, mantendo o caminho aberto para migrar as mesmas entidades para PostgreSQL.

PostgreSQL continua sendo o banco alvo para producao, principalmente quando houver multiplos usuarios, organizacoes, permissoes avancadas, historico maior, auditoria e consultas mais complexas.

Redis/Celery distribuido e storage S3-compatible entram em fases posteriores.

## IA

Transcricao e LLM devem rodar como servicos externos no inicio. Rodar modelos pesados localmente no computador ou celular do usuario nao e recomendado para o MVP.
