import { type ReactNode } from "react";
import { clsx } from "clsx";
import { Container } from "./Container";

/**
 * Sezione di pagina con spaziatura verticale coerente e (opzionale) intestazione.
 * `id` consente l'ancoraggio per la navigazione interna.
 */
export function Section({
  id,
  children,
  className,
  containerClassName,
  muted = false,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  containerClassName?: string;
  /** Sfondo grigio chiaro alternato per ritmo visivo. */
  muted?: boolean;
}) {
  return (
    <section
      id={id}
      className={clsx("py-16 sm:py-20 lg:py-24", muted && "bg-slate-50", className)}
    >
      <Container className={containerClassName}>{children}</Container>
    </section>
  );
}

/** Intestazione di sezione: occhiello + titolo + sottotitolo, centrabile. */
export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
  className,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  align?: "center" | "left";
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "max-w-2xl",
        align === "center" ? "mx-auto text-center" : "text-left",
        className,
      )}
    >
      {eyebrow && (
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-brand-600">
          {eyebrow}
        </p>
      )}
      <h2 className="font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
        {title}
      </h2>
      {subtitle && <p className="mt-4 text-lg leading-relaxed text-slate-600">{subtitle}</p>}
    </div>
  );
}
