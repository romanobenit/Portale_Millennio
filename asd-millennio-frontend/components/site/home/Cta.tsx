import Link from "next/link";
import { Container } from "@/components/site/Container";
import { Reveal } from "@/components/site/Reveal";
import { portalLinks } from "@/lib/site";

/** Banda CTA finale: invito al tesseramento + contatti. */
export function Cta() {
  return (
    <section className="bg-gradient-to-br from-brand-600 to-brand-800 text-white">
      <Container className="py-16 sm:py-20">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Pronto a iniziare?
          </h2>
          <p className="mt-4 text-lg text-brand-50">
            Unisciti alla polisportiva Millennio: scegli la tua disciplina e vieni a trovarci al
            Palasirio.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href={portalLinks.tesseramento}
              className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-brand-700 shadow-sm transition-colors hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Diventa socio
            </Link>
            <Link
              href="/contatti"
              className="rounded-lg border-2 border-white/80 px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Contattaci
            </Link>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
