import { useMemo } from "react";

type AvatarProps = {
  name: string;
  size?: number;
  color?: string;
};

export function Avatar({ name, size = 32, color }: AvatarProps) {
  const initials = name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
  const hue = useMemo(
    () => Math.abs([...name].reduce((a, c) => a + c.charCodeAt(0), 0)) % 360,
    [name],
  );

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color || `linear-gradient(135deg, oklch(65% 0.18 ${hue}), oklch(55% 0.2 ${(hue + 60) % 360}))`,
        display: "grid",
        placeItems: "center",
        fontWeight: 700,
        fontSize: size * 0.4,
        color: "white",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.3)",
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}
