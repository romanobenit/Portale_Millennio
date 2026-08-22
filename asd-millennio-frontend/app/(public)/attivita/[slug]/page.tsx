import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { Cta } from "@/components/site/home/Cta";
import { discipline, getDisciplina, portalLinks, siteConfig } from "@/lib/site";

type Params = { slug: string };

/** Pre-genera staticamente una pagina per ogni disciplina. */
export function generateStaticParams(): Params[] {
  return discipline.map((d) => ({ slug: d.slug }));
}

export function generateMetadata({ params }: { params: Params }): Metadata {
  const d = getDisciplina(params.slug);
  if (!d) return { title: "Disciplina non trovata" };
  return {
    title: d.nome,
    description: d.descr,
    alternates: { canonical: `/attivita/${d.slug}` },
  };
}

export default function DisciplinaPage({ params }: { params: Params }) {
  const d = getDisciplina(params.slug);
  if (!d) notFound();

  return (
    <>
      <PageHeader eyebrow={d.tag} title={d.nome} subtitle={d.descr} />

      <Section>
        <div className="grid gap-10 lg:grid-cols-3 lg:gap-12">
          {/* Descrizione */}
          <div className="lg:col-span-2">
            <Reveal>
              {d.img ? (
                <div className="relative mb-6 aspect-[16/9] overflow-hidden rounded-2xl bg-slate-100">
                  <Image
                    src={d.img}
                    alt={`Foto della disciplina ${d.nome} alla Polisportiva Millennio`}
                    fill
                    sizes="(max-width: 1024px) 100vw, 66vw"
                    className="object-cover"
                    style={d.imgPosizione ? { objectPosition: d.imgPosizione } : undefined}
                  />
                </div>
              ) : (
                <span className="mb-6 block text-5xl" aria-hidden="true">
                  {d.emoji}
                </span>
              )}
              <p className="text-lg leading-relaxed text-slate-700">{d.lungo}</p>
              <p className="mt-4 leading-relaxed text-slate-600">
                Vieni a provare un allenamento: i nostri tecnici ti accoglieranno e ti aiuteranno a
                trovare il gruppo più adatto a te.
              </p>

              {d.video ? (
                <figure className="mt-8">
                  <div
                    className={`mx-auto overflow-hidden rounded-2xl bg-slate-900 shadow-lg ${
                      d.videoVerticale ? "max-w-[360px]" : "w-full"
                    }`}
                  >
                    {/* preload="metadata": scarica solo l'intestazione, non tutto il file.
                        Il poster resta l'anteprima visibile finché non si preme play. */}
                    <video
                      className={`w-full ${d.videoVerticale ? "aspect-[9/16]" : "aspect-video"}`}
                      src={d.video}
                      poster={d.videoPoster}
                      controls
                      preload="metadata"
                      playsInline
                    >
                      Il tuo browser non supporta la riproduzione dei video.{" "}
                      <a href={d.video}>Scarica il video</a>.
                    </video>
                  </div>
                  {d.videoDidascalia ? (
                    <figcaption className="mt-3 text-center text-sm text-slate-500">
                      {d.videoDidascalia}
                    </figcaption>
                  ) : null}
                </figure>
              ) : null}

              <div className="mt-8">
                <Link
                  href="/attivita"
                  className="inline-flex items-center gap-1 font-semibold text-brand-600 transition-colors hover:text-brand-700"
                >
                  <span aria-hidden="true">←</span> Tutte le attività
                </Link>
              </div>
            </Reveal>
          </div>

          {/* Info pratiche */}
          <aside>
            <Reveal delay={120}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                <h2 className="font-display text-lg font-bold text-slate-900">Info pratiche</h2>
                <dl className="mt-4 space-y-3 text-sm">
                  <div>
                    <dt className="font-medium text-slate-500">Sede</dt>
                    <dd className="text-slate-800">
                      {siteConfig.venue}, {siteConfig.city}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-slate-500">Orari</dt>
                    <dd className="text-slate-800">Su richiesta — in aggiornamento</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-slate-500">Referente</dt>
                    <dd className="text-slate-800">Contatta la segreteria</dd>
                  </div>
                </dl>
                <div className="mt-6 space-y-3">
                  <Link
                    href={portalLinks.tesseramento}
                    className="block rounded-lg bg-brand-600 px-4 py-2.5 text-center text-sm font-semibold text-white transition-colors hover:bg-brand-700"
                  >
                    Diventa socio
                  </Link>
                  <Link
                    href="/contatti"
                    className="block rounded-lg border border-slate-300 px-4 py-2.5 text-center text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-100"
                  >
                    Chiedi informazioni
                  </Link>
                </div>
              </div>
            </Reveal>
          </aside>
        </div>
      </Section>

      <Cta />
    </>
  );
}
