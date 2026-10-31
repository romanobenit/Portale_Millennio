"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { SceltaGiocatore } from "@/components/pickleball/SceltaGiocatore";
import {
  aggiornaOspite,
  cercaGiocatoriDirigenza,
  collegaOspite,
  eliminaOspite,
  fetchOspiti,
  invitaOspite,
  type GiocatoreRicerca,
  type Ospite,
} from "@/lib/api/pickleball";

const btnPrimario =
  "rounded-lg bg-blue-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

// Solo soci: un ospite si collega a un socio, non a un altro ospite
const cercaSoci = async (q: string) => (await cercaGiocatoriDirigenza(q)).filter((g) => !g.ospite);

function SchedaOspite({ o, onCambiato }: { o: Ospite; onCambiato: () => void }) {
  const [modifica, setModifica] = useState(false);
  const [collega, setCollega] = useState(false);
  const [club, setClub] = useState(o.club ?? "");
  const [email, setEmail] = useState(o.email ?? "");
  const [sesso, setSesso] = useState(o.sesso ?? "");
  const [anno, setAnno] = useState(o.anno_nascita ? String(o.anno_nascita) : "");
  const [socio, setSocio] = useState<GiocatoreRicerca | null>(null);
  const [busy, setBusy] = useState(false);

  const esegui = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try {
      await fn();
      toast.success(ok);
      setModifica(false);
      setCollega(false);
      onCambiato();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm">
          <p className="font-medium text-gray-900">
            {o.nome} {o.cognome}
            {o.club && <span className="font-normal text-gray-500"> · {o.club}</span>}
          </p>
          <p className="text-xs text-gray-500">
            {o.partite} {o.partite === 1 ? "partita" : "partite"}
            {o.rating_singolo !== null && ` · singolo ${Math.round(o.rating_singolo)}`}
            {o.rating_doppio !== null && ` · doppio ${Math.round(o.rating_doppio)}`}
            {o.invitato_at
              ? ` · invitato il ${new Date(o.invitato_at).toLocaleDateString("it-IT")}`
              : o.email ? " · email presente" : " · nessuna email"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={busy || !o.email} className={btnPrimario}
            title={o.email ? undefined : "Aggiungi prima l'email"}
            onClick={() => {
              if (!o.invitato_at || window.confirm("L'invito è già stato inviato: mandarlo di nuovo?"))
                esegui(() => invitaOspite(o.id), "Invito alla community inviato");
            }}>
            {o.invitato_at ? "Invita di nuovo" : "Invita alla community"}
          </button>
          <button type="button" disabled={busy} className={btnSecondario} onClick={() => { setModifica(!modifica); setCollega(false); }}>
            Modifica
          </button>
          <button type="button" disabled={busy} className={btnSecondario} onClick={() => { setCollega(!collega); setModifica(false); }}>
            Si è iscritto
          </button>
          {o.partite === 0 && (
            <button type="button" disabled={busy} className="text-sm font-medium text-red-600 hover:text-red-800"
              onClick={() => window.confirm(`Eliminare ${o.nome} ${o.cognome}?`) && esegui(() => eliminaOspite(o.id), "Ospite eliminato")}>
              Elimina
            </button>
          )}
        </div>
      </div>

      {modifica && (
        <div className="mt-3 rounded-lg bg-gray-50 p-3">
          <div className="grid gap-3 sm:grid-cols-4">
            <label className="block text-xs font-medium text-gray-600 sm:col-span-2">
              Club
              <input value={club} onChange={(e) => setClub(e.target.value)} maxLength={120} className={input} />
            </label>
            <label className="block text-xs font-medium text-gray-600">
              Sesso
              <select value={sesso} onChange={(e) => setSesso(e.target.value)} className={input}>
                <option value="">—</option>
                <option value="M">Uomo</option>
                <option value="F">Donna</option>
              </select>
            </label>
            <label className="block text-xs font-medium text-gray-600">
              Anno di nascita
              <input type="number" min={1920} max={2025} value={anno} onChange={(e) => setAnno(e.target.value)} className={input} />
            </label>
            <label className="block text-xs font-medium text-gray-600 sm:col-span-4">
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
            </label>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Inserisci l&apos;email solo se il giocatore ha accettato di essere contattato dall&apos;associazione.
          </p>
          <button type="button" disabled={busy} className={btnPrimario + " mt-3"}
            onClick={() => esegui(() => aggiornaOspite(o.id, {
              club: club.trim() || null,
              email: email.trim() || null,
              sesso: (sesso || null) as Ospite["sesso"],
              anno_nascita: anno ? Number(anno) : null,
            }), "Ospite aggiornato")}>
            Salva
          </button>
        </div>
      )}

      {collega && (
        <div className="mt-3 rounded-lg bg-gray-50 p-3">
          <p className="mb-2 text-xs text-gray-600">
            Scegli il socio che corrisponde a {o.nome} {o.cognome}: partite e piazzamenti passano a lui e l&apos;ospite viene
            eliminato.
          </p>
          <SceltaGiocatore etichetta="Socio" valore={socio} onChange={setSocio} cerca={cercaSoci} />
          <button type="button" disabled={busy || !socio} className={btnPrimario + " mt-3"}
            onClick={() => socio && window.confirm(`Collegare ${o.nome} ${o.cognome} a ${socio.nome}? L'operazione non si annulla.`)
              && esegui(() => collegaOspite(o.id, socio.socio_id), "Ospite collegato al socio")}>
            Collega
          </button>
        </div>
      )}
    </li>
  );
}

export function OspitiPanel() {
  const [ospiti, setOspiti] = useState<Ospite[] | null>(null);
  const [filtro, setFiltro] = useState("");

  const carica = useCallback(async () => {
    try {
      setOspiti(await fetchOspiti());
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore di rete");
    }
  }, []);

  useEffect(() => {
    carica();
  }, [carica]);

  if (!ospiti) return <p className="text-gray-500">Caricamento…</p>;
  const f = filtro.trim().toLowerCase();
  const visibili = ospiti.filter((o) => !f || `${o.nome} ${o.cognome} ${o.club ?? ""}`.toLowerCase().includes(f));

  return (
    <div className={card}>
      <h2 className="font-semibold text-gray-900">Ospiti ({ospiti.length})</h2>
      <p className="mt-1 text-xs text-gray-500">
        Giocatori non soci incontrati nei tornei: servono a calcolare l&apos;Elo dei soci e non compaiono nelle
        classifiche. Puoi invitarli a iscriversi alla community; quando si iscrivono, collegali al loro profilo socio.
      </p>
      {ospiti.length > 8 && (
        <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Cerca…"
          className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
      )}
      {visibili.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-500">Nessun ospite.</p>
      ) : (
        <ul className="mt-2 divide-y divide-gray-100">
          {visibili.map((o) => <SchedaOspite key={o.id} o={o} onCambiato={carica} />)}
        </ul>
      )}
    </div>
  );
}
