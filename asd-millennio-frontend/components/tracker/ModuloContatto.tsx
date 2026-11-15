"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  ABBONAMENTI,
  aggiornaContatto,
  cancellaContatto,
  CANALI,
  cercaDoppioni,
  creaContatto,
  ETICHETTA_SPORT,
  ETICHETTA_STATO,
  fetchContatto,
  FONTI,
  formattaData,
  oggiIso,
  sembraDatoDiSalute,
  SPORT,
  STATI,
  type Contatto,
  type ContattoDettaglio,
  type ContattoInput,
  type Membro,
} from "@/lib/api/tracker";

const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";
const label = "block text-xs font-medium text-gray-600";
const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";

interface Form {
  data_contatto: string;
  sport: string;
  fonte: string;
  nome: string;
  canale: string;
  recapito: string;
  stato: string;
  data_prova: string;
  tipo_abbonamento: string;
  importo_eur: string;
  responsabile_id: string;
  prossimo_followup: string;
  note: string;
  is_test: boolean;
}

function formDa(c: Contatto | null, mioId: string): Form {
  return {
    data_contatto: c?.data_contatto ?? oggiIso(),
    sport: c?.sport ?? "",
    fonte: c?.fonte ?? "",
    nome: c?.nome ?? "",
    canale: c?.canale ?? "",
    recapito: c?.recapito ?? "",
    stato: c?.stato ?? "lead",
    data_prova: c?.data_prova ?? "",
    tipo_abbonamento: c?.tipo_abbonamento ?? "",
    importo_eur: c?.importo_eur ? String(Number(c.importo_eur)).replace(".", ",") : "",
    responsabile_id: c ? (c.responsabile_id ?? "") : mioId,
    prossimo_followup: c?.prossimo_followup ?? "",
    note: c?.note ?? "",
    is_test: c?.is_test ?? false,
  };
}

function inInput(f: Form): ContattoInput {
  const vuoto = (v: string) => v.trim() || null;
  const importo = f.importo_eur.trim() ? Math.round(Number(f.importo_eur.replace(",", ".")) * 100) / 100 : null;
  return {
    data_contatto: f.data_contatto,
    sport: f.sport as ContattoInput["sport"],
    fonte: f.fonte as ContattoInput["fonte"],
    nome: f.nome.trim(),
    canale: (f.canale || null) as ContattoInput["canale"],
    recapito: vuoto(f.recapito),
    stato: f.stato as ContattoInput["stato"],
    data_prova: f.data_prova || null,
    tipo_abbonamento: (f.tipo_abbonamento || null) as ContattoInput["tipo_abbonamento"],
    importo_eur: importo,
    responsabile_id: f.responsabile_id || null,
    prossimo_followup: f.prossimo_followup || null,
    note: vuoto(f.note),
    is_test: f.is_test,
  };
}

