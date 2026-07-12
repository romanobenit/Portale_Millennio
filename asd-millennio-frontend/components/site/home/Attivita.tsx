import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { DisciplinaCard } from "@/components/site/DisciplinaCard";
import { discipline } from "@/lib/site";

/** Sezione "Attività" della home: griglia delle discipline (card condivise). */
export function Attivita() {
  return (
    <Section id="attivita" muted>
      <SectionHeading
        eyebrow="Attività"
        title="Le nostre discipline"
        subtitle="Tante proposte sportive per ogni età e livello, tutte presso il Palasirio."
      />
      <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {discipline.map((d, i) => (
          <Reveal as="li" key={d.slug} delay={i * 80}>
            <DisciplinaCard d={d} />
          </Reveal>
        ))}
      </ul>
    </Section>
  );
}
