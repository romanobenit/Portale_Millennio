"use client";

import { useEffect, useState } from "react";
import { fetchDashboardFundraising, type DashboardFundraising } from "@/lib/api/dirigenza";
import { Card } from "@/components/ui/Card";

type Fascia = "notte" | "mattina" | "pomeriggio";

const FASCIA_LABEL: Record<Fascia, string> = { notte: "Notte", mattina: "Mattina", pomeriggio: "Pomeriggio" };
const FASCIA_ORE_LABEL: Record<Fascia, string> = { notte: "00:00–07:59", mattina: "08:00–12:59", pomeriggio: "13:00–14:59" };
const FASCIA_BG: Record<Fascia, string> = { notte: "bg-indigo-50", mattina: "bg-blue-50", pomeriggio: "bg-violet-50" };
const FASCIA_TEXT: Record<Fascia, string> = { notte: "text-indigo-700", mattina: "text-blue-700", pomeriggio: "text-violet-700" };
const FASCIA_BAR: Record<Fascia, string> = { notte: "bg-indigo-400", mattina: "bg-blue-400", pomeriggio: "bg-violet-400" };
const FASCE: Fascia[] = ["notte", "mattina", "pomeriggio"];

function fmt(n: number) {
  return n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtInt(n: number) {
  return n.toLocaleString("it-IT");
}

export function DashboardFundraisingWidget() {
  const [data, setData] = useState<DashboardFundraising | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () =>
      fetchDashboardFundraising()
        .then(setData)
        .catch(() => {})
        .finally(() => setLoading(false));

    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          Caricamento dati fundraising…
        </div>
      </Card>
    );
  }
  if (!data) {
    return <Card><p className="text-red-500">Errore nel caricamento dei dati</p></Card>;
  }

  const pct = Math.min(data.percentuale, 100);
  const annoInizio = data.periodo_inizio.slice(0, 4);
  const annoFine = data.periodo_fine.slice(0, 4);
  const oreVenduteTotali = FASCE.reduce((s, f) => s + data.ore_vendute[f], 0);
  const oreTotaliPeriodo = FASCE.reduce((s, f) => s + data.ore_totali_periodo[f], 0);
  const pctCapacitaGlobale = oreTotaliPeriodo > 0 ? (oreVenduteTotali / oreTotaliPeriodo) * 100 : 0;

  return (
    <div className="space-y-6">

      {/* ── Sezione 1 — Raccolta fondi ──────────────────────────────────────── */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Raccolta fondi Palasirion</h2>
            <p className="text-xs text-gray-400 mt-0.5">Periodo di vendita: {annoInizio}–{annoFine}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-700">€{fmt(data.totale_raccolto_eur)}</div>
            <div className="text-xs text-gray-500">su obiettivo €{fmtInt(data.obiettivo_eur)}</div>
          </div>
        </div>

        {/* Progress bar principale */}
        <div className="mb-1">
          <div className="w-full bg-gray-100 rounded-full h-7 overflow-hidden relative">
            <div
              className="bg-gradient-to-r from-green-500 to-emerald-400 h-7 rounded-full transition-all duration-700 flex items-center justify-end pr-3"
              style={{ width: `${Math.max(pct, 1.5)}%` }}
            >
              {pct > 6 && (
                <span className="text-white text-sm font-bold">{pct.toFixed(1)}%</span>
              )}
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>{data.percentuale.toFixed(2)}% dell&apos;obiettivo raggiunto</span>
            <span>Obiettivo: €{fmtInt(data.obiettivo_eur)}</span>
          </div>
        </div>

        {/* KPI sintetici */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          <div className="rounded-xl bg-green-50 p-3 text-center">
            <div className="text-xl font-bold text-green-700">{data.nft_emessi_totali}</div>
            <div className="text-xs text-green-600">NFT emessi</div>
          </div>
          <div className="rounded-xl bg-gray-50 p-3 text-center">
            <div className="text-xl font-bold text-gray-700">{fmtInt(oreVenduteTotali)}h</div>
            <div className="text-xs text-gray-500">Ore vendute totali</div>
          </div>
          <div className="rounded-xl bg-gray-50 p-3 text-center">
            <div className="text-xl font-bold text-gray-700">{fmtInt(oreTotaliPeriodo)}h</div>
            <div className="text-xs text-gray-500">Capacità {annoInizio}–{annoFine}</div>
          </div>
          <div className="rounded-xl bg-blue-50 p-3 text-center">
            <div className="text-xl font-bold text-blue-700">{pctCapacitaGlobale.toFixed(2)}%</div>
            <div className="text-xs text-blue-600">Capacità utilizzata</div>
          </div>
        </div>
      </Card>

      {/* ── Sezione 2 — Riempimento per fascia ─────────────────────────────── */}
      <Card title="Ore vendute per fascia">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {FASCE.map((f) => {
            const vendute = data.ore_vendute[f];
            const totali = data.ore_totali_periodo[f];
            const libere = data.ore_disponibili[f];
            const pctF = totali > 0 ? (vendute / totali) * 100 : 0;
            return (
              <div key={f} className={`rounded-xl ${FASCIA_BG[f]} p-4`}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className={`font-bold text-sm ${FASCIA_TEXT[f]}`}>{FASCIA_LABEL[f]}</div>
                    <div className={`text-xs opacity-70 ${FASCIA_TEXT[f]}`}>{FASCIA_ORE_LABEL[f]}</div>
                  </div>
                  <div className={`text-right text-xs ${FASCIA_TEXT[f]} opacity-70`}>
                    {fmtInt(totali)}h totali
                  </div>
                </div>

                {/* Barra riempimento */}
                <div className="w-full bg-white/60 rounded-full h-2.5 mb-2">
                  <div
                    className={`${FASCIA_BAR[f]} h-2.5 rounded-full transition-all duration-500`}
                    style={{ width: `${Math.max(pctF, pctF > 0 ? 2 : 0)}%` }}
                  />
                </div>

                <div className="flex justify-between text-xs">
                  <span className={`font-semibold ${FASCIA_TEXT[f]}`}>{fmtInt(vendute)}h vendute</span>
                  <span className={`${FASCIA_TEXT[f]} opacity-60`}>{fmtInt(libere)}h libere</span>
                </div>
                <div className={`text-xs mt-1 font-medium ${FASCIA_TEXT[f]}`}>
                  {pctF.toFixed(2)}% utilizzate
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* ── Sezione 3 — Incassi 30 giorni ──────────────────────────────────── */}
      {data.incassi_30gg.length > 0 ? (
        <Card title="Incassi ultimi 30 giorni">
          <div className="space-y-1.5">
            {(() => {
              const maxI = Math.max(...data.incassi_30gg.map((x) => x.importo), 1);
              return data.incassi_30gg.map((g) => {
                const w = (g.importo / maxI) * 100;
                return (
                  <div key={g.data} className="flex items-center gap-3 text-xs">
                    <span className="w-24 text-gray-400 shrink-0 tabular-nums">{g.data}</span>
                    <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                      <div className="bg-emerald-500 h-4 transition-all" style={{ width: `${w}%` }} />
                    </div>
                    <span className="w-24 text-right font-semibold text-gray-700 tabular-nums">
                      €{fmt(g.importo)}
                    </span>
                  </div>
                );
              });
            })()}
          </div>
        </Card>
      ) : (
        <Card title="Incassi ultimi 30 giorni">
          <p className="text-sm text-gray-400 py-2">Nessun incasso negli ultimi 30 giorni.</p>
        </Card>
      )}

      {/* ── Sezione 4 — Top 5 vendite ───────────────────────────────────────── */}
      {data.top_5_vendite.length > 0 && (
        <Card title="Top 5 acquisti per importo">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-gray-400 text-left">
                  <th className="pb-2 pr-4 font-medium">#</th>
                  <th className="pb-2 pr-4 font-medium">Data</th>
                  <th className="pb-2 pr-4 font-medium">Fascia</th>
                  <th className="pb-2 pr-4 text-right font-medium">Ore</th>
                  <th className="pb-2 pr-4 text-right font-medium">Importo</th>
                  <th className="pb-2 text-right font-medium">Token ID</th>
                </tr>
              </thead>
              <tbody>
                {data.top_5_vendite.map((v, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 pr-4 text-gray-300 font-bold">{i + 1}</td>
                    <td className="py-2 pr-4 tabular-nums">{v.data}</td>
                    <td className="py-2 pr-4 capitalize">{v.fascia}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{v.ore}h</td>
                    <td className="py-2 pr-4 text-right font-semibold text-green-700 tabular-nums">
                      €{fmt(v.importo)}
                    </td>
                    <td className="py-2 text-right text-gray-400 text-xs tabular-nums">
                      {v.token_id != null ? `#${v.token_id}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
