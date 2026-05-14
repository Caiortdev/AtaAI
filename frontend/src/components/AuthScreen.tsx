import { useState } from "react";

import { loginUser, registerUser } from "../api";
import type { User } from "../types";
import { Icon } from "./ui/Icon";
import { Glass } from "./ui/Glass";
import { Button } from "./ui/Button";
import { Chip } from "./ui/Chip";
import { Field } from "./ui/Input";

type AuthScreenProps = {
  onSuccess: (token: string, user: User) => void;
};

export function AuthScreen({ onSuccess }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "login") {
        const session = await loginUser({ email, password });
        onSuccess(session.access_token, session.user);
      } else {
        const session = await registerUser({ email, password, name });
        onSuccess(session.access_token, session.user);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="bg-mesh"><div className="blob" /></div>
      <div className="grain" />
      <div style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", minHeight: "100vh", position: "relative", zIndex: 2 }}>
        {/* Left - branding */}
        <div style={{ padding: "48px 56px", position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div style={{ position: "absolute", top: "20%", left: "30%", width: 380, height: 380, borderRadius: "50%", background: "radial-gradient(circle, var(--accent-glow), transparent 70%)", filter: "blur(60px)", opacity: 0.4, pointerEvents: "none" }} />
          <div className="brand" style={{ position: "relative", zIndex: 1 }}>
            <div className="brand-mark" style={{ width: 38, height: 38, borderRadius: 11 }}>
              <Icon name="waveform" weight="fill" size={22} />
            </div>
            <div className="brand-name" style={{ fontSize: 18 }}>AtaAI <span>. beta</span></div>
          </div>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div className="row" style={{ gap: 6, marginBottom: 16 }}>
              <Chip tone="solid" icon="sparkle">IA generativa</Chip>
              <Chip icon="shield-check">LGPD</Chip>
            </div>
            <h1 style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.025em", margin: 0, lineHeight: 1.05, maxWidth: 500 }}>
              Reunioes que viram <em style={{ fontStyle: "normal", background: "linear-gradient(135deg, var(--accent), oklch(70% 0.22 320))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>atas acionaveis</em>, em minutos.
            </h1>
            <p className="dim" style={{ fontSize: 15.5, lineHeight: 1.6, marginTop: 18, maxWidth: 460 }}>
              Capture, transcreva e estruture reunioes — decisoes, tarefas e prazos extraidos automaticamente pela IA.
            </p>
          </div>
          <div className="row" style={{ gap: 18, position: "relative", zIndex: 1 }}>
            <StatItem label="atas geradas" value="142" />
            <StatItem label="horas transcritas" value="71" />
            <StatItem label="tempo medio" value="4 min" />
          </div>
        </div>

        {/* Right - form */}
        <div style={{ padding: "48px 56px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
          <Glass strong style={{ padding: 40, width: "100%", maxWidth: 420, borderRadius: 22 }}>
            <div style={{ marginBottom: 26 }}>
              <div style={{ fontWeight: 800, fontSize: 26, letterSpacing: "-0.02em" }}>
                {mode === "login" ? "Entrar" : "Criar conta"}
              </div>
              <div className="dim" style={{ fontSize: 14, marginTop: 6 }}>
                {mode === "login" ? "Acesse suas reunioes e atas." : "Comece gratis."}
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="col" style={{ gap: 14 }}>
                {mode === "signup" && (
                  <Field label="Nome completo">
                    <input className="input" placeholder="Seu nome" value={name} onChange={(e) => setName(e.target.value)} required />
                  </Field>
                )}
                <Field label="E-mail">
                  <input className="input" type="email" placeholder="seu@email.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </Field>
                <Field label="Senha">
                  <input className="input" type="password" placeholder="********" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>

                {error && <div style={{ padding: 12, borderRadius: 10, background: "oklch(70% 0.22 25 / 0.15)", color: "var(--recording)", fontSize: 13 }}>{error}</div>}

                <Button className="btn-lg" style={{ width: "100%", justifyContent: "center", marginTop: 4 }} icon={mode === "login" ? "sign-in" : "user-plus"} disabled={loading}>
                  {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
                </Button>
              </div>
            </form>
          </Glass>

          <div className="muted" style={{ fontSize: 13, marginTop: 22, textAlign: "center" }}>
            {mode === "login" ? "Nao tem conta? " : "Ja tem conta? "}
            <a onClick={() => setMode(mode === "login" ? "signup" : "login")} style={{ color: "var(--accent)", fontWeight: 700, cursor: "pointer" }}>
              {mode === "login" ? "Criar uma agora" : "Entrar"}
            </a>
          </div>
        </div>
      </div>
    </>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.01em" }}>{value}</div>
      <div className="muted" style={{ fontSize: 11.5, marginTop: 2, fontWeight: 500 }}>{label}</div>
    </div>
  );
}
