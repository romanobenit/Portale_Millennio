import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Timeline } from "@/components/site/Timeline";
import { Cta } from "@/components/site/home/Cta";
import {
  siteConfig,
  storiaIntro,
  storiaTappe,
  visioneIntro,
  visionePilastri,
  visioneTagline,
} from "@/lib/site";

export const metadata: Metadata = {
  title: "Chi siamo",
  description:
    "La Polisportiva Millennio di Cercola: dal 2009 punto di riferimento per il badminton in Campania, arti marziali e pallavolo. Sport inclusivo per tutti.",
  alternates: { canonical: "/chi-siamo" },
};

export default function ChiSiamoPage() {
  return (
    <>
      <PageHeader
        eyebrow="La polisportiva"
        title="Chi siamo"
        subtitle={`Dal ${siteConfig.founded} sport, inclusione e comunità a ${siteConfig.city}.`}
      />

      {/* Storia */}
      <Section id="storia">
        <SectionHeading
          eyebrow="La nostra storia"
          title="Una storia che parte dal badminton"
        />
        <div className="mx-auto mt-8 max-w-3xl space-y-4 text-lg leading-relaxed text-slate-600">
          {storiaIntro.map((p, i) => (
            <Reveal key={i} delay={i * 80}>
              <p>{p}</p>
            </Reveal>
          ))}
        </div>
        <div className="mt-14">
          <Timeline items={storiaTappe} />
        </div>
      </Section>

      {/* Visione */}
      <Section id="visione" muted>
        <SectionHeading
          eyebrow="La nostra visione"
          title="Lo sport come diritto di tutti"
          subtitle={visioneIntro}
        />
        <ul className="mt-12 grid gap-6 md:grid-cols-3">
          {visionePilastri.map((p, i) => (
            <Reveal as="li" key={p.titolo} delay={i * 90}>
              <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <span
                  className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 font-display text-lg font-bold text-white"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <h3 className="font-display text-xl font-bold text-slate-900">{p.titolo}</h3>
                <p className="mt-2 leading-relaxed text-slate-600">{p.descr}</p>
              </div>
            </Reveal>
          ))}
        </ul>

        <Reveal className="mx-auto mt-12 max-w-3xl">
          <blockquote className="rounded-2xl border-l-4 border-brand-600 bg-white p-6 text-lg italic leading-relaxed text-slate-700 shadow-sm sm:p-8">
            {visioneTagline}
          </blockquote>
        </Reveal>
      </Section>

      <Cta />
    </>
  );
}
