import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { PageHeader } from "@/components/site/PageHeader";
import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Timeline } from "@/components/site/Timeline";
import type { TappaStoria } from "@/lib/site";

export const metadata: Metadata = {
  title: "Millennio Digitale",
  description:
    "Coding, creatività digitale e nuove tecnologie: dal 2014 la Polisportiva Millennio di Cercola porta la programmazione a ragazzi, scuole e docenti.",
  alternates: { canonical: "/millennio-digitale" },
};

const percorso: TappaStoria[] = [
  {
    label: "2014",
    titolo: "Nasce il Coderdojo di Cercola",
    descr:
      "Laboratorio gratuito di avvicinamento alla programmazione per bambini e ragazzi, con Scratch.",
  },
  {
    label: "2015",
    titolo: "Il settore e-sport",
    descr:
      "Nasce il settore di gioco elettronico competitivo (Dota 2), riconosciuto dal CONI tramite l'affiliazione all'ente di promozione sportiva ASI, con partecipazione a qualificazioni online di tornei internazionali.",
  },
  {
    label: "2016 – 2020",
    titolo: "Scuola Viva con l'Istituto Aldo Moro",
    descr:
      "Il coding entra nei progetti \"Scuola Viva\" dell'Istituto Comprensivo Aldo Moro di Napoli, con convenzioni, cronoprogrammi annuali e lavori realizzati dagli studenti.",
  },
  {
    label: "2021",
    titolo: "Undici percorsi nelle scuole",
    descr:
      "Una relazione tecnica ufficiale attesta 11 attività didattiche realizzate tra il 2014 e il 2020 in diversi istituti scolastici del territorio.",
  },
  {
    label: "2023 – 2026",
    titolo: "Una collaborazione che continua",
    descr:
      "Prosegue senza interruzioni il rapporto con l'Istituto Aldo Moro attraverso i bandi PON e Scuola Viva, fino all'anno scolastico 2025-26.",
  },
];

const strumenti = [
  { nome: "Scratch e Snap!", descr: "I primi passi: programmazione a blocchi, giochi e animazioni." },
  { nome: "App Inventor", descr: "Le prime app per smartphone, costruite e provate dai ragazzi." },
  {
    nome: "Python",
    descr: "Il linguaggio vero, con le librerie per il calcolo scientifico e il machine learning.",
  },
  { nome: "Django e GitHub", descr: "Siti web e lavoro di squadra sul codice, come nei progetti reali." },
];

const puntiForza = [
  "Oltre dieci anni di didattica digitale continuativa per ragazzi, in collaborazione con le scuole.",
  "Un percorso di programmazione che arriva al machine learning e al calcolo scientifico.",
  "Progetti presentati su bandi pubblici dedicati all'intelligenza artificiale (2023-2025).",
  "Un riconoscimento istituzionale (CONI / ASI) per le attività nel digitale.",
];

function Foto({
  src,
  alt,
  width,
  height,
  className,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  className?: string;
}) {
  return (
    <div className={`overflow-hidden rounded-2xl bg-slate-100 shadow-sm ${className ?? ""}`}>
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        sizes="(max-width: 1024px) 100vw, 50vw"
        className="h-auto w-full"
      />
    </div>
  );
}

