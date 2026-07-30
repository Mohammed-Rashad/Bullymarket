import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${className}`} {...props} />;
}

export function Button({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`button ${className}`} {...props} />;
}

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`input ${className}`} {...props} />;
}

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-mark">◎</span>
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="notice error-notice" role="alert">
      {message}
    </div>
  );
}

export function Loading({ label = "Loading market data…" }: { label?: string }) {
  return (
    <div className="loading">
      <span className="loading-dot" />
      {label}
    </div>
  );
}

