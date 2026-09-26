"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getKeycloak, initKeycloakOnce, isDirigenza } from "@/lib/auth/keycloak";
import { setAuthToken } from "@/lib/api/client";
import { fetchMe } from "@/lib/api/soci";
import { clsx } from "clsx";

const NAV_LINKS = [
  { href: "/dashboard", label: "Il mio profilo" },
  { href: "/raccolta-fondi", label: "Sostieni e scegli ore" },
  { href: "/dashboard/miei-nft", label: "Il mio sostegno" },
  { href: "/dashboard/tessere", label: "Le mie tessere" },
  { href: "/dashboard/minori", label: "I miei minori" },
  { href: "/dashboard/prenotazioni", label: "Prenota campo", highlight: true },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [nomeUtente, setNomeUtente] = useState("");
  const [authReady, setAuthReady] = useState(false);
  const [isDir, setIsDir] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  // Primo accesso: se non esiste ancora un profilo socio (/me → 404), porta al wizard.
  // L'interceptor axios riduce l'errore a Error(detail): il backend risponde
  // "Profilo non trovato" per il 404 di /me.
  useEffect(() => {
    if (!authReady || pathname === "/dashboard/onboarding") return;
    fetchMe().catch((e: unknown) => {
      if (e instanceof Error && e.message.toLowerCase().includes("profilo non trovato")) {
        router.replace("/dashboard/onboarding");
      }
    });
  }, [authReady, pathname, router]);

  useEffect(() => {
    // initKeycloakOnce usa un flag modulo-level: sicuro con StrictMode (doppio mount)
    initKeycloakOnce({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    })
      .then((authenticated) => {
        const kc = getKeycloak();
        if (authenticated && kc.token) {
          setAuthToken(kc.token);
          setNomeUtente(
            kc.tokenParsed?.["given_name"] ??
            kc.tokenParsed?.["preferred_username"] ??
            ""
          );
          kc.onTokenExpired = () => {
            kc.updateToken(60)
              .then((refreshed) => { if (refreshed && kc.token) setAuthToken(kc.token); })
              .catch(() => kc.login());
          };
          setIsDir(isDirigenza(kc));
          setAuthReady(true);
        } else {
          getKeycloak().login({ redirectUri: window.location.href });
        }
      })
      .catch((err) => {
        console.error("Keycloak init error:", err);
      });
  }, []);

  const handleLogout = () =>
    getKeycloak().logout({ redirectUri: window.location.origin });

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
          <p className="text-sm text-gray-500">Accesso in corso…</p>
        </div>
      </div>
    );
  }

  const navLinkClass = (href: string, highlight?: boolean) =>
    clsx(
      "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
      pathname === href
        ? "bg-blue-700 text-white"
        : highlight
          ? "bg-accent-500 text-white font-semibold hover:bg-accent-600"
          : "text-gray-700 hover:bg-gray-100"
    );

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 bg-blue-700 text-white px-4 md:px-6 py-3 md:py-4 flex items-center justify-between gap-3 shadow">
        <Link href="/" className="text-lg md:text-xl font-bold truncate">ASD Millennio</Link>

        <div className="hidden md:flex items-center gap-4">
          {nomeUtente && <span className="text-sm text-blue-100">Ciao, {nomeUtente}</span>}
          {isDir && (
            <Link
              href="/dirigenza"
              className="rounded-lg bg-white/15 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/25 transition-colors"
            >
              Area dirigenza →
            </Link>
          )}
          <Link
            href="/"
            className="text-sm text-blue-200 hover:text-white transition-colors"
          >
            Sito pubblico
          </Link>
          <button
            onClick={handleLogout}
            className="text-sm text-blue-200 hover:text-white transition-colors"
          >
            Esci
          </button>
        </div>

        <button
          type="button"
          className="md:hidden inline-flex items-center justify-center rounded-md p-2 -mr-2 text-white hover:bg-white/10"
          aria-expanded={menuOpen}
          aria-controls="dashboard-mobile-menu"
          aria-label={menuOpen ? "Chiudi menu" : "Apri menu"}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            )}
          </svg>
        </button>

      {menuOpen && (
        <nav
          id="dashboard-mobile-menu"
          aria-label="Area soci (mobile)"
          className="md:hidden absolute inset-x-0 top-full h-[calc(100dvh-100%)] overflow-y-auto bg-white p-4 space-y-1 shadow-lg"
        >
          {nomeUtente && <p className="px-3 pb-2 text-sm text-gray-500">Ciao, {nomeUtente}</p>}
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className={navLinkClass(link.href, link.highlight)}>
              {link.label}
            </Link>
          ))}
          <div className="my-3 border-t border-gray-200" />
          {isDir && (
            <Link href="/dirigenza" className="block rounded-lg px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50">
              Area dirigenza →
            </Link>
          )}
          <Link href="/" className="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100">
            Sito pubblico
          </Link>
          <button
            onClick={handleLogout}
            className="block w-full text-left rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Esci
          </button>
        </nav>
      )}
      </header>

      <div className="flex flex-1">
        <nav className="hidden md:block w-56 shrink-0 bg-white border-r border-gray-200 p-4 space-y-1">
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className={navLinkClass(link.href, link.highlight)}>
              {link.label}
            </Link>
          ))}
        </nav>

        <main className="flex-1 min-w-0 p-4 md:p-6 max-w-5xl">{children}</main>
      </div>
    </div>
  );
}
