"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  eliminaTesseramento,
  fetchTesseramento,
  modificaTesseramento,
  type ModificaTesseramento,
  type TesseramentoDettaglio,
} from "@/lib/api/tesseramento";

const CATEGORIE: [string, string][] = [
  ["volley", "Pallavolo"],
  ["badminton", "Badminton"],
  ["kung_fu", "Kung Fu"],
  ["pickleball", "Pickleball"],
  ["sostenitore", "Sostenitore"],
];
const STATI: [string, string][] = [
  ["attiva", "Attiva"],
  ["sospesa", "Sospesa"],
  ["scaduta", "Scaduta"],
];
const STATO_PAGAMENTO: Record<string, string> = {
  in_attesa_pagamento: "non completato",
  pagato: "pagato online",
  rimborsato: "rimborsato",
  erogazione_liberale: "erogazione liberale",
};

const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-500";
const label = "block text-xs font-medium text-gray-600";

interface Form {
  nome: string;
  cognome: string;
  codice_fiscale: string;
  data_nascita: string;
  telefono: string;
  indirizzo: string;
  categoria: string;
  stato: string;
  data_scadenza: string;
  certificato_medico_tipo: string;
  certificato_medico_scadenza: string;
}

function formDa(d: TesseramentoDettaglio): Form {
  return {
    nome: d.nome,
    cognome: d.cognome,
    codice_fiscale: d.codice_fiscale,
    data_nascita: d.data_nascita,
    telefono: d.telefono ?? "",
    indirizzo: d.indirizzo ?? "",
    categoria: d.categoria,
    stato: d.stato,
    data_scadenza: d.data_scadenza ?? "",
    certificato_medico_tipo: d.certificato_medico_tipo ?? "",
    certificato_medico_scadenza: d.certificato_medico_scadenza ?? "",
  };
}

/** Solo i campi cambiati, così il server tocca solo quelli. */
function modifiche(d: TesseramentoDettaglio, f: Form): ModificaTesseramento {
  const prima = formDa(d);
  const cambiato = (k: keyof Form) => f[k].trim() !== prima[k].trim();
  const socio: NonNullable<ModificaTesseramento["socio"]> = {};
  if (cambiato("nome")) socio.nome = f.nome;
  if (cambiato("cognome")) socio.cognome = f.cognome;
  if (cambiato("codice_fiscale")) socio.codice_fiscale = f.codice_fiscale.trim().toUpperCase();
  if (cambiato("data_nascita")) socio.data_nascita = f.data_nascita;
  if (cambiato("telefono")) socio.telefono = f.telefono.trim() || null;
  if (cambiato("indirizzo")) socio.indirizzo = f.indirizzo.trim() || null;
  const tessera: NonNullable<ModificaTesseramento["tessera"]> = {};
  if (cambiato("categoria")) tessera.categoria = f.categoria;
  if (cambiato("stato")) tessera.stato = f.stato as "attiva" | "sospesa" | "scaduta";
  if (cambiato("data_scadenza")) tessera.data_scadenza = f.data_scadenza || null;
  if (cambiato("certificato_medico_tipo") || cambiato("certificato_medico_scadenza")) {
    tessera.certificato_medico_tipo = (f.certificato_medico_tipo || null) as "non_agonistico" | "agonistico" | null;
    tessera.certificato_medico_scadenza = f.certificato_medico_scadenza || null;
  }
  return {
    ...(Object.keys(socio).length ? { socio } : {}),
    ...(Object.keys(tessera).length ? { tessera } : {}),
  };
}

