"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { formattaEuro } from "@/lib/api/credito";
import { ETICHETTA_SPORT, fetchRiepilogo, oggiIso, type Fonte, type Riepilogo, type RigaRiepilogo } from "@/lib/api/tracker";

type Periodo = "mese" | "tre_mesi" | "anno_sportivo" | "tutto" | "personalizzato";
const PERIODI: [Periodo, string][] = [
  ["mese", "Questo mese"],
  ["tre_mesi", "Ultimi 3 mesi"],
  ["anno_sportivo", "Anno sportivo"],
  ["tutto", "Tutto"],
  ["personalizzato", "Personalizzato"],
];

const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function intervallo(p: Periodo): { dal?: string; al?: string } {
  const oggi = new Date();
  if (p === "mese") return { dal: iso(new Date(oggi.getFullYear(), oggi.getMonth(), 1)), al: oggiIso() };
  if (p === "tre_mesi") return { dal: iso(new Date(oggi.getFullYear(), oggi.getMonth() - 2, 1)), al: oggiIso() };
  if (p === "anno_sportivo") {
    // Anno sportivo: dal 1° luglio al 30 giugno
    const inizio = oggi.getMonth() >= 6 ? oggi.getFullYear() : oggi.getFullYear() - 1;
    return { dal: `${inizio}-07-01`, al: oggiIso() };
  }
  return {};
}

const pct = (v: string | null) => (v === null ? "—" : `${Number(v).toLocaleString("it-IT")}%`);

function Riga({ r, conCosti, totale }: { r: RigaRiepilogo; conCosti: boolean; totale?: boolean }) {
  const vuota = r.lead === 0 && !totale;
  return (
    <tr className={clsx(totale ? "border-t-2 border-gray-300 font-semibold" : "border-t border-gray-100", vuota && "text-gray-400")}>
      <td className="py-2 pr-3 text-left">{totale ? "Totale" : ETICHETTA_SPORT[r.sport as keyof typeof ETICHETTA_SPORT]}</td>
      <td className="px-2 py-2">{r.lead}</td>
      <td className="px-2 py-2">{r.prove_prenotate}</td>
      <td className="px-2 py-2">{r.prove_svolte}</td>
      <td className="px-2 py-2">{r.iscritti}</td>
      <td className="px-2 py-2">{r.paganti}</td>
      <td className="px-2 py-2">{r.persi}</td>
      <td className="px-2 py-2">{pct(r.conversione_pct)}</td>
      <td className="px-2 py-2">{formattaEuro(r.incassato_eur)}</td>
      <td className="px-2 py-2">{formattaEuro(r.impegnato_eur)}</td>
      {conCosti && (
        <>
          <td className="px-2 py-2">{formattaEuro(r.costo_istruttore_eur ?? 0)}</td>
          <td className={clsx("py-2 pl-2", Number(r.margine_eur) < 0 && !vuota && "text-red-700")}>
            {formattaEuro(r.margine_eur ?? 0)}
          </td>
        </>
      )}
    </tr>
  );
}

/** Vista per sport (fonte assente) o per fonte, es. Meta Ads. Tutti i numeri arrivano dal server. */
export function RiepilogoTracker({ fonte }: { fonte?: Fonte }) {
  const [periodo, setPeriodo] = useState<Periodo>("tutto");
  const [dal, setDal] = useState("");
  const [al, setAl] = useState(oggiIso());
  const [soloTest, setSoloTest] = useState(false);
  const [dati, setDati] = useState<Riepilogo | null>(null);

  const carica = useCallback(async () => {
    const range = periodo === "personalizzato" ? { dal: dal || undefined, al: al || undefined } : intervallo(periodo);
    try {
      setDati(await fetchRiepilogo({ fonte, ...range, test: soloTest }));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Riepilogo non disponibile");
    }
  }, [fonte, periodo, dal, al, soloTest]);

  useEffect(() => {
    carica();
  }, [carica]);

  const conCosti = !fonte;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="block text-xs font-medium text-gray-600">
          Contatti arrivati
          <select value={periodo} onChange={(e) => setPeriodo(e.target.value as Periodo)}
            className="mt-1 block rounded-lg border border-gray-300 px-3 py-2 text-sm">
            {PERIODI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        {periodo === "personalizzato" && (
          <>
            <label className="block text-xs font-medium text-gray-600">
              Dal
              <input type="date" value={dal} onChange={(e) => setDal(e.target.value)}
                className="mt-1 block rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </label>
            <label className="block text-xs font-medium text-gray-600">
              Al
              <input type="date" value={al} onChange={(e) => setAl(e.target.value)}
                className="mt-1 block rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </label>
          </>
        )}
        <label className="flex items-center gap-2 pb-2 text-sm text-gray-700">
          <input type="checkbox" checked={soloTest} onChange={(e) => setSoloTest(e.target.checked)} />
          Solo righe di prova (TEST)
        </label>
      </div>

      {soloTest && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          Stai guardando solo le righe di prova: servono a verificare i conti, non sono dati reali.
        </p>
      )}

      {!dati ? (
        <p className="text-sm text-gray-500">Caricamento…</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white p-4">
          <table className="w-full min-w-[760px] text-right text-sm tabular-nums">
            <thead className="text-xs text-gray-500">
              <tr>
                <th className="pb-2 pr-3 text-left font-medium">Sport</th>
                <th className="px-2 pb-2 font-medium">Lead</th>
                <th className="px-2 pb-2 font-medium">Prove pren.</th>
                <th className="px-2 pb-2 font-medium">Prove svolte</th>
                <th className="px-2 pb-2 font-medium">Iscritti</th>
                <th className="px-2 pb-2 font-medium">Paganti</th>
                <th className="px-2 pb-2 font-medium">Persi</th>
                <th className="px-2 pb-2 font-medium">Conversione</th>
                <th className="px-2 pb-2 font-medium">Incassato</th>
                <th className="px-2 pb-2 font-medium">Impegnato</th>
                {conCosti && (
                  <>
                    <th className="px-2 pb-2 font-medium">Costo istruttore</th>
                    <th className="pb-2 pl-2 font-medium">Margine</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody className="text-gray-900">
              {dati.righe.map((r) => <Riga key={r.sport} r={r} conCosti={conCosti} />)}
              <Riga r={dati.totale} conCosti={conCosti} totale />
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-500">
        Si contano i contatti arrivati nel periodo, per le fasi che hanno raggiunto (anche se poi sono andati avanti o
        sono persi). Conversione = paganti ÷ lead. Incassato = importi dei paganti; impegnato = importi degli iscritti
        che non hanno ancora pagato.
        {conCosti
          ? " Costo istruttore = costo mensile per sport × mesi del periodo (con «Tutto», dal primo contatto a oggi)."
          : " Il costo istruttore non compare: è dello sport, non della fonte."}
      </p>
    </div>
  );
}
