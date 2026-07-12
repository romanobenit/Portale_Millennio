"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getKeycloak, initKeycloakOnce, isDirigenza } from "@/lib/auth/keycloak";
import { setAuthToken } from "@/lib/api/client";

/**
 * Layout dell'area /dirigenza:
 *  1. gate di autenticazione (inizializza Keycloak + verifica ruolo dirigenza);
 *  2. chrome condivisa (header + sidebar) per TUTTE le pagine dirigenza,
 *     così ognuna ha navigazione e ritorno all'area soci / sito pubblico.
 */

const NAV_ITEMS = [
  {
    href: "/dirigenza",
    label: "Dashboard",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: "/dirigenza/pricing",
    label: "Gestione Pricing",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    href: "/dirigenza/rendiconto",
    label: "Rendiconto annuale",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    href: "/dirigenza/campi",
    label: "Gestione Campi",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
      </svg>
    ),
  },
  {
    href: "/dirigenza/tesseramenti",
    label: "Verifiche tesseramenti",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    href: "/dirigenza/quote",
    label: "Quote tessera",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
];

function LiveDot() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      Live 5s
    </span>
  );
}

export default function DirigenzaLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [stato, setStato] = useState<"loading" | "ok" | "negato">("loading");
  const [ora, setOra] = useState("");

  useEffect(() => {
    // initKeycloakOnce usa un flag modulo-level: sicuro con StrictMode (doppio mount)
    initKeycloakOnce({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    })
      .then((authenticated) => {
        const kc = getKeycloak();
        if (!authenticated || !kc.token) {
          getKeycloak().login({ redirectUri: window.location.href });
          return;
        }
        setAuthToken(kc.token);
        kc.onTokenExpired = () => {
          kc.updateToken(60)
            .then((refreshed) => { if (refreshed && kc.token) setAuthToken(kc.token); })
            .catch(() => kc.login());
        };
        setStato(isDirigenza(kc) ? "ok" : "negato");
      })
      .catch((err) => {
        console.error("Keycloak init error (dirigenza):", err);
        setStato("negato");
      });
  }, []);

  useEffect(() => {
    const tick = () => setOra(new Date().toLocaleTimeString("it-IT"));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  const logout = () => getKeycloak().logout({ redirectUri: window.location.origin });

  if (stato === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
          <p className="text-sm text-gray-500">Accesso area dirigenza…</p>
        </div>
      </div>
    );
  }

  if (stato === "negato") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
        <div className="max-w-sm space-y-3 text-center">
          <h1 className="text-lg font-semibold text-gray-900">Accesso riservato</h1>
          <p className="text-sm text-gray-600">
            Quest&apos;area è riservata alla dirigenza: il tuo account non ha il ruolo necessario.
          </p>
          <Link href="/dashboard" className="inline-block text-sm font-medium text-blue-600 hover:underline">
            ← Torna alla tua area
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <span className="font-bold text-gray-900">ASD Millennio</span>
          <span className="text-gray-300">·</span>
          <span className="text-sm text-gray-500">Area dirigenza</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <LiveDot />
          <span className="tabular-nums font-mono text-xs text-gray-400 hidden sm:inline">{ora}</span>
          <Link href="/dashboard" className="text-blue-600 hover:underline text-xs font-medium">
            ← Area soci
          </Link>
          <a href="/" className="text-gray-400 hover:text-gray-600 text-xs">Sito pubblico</a>
          <button onClick={logout} className="text-gray-400 hover:text-gray-700 text-xs">Esci</button>
        </div>
      </header>

      <div className="flex">
        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <aside className="w-52 shrink-0 bg-white border-r border-gray-200 min-h-[calc(100vh-53px)] pt-6 pb-4 px-3">
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const active =
                item.href === "/dirigenza"
                  ? pathname === "/dirigenza"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition
                    ${active
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 px-3">
            <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-2">Periodo vendita</p>
            <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600 space-y-1">
              <div className="flex justify-between"><span>Inizio</span><span className="font-mono font-medium">01/01/2027</span></div>
              <div className="flex justify-between"><span>Fine</span><span className="font-mono font-medium">31/12/2042</span></div>
              <div className="flex justify-between"><span>Anni</span><span className="font-mono font-medium">16</span></div>
            </div>
          </div>
        </aside>

        {/* ── Contenuto (le pagine dirigenza) ───────────────────────────── */}
        <main className="flex-1 p-6 max-w-5xl">{children}</main>
      </div>
    </div>
  );
}
