type IconProps = {
  name: string;
  weight?: "regular" | "fill" | "duotone" | "bold";
  size?: number;
  className?: string;
  style?: React.CSSProperties;
};

export function Icon({ name, weight = "regular", size, className = "", style }: IconProps) {
  const cls = `ph${weight === "regular" ? "" : `-${weight}`} ph-${name} ${className}`;
  return <i className={cls} style={{ fontSize: size, ...style }} />;
}
