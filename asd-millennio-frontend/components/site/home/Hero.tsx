import Image from "next/image";
import Link from "next/link";
import { Container } from "@/components/site/Container";
import { siteConfig, discipline, portalLinks } from "@/lib/site";

/**
 * Hero della home: foto d'azione (next/image, priority = LCP) con overlay brand
 * per garantire il contrasto del testo, titolo, CTA e statistiche.
 */
export function Hero() {
  return (
    <section className="relative isolate overflow-hidden bg-slate-900 text-white">
      {/* Foto di sfondo */}
      <Image
        src="/images/1.jpeg"
        alt=""
        fill
        priority
        sizes="100vw"
        className="absolute inset-0 -z-10 h-full w-full object-cover object-center"
      />
      {/* Overlay brand: più scuro in alto a sinistra (dove c'è il testo) */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-br from-brand-900/95 via-brand-900/80 to-slate-900/70"
      />
      <Container className="relative py-20 sm:py-28 lg:py-32">
        <div className="max-w-2xl">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-medium ring-1 ring-inset ring-white/20">
            <span className="h-1.5 w-1.5 rounded-full bg-white" aria-hidden="true" />
            {siteConfig.city} · dal {siteConfig.founded}
          </p>
          <h1 className="font-display text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Sport, crescita e comunità al {siteConfig.venue}
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-brand-50">
            {siteConfig.description}
          </p>
          <div className="mt-8 flex flex-wrap gap-3 sm:gap-4">
            <Link
              href={portalLinks.tesseramento}
              className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-brand-800 shadow-sm transition-colors hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Diventa socio
            </Link>
            <Link
              href={portalLinks.prenotaCampo}
              className="rounded-lg border-2 border-white/80 px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Prenota campo
            </Link>
            <Link
              href={portalLinks.raccoltaFondi}
              className="rounded-lg border-2 border-white/80 px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Raccolta fondi
            </Link>
          </div>

          <dl className="mt-12 grid max-w-md grid-cols-3 gap-6 border-t border-white/15 pt-8">
            <div>
              <dt className="text-sm text-brand-100">Dal</dt>
              <dd className="font-display text-2xl font-bold">{siteConfig.founded}</dd>
            </div>
            <div>
              <dt className="text-sm text-brand-100">Discipline</dt>
              <dd className="font-display text-2xl font-bold">{discipline.length}+</dd>
            </div>
            <div>
              <dt className="text-sm text-brand-100">Impianto</dt>
              <dd className="font-display text-2xl font-bold">{siteConfig.venue}</dd>
            </div>
          </dl>
        </div>
      </Container>
    </section>
  );
}
