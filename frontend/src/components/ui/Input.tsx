import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
};

export function Input({ label, className = "", id, ...props }: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-sm font-medium text-text-secondary">{label}</span>
      )}
      <input id={inputId} className={`input ${className}`} {...props} />
    </label>
  );
}

export function Textarea({ label, className = "", id, ...props }: TextareaProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-sm font-medium text-text-secondary">{label}</span>
      )}
      <textarea id={inputId} className={`input min-h-20 resize-y ${className}`} {...props} />
    </label>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-text-secondary">{label}</span>
      {children}
    </label>
  );
}
