import type { ReactNode, ButtonHTMLAttributes } from "react";
import { Icon } from "./Icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "lg";
  icon?: string;
  iconRight?: string;
  children?: ReactNode;
};

export function Button({
  variant = "primary",
  size,
  icon,
  iconRight,
  children,
  className = "",
  ...rest
}: ButtonProps) {
  const sizeClass = size === "lg" ? "btn-lg" : size === "sm" ? "btn-sm" : "";
  return (
    <button className={`btn btn-${variant} ${sizeClass} ${className}`} {...rest}>
      {icon && <Icon name={icon} weight="bold" />}
      {children}
      {iconRight && <Icon name={iconRight} weight="bold" />}
    </button>
  );
}
