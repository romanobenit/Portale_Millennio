import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/site/PageHeader";
import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Cta } from "@/components/site/home/Cta";
import { comeIscriversi, discipline, portalLinks } from "@/lib/site";

export const metadata: Metadata = {
  title: "Corsi e iscrizioni",
  description:
    "I corsi della Polisportiva Millennio a Cercola: come iscriversi, prova gratuita e tesseramento. Discipline per tutte le età al Palasirio.",
  alternates: { canonical: "/corsi" },
};

export default function CorsiPage() {
  return (
    <>
      <PageHeader
        eyebrow="Corsi"
        title="Corsi e iscrizioni"
        subtitle="Allenamenti per ogni età e livello. Ecco come unirti alla nostra polisportiva."
      />

      {/* Come iscriversi */}
      <Section>
        <SectionHeading eyebrow="Iscrizioni" title="Come iscriversi" />
        <ol className="mt-12 grid gap-6 sm:grid-cols-3">
          {comeIscriversi.map((s, i) => (
            <Reveal as="li" key={s.titolo} delay={i * 90}>
              <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <span
                  className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 font-display text-lg font-bold text-white"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <h3 className="font-display text-lg font-bold text-slate-900">{s.titolo}</h3>
                <p className="mt-2 leading-relaxed text-slate-600">{s.descr}</p>
              </div>
            </Reveal>
          ))}
        </ol>
        <div className="mt-10 text-center">
          <Link
            href={portalLinks.tesseramento}
            className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-6 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          >
            Diventa socio
          </Link>
        </div>
      </Section>

      {/* Offerta */}
      <Section muted>
        <SectionHeading
          eyebrow="Offerta"
          title="Le discipline disponibili"
          subtitle="Orari su richiesta: contatta la segreteria per i dettagli del gruppo più adatto a te."
        />
        <ul className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
          {discipline.map((d, i) => (
            <Reveal as="li" key={d.slug} delay={i * 70}>
              <Link
                href={`/attivita/${d.slug}`}
                className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:border-brand-200 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
              >
                <span className="text-2xl" aria-hidden="true">
                  {d.emoji}
                </span>
                <span>
                  <span className="block font-semibold text-slate-900">{d.nome}</span>
                  <span className="block text-sm text-slate-500">{d.tag}</span>
                </span>
              </Link>
            </Reveal>
          ))}
        </ul>
      </Section>

      <Cta />
    </>
  );
}
