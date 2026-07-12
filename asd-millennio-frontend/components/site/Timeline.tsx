import { Reveal } from "./Reveal";
import type { TappaStoria } from "@/lib/site";

/**
 * Timeline verticale (lista ordinata) con pallini e linea di connessione.
 * Layout flex robusto: colonna [pallino + linea] | contenuto. Animazione a cascata.
 */
export function Timeline({ items }: { items: TappaStoria[] }) {
  return (
    <ol className="mx-auto max-w-3xl">
      {items.map((t, i) => {
        const last = i === items.length - 1;
        return (
          <li key={t.label + i} className="flex gap-4 sm:gap-6">
            {/* colonna pallino + linea */}
            <div className="flex flex-col items-center" aria-hidden="true">
              <span className="mt-1.5 h-4 w-4 shrink-0 rounded-full bg-brand-600 ring-4 ring-brand-50" />
              {!last && <span className="my-1 w-0.5 grow bg-brand-100" />}
            </div>
            {/* contenuto */}
            <Reveal className={last ? "" : "pb-10"} delay={i * 60}>
              <span className="text-sm font-semibold uppercase tracking-wide text-brand-600">
                {t.label}
              </span>
              <h3 className="mt-1 font-display text-xl font-bold text-slate-900">{t.titolo}</h3>
              <p className="mt-1 leading-relaxed text-slate-600">{t.descr}</p>
            </Reveal>
          </li>
        );
      })}
    </ol>
  );
}
