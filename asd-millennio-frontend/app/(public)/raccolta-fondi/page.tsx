import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { SocialIcons } from "@/components/site/SocialIcons";
import { siteConfig } from "@/lib/site";

export const metadata: Metadata = {
  title: "Raccolta fondi Palasirio",
  description: "Stiamo preparando la raccolta fondi per il Palasirio: a breve tutti i dettagli.",
  alternates: { canonical: "/raccolta-fondi" },
};

export default function RaccoltaFondiPage() {
  return (
    <>
      <PageHeader
        eyebrow="Raccolta fondi"
        title="Stiamo preparando qualcosa per il Palasirio"
        subtitle="La pagina della raccolta fondi è in costruzione: a breve tutti i dettagli su come sostenerci."
      />

      <Section>
        <Reveal className="mx-auto max-w-xl text-center">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8 shadow-sm">
            <h2 className="font-display text-2xl font-bold text-slate-900">In arrivo</h2>
            <p className="mt-3 text-slate-600">
              Stiamo lavorando alla raccolta fondi per il Palasirio. Torna a trovarci presto, oppure
              seguici sui social per essere tra i primi a saperlo.
            </p>
            <SocialIcons className="mt-6 flex justify-center gap-3" tone="light" />
            <p className="mt-6 text-sm text-slate-500">
              Domande? Scrivici a{" "}
              <a href={`mailto:${siteConfig.contact.email}`} className="font-medium text-brand-700 hover:underline">
                {siteConfig.contact.email}
              </a>
              .
            </p>
          </div>
        </Reveal>
      </Section>
    </>
  );
}
