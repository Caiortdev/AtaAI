import { Badge } from "./components/ui/Badge";
import { Button } from "./components/ui/Button";
import { Field } from "./components/ui/Input";
import { Panel } from "./components/ui/Panel";
import { Tabs } from "./components/ui/Tabs";
import { ThemeToggle } from "./components/ThemeToggle";

export function DesignSystemDemo() {
  return (
    <div className="min-h-screen p-8">
      <div className="mx-auto max-w-5xl space-y-10">
        <header className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="glass flex h-10 w-10 items-center justify-center rounded-glass-sm text-base font-bold text-accent">
                A
              </div>
              <div>
                <span className="text-lg font-semibold text-text-primary">AtaAI</span>
                <p className="text-xs text-text-secondary">Liquid Glass Design System</p>
              </div>
            </div>
          </div>
          <ThemeToggle />
        </header>

        <ColorsSection />
        <GlassSection />
        <ButtonsSection />
        <BadgesSection />
        <InputsSection />
        <PanelsSection />
        <TabsSection />
        <WidgetSection />
        <MeetingListSection />
      </div>
    </div>
  );
}

function ColorsSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Cores</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-5">
        <ColorSwatch label="Accent" className="bg-accent" />
        <ColorSwatch label="Danger" className="bg-danger" />
        <ColorSwatch label="Success" className="bg-success" />
        <ColorSwatch label="Warning" className="bg-warning" />
        <ColorSwatch label="Text Primary" className="bg-text-primary" />
      </div>
    </section>
  );
}

function GlassSection() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Glass Layers</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="glass rounded-glass p-6 text-center">
          <p className="text-sm font-medium text-text-primary">Glass</p>
          <p className="mt-1 text-xs text-text-secondary">blur 20px + border highlight</p>
        </div>
        <div className="glass-lg rounded-glass p-6 text-center">
          <p className="text-sm font-medium text-text-primary">Glass LG</p>
          <p className="mt-1 text-xs text-text-secondary">blur 40px + stronger shadow</p>
        </div>
        <div className="glass-subtle rounded-glass p-6 text-center">
          <p className="text-sm font-medium text-text-primary">Glass Subtle</p>
          <p className="mt-1 text-xs text-text-secondary">blur 12px + minimal</p>
        </div>
      </div>
    </section>
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
            Painel com efeito glass, titulo e acoes no header.
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
