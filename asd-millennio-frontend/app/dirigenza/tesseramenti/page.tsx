"use client";

import { useEffect, useState } from "react";
import {
  fetchVerifiche, confermaVerifica, rifiutaVerifica, scaricaDocumento,
  TesseramentoDaVerificare,
} from "@/lib/api/tesseramento";
import toast from "react-hot-toast";

const CAT_LABEL: Record<string, string> = {
  volley: "Pallavolo", badminton: "Badminton", kung_fu: "Kung Fu", pickleball: "Pickleball", sostenitore: "Sostenitore",
};

export default function VerificheTesseramentiPage() {
  const [items, setItems] = useState<TesseramentoDaVerificare[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const carica = async () => {
    try { setItems(await fetchVerifiche()); }
    catch { toast.error("Impossibile caricare la coda verifiche."); }
    finally { setLoading(false); }
  };

  useEffect(() => { carica(); }, []);

  const azione = async (id: string, tipo: "conferma" | "rifiuta") => {
    if (tipo === "rifiuta" && !confirm("Rifiutare il tesseramento? La quota diventerà erogazione liberale (non rimborsata).")) return;
    setBusy(id);
    try {
      if (tipo === "conferma") await confermaVerifica(id);
      else await rifiutaVerifica(id);
      toast.success(tipo === "conferma" ? "Tesseramento confermato." : "Tesseramento rifiutato.");
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore");
    } finally { setBusy(null); }
  };

  if (loading) return <div className="text-sm text-gray-500 py-8">Caricamento…</div>;

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-1">Verifiche tesseramenti</h1>
      <p className="text-gray-500 text-sm mb-6">
        Tesseramenti attivi in via provvisoria da confermare. Verifica che il codice fiscale
        corrisponda al documento d&apos;identità (e la tutela, per i minori). Non confermati entro 30 giorni →
        conferma automatica.
      </p>

      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">Nessun tesseramento in attesa di verifica.</p>
      ) : (
        <div className="space-y-4">
          {items.map((it) => (
            <div key={it.tessera_id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm font-semibold text-gray-800">{it.numero_tessera}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{CAT_LABEL[it.categoria] ?? it.categoria}</span>
                    {it.socio.is_minor && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">Minore</span>}
                  </div>
                  <p className="text-sm text-gray-900 font-medium">{it.socio.nome} {it.socio.cognome}</p>
                  <p className="text-xs text-gray-500 font-mono">CF {it.socio.codice_fiscale}</p>
                  {it.tutore && <p className="text-xs text-gray-500">Tutore: {it.tutore.nome} {it.tutore.cognome}</p>}
                  {it.importo_eur != null && <p className="text-xs text-gray-500 mt-1">Quota versata: € {it.importo_eur.toFixed(2)}</p>}
                </div>
                <div className="text-right">
                  {it.verifica_scadenza && (
                    <p className="text-xs text-gray-400 mb-2">Scade il {new Date(it.verifica_scadenza).toLocaleDateString("it-IT")}</p>
                  )}
                  <div className="flex gap-2 justify-end">
                    <button onClick={() => azione(it.tessera_id, "rifiuta")} disabled={busy === it.tessera_id}
                      className="rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50">Rifiuta</button>
                    <button onClick={() => azione(it.tessera_id, "conferma")} disabled={busy === it.tessera_id}
                      className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50">Conferma</button>
                  </div>
                </div>
              </div>
              <div className="mt-3 border-t border-gray-100 pt-3 flex flex-wrap gap-3">
                {it.documenti.length === 0 && <span className="text-xs text-red-500">Nessun documento caricato</span>}
                {it.documenti.map((d) => (
                  <button key={d.id} onClick={() => scaricaDocumento(d.id)}
                    className="text-xs text-blue-700 hover:underline inline-flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                    {d.tipo === "identita" ? "Documento identità" : "Prova tutela"}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