/** Finestra della dirigenza per correggere una tessera (e l'anagrafica del socio) o eliminarla. */
export function GestioneTessera({
  tesseraId, onChiudi, onCambiato,
}: { tesseraId: string; onChiudi: () => void; onCambiato: () => void }) {
  const [d, setD] = useState<TesseramentoDettaglio | null>(null);
  const [f, setF] = useState<Form | null>(null);
  const [invio, setInvio] = useState(false);

  useEffect(() => {
    fetchTesseramento(tesseraId)
      .then((det) => {
        setD(det);
        setF(formDa(det));
      })
      .catch((e: unknown) => {
        toast.error(e instanceof Error ? e.message : "Tessera non trovata");
        onChiudi();
      });
  }, [tesseraId, onChiudi]);

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onChiudi();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onChiudi]);

  const set = (k: keyof Form, v: string) => setF((prev) => (prev ? { ...prev, [k]: v } : prev));

  const esegui = async (azione: () => Promise<unknown>, ok: string, chiudi = false) => {
    setInvio(true);
    try {
      const res = await azione();
      toast.success(ok);
      onCambiato();
      if (chiudi) onChiudi();
      else if (res && typeof res === "object" && "tessera_id" in res) {
        setD(res as TesseramentoDettaglio);
        setF(formDa(res as TesseramentoDettaglio));
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  const community = d?.categoria === "community";
  const diff = d && f ? modifiche(d, f) : {};
  const nienteDaSalvare = Object.keys(diff).length === 0;

  const salva = () => {
    if (!d || nienteDaSalvare) return;
    if (diff.tessera?.categoria &&
      !window.confirm("Cambiando categoria la tessera riceve un nuovo numero. Continuare?")) return;
    esegui(() => modificaTesseramento(d.tessera_id, diff), "Modifiche salvate");
  };

  const elimina = () => {
    if (!d) return;
    const avviso = `Eliminare la tessera ${d.numero_tessera} di ${d.nome} ${d.cognome}? Non si può annullare.` +
      (d.stato === "attiva" ? " Il socio perde subito l'accesso ai campi e agli eventi legati a questa tessera." : "") +
      (d.altre_tessere === 0 ? " Il socio resta in anagrafica, senza tessere." : "");
    if (window.confirm(avviso)) esegui(() => eliminaTesseramento(d.tessera_id), "Tessera eliminata", true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog" aria-modal="true" aria-labelledby="titolo-gestione-tessera" onClick={onChiudi}>
      <div className="w-full max-w-2xl rounded-xl bg-white p-5 shadow-xl sm:p-6" onClick={(e) => e.stopPropagation()}>
        {!d || !f ? (
          <p className="text-sm text-gray-500">Caricamento…</p>
        ) : (
          <>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 id="titolo-gestione-tessera" className="text-lg font-semibold text-gray-900">
                  Tessera <span className="font-mono">{d.numero_tessera}</span>
                </h2>
                <p className="text-sm text-gray-500">
                  {d.anno_sportivo ?? "—"} · {d.email}
                  {d.is_minor && " · minore (gestito dal tutore)"}
                </p>
              </div>
              <button type="button" onClick={onChiudi} className="text-sm text-gray-500 hover:text-gray-800">Chiudi</button>
            </div>

            <h3 className="mt-5 text-sm font-semibold text-gray-900">Anagrafica</h3>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              <label className={label}>Nome<input value={f.nome} onChange={(e) => set("nome", e.target.value)} className={input} /></label>
              <label className={label}>Cognome<input value={f.cognome} onChange={(e) => set("cognome", e.target.value)} className={input} /></label>
              <label className={label}>
                Codice fiscale
                <input value={f.codice_fiscale} maxLength={16}
                  onChange={(e) => set("codice_fiscale", e.target.value.toUpperCase())} className={`${input} font-mono`} />
              </label>
              <label className={label}>
                Data di nascita
                <input type="date" value={f.data_nascita} disabled={d.is_minor}
                  onChange={(e) => set("data_nascita", e.target.value)} className={input} />
              </label>
              <label className={label}>Telefono<input value={f.telefono} onChange={(e) => set("telefono", e.target.value)} className={input} /></label>
              <label className={label}>Indirizzo<input value={f.indirizzo} onChange={(e) => set("indirizzo", e.target.value)} className={input} /></label>
            </div>
            <p className="mt-1 text-xs text-gray-500">L&apos;email non si cambia da qui: è quella con cui il socio accede.</p>

            <h3 className="mt-5 text-sm font-semibold text-gray-900">Tessera</h3>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              <label className={label}>
                Categoria
                <select value={f.categoria} disabled={community} onChange={(e) => set("categoria", e.target.value)} className={input}>
                  {community && <option value="community">Community</option>}
                  {CATEGORIE.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className={label}>
                Stato
                <select value={f.stato} onChange={(e) => set("stato", e.target.value)} className={input}>
                  {!STATI.some(([k]) => k === d.stato) && <option value={d.stato} disabled>{d.stato.replaceAll("_", " ")}</option>}
                  {STATI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              {!community && (
                <label className={label}>
                  Scadenza
                  <input type="date" value={f.data_scadenza} onChange={(e) => set("data_scadenza", e.target.value)} className={input} />
                </label>
              )}
              <label className={label}>
                Certificato medico
                <select value={f.certificato_medico_tipo} onChange={(e) => set("certificato_medico_tipo", e.target.value)} className={input}>
                  <option value="">Non caricato</option>
                  <option value="non_agonistico">Non agonistico</option>
                  <option value="agonistico">Agonistico</option>
                </select>
              </label>
              {f.certificato_medico_tipo && (
                <label className={label}>
                  Scadenza certificato
                  <input type="date" value={f.certificato_medico_scadenza}
                    onChange={(e) => set("certificato_medico_scadenza", e.target.value)} className={input} />
                </label>
              )}
            </div>
            {d.verifica_stato === "in_verifica" && (
              <p className="mt-2 text-xs text-blue-700">Tesseramento online ancora in verifica: la conferma si fa dalla coda verifiche.</p>
            )}

            {d.pagamenti.length > 0 && (
              <div className="mt-5 rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
                <p className="font-medium text-gray-900">Pagamenti della quota</p>
                <ul className="mt-1 space-y-0.5">
                  {d.pagamenti.map((p, i) => (
                    <li key={i}>
                      € {Number(p.importo_eur).toFixed(2).replace(".", ",")} · {STATO_PAGAMENTO[p.stato] ?? p.stato} ·{" "}
                      {new Date(p.created_at).toLocaleDateString("it-IT")}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button type="button" onClick={salva} disabled={invio || nienteDaSalvare}
                className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">
                {invio ? "Salvataggio…" : "Salva modifiche"}
              </button>
              <button type="button" onClick={onChiudi}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50">
                Annulla
              </button>
              {d.eliminabile ? (
                <button type="button" onClick={elimina} disabled={invio}
                  className="ml-auto text-sm font-medium text-red-600 hover:text-red-800 disabled:opacity-50">
                  Elimina tessera
                </button>
              ) : (
                d.stato !== "sospesa" && (
                  <button type="button" disabled={invio}
                    onClick={() => window.confirm("Sospendere la tessera?") &&
                      esegui(() => modificaTesseramento(d.tessera_id, { tessera: { stato: "sospesa" } }), "Tessera sospesa")}
                    className="ml-auto text-sm font-medium text-orange-700 hover:text-orange-900 disabled:opacity-50">
                    Sospendi tessera
                  </button>
                )
              )}
            </div>
            {!d.eliminabile && d.motivo_non_eliminabile && (
              <p className="mt-2 text-xs text-gray-500">{d.motivo_non_eliminabile}</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
