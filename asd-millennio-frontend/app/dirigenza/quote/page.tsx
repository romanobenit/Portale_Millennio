"use client";

import { useEffect, useState } from "react";
import { fetchQuote, creaQuota, aggiornaQuota, Quota } from "@/lib/api/tesseramento";
import toast from "react-hot-toast";

const CATEGORIE = ["volley", "badminton", "kung_fu", "pickleball", "sostenitore"];
const CAT_LABEL: Record<string, string> = {
  volley: "Pallavolo", badminton: "Badminton", kung_fu: "Kung Fu", pickleball: "Pickleball", sostenitore: "Sostenitore",
};
const ANNO = "2026-2027";

export default function QuotePage() {
  const [quote, setQuote] = useState<Quota[]>([]);
  const [loading, setLoading] = useState(true);
  const [nuova, setNuova] = useState({ categoria: "volley", is_minore: false, importo_eur: "" });
  const [busy, setBusy] = useState(false);

  const carica = async () => {
    try { setQuote(await fetchQuote(ANNO)); }
    catch { toast.error("Impossibile caricare le quote."); }
    finally { setLoading(false); }
  };
  useEffect(() => { carica(); }, []);

  const crea = async () => {
    const imp = parseFloat(nuova.importo_eur);
    if (isNaN(imp) || imp < 0) { toast.error("Importo non valido."); return; }
    setBusy(true);
    try {
      await creaQuota({ categoria: nuova.categoria, is_minore: nuova.is_minore, importo_eur: imp, anno_sportivo: ANNO });
      toast.success("Quota creata.");
      setNuova({ categoria: "volley", is_minore: false, importo_eur: "" });
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore");
    } finally { setBusy(false); }
  };

  const toggle = async (q: Quota) => {
    try { await aggiornaQuota(q.id, { attivo: !q.attivo }); await carica(); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Errore"); }
  };

  const cambiaImporto = async (q: Quota, val: string) => {
    const imp = parseFloat(val);
    if (isNaN(imp)) return;
    try { await aggiornaQuota(q.id, { importo_eur: imp }); await carica(); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Errore"); }
  };

  if (loading) return <div className="text-sm text-gray-500 py-8">Caricamento…</div>;

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-1">Quote tessera</h1>
      <p className="text-gray-500 text-sm mb-6">Quote associative per categoria e fascia (adulto/minore), anno sportivo {ANNO}.</p>

      <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Categoria</label>
          <select value={nuova.categoria} onChange={(e) => setNuova({ ...nuova, categoria: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
            {CATEGORIE.map((c) => <option key={c} value={c}>{CAT_LABEL[c]}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700 pb-2">
          <input type="checkbox" checked={nuova.is_minore} onChange={(e) => setNuova({ ...nuova, is_minore: e.target.checked })} className="h-4 w-4 rounded border-gray-300" />
          Minore
        </label>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Importo €</label>
          <input type="number" step="0.01" value={nuova.importo_eur} onChange={(e) => setNuova({ ...nuova, importo_eur: e.target.value })} className="w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm" />
        </div>
        <button onClick={crea} disabled={busy} className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">Aggiungi quota</button>
      </div>

      {quote.length === 0 ? (
        <p className="text-gray-500 text-sm">Nessuna quota configurata. I soci non potranno tesserarsi finché non ne aggiungi almeno una.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-200">
                <th className="py-2 font-medium">Categoria</th>
                <th className="py-2 font-medium">Fascia</th>
                <th className="py-2 font-medium">Importo €</th>
                <th className="py-2 font-medium">Stato</th>
              </tr>
            </thead>
            <tbody>
              {quote.map((q) => (
                <tr key={q.id} className="border-b border-gray-100">
                  <td className="py-2.5">{CAT_LABEL[q.categoria] ?? q.categoria}</td>
                  <td className="py-2.5">{q.is_minore ? "Minore" : "Adulto"}</td>
                  <td className="py-2.5">
                    <input type="number" step="0.01" defaultValue={q.importo_eur}
                      onBlur={(e) => e.target.value !== String(q.importo_eur) && cambiaImporto(q, e.target.value)}
                      className="w-24 rounded-lg border border-gray-300 px-2 py-1 text-sm" />
                  </td>
                  <td className="py-2.5">
                    <button onClick={() => toggle(q)}
                      className={q.attivo ? "text-xs px-2 py-1 rounded-full bg-green-100 text-green-800" : "text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600"}>
                      {q.attivo ? "Attiva" : "Disattivata"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