function Tendina({
  testo, valore, onChange, opzioni, obbligatoria, vuota = "—",
}: {
  testo: string; valore: string; onChange: (v: string) => void; opzioni: [string, string][]; obbligatoria?: boolean; vuota?: string;
}) {
  return (
    <label className={label}>
      {testo}
      {obbligatoria && <span className="text-red-600"> *</span>}
      <select value={valore} onChange={(e) => onChange(e.target.value)} className={input} required={obbligatoria}>
        {(!obbligatoria || !valore) && <option value="">{obbligatoria ? "Scegli…" : vuota}</option>}
        {opzioni.map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>
    </label>
  );
}

/**
 * Inserimento o modifica di un contatto. In modifica mostra lo storico degli stati
 * e, alla dirigenza, la cancellazione su richiesta dell'interessato.
 */
export function ModuloContatto({
  contattoId, membri, mioId, dirigenza, onChiudi, onSalvato, onApri,
}: {
  contattoId: string | null;          // null = nuovo contatto
  membri: Membro[];
  mioId: string;
  dirigenza: boolean;
  onChiudi: () => void;
  onSalvato: () => void;
  onApri: (id: string) => void;       // apre un possibile doppione
}) {
  const [dett, setDett] = useState<ContattoDettaglio | null>(null);
  const [f, setF] = useState<Form>(() => formDa(null, mioId));
  const [doppioni, setDoppioni] = useState<Contatto[]>([]);
  const [invio, setInvio] = useState(false);

  useEffect(() => {
    if (!contattoId) {
      setDett(null);
      setF(formDa(null, mioId));
      return;
    }
    fetchContatto(contattoId)
      .then((d) => {
        setDett(d);
        setF(formDa(d, mioId));
      })
      .catch(() => toast.error("Contatto non trovato"));
  }, [contattoId, mioId]);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((prev) => ({ ...prev, [k]: v }));

  const controllaDoppioni = async () => {
    if (f.nome.trim().length < 2) return setDoppioni([]);
    try {
      setDoppioni(await cercaDoppioni(f.nome.trim(), contattoId ?? undefined));
    } catch {
      setDoppioni([]);
    }
  };

  const importoValido = !f.importo_eur.trim() || Number(f.importo_eur.replace(",", ".")) >= 0;
  const valido = f.nome.trim().length >= 2 && f.sport && f.fonte && f.stato && f.data_contatto && importoValido;

  const salva = async () => {
    if (!contattoId && doppioni.length > 0 &&
      !window.confirm("C'è già un contatto con questo nome. Crearne comunque uno nuovo?")) return;
    setInvio(true);
    try {
      if (contattoId) {
        await aggiornaContatto(contattoId, inInput(f));
        toast.success("Contatto aggiornato");
      } else {
        await creaContatto(inInput(f));
        toast.success("Contatto aggiunto");
      }
      onSalvato();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Salvataggio non riuscito");
    } finally {
      setInvio(false);
    }
  };

  const cancella = async () => {
    if (!contattoId || !dett) return;
    if (!window.confirm(
      `Cancellare definitivamente ${dett.nome}? Va fatto solo se la persona ha chiesto di essere rimossa: ` +
      "la riga e il suo storico spariscono e i conteggi cambiano. Negli altri casi metti lo stato «Perso».",
    )) return;
    setInvio(true);
    try {
      await cancellaContatto(contattoId);
      toast.success("Contatto cancellato");
      onSalvato();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Cancellazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  if (contattoId && !dett) return <p className="text-sm text-gray-500">Caricamento…</p>;

  const membriOpzioni: [string, string][] = membri.map((m) => [m.id, m.id === mioId ? `${m.nome} (io)` : m.nome]);

  return (
    <div className="rounded-xl border border-blue-200 bg-white p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-semibold text-gray-900">{contattoId ? `Contatto: ${dett?.nome}` : "Nuovo contatto"}</h2>
        <button type="button" onClick={onChiudi} className="text-sm text-gray-500 hover:text-gray-800">Chiudi</button>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className={label}>
          Nome e cognome<span className="text-red-600"> *</span>
          <input value={f.nome} onChange={(e) => set("nome", e.target.value)} onBlur={controllaDoppioni}
            maxLength={120} className={input} autoComplete="off" />
        </label>
        <label className={label}>
          Data contatto<span className="text-red-600"> *</span>
          <input type="date" value={f.data_contatto} onChange={(e) => set("data_contatto", e.target.value)} className={input} />
        </label>
        <Tendina testo="Stato" valore={f.stato} onChange={(v) => set("stato", v)} opzioni={STATI} obbligatoria />
        <Tendina testo="Sport" valore={f.sport} onChange={(v) => set("sport", v)} opzioni={SPORT} obbligatoria />
        <div>
          <Tendina testo="Fonte" valore={f.fonte} onChange={(v) => set("fonte", v)} opzioni={FONTI} obbligatoria />
          <p className="mt-1 text-xs text-gray-500">Chiedi sempre: «Come ci hai conosciuto?»</p>
        </div>
        <Tendina testo="Canale" valore={f.canale} onChange={(v) => set("canale", v)} opzioni={CANALI} />
        <label className={label}>
          Recapito
          <input value={f.recapito} onChange={(e) => set("recapito", e.target.value)} maxLength={120} className={input}
            placeholder="Numero, email o profilo" autoComplete="off" />
        </label>
        <label className={label}>
          Data prova
          <input type="date" value={f.data_prova} onChange={(e) => set("data_prova", e.target.value)} className={input} />
        </label>
        <Tendina testo="Tipo abbonamento" valore={f.tipo_abbonamento} onChange={(v) => set("tipo_abbonamento", v)}
          opzioni={ABBONAMENTI} />
        <label className={label}>
          Importo (€)
          <input inputMode="decimal" value={f.importo_eur} onChange={(e) => set("importo_eur", e.target.value)}
            className={input} placeholder="Versato o da versare" />
        </label>
        <Tendina testo="Responsabile follow-up" valore={f.responsabile_id} onChange={(v) => set("responsabile_id", v)}
          opzioni={membriOpzioni} vuota="Nessuno" />
        <label className={label}>
          Prossimo follow-up
          <input type="date" value={f.prossimo_followup} onChange={(e) => set("prossimo_followup", e.target.value)}
            className={input} />
        </label>
        <label className={`${label} sm:col-span-2 lg:col-span-3`}>
          Note
          <textarea value={f.note} onChange={(e) => set("note", e.target.value)} maxLength={1000} rows={2}
            className={input} />
          <span className={sembraDatoDiSalute(f.note) ? "mt-1 block font-medium text-red-700" : "mt-1 block font-normal text-gray-500"}>
            {sembraDatoDiSalute(f.note)
              ? "Sembra un dato di salute: nelle note non vanno certificati, patologie, infortuni o simili."
              : "Solo informazioni utili al follow-up: niente dati di salute o sensibili."}
          </span>
        </label>
        {dirigenza && (
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={f.is_test} onChange={(e) => set("is_test", e.target.checked)} />
            Riga di prova (TEST): fuori dai conteggi reali
          </label>
        )}
      </div>

      {doppioni.length > 0 && (
        <div className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">Esiste già un contatto con questo nome: una riga per persona, aggiorna quella.</p>
          <ul className="mt-1 space-y-1">
            {doppioni.map((d) => (
              <li key={d.id}>
                <button type="button" onClick={() => onApri(d.id)} className="underline hover:no-underline">
                  {d.nome} · {ETICHETTA_SPORT[d.sport]} · {ETICHETTA_STATO[d.stato]} · {formattaData(d.data_contatto)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button type="button" onClick={salva} disabled={!valido || invio} className={btnPrimario}>
          {invio ? "Salvataggio…" : contattoId ? "Salva modifiche" : "Aggiungi contatto"}
        </button>
        <button type="button" onClick={onChiudi} className={btnSecondario}>Annulla</button>
        {contattoId && dirigenza && (
          <button type="button" onClick={cancella} disabled={invio}
            className="ml-auto text-sm font-medium text-red-600 hover:text-red-800 disabled:opacity-50">
            Cancella su richiesta dell&apos;interessato
          </button>
        )}
      </div>

      {dett && dett.storico.length > 0 && (
        <div className="mt-5 border-t border-gray-100 pt-4">
          <h3 className="text-sm font-semibold text-gray-900">Storico dello stato</h3>
          <ol className="mt-2 space-y-1 text-sm text-gray-700">
            {dett.storico.map((s, i) => (
              <li key={i}>
                <span className="font-medium">{ETICHETTA_STATO[s.stato]}</span>
                <span className="text-gray-500">
                  {" "}· {new Date(s.cambiato_at).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" })}
                  {s.cambiato_da && ` · ${s.cambiato_da}`}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
