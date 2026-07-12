"use client";

import { DashboardFundraisingWidget } from "@/components/nft/DashboardFundraising";

// L'autenticazione e la chrome (header + sidebar) sono gestite da app/dirigenza/layout.tsx
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
    href: "/dirigenza/campi",
    title: "Gestione Campi",
    desc: "Configura gli slot prenotabili: orari, numero campi e tariffe",
    color: "bg-emerald-600",
    icon: "🏸",
  },
  {
    href: "/staff/verifica",
    title: "Verifica accessi",
    desc: "Scansiona QR code NFT per la verifica accesso al Palasirio",
    color: "bg-gray-700",
    icon: "🔍",
  },
];

export default function DirigenzaPage() {
  return (
    <div className="space-y-6">
      {/* Titolo pagina */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Palasirio — raccolta fondi NFT · periodo 2027–2042
        </p>
      </div>

      {/* Azioni rapide */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
    </div>
  );
}
