import type { ReactNode, CSSProperties } from "react";
import { Glass } from "./Glass";

type PanelProps = {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  strong?: boolean;
  style?: CSSProperties;
};

export function Panel({ title, actions, children, className = "", strong, style }: PanelProps) {
  return (
    <Glass strong={strong} className={className} style={{ padding: 24, ...style }}>
      {(title || actions) && (
        <div className="row between" style={{ marginBottom: 16 }}>
          {title && <div style={{ fontWeight: 700, fontSize: 15 }}>{title}</div>}
          {actions && <div className="row">{actions}</div>}
        </div>
      )}
      {children}
    </Glass>
  );
}
