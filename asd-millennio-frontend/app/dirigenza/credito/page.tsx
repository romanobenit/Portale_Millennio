"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { ListaMovimenti } from "@/components/credito/ListaMovimenti";
import {
  cercaSaldiSoci,
  ETICHETTA_MOVIMENTO,
  fetchRiepilogoCredito,
  fetchSchedaCredito,
  formattaEuro,
  registraMovimento,
  type RiepilogoCredito,
  type SaldoSocio,
  type SchedaCreditoSocio,
} from "@/lib/api/credito";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

type TipoManuale = "ricarica_sede" | "accredito" | "storno";
const TIPI: { valore: TipoManuale; label: string; aiuto: string }[] = [
  { valore: "ricarica_sede", label: "Ricarica in sede", aiuto: "Il socio ha versato l'importo in sede (contanti o POS)." },
  { valore: "accredito", label: "Accredito", aiuto: "Credito concesso dalla dirigenza: indica il motivo." },
  { valore: "storno", label: "Storno", aiuto: "Correzione di un errore: toglie credito. Indica il motivo." },
];

function FormMovimento({ scheda, onFatto }: { scheda: SchedaCreditoSocio; onFatto: (s: SchedaCreditoSocio) => void }) {
  const [tipo, setTipo] = useState<TipoManuale>("ricarica_sede");
  const [importo, setImporto] = useState("");
  const [causale, setCausale] = useState("");
  const [invio, setInvio] = useState(false);

  const valore = Number(importo.replace(",", "."));
  const serveCausale = tipo !== "ricarica_sede";
  const valido = valore > 0 && valore <= 1000 && (!serveCausale || causale.trim().length >= 3);

  const invia = async () => {
    const segno = tipo === "storno" ? "-" : "+";
    if (!window.confirm(`${TIPI.find((t) => t.valore === tipo)!.label} di ${segno}${formattaEuro(valore)} a ${scheda.nome} ${scheda.cognome}?`)) return;
    setInvio(true);
    try {
      const s = await registraMovimento(scheda.socio_id, {
        tipo,
        importo_eur: Math.round(valore * 100) / 100,
        causale: causale.trim() || null,
      });
      toast.success("Movimento registrato");
      setImporto("");
      setCausale("");
      onFatto(s);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Registrazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {TIPI.map((t) => (
          <button key={t.valore} type="button" onClick={() => setTipo(t.valore)}
            className={clsx("rounded-lg border px-3 py-1.5 text-sm font-medium",
              tipo === t.valore ? "border-blue-700 bg-blue-700 text-white" : "border-gray-300 text-gray-700")}>
            {t.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500">{TIPI.find((t) => t.valore === tipo)!.aiuto}</p>
      <div className="grid gap-3 sm:grid-cols-[10rem_1fr]">
        <label className="block text-xs font-medium text-gray-600">
          Importo (€)
          <input inputMode="decimal" value={importo} onChange={(e) => setImporto(e.target.value)} className={input}
            placeholder="es. 20" />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          Causale{serveCausale ? "" : " (facoltativa)"}
          <input value={causale} maxLength={300} onChange={(e) => setCausale(e.target.value)} className={input}
            placeholder={tipo === "ricarica_sede" ? "es. Contanti" : "es. Rimborso torneo annullato"} />
        </label>
      </div>
      <button type="button" onClick={invia} disabled={!valido || invio} className={btnPrimario}>
        {invio ? "Registrazione…" : "Registra movimento"}
      </button>
    </div>
  );
}

export default function DirigenzaCreditoPage() {
  const [riepilogo, setRiepilogo] = useState<RiepilogoCredito | null>(null);
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState<SaldoSocio[]>([]);
  const [scheda, setScheda] = useState<SchedaCreditoSocio | null>(null);
  const [errore, setErrore] = useState<string | null>(null);

  const caricaRiepilogo = useCallback(async () => {
    try {
      setRiepilogo(await fetchRiepilogoCredito());
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore di rete");
    }
  }, []);

  useEffect(() => {
    caricaRiepilogo();
  }, [caricaRiepilogo]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setRisultati([]);
      return;
    }
    const t = setTimeout(() => {
      cercaSaldiSoci(q.trim()).then(setRisultati).catch(() => setRisultati([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const apri = async (socioId: string) => {
    try {
      setScheda(await fetchSchedaCredito(socioId));
      setQ("");
      setRisultati([]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore di rete");
    }
  };

  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!riepilogo) return <p className="text-gray-500">Caricamento…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Credito soci</h1>
        <p className="mt-1 text-sm text-gray-500">
          Registro del credito interno: si usa solo per i servizi dell&apos;associazione, niente trasferimenti fra soci
          né prelievi. I movimenti non si modificano: per correggere un errore registra uno storno.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <div className={card}>
          <p className="text-xs text-gray-500">Credito dei soci in totale</p>
          <p className="mt-1 text-2xl font-bold tabular-nums">{formattaEuro(riepilogo.credito_in_circolo_eur)}</p>
        </div>
        <div className={card}>
          <p className="text-xs text-gray-500">Soci con credito</p>
          <p className="mt-1 text-2xl font-bold tabular-nums">{riepilogo.soci_con_saldo}</p>
        </div>
        <div className={clsx(card, "col-span-2 lg:col-span-1")}>
          <p className="text-xs text-gray-500">Ricarica online</p>
          <p className={clsx("mt-1 text-sm font-semibold", riepilogo.ricarica_online_attiva ? "text-green-700" : "text-gray-600")}>
            {riepilogo.ricarica_online_attiva ? "Attiva" : "Disattivata (si ricarica solo in sede)"}
          </p>
        </div>
      </div>

      {riepilogo.ultimi_30gg.length > 0 && (
        <div className={card}>
          <h2 className="font-semibold text-gray-900">Ultimi 30 giorni</h2>
          <ul className="mt-2 divide-y divide-gray-100 text-sm">
            {riepilogo.ultimi_30gg.map((r) => (
              <li key={r.tipo} className="flex justify-between py-2">
                <span>
                  {ETICHETTA_MOVIMENTO[r.tipo] ?? r.tipo} <span className="text-gray-400">({r.movimenti})</span>
                </span>
                <span className="tabular-nums">{formattaEuro(r.totale_eur, true)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className={card}>
        <h2 className="font-semibold text-gray-900">Cerca un socio</h2>
        <div className="relative mt-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nome, cognome o codice fiscale…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          {risultati.length > 0 && (
            <ul className="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg">
              {risultati.map((r) => (
                <li key={r.socio_id}>
                  <button type="button" onClick={() => apri(r.socio_id)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50">
                    <span>
                      {r.cognome} {r.nome} <span className="text-xs text-gray-400">{r.codice_fiscale}</span>
                    </span>
                    <span className="tabular-nums text-gray-600">{formattaEuro(r.saldo_eur)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {scheda && (
        <div className={card}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="font-semibold text-gray-900">{scheda.nome} {scheda.cognome}</h2>
              <p className="text-xs text-gray-400">{scheda.codice_fiscale}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Saldo</p>
              <p className="text-2xl font-bold tabular-nums">{formattaEuro(scheda.saldo_eur)}</p>
            </div>
          </div>
          <div className="mt-4 border-t border-gray-100 pt-4">
            <FormMovimento scheda={scheda} onFatto={(s) => { setScheda(s); caricaRiepilogo(); }} />
          </div>
          <h3 className="mt-6 text-sm font-semibold text-gray-700">Movimenti</h3>
          <ListaMovimenti movimenti={scheda.movimenti} />
        </div>
      )}
    </div>
  );
}
