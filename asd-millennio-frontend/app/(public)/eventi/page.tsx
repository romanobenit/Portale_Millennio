import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Cta } from "@/components/site/home/Cta";
import { eventi } from "@/lib/site";

export const metadata: Metadata = {
  title: "Eventi e tornei",
  description:
    "Gli eventi della Polisportiva Millennio: la Baddy Cup, il Trofeo Vesuvio e i viaggi sportivi in Europa. Badminton, scuole e comunità a Cercola.",
  alternates: { canonical: "/eventi" },
};

export default function EventiPage() {
  return (
    <>
      <PageHeader
        eyebrow="Eventi"
        title="Eventi e tornei"
        subtitle="Gli appuntamenti che animano la nostra comunità sportiva."
      />

      <Section>
        <ul className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {eventi.map((e, i) => (
            <Reveal as="li" key={e.titolo} delay={i * 80}>
              <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                    {e.tag}
                  </span>
                </div>
                <h2 className="mt-4 font-display text-xl font-bold text-slate-900">{e.titolo}</h2>
                <p className="mt-1 text-sm font-medium text-slate-500">{e.ricorrenza}</p>
                <p className="mt-3 flex-1 leading-relaxed text-slate-600">{e.descr}</p>
              </article>
            </Reveal>
          ))}
        </ul>

        <p className="mt-10 text-center text-sm text-slate-500">
          Per conoscere le prossime date, seguici sui social o contattaci.
        </p>
      </Section>

      <Cta />
    </>
  );
}
