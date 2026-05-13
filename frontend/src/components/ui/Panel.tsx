import type { ReactNode } from "react";

type PanelProps = {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Panel({ title, actions, children, className = "" }: PanelProps) {
  return (
    <section
      className={`rounded-lg border border-border bg-surface p-4 shadow-panel ${className}`}
    >
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
