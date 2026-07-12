import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { DisciplinaCard } from "@/components/site/DisciplinaCard";
import { discipline, siteConfig } from "@/lib/site";

export const metadata: Metadata = {
  title: "Attività e discipline",
  description:
    "Le discipline della Polisportiva Millennio a Cercola: badminton, kung fu, pallavolo e pickleball. Corsi e allenamenti per tutte le età.",
  alternates: { canonical: "/attivita" },
};

export default function AttivitaPage() {
  return (
    <>
      <PageHeader
        eyebrow="Sport"
        title="Le nostre attività"
        subtitle={`Discipline per ogni età e livello, all'impianto ${siteConfig.venue} di ${siteConfig.city}.`}
      />
      <Section>
        <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {discipline.map((d, i) => (
            <Reveal as="li" key={d.slug} delay={i * 80}>
              <DisciplinaCard d={d} />
            </Reveal>
          ))}
        </ul>
      </Section>
    </>
  );
}
