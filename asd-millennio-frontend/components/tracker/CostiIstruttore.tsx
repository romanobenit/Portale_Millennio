"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { formattaEuro } from "@/lib/api/credito";
import {
  eliminaCostoIstruttore,
  ETICHETTA_SPORT,
  fetchCostiIstruttore,
  impostaCostoIstruttore,
  SPORT,
  type CostoIstruttore,
  type Sport,
} from "@/lib/api/tracker";

const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

const meseDi = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("it-IT", { month: "long", year: "numeric" });

/** Costo mensile dell'istruttore per sport: vale dal mese indicato fino alla variazione successiva. */
export function CostiIstruttore() {
  const [costi, setCosti] = useState<CostoIstruttore[] | null>(null);
  const [sport, setSport] = useState<Sport>("kung_fu");
  const [mese, setMese] = useState(() => new Date().toISOString().slice(0, 7));
  const [costo, setCosto] = useState("");
  const [invio, setInvio] = useState(false);

  const carica = useCallback(async () => {
    try {
      setCosti(await fetchCostiIstruttore());
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Costi non disponibili");
    }
  }, []);

  useEffect(() => {
    carica();
  }, [carica]);

  const valore = Number(costo.replace(",", "."));
  const valido = costo.trim() !== "" && valore >= 0 && /^\d{4}-\d{2}$/.test(mese);

  const salva = async () => {
    setInvio(true);
    try {
      await impostaCostoIstruttore({ sport, valido_dal: `${mese}-01`, costo_mensile_eur: Math.round(valore * 100) / 100 });
      toast.success("Costo salvato");
      setCosto("");
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Salvataggio non riuscito");
    } finally {
      setInvio(false);
    }
  };

  const elimina = async (c: CostoIstruttore) => {
    if (!window.confirm(`Togliere il costo di ${ETICHETTA_SPORT[c.sport]} da ${meseDi(c.valido_dal)}?`)) return;
    try {
      await eliminaCostoIstruttore(c.id);
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
        <h2 className="font-semibold text-gray-900">Nuovo costo o variazione</h2>
        <p className="mt-1 text-xs text-gray-500">
          Il costo mensile vale dal mese scelto finché non ne inserisci uno nuovo. Lo stesso sport e mese sovrascrive.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-4">
          <label className="block text-xs font-medium text-gray-600 sm:col-span-2">
            Sport
            <select value={sport} onChange={(e) => setSport(e.target.value as Sport)} className={input}>
              {SPORT.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="block text-xs font-medium text-gray-600">
            Dal mese
            <input type="month" value={mese} onChange={(e) => setMese(e.target.value)} className={input} />
          </label>
          <label className="block text-xs font-medium text-gray-600">
            Costo mensile (€)
            <input inputMode="decimal" value={costo} onChange={(e) => setCosto(e.target.value)} className={input} />
          </label>
        </div>
        <button type="button" onClick={salva} disabled={!valido || invio}
          className="mt-4 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">
          {invio ? "Salvataggio…" : "Salva"}
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
        <h2 className="font-semibold text-gray-900">Costi inseriti</h2>
        {!costi ? (
          <p className="mt-2 text-sm text-gray-500">Caricamento…</p>
        ) : costi.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">Nessun costo: nella vista per sport il costo istruttore risulta zero.</p>
        ) : (
          <ul className="mt-2 divide-y divide-gray-100">
            {costi.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span>
                  <span className="font-medium text-gray-900">{ETICHETTA_SPORT[c.sport]}</span>
                  <span className="text-gray-500"> · da {meseDi(c.valido_dal)}</span>
                </span>
                <span className="flex items-center gap-4">
                  <span className="tabular-nums">{formattaEuro(c.costo_mensile_eur)}/mese</span>
                  <button type="button" onClick={() => elimina(c)} className="text-xs font-medium text-red-600 hover:text-red-800">
                    Togli
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
