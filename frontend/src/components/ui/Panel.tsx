import type { ReactNode } from "react";

type PanelProps = {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  variant?: "glass" | "solid";
};

export function Panel({ title, actions, children, className = "", variant = "glass" }: PanelProps) {
  const base = variant === "glass"
    ? "glass rounded-glass"
    : "rounded-glass border border-glass-border bg-surface";

  return (
    <section className={`${base} p-5 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold text-text-primary">{title}</h2>}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
