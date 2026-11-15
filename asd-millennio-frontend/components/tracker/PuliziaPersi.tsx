"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { cancellaPersi, formattaData, oggiIso } from "@/lib/api/tracker";

/** Pulizia manuale della dirigenza: cancella i contatti persi fino a una data, con il loro storico. */
export function PuliziaPersi({ onFatto }: { onFatto: () => void }) {
  const [aperta, setAperta] = useState(false);
  const [finoAl, setFinoAl] = useState(oggiIso());
  const [quanti, setQuanti] = useState<number | null>(null);
  const [invio, setInvio] = useState(false);

  // Anteprima: quanti contatti verrebbero cancellati con la data scelta
  useEffect(() => {
    if (!aperta || !finoAl) return;
    setQuanti(null);
    cancellaPersi(finoAl, false)
      .then((r) => setQuanti(r.contatti))
      .catch(() => toast.error("Anteprima non disponibile"));
  }, [aperta, finoAl]);

  const cancella = async () => {
    if (!quanti || !window.confirm(
      `Cancellare definitivamente ${quanti} ${quanti === 1 ? "contatto perso" : "contatti persi"} fino al ` +
      `${formattaData(finoAl)}? Spariscono anche dai conteggi delle viste (lead, persi, conversione).`,
    )) return;
    setInvio(true);
    try {
      const r = await cancellaPersi(finoAl, true);
      toast.success(`${r.contatti} ${r.contatti === 1 ? "contatto cancellato" : "contatti cancellati"}`);
      setQuanti(0);
      onFatto();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Cancellazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  if (!aperta) {
    return (
      <button type="button" onClick={() => setAperta(true)} className="text-sm font-medium text-red-600 hover:text-red-800">
        Cancella i contatti persi…
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-red-200 bg-white p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-semibold text-gray-900">Cancella i contatti persi</h2>
        <button type="button" onClick={() => setAperta(false)} className="text-sm text-gray-500 hover:text-gray-800">Chiudi</button>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Cancella per sempre i contatti oggi in stato «Perso» che ci sono passati entro la data scelta, con il loro
        storico. Non si può annullare e cambia i conteggi delle viste.
      </p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="block text-xs font-medium text-gray-600">
          Persi fino al
          <input type="date" value={finoAl} max={oggiIso()} onChange={(e) => setFinoAl(e.target.value)}
            className="mt-1 block rounded-lg border border-gray-300 px-3 py-2 text-sm" />
        </label>
        <p className="pb-2 text-sm text-gray-700">
          {quanti === null ? "Conteggio…" : quanti === 0 ? "Nessun contatto da cancellare."
            : `${quanti} ${quanti === 1 ? "contatto" : "contatti"} da cancellare`}
        </p>
      </div>
      <button type="button" onClick={cancella} disabled={!quanti || invio}
        className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50">
        {invio ? "Cancellazione…" : "Cancella"}
      </button>
    </div>
  );
}
