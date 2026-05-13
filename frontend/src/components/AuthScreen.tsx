import { type FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { loginUser, registerUser } from "../api";
import type { AuthPayload, RegisterPayload, User } from "../types";
import { Button } from "./ui/Button";
import { Field } from "./ui/Input";

type AuthScreenProps = {
  onSuccess: (accessToken: string, user: User) => void;
};

export function AuthScreen({ onSuccess }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState<RegisterPayload>({ name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);

  const loginMutation = useMutation({
    mutationFn: (payload: AuthPayload) => loginUser(payload),
    onSuccess: (session) => onSuccess(session.access_token, session.user),
    onError: (err) => setError(err.message),
  });

  const registerMutation = useMutation({
    mutationFn: (payload: RegisterPayload) => registerUser(payload),
    onSuccess: (session) => onSuccess(session.access_token, session.user),
    onError: (err) => setError(err.message),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (mode === "register") {
      registerMutation.mutate(form);
      return;
    }
    loginMutation.mutate({ email: form.email, password: form.password });
  }

  const isPending = loginMutation.isPending || registerMutation.isPending;

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg-primary px-5">
      <section className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-elevated">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-bold text-white">
            A
          </div>
          <span className="text-sm font-semibold text-accent">AtaAI</span>
        </div>
        <h1 className="mt-4 text-2xl font-semibold text-text-primary">
          {mode === "login" ? "Entrar na conta" : "Criar conta"}
        </h1>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          {mode === "register" && (
            <Field label="Nome">
              <input
                className="input"
                minLength={2}
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
          )}

          <Field label="E-mail">
            <input
              className="input"
              minLength={5}
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>

          <Field label="Senha">
            <input
              className="input"
              minLength={8}
              required
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>

          {error && (
            <div className="rounded-md border border-danger/30 bg-danger-muted p-3 text-sm text-danger">
              {error}
            </div>
          )}

          <Button className="w-full" disabled={isPending}>
            {isPending ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
          </Button>
        </form>

        <button
          className="mt-4 w-full text-sm font-medium text-accent transition hover:text-accent-hover"
          onClick={() => {
            setError(null);
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Criar uma nova conta" : "Entrar com uma conta existente"}
        </button>
      </section>
    </main>
  );
}
