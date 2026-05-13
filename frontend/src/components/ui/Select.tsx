import type { ReactNode, SelectHTMLAttributes } from "react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  children: ReactNode;
};

export function Select({ label, className = "", children, id, ...props }: SelectProps) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-sm font-medium text-text-secondary">{label}</span>
      )}
      <select id={selectId} className={`input ${className}`} {...props}>
        {children}
      </select>
    </label>
  );
}