export default function MillennioDigitalePage() {
  return (
    <>
      <PageHeader
        eyebrow="Coding e nuove tecnologie"
        title="Millennio Digitale"
        subtitle="Dal 2014 portiamo la programmazione e la creatività digitale a ragazzi, scuole e docenti."
      />

      {/* Introduzione */}
      <Section>
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <Reveal className="space-y-4 text-lg leading-relaxed text-slate-600">
            <p>
              Accanto a pallavolo, badminton, kung fu e pickleball, la Polisportiva Millennio ha costruito
              negli anni un settore dedicato alle <strong className="text-slate-900">competenze digitali</strong>,
              al <strong className="text-slate-900">coding</strong> e alle tecnologie emergenti.
            </p>
            <p>
              Non si tratta di iniziative occasionali: dal 2014 organizziamo laboratori e percorsi formativi
              su più anni, insieme agli istituti scolastici del territorio, con progettazione, verifica e
              rendicontazione regolari.
            </p>
            <p>Lo stesso spirito dello sport: imparare facendo, insieme, divertendosi.</p>
          </Reveal>
          <Reveal delay={100}>
            <Foto
              src="/images/digitale/laboratorio-coding-2.jpg"
              alt="Ragazzi al computer durante un laboratorio di coding con Scratch, con l'istruttore alla lavagna interattiva"
              width={1600}
              height={898}
            />
          </Reveal>
        </div>
      </Section>

      {/* Percorso */}
      <Section id="percorso" muted>
        <SectionHeading
          eyebrow="Il nostro percorso"
          title="Più di dieci anni di formazione digitale"
          subtitle="Un impegno documentato con continuità, dal primo Coderdojo ai progetti con le scuole di oggi."
        />
        <div className="mt-14">
          <Timeline items={percorso} />
        </div>
      </Section>

      {/* Coderdojo */}
      <Section id="coderdojo">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <Reveal className="lg:order-2">
            <SectionHeading
              align="left"
              eyebrow="Coderdojo Cercola"
              title="La domenica mattina si programma"
            />
            <div className="mt-6 space-y-4 text-lg leading-relaxed text-slate-600">
              <p>
                Il Coderdojo è un club gratuito dove bambini e ragazzi imparano a programmare creando
                giochi, storie animate e piccoli progetti con Scratch.
              </p>
              <p>
                Nell&apos;edizione 2016 ci siamo incontrati una domenica al mese, da gennaio a giugno, in
                Viale dei Tigli 8 a Cercola, dalle 10:30 alle 13:00.
              </p>
            </div>
          </Reveal>
          <Reveal delay={100} className="lg:order-1">
            <Foto
              src="/images/digitale/coderdojo-cercola-2016.jpg"
              alt="Locandina del Coderdojo Cercola 2016 con il calendario degli incontri della domenica"
              width={1046}
              height={579}
            />
          </Reveal>
        </div>
      </Section>

      {/* Pixel art */}
      <Section id="pixel-art" muted>
        <SectionHeading
          eyebrow="Imparare con le mani"
          title="Dal quadretto al codice"
          subtitle="Prima dello schermo, la carta a quadretti: i ragazzi disegnano un personaggio pixel per pixel, lo trascrivono riga per riga come una sequenza di numeri e colori e poi lo ricostruiscono con le perline. È così che un computer descrive un'immagine."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-5">
          <Reveal className="md:col-span-2">
            <Foto
              src="/images/digitale/pixel-art-mario.jpg"
              alt="Personaggio in pixel art disegnato su carta a quadretti, con il codice riga per riga e la versione in perline"
              width={1200}
              height={1600}
            />
          </Reveal>
          <Reveal delay={100} className="md:col-span-3">
            <Foto
              src="/images/digitale/pixel-art-parete.jpg"
              alt="Parete con i lavori in pixel art realizzati dai ragazzi: cuori, emoji, personaggi e i fogli con le sequenze di codifica"
              width={1600}
              height={1200}
            />
          </Reveal>
        </div>
      </Section>

      {/* Tecnologie emergenti e IA */}
      <Section id="intelligenza-artificiale">
        <SectionHeading
          eyebrow="Tecnologie emergenti"
          title="Verso l'intelligenza artificiale"
          subtitle="Il programma didattico della sezione Coding accompagna i ragazzi passo dopo passo, dai blocchi colorati fino al machine learning."
        />
        <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {strumenti.map((s, i) => (
            <Reveal as="li" key={s.nome} delay={i * 80}>
              <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <span
                  className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 font-display text-lg font-bold text-white"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <h3 className="font-display text-xl font-bold text-slate-900">{s.nome}</h3>
                <p className="mt-2 leading-relaxed text-slate-600">{s.descr}</p>
              </div>
            </Reveal>
          ))}
        </ul>
        <Reveal className="mx-auto mt-12 max-w-3xl space-y-4 text-lg leading-relaxed text-slate-600">
          <p>
            Tra il 2023 e il 2025 abbiamo elaborato proposte progettuali per bandi pubblici dedicati alle
            competenze digitali e all&apos;intelligenza artificiale, tra cui il bando{" "}
            <em>&ldquo;vIvA – Competenze Digitali IA e Made in Italy&rdquo;</em>, e abbiamo lavorato sul bando
            del Ministero della Cultura per la Transizione Digitale (PNRR 2023), dedicato a videogiochi,
            software e strumenti multimediali.
          </p>
        </Reveal>
      </Section>

      {/* In aula */}
      <Section id="in-aula" muted>
        <SectionHeading eyebrow="In aula" title="Coderdojo – IC Aldo Moro" />
        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <Reveal>
            <Foto
              src="/images/digitale/laboratorio-coding-1.jpg"
              alt="Ragazzi al lavoro sui computer durante un laboratorio di coding"
              width={1600}
              height={898}
            />
          </Reveal>
          <Reveal delay={100}>
            <Foto
              src="/images/digitale/laboratorio-coding-2.jpg"
              alt="Laboratorio di coding: i ragazzi programmano con Scratch mentre l'istruttore spiega alla lavagna interattiva"
              width={1600}
              height={898}
            />
          </Reveal>
        </div>
      </Section>

      {/* Sintesi + contatto */}
      <Section>
        <SectionHeading eyebrow="In sintesi" title="Cosa porta Millennio Digitale" />
        <ul className="mx-auto mt-10 grid max-w-4xl gap-4 sm:grid-cols-2">
          {puntiForza.map((p, i) => (
            <Reveal as="li" key={p} delay={i * 70}>
              <div className="flex h-full gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <svg
                  className="mt-0.5 h-6 w-6 shrink-0 text-brand-600"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <p className="leading-relaxed text-slate-700">{p}</p>
              </div>
            </Reveal>
          ))}
        </ul>
        <Reveal className="mx-auto mt-12 max-w-2xl text-center">
          <p className="text-lg leading-relaxed text-slate-600">
            Sei una scuola o un ente e vuoi organizzare un laboratorio o un corso di formazione per
            studenti o docenti?
          </p>
          <Link
            href="/contatti"
            className="mt-6 inline-flex items-center rounded-full bg-brand-600 px-6 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-brand-700"
          >
            Contattaci
          </Link>
        </Reveal>
      </Section>
    </>
  );
}
