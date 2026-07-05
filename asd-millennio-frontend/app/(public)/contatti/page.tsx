import type { Metadata } from "next";
import { PageHeader } from "@/components/site/PageHeader";
import { Section } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { ContactForm } from "@/components/site/ContactForm";
import { SocialIcons } from "@/components/site/SocialIcons";
import { siteConfig } from "@/lib/site";

export const metadata: Metadata = {
  title: "Contatti",
  description: `Contatta la Polisportiva Millennio a ${siteConfig.city}: ${siteConfig.contact.address}. Telefono ${siteConfig.contact.phone}, email ${siteConfig.contact.email}.`,
  alternates: { canonical: "/contatti" },
};

const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  siteConfig.contact.mapsQuery,
)}`;

export default function ContattiPage() {
  const { contact } = siteConfig;
  return (
    <>
      <PageHeader
        eyebrow="Contatti"
        title="Contattaci"
        subtitle="Hai domande sui corsi, le iscrizioni o il Palasirio? Scrivici: ti risponderemo al più presto."
      />

      <Section>
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
          {/* Form */}
          <Reveal>
            <h2 className="font-display text-2xl font-bold text-slate-900">Scrivici un messaggio</h2>
            <p className="mt-2 text-slate-600">I campi con * sono obbligatori.</p>
            <div className="mt-6">
              <ContactForm />
            </div>
          </Reveal>

          {/* Recapiti */}
          <Reveal delay={120}>
            <div className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
                <h2 className="font-display text-2xl font-bold text-slate-900">Dove siamo</h2>
                <ul className="mt-5 space-y-4 text-slate-700">
                  <li className="flex items-start gap-3">
                    <Icon path="M12 21s-6-5.686-6-10a6 6 0 1112 0c0 4.314-6 10-6 10z M12 11a2 2 0 100-4 2 2 0 000 4z" />
                    <span>
                      {contact.address}
                      <br />
                      <span className="text-sm text-slate-500">Impianto {siteConfig.venue}</span>
                    </span>
                  </li>
                  <li className="flex items-center gap-3">
                    <Icon path="M2 5a2 2 0 012-2h2.6a1 1 0 01.95.68l1 3a1 1 0 01-.27 1.05l-1.4 1.4a14 14 0 006 6l1.4-1.4a1 1 0 011.05-.27l3 1a1 1 0 01.68.95V19a2 2 0 01-2 2A16 16 0 012 5z" />
                    <a href={`tel:${contact.phone.replace(/\s/g, "")}`} className="hover:text-brand-700">
                      {contact.phone}
                    </a>
                  </li>
                  <li className="flex items-center gap-3">
                    <Icon path="M3 6h18v12H3z M3 7l9 6 9-6" />
                    <a href={`mailto:${contact.email}`} className="break-all hover:text-brand-700">
                      {contact.email}
                    </a>
                  </li>
                </ul>
                <a
                  href={mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
                >
                  Apri su Google Maps
                  <span aria-hidden="true">↗</span>
                </a>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="font-display text-lg font-bold text-slate-900">Seguici</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Foto, video e aggiornamenti dalle nostre attività.
                </p>
                <SocialIcons className="mt-4 flex gap-3" tone="light" />
              </div>
            </div>
          </Reveal>
        </div>
      </Section>
    </>
  );
}

/** Iconcina inline per i recapiti. */
function Icon({ path }: { path: string }) {
  return (
    <svg
      className="mt-0.5 h-5 w-5 shrink-0 text-brand-600"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}
