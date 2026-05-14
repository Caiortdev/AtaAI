import type { ReactNode, CSSProperties } from "react";
import { Glass } from "./Glass";
import { Icon } from "./Icon";

type CardProps = {
  title?: string;
  subtitle?: string;
  icon?: string;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
};

export function Card({ title, subtitle, icon, action, children, className = "", style }: CardProps) {
  return (
    <Glass className={`card ${className}`} style={style}>
      {(title || icon || action) && (
        <div className="row between" style={{ marginBottom: subtitle ? 4 : 16 }}>
          <div className="row" style={{ gap: 12 }}>
            {icon && (
              <div className="card-icon">
                <Icon name={icon} weight="duotone" size={20} />
              </div>
            )}
            <div>
              {title && <div style={{ fontWeight: 700, fontSize: 15 }}>{title}</div>}
              {subtitle && <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>{subtitle}</div>}
            </div>
          </div>
          {action}
        </div>
      )}
      {children}
    </Glass>
  );
}
