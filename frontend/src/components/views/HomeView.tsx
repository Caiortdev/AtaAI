import { useQuery } from "@tanstack/react-query";

import { listMeetings } from "../../api";
import { useWorkspaceStore } from "../../store";
import { Icon } from "../ui/Icon";
import { Glass } from "../ui/Glass";
import { Button } from "../ui/Button";
import { Chip } from "../ui/Chip";
import { Avatar } from "../ui/Avatar";

type HomeViewProps = {
  selectedPresetId: string | null;
  onSelectPreset: (id: string) => void;
  onNavigateToAtas: () => void;
};
export function HomeView({ selectedPresetId, onSelectPreset, onNavigateToAtas }: HomeViewProps) {
  const accessToken = useWorkspaceStore((s) => s.accessToken);
  const selectMeeting = useWorkspaceStore((s) => s.selectMeeting);
  const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);

  const meetingsQuery = useQuery({
    queryKey: ["meetings", accessToken],
    queryFn: listMeetings,
    enabled: Boolean(accessToken),
  });

  const meetings = meetingsQuery.data ?? [];
  const processing = meetings.find((m) => m.status === "processing" || m.status === "queued");
  const recents = meetings.filter((m) => m.status === "completed").slice(0, 5);

  return (
    <div className="page" style={{ maxWidth: 1080 }}>
      <div style={{ margin: "8px 0 28px" }}>
        <div className="muted" style={{ fontSize: 13, fontWeight: 600, letterSpacing: 0.04, textTransform: "uppercase", marginBottom: 6 }}>
          {new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}
        </div>
        <h1 className="page-title" style={{ fontSize: 36 }}>Boa tarde</h1>
        <p className="page-sub" style={{ fontSize: 16 }}>
          {processing
            ? <>Uma reuniao esta processando</>
            : "Tudo em dia."}
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 28 }}>
        <QuickAction
          icon="microphone-stage"
          title="Gravar agora"
          desc="Inicie uma sessao ao vivo com transcricao em tempo real."
          tone="danger"
          onClick={() => setActiveTab("capture")}
        />
        <QuickAction
          icon="cloud-arrow-up"
          title="Subir arquivo"
          desc="Audio ou video ja gravado — a IA gera a ata sozinha."
          tone="accent"
          onClick={() => setActiveTab("estudio")}
        />
      </div>
      {processing && (
        <Glass className="hover-lift" style={{ padding: 22, marginBottom: 28, cursor: "pointer" }} onClick={onNavigateToAtas}>
          <div className="row" style={{ gap: 18 }}>
            <div style={{ width: 48, height: 48, borderRadius: 14, flexShrink: 0, background: "oklch(80% 0.16 80 / 0.18)", color: "oklch(82% 0.16 80)", display: "grid", placeItems: "center" }}>
              <Icon name="circle-notch" weight="duotone" size={26} style={{ animation: "spin 2s linear infinite" }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="row" style={{ gap: 8, marginBottom: 4 }}>
                <Chip tone="warn" icon="circle-notch">Processando</Chip>
              </div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{processing.title}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>{processing.client_name || "Sem cliente"}</div>
            </div>
            <Icon name="arrow-right" size={20} style={{ color: "var(--text-mute)" }} />
          </div>
        </Glass>
      )}

      <div>
        <div className="row between" style={{ marginBottom: 14 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 17 }}>Reunioes recentes</div>
            <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>Suas ultimas atas geradas</div>
          </div>
          <Button variant="ghost" size="sm" iconRight="arrow-right" onClick={onNavigateToAtas}>Ver todas</Button>
        </div>
        {recents.length > 0 ? (
          <Glass style={{ padding: 8 }}>
            <div className="col" style={{ gap: 2 }}>
              {recents.map((r, i) => (
                <RecentItem key={r.id} title={r.title} client={r.client_name || "Sem cliente"} participants={r.participants || []} divider={i < recents.length - 1} onClick={() => { selectMeeting(r.id); onNavigateToAtas(); }} />
              ))}
            </div>
          </Glass>
        ) : (
          <Glass style={{ padding: 40, textAlign: "center" }}>
            <Icon name="file-magnifying-glass" weight="duotone" size={36} style={{ color: "var(--text-mute)", marginBottom: 10 }} />
            <div className="muted">Nenhuma ata gerada ainda.</div>
          </Glass>
        )}
      </div>
    </div>
  );
}

function QuickAction({ icon, title, desc, tone, onClick }: { icon: string; title: string; desc: string; tone: "accent" | "danger"; onClick: () => void }) {
  return (
    <Glass strong className="hover-lift" onClick={onClick} style={{ padding: 26, cursor: "pointer", position: "relative", overflow: "hidden", minHeight: 168 }}>
      <div style={{ position: "absolute", top: -40, right: -40, width: 180, height: 180, borderRadius: "50%", background: tone === "accent" ? "var(--accent-glow)" : "oklch(70% 0.22 25 / 0.4)", filter: "blur(20px)", pointerEvents: "none" }} />
      <div style={{ position: "relative", zIndex: 1, height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div style={{ width: 52, height: 52, borderRadius: 15, background: tone === "accent" ? "linear-gradient(135deg, var(--accent), oklch(60% 0.22 calc(var(--accent-h) + 30)))" : "linear-gradient(135deg, oklch(70% 0.22 25), oklch(65% 0.2 5))", color: "white", display: "grid", placeItems: "center", boxShadow: tone === "accent" ? "0 12px 30px -6px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.3)" : "0 12px 30px -6px oklch(70% 0.22 25 / 0.5), inset 0 1px 0 rgba(255,255,255,0.3)" }}>
          <Icon name={icon} weight="fill" size={26} />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 19, letterSpacing: "-0.015em" }}>{title}</div>
          <div className="dim" style={{ fontSize: 13.5, marginTop: 4, maxWidth: 320 }}>{desc}</div>
          <div className="row" style={{ gap: 6, marginTop: 14, color: "var(--accent)", fontWeight: 600, fontSize: 13 }}>
            <span>Comecar</span>
            <Icon name="arrow-right" weight="bold" size={14} />
          </div>
        </div>
      </div>
    </Glass>
  );
}

function RecentItem({ title, client, participants, divider, onClick }: { title: string; client: string; participants: string[]; divider: boolean; onClick: () => void }) {
  return (
    <div onClick={onClick} className="row" style={{ gap: 14, padding: "14px 14px", borderRadius: 12, cursor: "pointer", transition: "all 0.15s var(--ease)", borderBottom: divider ? "1px solid var(--line)" : "none" }} onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--chip-bg)"; }} onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
      <div style={{ display: "flex", flexShrink: 0 }}>
        {participants.slice(0, 3).map((p, i) => (
          <div key={p} style={{ marginLeft: i > 0 ? -10 : 0, border: "2px solid var(--bg-1)", borderRadius: "50%" }}>
            <Avatar name={p} size={30} />
          </div>
        ))}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</div>
        <div className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>{client}</div>
      </div>
      <Icon name="caret-right" size={14} style={{ color: "var(--text-mute)" }} />
    </div>
  );
}
