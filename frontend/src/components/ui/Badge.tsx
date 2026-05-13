import type { ReactNode } from "react";

type BadgeVariant = "default" | "accent" | "success" | "warning" | "danger";

type BadgeProps = {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
};

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-white/40 dark:bg-white/10 text-text-secondary",
  accent: "bg-[var(--color-accent)]/12 text-accent",
  success: "bg-[var(--color-success)]/12 text-success",
  warning: "bg-[var(--color-warning)]/12 text-warning",
  danger: "bg-[var(--color-danger)]/12 text-danger",
};

export function Badge({ variant = "default", children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium backdrop-blur-sm ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
