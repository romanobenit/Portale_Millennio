"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getKeycloak, isDirigenza } from "@/lib/auth/keycloak";
import toast from "react-hot-toast";
import { fetchRendiconto, type RendicontoAnnuale } from "@/lib/api/dirigenza";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

const FASCIA_LABEL: Record<string, string> = { notte: "Notte", mattina: "Mattina", pomeriggio: "Pomeriggio" };

// Anni civili del periodo di vendita Palasirion
const ANNI_DISPONIBILI = Array.from({ length: 2042 - 2027 + 1 }, (_, i) => 2027 + i);

export default function RendicontoPage() {
  const router = useRouter();
  const [anno, setAnno] = useState(2027);
  const [data, setData] = useState<RendicontoAnnuale | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc.authenticated || !isDirigenza(kc)) { router.push("/"); return; }
  }, [router]);

  const carica = async () => {
    setLoading(true);
    try {
      setData(await fetchRendiconto(anno));
    } catch {
      toast.error("Errore nel caricamento rendiconto");
    } finally {
      setLoading(false);
    }
  };

  const totaleOre = data?.fasce.reduce((s, f) => s + f.ore_vendute, 0) ?? 0;
  const totaleOrePeriodo = data?.fasce.reduce((s, f) => s + f.ore_totali_stagione, 0) ?? 0;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 print:p-0">
      {/* Header navigazione — nascosto in stampa */}
      <div className="flex items-center justify-between print:hidden">
        <h1 className="text-2xl font-bold text-gray-900">Rendiconto annuale</h1>
        <button onClick={() => router.push("/dirigenza")} className="text-sm text-blue-600 hover:underline">
          ← Dashboard
        </button>
      </div>

      {/* Selettore anno */}
      <Card className="print:hidden">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Anno civile</label>
            <select
              value={anno}
              onChange={(e) => setAnno(Number(e.target.value))}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm min-w-[110px]"
            >
              {ANNI_DISPONIBILI.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>
          <Button onClick={carica} loading={loading}>
            Genera rendiconto
          </Button>
        </div>
      </Card>

      {data && (
        <div id="rendiconto-content" className="space-y-6">

          {/* Header documento — visibile anche in stampa */}
          <Card>
            <div className="flex justify-between items-start gap-4 flex-wrap">
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1">ASD Millennio — Palasirion</div>
                <h2 className="text-xl font-bold text-gray-900">
                  Rendiconto uso Palasirion — Anno {data.anno}
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Periodo: {data.periodo_inizio} → {data.periodo_fine}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Generato il {new Date(data.generato_il).toLocaleString("it-IT")}
                </p>
              </div>
              <Button size="sm" variant="secondary" onClick={() => window.print()} className="print:hidden">
                Stampa / Salva PDF
              </Button>
            </div>
          </Card>

          {/* KPI totali */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="rounded-xl bg-green-50 p-4 text-center">
              <div className="text-3xl font-bold text-green-700">
                €{data.totale_ricavi.toLocaleString("it-IT", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-green-600 mt-1">Ricavi lordi totali</div>
            </div>
            <div className="rounded-xl bg-blue-50 p-4 text-center">
              <div className="text-3xl font-bold text-blue-700">{data.totale_nft}</div>
              <div className="text-xs text-blue-600 mt-1">NFT emessi nell&apos;anno</div>
            </div>
            <div className="rounded-xl bg-gray-50 p-4 text-center">
              <div className="text-3xl font-bold text-gray-700">{totaleOre}h</div>
              <div className="text-xs text-gray-500 mt-1">
                Ore vendute / {totaleOrePeriodo}h disponibili
              </div>
            </div>
          </div>

          {/* Tabella dettaglio per fascia */}
          <Card title="Dettaglio per fascia oraria">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-gray-400 text-left">
                    <th className="pb-2 pr-6">Fascia</th>
                    <th className="pb-2 pr-6 text-right">Ore disponibili</th>
                    <th className="pb-2 pr-6 text-right">Ore vendute</th>
                    <th className="pb-2 pr-6 text-right">% utilizzo</th>
                    <th className="pb-2 text-right">Ricavi stimati</th>
                  </tr>
                </thead>
                <tbody>
                  {data.fasce.map((f) => {
                    const pctUt = f.ore_totali_stagione > 0
                      ? (f.ore_vendute / f.ore_totali_stagione * 100).toFixed(2)
                      : "0.00";
                    return (
                      <tr key={f.fascia} className="border-b last:border-0">
                        <td className="py-3 pr-6 font-semibold">{FASCIA_LABEL[f.fascia] ?? f.fascia}</td>
                        <td className="py-3 pr-6 text-right tabular-nums">{f.ore_totali_stagione}h</td>
                        <td className="py-3 pr-6 text-right tabular-nums font-medium">{f.ore_vendute}h</td>
                        <td className="py-3 pr-6 text-right">
                          <span className={`font-semibold ${Number(pctUt) > 50 ? "text-green-700" : "text-gray-500"}`}>
                            {pctUt}%
                          </span>
                        </td>
                        <td className="py-3 text-right font-semibold tabular-nums">
                          €{f.ricavi_lordi.toLocaleString("it-IT", { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    );
                  })}
                  {/* Riga totale */}
                  <tr className="bg-gray-50 font-bold border-t-2 border-gray-200">
                    <td className="py-3 pr-6">Totale</td>
                    <td className="py-3 pr-6 text-right tabular-nums">{totaleOrePeriodo}h</td>
                    <td className="py-3 pr-6 text-right tabular-nums">{totaleOre}h</td>
                    <td className="py-3 pr-6 text-right tabular-nums">
                      {totaleOrePeriodo > 0 ? (totaleOre / totaleOrePeriodo * 100).toFixed(2) : "0.00"}%
                    </td>
                    <td className="py-3 text-right tabular-nums">
                      €{data.totale_ricavi.toLocaleString("it-IT", { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>

          {/* Footer documento */}
          <p className="text-xs text-gray-400 text-center pb-2">
            ASD Millennio — Palasirion — millennioasd.com
            {" "}— Documento generato automaticamente dalla piattaforma digitale il{" "}
            {new Date(data.generato_il).toLocaleDateString("it-IT")}
          </p>
        </div>
      )}
    </div>
  );
}
