type StatusDotProps = {
  tone?: "success" | "warn" | "danger" | "accent";
};

export function StatusDot({ tone = "success" }: StatusDotProps) {
  const color =
    tone === "success" ? "var(--success)"
    : tone === "warn" ? "var(--warning)"
    : tone === "danger" ? "var(--recording)"
    : "var(--accent)";

  return <span className="dot pulse" style={{ color }} />;
}
