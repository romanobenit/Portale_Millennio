import { Container } from "./Container";

/**
 * Intestazione standard delle pagine interne (banda brand con titolo).
 * Riutilizzata da tutte le pagine pubbliche per coerenza (Chi siamo, Attività, ...).
 */
export function PageHeader({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <section className="relative isolate overflow-hidden bg-gradient-to-br from-brand-700 via-brand-800 to-slate-900 text-white">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-20 [background:radial-gradient(50rem_25rem_at_75%_-20%,white,transparent)]"
      />
      <Container className="relative py-14 sm:py-20">
        {eyebrow && (
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-brand-100">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">{title}</h1>
        {subtitle && <p className="mt-4 max-w-2xl text-lg leading-relaxed text-brand-50">{subtitle}</p>}
      </Container>
    </section>
  );
}
