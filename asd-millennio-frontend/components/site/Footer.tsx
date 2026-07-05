import Link from "next/link";
import { siteConfig, mainNav, portalLinks } from "@/lib/site";
import { Container } from "./Container";
import { Logo } from "./Logo";
import { SocialIcons } from "./SocialIcons";

/** Footer pubblico moderno: brand, navigazione, contatti, social, note legali. */
export function Footer() {
  const year = new Date().getFullYear();
  const { contact } = siteConfig;

  return (
    <footer className="bg-slate-900 text-slate-300">
      <Container className="py-14">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div className="lg:col-span-1">
            <Logo />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-400">
              Polisportiva dilettantistica a {siteConfig.city} dal {siteConfig.founded}. Sport,
              crescita e comunità presso l&apos;impianto {siteConfig.venue}.
            </p>
            <SocialIcons className="mt-6 flex gap-3" />
          </div>

          {/* Esplora */}
          <nav aria-label="Esplora">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Esplora</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {mainNav.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-slate-400 transition-colors hover:text-white">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* Servizi del portale */}
          <nav aria-label="Servizi">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Servizi</h2>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <Link href={portalLinks.tesseramento} className="text-slate-400 transition-colors hover:text-white">
                  Diventa socio
                </Link>
              </li>
              <li>
                <Link href={portalLinks.prenotaCampo} className="text-slate-400 transition-colors hover:text-white">
                  Prenota campo
                </Link>
              </li>
              <li>
                <Link href={portalLinks.raccoltaFondi} className="text-slate-400 transition-colors hover:text-white">
                  Raccolta fondi
                </Link>
              </li>
            </ul>
          </nav>

          {/* Contatti */}
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">Contatti</h2>
            <ul className="mt-4 space-y-2 text-sm text-slate-400">
              <li>{siteConfig.city}</li>
              {contact.address && <li>{contact.address}</li>}
              {contact.email && (
                <li>
                  <a href={`mailto:${contact.email}`} className="transition-colors hover:text-white">
                    {contact.email}
                  </a>
                </li>
              )}
              {contact.phone && (
                <li>
                  <a href={`tel:${contact.phone.replace(/\s/g, "")}`} className="transition-colors hover:text-white">
                    {contact.phone}
                  </a>
                </li>
              )}
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-white/10 pt-8 text-xs leading-relaxed text-slate-500">
          <p>
            © {year} {siteConfig.legalName}. Tutti i diritti riservati.
          </p>
          <p className="mt-2">
            I token NFT eventualmente proposti nella raccolta fondi non sono strumenti finanziari
            ai sensi della Direttiva MiFID II: rappresentano esclusivamente diritti d&apos;uso
            dell&apos;impianto {siteConfig.venue}.
          </p>
        </div>
      </Container>
    </footer>
  );
}
