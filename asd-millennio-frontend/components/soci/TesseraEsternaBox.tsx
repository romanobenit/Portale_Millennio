"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import {
  caricaTesseraEsterna,
  fetchTessereEsterne,
  type TesseraEsterna,
  type TesseraEsternaInput,
} from "@/lib/api/tesseramento";
import { formattaData } from "@/lib/api/eventi";
import { TesseraEsternaCampi, TESSERA_ESTERNA_VUOTA, erroreTesseraEsterna } from "./TesseraEsternaCampi";

const VERIFICA: Record<TesseraEsterna["verifica_stato"], { label: string; classes: string }> = {
  in_verifica: { label: "In verifica", classes: "bg-blue-100 text-blue-800" },
  confermata: { label: "Verificata", classes: "bg-green-100 text-green-800" },
  rifiutata: { label: "Non accettata", classes: "bg-red-100 text-red-700" },
};

/** Tessera dell'altra ASD collegata all'iscrizione community: stato, scadenza e aggiornamento. */
export function TesseraEsternaBox({ socioId }: { socioId?: string }) {
  const [tessere, setTessere] = useState<TesseraEsterna[] | null>(null);
  const [mostraForm, setMostraForm] = useState(false);
  const [dati, setDati] = useState<TesseraEsternaInput>(TESSERA_ESTERNA_VUOTA);
  const [file, setFile] = useState<File | null>(null);
  const [salvando, setSalvando] = useState(false);

  const carica = useCallback(async () => {
    try {
      setTessere(await fetchTessereEsterne(socioId));
    } catch {
      setTessere([]);
    }
  }, [socioId]);

  useEffect(() => {
    carica();
  }, [carica]);

  const salva = async () => {
    const errore = erroreTesseraEsterna(dati, file);
    if (errore) {
      toast.error(errore);
      return;
    }
    setSalvando(true);
    try {
      await caricaTesseraEsterna(dati, file!, socioId);
      toast.success("Tessera aggiornata: puoi già prenotare, la segreteria la verificherà.");
      setMostraForm(false);
      setDati(TESSERA_ESTERNA_VUOTA);
      setFile(null);
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Caricamento non riuscito");
    } finally {
      setSalvando(false);
    }
  };

  if (tessere === null) return <p className="text-xs text-gray-400">Caricamento tessera…</p>;

  const attuale = tessere[0];
  const oggi = new Date().toISOString().slice(0, 10);
  const scaduta = attuale && attuale.data_scadenza < oggi;

  return (
    <div>
      {attuale ? (
        <div className="text-xs text-gray-600">
          <p>
            <span className="font-medium text-gray-800">{attuale.asd_nome}</span> · {attuale.ente}
          </p>
          <p>
            Tessera n. {attuale.numero_tessera} · {attuale.disciplina} ·{" "}
            <span className={clsx("font-medium", scaduta ? "text-red-600" : "text-gray-800")}>
              {scaduta ? "scaduta il" : "valida fino al"} {formattaData(attuale.data_scadenza)}
            </span>
            <span className={clsx("ml-2 rounded-full px-2 py-0.5 font-medium", VERIFICA[attuale.verifica_stato].classes)}>
              {VERIFICA[attuale.verifica_stato].label}
            </span>
          </p>
          {(scaduta || attuale.verifica_stato === "rifiutata") && (
            <p className="mt-1 font-medium text-red-600">
              Per prenotare gli eventi carica la tessera rinnovata.
            </p>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-400">Nessuna tessera caricata.</p>
      )}
      <button onClick={() => setMostraForm((v) => !v)} className="mt-2 text-xs text-blue-700 hover:underline">
        {mostraForm ? "Chiudi" : "Aggiorna tessera"}
      </button>
      {mostraForm && (
        <div className="mt-3 space-y-3 rounded-lg bg-gray-50 p-3">
          <TesseraEsternaCampi dati={dati} onChange={setDati} onFile={setFile} />
          <button
            onClick={salva}
            disabled={salvando}
            className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
          >
            {salvando ? "Caricamento…" : "Salva tessera"}
          </button>
        </div>
      )}
    </div>
  );
}
