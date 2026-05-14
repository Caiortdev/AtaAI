import type { ReactNode, CSSProperties } from "react";

type GlassProps = {
  strong?: boolean;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: () => void;
};

export function Glass({ strong, children, className = "", style, onClick }: GlassProps) {
  return (
    <div
      className={`${strong ? "glass-strong" : "glass"} ${className}`}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
