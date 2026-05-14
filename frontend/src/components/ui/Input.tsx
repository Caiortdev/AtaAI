import type { InputHTMLAttributes, TextareaHTMLAttributes, ReactNode } from "react";

type FieldProps = {
  label?: string;
  hint?: string;
  children: ReactNode;
};

export function Field({ label, hint, children }: FieldProps) {
  return (
    <div className="field">
      {label && <label className="field-label">{label}</label>}
      {children}
      {hint && <div className="muted" style={{ fontSize: 12 }}>{hint}</div>}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`input ${props.className || ""}`} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`textarea ${props.className || ""}`} />;
}
