import type { ReactNode, CSSProperties } from "react";
import { Icon } from "./Icon";

type ChipProps = {
  tone?: "solid" | "success" | "warn" | "danger";
  icon?: string;
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
};

export function Chip({ tone, icon, children, style, className = "" }: ChipProps) {
  return (
    <span className={`chip ${tone || ""} ${className}`} style={style}>
      {icon && <Icon name={icon} size={13} />}
      {children}
    </span>
  );
}
