"use client";

import { useEffect, useState } from "react";
import { getKeycloak, isDirigenza } from "@/lib/auth/keycloak";
import { useRouter } from "next/navigation";
import { DashboardFundraisingWidget } from "@/components/nft/DashboardFundraising";

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
];

const QUICK_ACTIONS = [
  {
    href: "/dirigenza/pricing",
    title: "Tariffe & Moltiplicatori",
    desc: "Modifica tariffe base, leve dinamiche e sconti promozionali",
    color: "bg-blue-600",
    icon: "💰",
  },
  {
    href: "/dirigenza/rendiconto",
    title: "Rendiconto 2027–2042",
    desc: "Genera il rendiconto per anno civile con dettaglio per fascia",
    color: "bg-violet-600",
    icon: "📊",
  },
  {
    href: "/staff/verifica",
    title: "Verifica accessi",
    desc: "Scansiona QR code NFT per la verifica accesso al Palasirion",
    color: "bg-gray-700",
    icon: "🔍",
  },
];

function LiveDot() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      Aggiornamento live ogni 5s
    </span>
  );
}

export default function DirigenzaPage() {
  const router = useRouter();
  const [ora, setOra] = useState("");

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc.authenticated || !isDirigenza(kc)) {
      router.push("/");
      return;
    }
    // Orologio live
    const tick = () => setOra(new Date().toLocaleTimeString("it-IT"));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [router]);

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
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <LiveDot />
          <span className="tabular-nums font-mono text-xs">{ora}</span>
          <a href="/" className="text-blue-600 hover:underline text-xs">← Sito principale</a>
        </div>
      </header>

      <div className="flex">
        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <aside className="w-52 shrink-0 bg-white border-r border-gray-200 min-h-[calc(100vh-53px)] pt-6 pb-4 px-3">
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const active = typeof window !== "undefined" && window.location.pathname === item.href;
              return (
                <a
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
                </a>
              );
            })}
          </nav>

          <div className="mt-8 px-3">
            <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-2">Periodo vendita</p>
            <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600 space-y-1">
              <div className="flex justify-between"><span>Inizio</span><span className="font-mono font-medium">01/01/2027</span></div>
              <div className="flex justify-between"><span>Fine</span><span className="font-mono font-medium">31/12/2042</span></div>
              <div className="flex justify-between"><span>Anni</span><span className="font-mono font-medium">16</span></div>
              <div className="flex justify-between"><span>Slot tot.</span><span className="font-mono font-medium">12.522</span></div>
            </div>
          </div>
        </aside>

        {/* ── Contenuto principale ───────────────────────────────────────── */}
        <main className="flex-1 p-6 max-w-5xl space-y-6">

          {/* Titolo pagina */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Palasirion — raccolta fondi NFT · periodo 2027–2042
            </p>
          </div>

          {/* Azioni rapide */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {QUICK_ACTIONS.map((a) => (
              <a
                key={a.href}
                href={a.href}
                className="group rounded-xl border border-gray-200 bg-white p-4 hover:border-blue-200 hover:shadow-sm transition"
              >
                <div className="flex items-start gap-3">
                  <div className={`${a.color} rounded-lg w-9 h-9 flex items-center justify-center text-lg shrink-0`}>
                    {a.icon}
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-gray-900 group-hover:text-blue-700 transition">
                      {a.title}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5 leading-snug">{a.desc}</div>
                  </div>
                </div>
              </a>
            ))}
          </div>

          {/* Widget fundraising completo */}
          <DashboardFundraisingWidget />
        </main>
      </div>
    </div>
  );
}
