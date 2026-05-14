import { Icon } from "./Icon";

type TabItem = {
  value: string;
  label: string;
  icon?: string;
};

type TabsProps = {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
};

export function Tabs({ items, value, onChange }: TabsProps) {
  return (
    <div
      style={{
        display: "inline-flex",
        padding: 4,
        gap: 4,
        background: "var(--chip-bg)",
        borderRadius: 12,
        border: "1px solid var(--line)",
      }}
    >
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          className="btn"
          style={{
            padding: "8px 14px",
            fontSize: 13,
            borderRadius: 9,
            background: value === it.value ? "var(--glass-bg-strong)" : "transparent",
            color: value === it.value ? "var(--text)" : "var(--text-dim)",
            boxShadow: value === it.value ? "inset 0 1px 0 var(--glass-inner)" : "none",
          }}
        >
          {it.icon && <Icon name={it.icon} />}
          {it.label}
        </button>
      ))}
    </div>
  );
}
