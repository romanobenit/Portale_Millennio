import { type ReactNode } from "react";
import { clsx } from "clsx";

/**
 * Contenitore centrato con padding orizzontale responsive e larghezza massima.
 * Riutilizzato da tutte le sezioni del sito pubblico per allineamento coerente.
 */
export function Container({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}) {
  return (
    <Tag className={clsx("mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8", className)}>
      {children}
    </Tag>
  );
}
