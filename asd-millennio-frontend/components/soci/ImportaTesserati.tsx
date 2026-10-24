"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { importaTesserati, type ImportTesserati } from "@/lib/api/tesseramento";

const CATEGORIE = [
  { value: "pickleball", label: "Pickleball" },
  { value: "badminton", label: "Badminton" },
  { value: "volley", label: "Pallavolo" },
  { value: "kung_fu", label: "Kung Fu" },
  { value: "sostenitore", label: "Socio sostenitore" },
];

const ESITO: Record<string, { label: string; classes: string }> = {
  nuovo: { label: "Nuovo socio", classes: "bg-green-100 text-green-800" },
  esistente: { label: "Già registrato", classes: "bg-blue-100 text-blue-800" },
  errore: { label: "Errore", classes: "bg-red-100 text-red-700" },
};

function scaricaModello() {
  // ";" e BOM: Excel in italiano lo apre direttamente in colonne.
  const testo =
    "﻿Cognome;Nome;Data di nascita;Codice fiscale;Email;Telefono\n" +
    "Rossi;Mario;24/09/1975;RSSMRA75P24F839X;mario.rossi@esempio.it;3331234567\n";
  const url = URL.createObjectURL(new Blob([testo], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "modello-tesserati.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/** Tesseramento in sede di più persone da un file CSV, con anteprima prima di confermare. */
export function ImportaTesserati({ onFatto }: { onFatto: () => void }) {
  const [categoria, setCategoria] = useState("pickleball");
  const [file, setFile] = useState<File | null>(null);
  const [consensi, setConsensi] = useState(false);
  const [risultato, setRisultato] = useState<ImportTesserati | null>(null);
  const [busy, setBusy] = useState(false);

  const esegui = async (conferma: boolean) => {
    if (!file) {
      toast.error("Scegli il file da importare");
      return;
    }
    if (conferma && !consensi) {
      toast.error("Conferma che consensi e quote sono stati raccolti");
      return;
    }
    setBusy(true);
    try {
      const r = await importaTesserati(file, categoria, { conferma, consensiFirmati: consensi });
      setRisultato(r);
      if (conferma) {
        toast.success(`Importazione completata: ${r.nuovi + r.esistenti} tessere emesse`);
        onFatto();
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Importazione non riuscita");
    } finally {
      setBusy(false);
    }
  };

  const daImportare = risultato && !risultato.importato ? risultato.nuovi + risultato.esistenti : 0;

  return (
    <div className="space-y-4 rounded-xl border border-blue-200 bg-blue-50/40 p-4 sm:p-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Importa tesserati da file</h2>
        <p className="text-sm text-gray-500">
          File CSV (da Excel: «Salva con nome → CSV») con le colonne Cognome, Nome, Data di nascita, Codice fiscale,
          Email; le altre colonne vengono ignorate. Stesse regole di «Tessera in sede»: tessera subito attiva, solo
          maggiorenni. Prima vedi l&apos;anteprima, poi confermi.
        </p>
        <button onClick={scaricaModello} className="mt-1 text-sm text-blue-700 hover:underline">
          Scarica il modello
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-gray-700">Categoria</span>
          <select
            value={categoria}
            onChange={(e) => {
              setCategoria(e.target.value);
              setRisultato(null);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            {CATEGORIE.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-gray-700">File</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setRisultato(null);
            }}
            className="block text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-blue-700"
          />
        </label>
        <button
          onClick={() => esegui(false)}
          disabled={busy || !file}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50"
        >
          {busy && !risultato ? "Controllo…" : "Anteprima"}
        </button>
      </div>

      {risultato && (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            {risultato.importato ? "Importati" : "Da importare"}: <strong>{risultato.nuovi}</strong> nuovi soci,{" "}
            <strong>{risultato.esistenti}</strong> già registrati · <strong>{risultato.errori}</strong> righe con errori
            {risultato.errori > 0 && !risultato.importato && " (verranno saltate)"}
          </p>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="w-full whitespace-nowrap text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-3 py-2">Riga</th>
                  <th className="px-3 py-2">Persona</th>
                  <th className="px-3 py-2">Esito</th>
                  <th className="px-3 py-2">Dettagli</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {risultato.righe.map((r) => (
                  <tr key={r.riga}>
                    <td className="px-3 py-2 text-gray-500">{r.riga}</td>
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {r.cognome} {r.nome}
                    </td>
                    <td className="px-3 py-2">
                      <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", ESITO[r.esito].classes)}>
                        {ESITO[r.esito].label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {r.numero_tessera ? <span className="font-mono">{r.numero_tessera}</span> : r.messaggio ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!risultato.importato && daImportare > 0 && (
            <div className="space-y-3">
              <label className="flex items-start gap-2 text-sm text-gray-700">
                <input type="checkbox" className="mt-0.5" checked={consensi} onChange={(e) => setConsensi(e.target.checked)} />
                <span>
                  Per tutte le persone dell&apos;elenco ho verificato il documento d&apos;identità, hanno firmato i
                  consensi privacy e trattamento dati sul modulo cartaceo e hanno pagato la quota.
                </span>
              </label>
              <button
                onClick={() => esegui(true)}
                disabled={busy}
                className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
              >
                {busy ? "Importazione…" : `Importa ${daImportare} ${daImportare === 1 ? "tessera" : "tessere"}`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
