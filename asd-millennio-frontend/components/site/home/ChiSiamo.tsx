import Link from "next/link";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { siteConfig } from "@/lib/site";

const facts = [
  { k: "Realtà", v: "Polisportiva dilettantistica" },
  { k: "Sede", v: siteConfig.city },
  { k: "Impianto", v: siteConfig.venue },
  { k: "Dal", v: String(siteConfig.founded) },
];

/** Sezione "Chi siamo" (teaser): testo introduttivo + scheda fatti chiave. */
export function ChiSiamo() {
  return (
    <Section id="chi-siamo">
      <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
        <Reveal>
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-brand-600">
            Chi siamo
          </p>
          <h2 className="font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Una grande famiglia sportiva a {siteConfig.city}
          </h2>
          <div className="mt-5 space-y-4 text-lg leading-relaxed text-slate-600">
            <p>
              Dal {siteConfig.founded} la polisportiva {siteConfig.shortName} promuove lo sport e i
              suoi valori presso l&apos;impianto {siteConfig.venue}: rispetto, impegno, divertimento
              e senso di comunità.
            </p>
            <p>
              Offriamo discipline diverse per bambini, ragazzi e adulti, con un&apos;attenzione
              particolare alla crescita personale, oltre che sportiva, di ogni tesserato.
            </p>
          </div>
          <Link
            href="/chi-siamo"
            className="mt-6 inline-flex items-center gap-1 font-semibold text-brand-600 transition-colors hover:text-brand-700"
          >
            Scopri la nostra storia
            <span aria-hidden="true">→</span>
          </Link>
        </Reveal>

        <Reveal delay={120}>
          <dl className="grid grid-cols-2 gap-4">
            {facts.map((f) => (
              <div
                key={f.k}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm"
              >
                <dt className="text-sm font-medium uppercase tracking-wide text-slate-500">{f.k}</dt>
                <dd className="mt-1 font-display text-xl font-bold text-slate-900">{f.v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </div>
    </Section>
  );
}
