"use client";

import { useState } from "react";
import { caricaCertificatoMedico } from "@/lib/api/tesseramento";
import type { Tessera } from "@/lib/api/soci";
import toast from "react-hot-toast";
import { clsx } from "clsx";

export function CertificatoMedicoBox({
  tessera,
  onAggiornato,
}: {
  tessera: Tessera;
  onAggiornato: (t: Tessera) => void;
}) {
  const [mostraForm, setMostraForm] = useState(false);
  const [tipo, setTipo] = useState<"non_agonistico" | "agonistico">("non_agonistico");
  const [scadenza, setScadenza] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [caricando, setCaricando] = useState(false);

  const oggiISO = new Date().toISOString().slice(0, 10);
  const scaduto = !!tessera.certificato_medico_scadenza && tessera.certificato_medico_scadenza < oggiISO;

  const salva = async () => {
    if (!file || !scadenza) {
      toast.error("Seleziona un file e la data di scadenza.");
      return;
    }
    setCaricando(true);
    try {
      const aggiornata = await caricaCertificatoMedico(tessera.id, tipo, scadenza, file);
      toast.success("Certificato medico caricato.");
      onAggiornato(aggiornata);
      setMostraForm(false);
      setFile(null);
      setScadenza("");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nel caricamento del certificato");
    } finally {
      setCaricando(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs text-gray-600">
          {tessera.certificato_medico_tipo ? (
            <span className={clsx("font-medium", scaduto ? "text-red-600" : "text-gray-800")}>
              {tessera.certificato_medico_tipo === "agonistico" ? "Agonistico" : "Non agonistico"}
              {" — "}{scaduto ? "scaduto il" : "scade il"} {tessera.certificato_medico_scadenza}
            </span>
          ) : (
            <span className="text-gray-400">nessuno caricato</span>
          )}
        </p>
        <button onClick={() => setMostraForm((s) => !s)} className="text-xs text-blue-700 hover:underline">
          {tessera.certificato_medico_tipo ? "Aggiorna certificato" : "Carica certificato"}
        </button>
      </div>

      {mostraForm && (
        <div className="mt-3 space-y-2 rounded-lg bg-gray-50 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value as "non_agonistico" | "agonistico")}
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs"
            >
              <option value="non_agonistico">Non agonistico</option>
              <option value="agonistico">Agonistico</option>
            </select>
            <input
              type="date"
              value={scadenza}
              onChange={(e) => setScadenza(e.target.value)}
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs"
            />
            <input
              type="file"
              accept=".pdf,image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-xs"
            />
          </div>
          <button
            onClick={salva}
            disabled={caricando}
            className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors"
          >
            {caricando ? "Caricamento…" : "Salva certificato"}
          </button>
        </div>
      )}
    </div>
  );
}
