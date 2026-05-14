import type { ReactNode } from "react";

type BadgeProps = {
  variant?: "default" | "accent" | "success" | "warning" | "danger";
  children: ReactNode;
};

export function Badge({ variant = "default", children }: BadgeProps) {
  const toneMap: Record<string, string> = {
    default: "",
    accent: "solid",
    success: "success",
    warning: "warn",
    danger: "danger",
  };
  return <span className={`chip ${toneMap[variant]}`}>{children}</span>;
}
