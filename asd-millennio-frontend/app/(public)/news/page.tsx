import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { SocialIcons } from "@/components/site/SocialIcons";
import { news } from "@/lib/site";

export const metadata: Metadata = {
  title: "News",
  description:
    "Notizie, comunicazioni e aggiornamenti dalla Polisportiva Millennio di Cercola.",
  alternates: { canonical: "/news" },
};

function formatData(iso: string) {
  return new Date(iso).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

export default function NewsPage() {
  return (
    <>
      <PageHeader eyebrow="Aggiornamenti" title="News" subtitle="Le ultime novità dalla polisportiva." />

      <Section>
        {news.length === 0 ? (
          <Reveal className="mx-auto max-w-xl text-center">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-10">
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-600" aria-hidden="true">
                <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h16v14H4z M8 9h8 M8 13h5" />
                </svg>
              </span>
              <h2 className="mt-5 font-display text-xl font-bold text-slate-900">
                Nessuna notizia al momento
              </h2>
              <p className="mt-2 text-slate-600">
                Stiamo preparando questa sezione. Nel frattempo, seguici sui social per non perdere
                gli aggiornamenti dalle nostre attività.
              </p>
              <SocialIcons className="mt-6 flex justify-center gap-3" tone="light" />
            </div>
          </Reveal>
        ) : (
          <ul className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {news.map((n, i) => (
              <Reveal as="li" key={n.slug} delay={i * 80}>
                <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <time className="text-sm font-medium text-slate-500" dateTime={n.data}>
                    {formatData(n.data)}
                  </time>
                  <h2 className="mt-2 font-display text-xl font-bold text-slate-900">{n.titolo}</h2>
                  <p className="mt-3 flex-1 leading-relaxed text-slate-600">{n.estratto}</p>
                </article>
              </Reveal>
            ))}
          </ul>
        )}
      </Section>
    </>
  );
}
