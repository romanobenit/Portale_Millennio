"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { CostiIstruttore } from "@/components/tracker/CostiIstruttore";
import { ModuloContatto } from "@/components/tracker/ModuloContatto";
import { PuliziaPersi } from "@/components/tracker/PuliziaPersi";
import { RiepilogoTracker } from "@/components/tracker/RiepilogoTracker";
import { formattaEuro } from "@/lib/api/credito";
import {
  ETICHETTA_CANALE,
  ETICHETTA_FONTE,
  ETICHETTA_SPORT,
  ETICHETTA_STATO,
  fetchContatti,
  fetchMembri,
  fetchMeTracker,
  fetchMieiFollowup,
  FONTI,
  formattaData,
  oggiIso,
  SPORT,
  STATI,
  type Contatto,
  type FiltriContatti,
  type ListaContatti,
  type Membro,
  type MeTracker,
  type Stato,
} from "@/lib/api/tracker";

type Scheda = "contatti" | "followup" | "sport" | "meta" | "costi";

const COLORE_STATO: Record<Stato, string> = {
  lead: "bg-gray-100 text-gray-700",
  prova_prenotata: "bg-sky-100 text-sky-800",
  prova_svolta: "bg-indigo-100 text-indigo-800",
  iscritto: "bg-amber-100 text-amber-800",
  pagato: "bg-green-100 text-green-800",
  perso: "bg-red-100 text-red-700",
};

const select = "rounded-lg border border-gray-300 px-3 py-2 text-sm";
const LIMITE = 50;

function Badge({ stato }: { stato: Stato }) {
  return (
    <span className={clsx("whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", COLORE_STATO[stato])}>
      {ETICHETTA_STATO[stato]}
    </span>
  );
}

function giorniDiRitardo(iso: string): number {
  return Math.round((new Date(`${oggiIso()}T00:00:00`).getTime() - new Date(`${iso}T00:00:00`).getTime()) / 86400000);
}

