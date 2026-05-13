import { useState } from "react";
import { Badge } from "./components/ui/Badge";
import { Button } from "./components/ui/Button";
import { Field } from "./components/ui/Input";
import { Panel } from "./components/ui/Panel";
import { Tabs } from "./components/ui/Tabs";
import { ThemeToggle } from "./components/ThemeToggle";
import { useWorkspaceStore } from "./store";

export function DesignSystemDemo() {
  const theme = useWorkspaceStore((s) => s.theme);

  return (
    <div className="min-h-screen bg-bg-primary p-8 transition-colors">
      <div className="mx-auto max-w-5xl space-y-10">
        <header className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-bold text-white">
                A
              </div>
              <span className="text-lg font-semibold text-text-primary">AtaAI Design System</span>
            </div>
            <p className="mt-1 text-sm text-text-secondary">Preview dos componentes e tokens visuais</p>
          </div>
          <ThemeToggle />
        </header>

        <ColorsSection />
        <ButtonsSection />
        <BadgesSection />
        <InputsSection />
        <PanelsSection />
        <TabsSection />
      </div>
    </div>
  );
}

function ColorsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Paleta de Cores</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
        <ColorSwatch label="Accent" className="bg-accent" />
        <ColorSwatch label="Accent Hover" className="bg-accent-hover" />
        <ColorSwatch label="Accent Muted" className="bg-accent-muted" textDark />
        <ColorSwatch label="Danger" className="bg-danger" />
        <ColorSwatch label="Success" className="bg-success" />
        <ColorSwatch label="Warning" className="bg-warning" />
        <ColorSwatch label="BG Primary" className="bg-bg-primary border border-border" textDark />
        <ColorSwatch label="BG Secondary" className="bg-bg-secondary border border-border" textDark />
        <ColorSwatch label="BG Tertiary" className="bg-bg-tertiary border border-border" textDark />
        <ColorSwatch label="Surface" className="bg-surface border border-border" textDark />
        <ColorSwatch label="Text Primary" className="bg-text-primary" />
        <ColorSwatch label="Text Secondary" className="bg-text-secondary" />
      </div>
    </section>
  );
}

function ColorSwatch({ label, className, textDark }: { label: string; className: string; textDark?: boolean }) {
  return (
    <div className="text-center">
      <div className={`h-16 rounded-lg ${className}`} />
      <span className={`mt-1 block text-xs ${textDark ? "text-text-primary" : "text-text-secondary"}`}>
        {label}
      </span>
    </div>
  );
}

function ButtonsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Botoes</h2>
      <Panel>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" disabled>Disabled</Button>
        </div>
      </Panel>
    </section>
  );
}

function BadgesSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Badges</h2>
      <Panel>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="default">Rascunho</Badge>
          <Badge variant="accent">Processando</Badge>
          <Badge variant="success">Concluida</Badge>
          <Badge variant="warning">Na fila</Badge>
          <Badge variant="danger">Falhou</Badge>
        </div>
      </Panel>
    </section>
  );
}

function InputsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Inputs</h2>
      <Panel>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Titulo da reuniao">
            <input className="input" placeholder="Alinhamento com cliente" />
          </Field>
          <Field label="Cliente">
            <input className="input" placeholder="Nome da empresa" />
          </Field>
          <Field label="Modo de analise">
            <select className="input">
              <option>Somente audio</option>
              <option>Audio + video</option>
            </select>
          </Field>
          <Field label="Observacoes">
            <textarea className="input min-h-20 resize-y" placeholder="Contexto opcional..." />
          </Field>
        </div>
      </Panel>
    </section>
  );
}

function PanelsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Panels</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel title="Reuniao selecionada" actions={<Button variant="secondary">Exportar PDF</Button>}>
          <p className="text-sm text-text-secondary">
            Conteudo do painel com titulo e acoes no header.
          </p>
        </Panel>
        <Panel title="Status">
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-text-secondary">Etapa</dt>
              <dd className="font-medium text-text-primary">Concluida</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Arquivo</dt>
              <dd className="font-medium text-text-primary">reuniao-cliente.mp3</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Duracao</dt>
              <dd className="font-medium text-text-primary">45min 12s</dd>
            </div>
          </dl>
        </Panel>
      </div>
    </section>
  );
}

function TabsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Tabs (Visualizacao da Ata)</h2>
      <Panel>
        <Tabs
          tabs={[
            {
              id: "ata",
              label: "Ata",
              content: (
                <div className="prose-like space-y-2 text-sm text-text-primary">
                  <h3 className="text-base font-semibold">Ata de Reuniao - Alinhamento Q2</h3>
                  <p>Reuniao realizada em 10/05/2026 com participantes do time de produto e engenharia.</p>
                  <h3 className="text-base font-semibold">Decisoes</h3>
                  <ul className="list-disc pl-5 text-text-secondary">
                    <li>Priorizar feature X para o sprint 14</li>
                    <li>Adiar integracao com sistema legado</li>
                  </ul>
                </div>
              ),
            },
            {
              id: "transcricao",
              label: "Transcricao",
              content: (
                <pre className="whitespace-pre-wrap font-sans text-sm text-text-secondary">
                  {"[00:00] Joao: Bom dia pessoal, vamos comecar...\n[00:15] Maria: Oi, estou aqui. Podemos revisar os pontos da sprint?\n[00:30] Joao: Claro, primeiro item e a feature de exportacao..."}
                </pre>
              ),
            },
            {
              id: "tarefas",
              label: "Tarefas",
              content: (
                <div className="space-y-3">
                  <article className="rounded-md border border-border bg-bg-secondary p-3">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-semibold text-text-primary">Implementar exportacao PDF</h3>
                      <Badge variant="danger">Critica</Badge>
                    </div>
                    <p className="mt-2 text-sm text-text-secondary">Adicionar botao de exportar na tela de ata gerada</p>
                    <div className="mt-2 flex gap-3 text-xs text-text-secondary">
                      <span>Resp: Maria</span>
                      <span>Prazo: 15/05</span>
                    </div>
                  </article>
                  <article className="rounded-md border border-border bg-bg-secondary p-3">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-semibold text-text-primary">Revisar integracao API</h3>
                      <Badge variant="warning">Alta</Badge>
                    </div>
                    <p className="mt-2 text-sm text-text-secondary">Verificar endpoints de autenticacao</p>
                    <div className="mt-2 flex gap-3 text-xs text-text-secondary">
                      <span>Resp: Joao</span>
                      <span>Prazo: 20/05</span>
                    </div>
                  </article>
                </div>
              ),
            },
            {
              id: "resumo",
              label: "Resumo",
              content: (
                <div className="space-y-3 text-sm">
                  <div>
                    <h3 className="font-semibold text-text-primary">Resumo executivo</h3>
                    <p className="mt-1 text-text-secondary">Reuniao focada em prioridades do Q2. Decisoes tomadas sobre feature X e integracao legado.</p>
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">Riscos</h3>
                    <ul className="mt-1 list-disc pl-5 text-text-secondary">
                      <li>Prazo apertado para entrega da feature X</li>
                    </ul>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Panel>
    </section>
  );
}

function WidgetSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Widget de Gravacao (Preview)</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel title="Estado: Colapsado">
          <div className="flex items-center justify-center py-8">
            <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-accent shadow-elevated">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-bg-primary bg-danger animate-pulse" />
            </div>
          </div>
          <p className="text-center text-xs text-text-secondary">Icone flutuante no canto inferior direito</p>
        </Panel>

        <Panel title="Estado: Expandido">
          <div className="rounded-lg border border-border bg-surface">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-danger" />
                <span className="text-xs font-medium text-danger">REC</span>
                <span className="font-mono text-sm text-text-secondary">02:34</span>
              </div>
              <span className="text-text-secondary">X</span>
            </div>
            <div className="flex gap-2 border-b border-border px-4 py-3">
              <Button variant="secondary" className="flex-1 text-xs">Pausar</Button>
              <Button className="flex-1 text-xs">Finalizar</Button>
            </div>
            <div className="px-4 py-3">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">Transcricao ao vivo</h4>
              <div className="space-y-1 text-sm text-text-primary">
                <p>Joao: Entao vamos alinhar os proximos passos...</p>
                <p>Maria: Concordo, acho que devemos priorizar...</p>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </section>
  );
}

function MeetingListSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Lista de Reunioes</h2>
      <Panel title="Reunioes">
        <div className="space-y-2">
          <div className="rounded-md border border-accent bg-accent-muted px-3 py-2.5 text-left text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-text-primary">Alinhamento Q2</span>
              <Badge variant="success">Concluida</Badge>
            </div>
            <div className="mt-1 text-xs text-text-secondary">Empresa ABC</div>
          </div>
          <div className="rounded-md border border-border bg-surface px-3 py-2.5 text-left text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-text-primary">Sprint Planning 14</span>
              <Badge variant="accent">Processando</Badge>
            </div>
            <div className="mt-1 text-xs text-text-secondary">Time interno</div>
          </div>
          <div className="rounded-md border border-border bg-surface px-3 py-2.5 text-left text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-text-primary">Kickoff Projeto Y</span>
              <Badge variant="default">Rascunho</Badge>
            </div>
            <div className="mt-1 text-xs text-text-secondary">Cliente XYZ</div>
          </div>
        </div>
      </Panel>
    </section>
  );
}
