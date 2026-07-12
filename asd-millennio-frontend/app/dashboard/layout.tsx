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
  { href: "/dashboard/nft", label: "Sostieni e scegli ore" },
  { href: "/dashboard/miei-nft", label: "Il mio sostegno" },
  { href: "/dashboard/tessere", label: "Le mie tessere" },
  { href: "/dashboard/minori", label: "I miei minori" },
  { href: "/dashboard/prenotazioni", label: "Prenota campo" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [nomeUtente, setNomeUtente] = useState("");
  const [authReady, setAuthReady] = useState(false);
  const [isDir, setIsDir] = useState(false);

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

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-700 text-white px-6 py-4 flex items-center justify-between shadow">
        <Link href="/" className="text-xl font-bold">ASD Millennio</Link>
        <div className="flex items-center gap-4">
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
      </header>

      <div className="flex flex-1">
        <nav className="w-56 bg-white border-r border-gray-200 p-4 space-y-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname === link.href
                  ? "bg-blue-700 text-white"
                  : "text-gray-700 hover:bg-gray-100"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <main className="flex-1 p-6 max-w-5xl">{children}</main>
      </div>
    </div>
  );
}