/** Riga di un contatto: usata nell'elenco e nei follow-up. */
function RigaContatto({ c, onApri, followup }: { c: Contatto; onApri: () => void; followup?: boolean }) {
  const ritardo = c.prossimo_followup ? giorniDiRitardo(c.prossimo_followup) : 0;
  return (
    <li>
      <button type="button" onClick={onApri}
        className="flex w-full flex-col gap-1 px-1 py-3 text-left hover:bg-gray-50 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-medium text-gray-900">
            {c.nome}
            {c.is_test && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-800">TEST</span>}
          </p>
          <p className="text-xs text-gray-500">
            {ETICHETTA_SPORT[c.sport]} · {ETICHETTA_FONTE[c.fonte]}
            {c.canale && ` · ${ETICHETTA_CANALE[c.canale]}`}
            {c.recapito && ` ${c.recapito}`} · contatto del {formattaData(c.data_contatto)}
          </p>
          {followup && c.note && <p className="mt-1 text-sm text-gray-600">{c.note}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 sm:justify-end">
          {c.importo_eur && <span className="tabular-nums">{formattaEuro(c.importo_eur)}</span>}
          {c.prossimo_followup && (
            <span className={clsx(followup && ritardo > 0 && "font-semibold text-red-700")}>
              {followup
                ? ritardo === 0 ? "da richiamare oggi" : `in ritardo di ${ritardo} ${ritardo === 1 ? "giorno" : "giorni"}`
                : `follow-up ${formattaData(c.prossimo_followup)}`}
            </span>
          )}
          {!followup && c.responsabile_nome && <span>{c.responsabile_nome}</span>}
          <Badge stato={c.stato} />
        </div>
      </button>
    </li>
  );
}

function ElencoContatti({
  me, membri, onApri, versione,
}: { me: MeTracker; membri: Membro[]; onApri: (id: string) => void; versione: number }) {
  const [filtri, setFiltri] = useState<FiltriContatti>({ q: "", sport: "", fonte: "", stato: "", responsabile_id: "", test: false, page: 1 });
  const [cerca, setCerca] = useState("");
  const [dati, setDati] = useState<ListaContatti | null>(null);

  // La ricerca parte dopo una breve pausa nella digitazione
  useEffect(() => {
    const t = setTimeout(() => setFiltri((f) => (f.q === cerca ? f : { ...f, q: cerca, page: 1 })), 300);
    return () => clearTimeout(t);
  }, [cerca]);

  const carica = useCallback(async () => {
    try {
      setDati(await fetchContatti({ ...filtri, limit: LIMITE }));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Contatti non disponibili");
    }
  }, [filtri]);

  useEffect(() => {
    carica();
  }, [carica, versione]);

  const set = (k: keyof FiltriContatti, v: string | boolean) => setFiltri((f) => ({ ...f, [k]: v, page: 1 }));
  const pagine = dati ? Math.max(1, Math.ceil(dati.totale / LIMITE)) : 1;
  const pagina = filtri.page ?? 1;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <input value={cerca} onChange={(e) => setCerca(e.target.value)} placeholder="Cerca nome o recapito…"
          className={clsx(select, "lg:col-span-1")} />
        <select value={filtri.sport} onChange={(e) => set("sport", e.target.value)} className={select} aria-label="Sport">
          <option value="">Tutti gli sport</option>
          {SPORT.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filtri.fonte} onChange={(e) => set("fonte", e.target.value)} className={select} aria-label="Fonte">
          <option value="">Tutte le fonti</option>
          {FONTI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filtri.stato} onChange={(e) => set("stato", e.target.value)} className={select} aria-label="Stato">
          <option value="">Tutti gli stati</option>
          {STATI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filtri.responsabile_id} onChange={(e) => set("responsabile_id", e.target.value)} className={select}
          aria-label="Responsabile">
          <option value="">Tutti i responsabili</option>
          {membri.map((m) => <option key={m.id} value={m.id}>{m.id === me.id ? `${m.nome} (io)` : m.nome}</option>)}
        </select>
      </div>
      {me.dirigenza && (
        <label className="mt-3 flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={!!filtri.test} onChange={(e) => set("test", e.target.checked)} />
          Mostra solo le righe di prova (TEST)
        </label>
      )}

      {!dati ? (
        <p className="py-6 text-center text-sm text-gray-500">Caricamento…</p>
      ) : dati.contatti.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-500">Nessun contatto con questi filtri.</p>
      ) : (
        <>
          <p className="mt-3 text-xs text-gray-500">{dati.totale} {dati.totale === 1 ? "contatto" : "contatti"}</p>
          <ul className="mt-1 divide-y divide-gray-100">
            {dati.contatti.map((c) => <RigaContatto key={c.id} c={c} onApri={() => onApri(c.id)} />)}
          </ul>
          {pagine > 1 && (
            <div className="mt-3 flex items-center justify-center gap-3 text-sm">
              <button type="button" disabled={pagina <= 1} onClick={() => setFiltri((f) => ({ ...f, page: pagina - 1 }))}
                className="rounded-lg border border-gray-300 px-3 py-1 disabled:opacity-40">←</button>
              <span>Pagina {pagina} di {pagine}</span>
              <button type="button" disabled={pagina >= pagine} onClick={() => setFiltri((f) => ({ ...f, page: pagina + 1 }))}
                className="rounded-lg border border-gray-300 px-3 py-1 disabled:opacity-40">→</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MieiFollowup({ onApri, versione }: { onApri: (id: string) => void; versione: number }) {
  const [lista, setLista] = useState<Contatto[] | null>(null);

  useEffect(() => {
    fetchMieiFollowup().then(setLista).catch(() => toast.error("Follow-up non disponibili"));
  }, [versione]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
      <h2 className="font-semibold text-gray-900">Da richiamare oggi o in ritardo</h2>
      {!lista ? (
        <p className="py-6 text-center text-sm text-gray-500">Caricamento…</p>
      ) : lista.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-500">Nessun follow-up in sospeso.</p>
      ) : (
        <ul className="mt-2 divide-y divide-gray-100">
          {lista.map((c) => <RigaContatto key={c.id} c={c} onApri={() => onApri(c.id)} followup />)}
        </ul>
      )}
    </div>
  );
}

export default function TrackerPage() {
  const [me, setMe] = useState<MeTracker | null>(null);
  const [membri, setMembri] = useState<Membro[]>([]);
  const [scheda, setScheda] = useState<Scheda>("contatti");
  const [aperto, setAperto] = useState<string | null | undefined>(undefined); // undefined = nessun modulo, null = nuovo
  const [versione, setVersione] = useState(0);

  useEffect(() => {
    fetchMeTracker()
      .then(async (m) => {
        setMe(m);
        if (!m.dirigenza) setScheda("followup");   // Rita parte dai suoi follow-up
        setMembri(await fetchMembri());
      })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Tracker non disponibile"));
  }, []);

  if (!me) return <p className="text-gray-500">Caricamento…</p>;

  const schede: [Scheda, string][] = [
    ["followup", "I miei follow-up"],
    ["contatti", "Contatti"],
    ...(me.dirigenza
      ? ([["sport", "Per sport"], ["meta", "Meta Ads"], ["costi", "Costi istruttore"]] as [Scheda, string][])
      : []),
  ];

  const apri = (id: string | null) => {
    setAperto(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const salvato = () => {
    setAperto(undefined);
    setVersione((v) => v + 1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tracker iscritti</h1>
          <p className="mt-1 text-sm text-gray-500">
            Ogni persona interessata, dal primo messaggio all&apos;iscrizione: quale sport e quale fonte portano iscritti
            paganti. Una riga per persona; chi non prosegue va in «Perso», non si cancella.
          </p>
        </div>
        {aperto === undefined && (scheda === "contatti" || scheda === "followup") && (
          <button type="button" onClick={() => apri(null)}
            className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">
            + Nuovo contatto
          </button>
        )}
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-gray-200" aria-label="Sezioni tracker">
        {schede.map(([k, label]) => (
          <button key={k} type="button" onClick={() => { setScheda(k); setAperto(undefined); }}
            className={clsx("whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium",
              scheda === k ? "border-blue-700 text-blue-800" : "border-transparent text-gray-500 hover:text-gray-800")}>
            {label}
          </button>
        ))}
      </nav>

      {aperto !== undefined && (
        <ModuloContatto
          key={aperto ?? "nuovo"}
          contattoId={aperto}
          membri={membri}
          mioId={me.id}
          dirigenza={me.dirigenza}
          onChiudi={() => setAperto(undefined)}
          onSalvato={salvato}
          onApri={apri}
        />
      )}

      {scheda === "followup" && <MieiFollowup onApri={apri} versione={versione} />}
      {scheda === "contatti" && <ElencoContatti me={me} membri={membri} onApri={apri} versione={versione} />}
      {scheda === "contatti" && me.dirigenza && <PuliziaPersi onFatto={() => setVersione((v) => v + 1)} />}
      {scheda === "sport" && <RiepilogoTracker />}
      {scheda === "meta" && <RiepilogoTracker fonte="meta_ads" />}
      {scheda === "costi" && <CostiIstruttore />}
    </div>
  );
}
