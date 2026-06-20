import { type ReactNode } from "react";
import { clsx } from "clsx";

interface CardProps {
  className?: string;
  children: ReactNode;
  title?: string;
}

export function Card({ className, children, title }: CardProps) {
  return (
    <div className={clsx("rounded-xl border border-gray-200 bg-white p-6 shadow-sm", className)}>
      {title && <h2 className="mb-4 text-xl font-semibold text-gray-900">{title}</h2>}
      {children}
    </div>
  );
}
