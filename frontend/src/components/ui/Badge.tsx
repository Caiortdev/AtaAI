import type { ReactNode } from "react";

type BadgeVariant = "default" | "accent" | "success" | "warning" | "danger";

type BadgeProps = {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
};

const variantStyles: Record<BadgeVariant, string> = {
  default: "border-border bg-bg-secondary text-text-secondary",
  accent: "border-accent/30 bg-accent-muted text-accent",
  success: "border-success/30 bg-success-muted text-success",
  warning: "border-warning/30 bg-warning-muted text-warning",
  danger: "border-danger/30 bg-danger-muted text-danger",
};

export function Badge({ variant = "default", children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
