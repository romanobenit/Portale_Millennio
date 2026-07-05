import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Counter } from "@/components/site/Counter";
import { siteConfig, discipline, valori } from "@/lib/site";

/** "Perché sceglierci": contatori animati (anni, discipline) + griglia dei valori. */
export function PercheSceglierci() {
  const anni = new Date().getFullYear() - siteConfig.founded;

  return (
    <Section id="perche">
      <SectionHeading
        eyebrow="Perché sceglierci"
        title="Sport con valore, dal 2009"
        subtitle="Esperienza, attenzione alla persona e una comunità che cresce ogni anno."
      />

      {/* Contatori */}
      <Reveal className="mt-12">
        <dl className="mx-auto grid max-w-2xl grid-cols-2 gap-8 text-center">
          <div className="rounded-2xl bg-brand-50 p-8">
            <dd className="font-display text-5xl font-extrabold text-brand-600">
              <Counter to={anni} suffix="+" />
            </dd>
            <dt className="mt-2 font-medium text-slate-600">Anni di attività</dt>
          </div>
          <div className="rounded-2xl bg-brand-50 p-8">
            <dd className="font-display text-5xl font-extrabold text-brand-600">
              <Counter to={discipline.length} suffix="+" />
            </dd>
            <dt className="mt-2 font-medium text-slate-600">Discipline sportive</dt>
          </div>
        </dl>
      </Reveal>

      {/* Valori */}
      <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {valori.map((v, i) => (
          <Reveal as="li" key={v.titolo} delay={i * 80}>
            <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <span
                className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white"
                aria-hidden="true"
              >
                {/* check icon */}
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m5 13 4 4L19 7" />
                </svg>
              </span>
              <h3 className="font-display text-lg font-bold text-slate-900">{v.titolo}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{v.descr}</p>
            </div>
          </Reveal>
        ))}
      </ul>
    </Section>
  );
}
