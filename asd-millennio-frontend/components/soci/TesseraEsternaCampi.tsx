"use client";

import type { TesseraEsternaInput } from "@/lib/api/tesseramento";

const ENTI = [
  "FIBa – Federazione Italiana Badminton",
  "FIPAV – Federazione Italiana Pallavolo",
  "FITP – Federazione Italiana Tennis e Padel",
  "FIWuK – Federazione Italiana Wushu Kung Fu",
  "ACSI",
  "AICS",
  "ASC",
  "ASI",
  "CSEN",
  "CSI",
  "CUSI",
  "ENDAS",
  "Libertas",
  "MSP Italia",
  "OPES",
  "PGS",
  "UISP",
  "US ACLI",
];

const DISCIPLINE = ["Pickleball", "Badminton", "Pallavolo", "Kung Fu"];

export const TESSERA_ESTERNA_VUOTA: TesseraEsternaInput = {
  ente: "",
  asd_nome: "",
  asd_codice: "",
  numero_tessera: "",
  disciplina: "",
  data_scadenza: "",
};

/** Messaggio d'errore se i dati non sono completi (null = ok). */
export function erroreTesseraEsterna(dati: TesseraEsternaInput, file: File | null): string | null {
  if (!dati.ente.trim() || !dati.asd_nome.trim() || !dati.numero_tessera.trim() || !dati.disciplina.trim()) {
    return "Compila ente, ASD, numero di tessera e disciplina.";
  }
  if (!dati.data_scadenza) return "Indica la data di scadenza della tessera.";
  if (dati.data_scadenza < new Date().toISOString().slice(0, 10)) return "La tessera risulta già scaduta.";
  if (!file) return "Carica la foto o la scansione della tessera.";
  return null;
}

const input = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

export function TesseraEsternaCampi({
  dati,
  onChange,
  onFile,
}: {
  dati: TesseraEsternaInput;
  onChange: (d: TesseraEsternaInput) => void;
  onFile: (f: File | null) => void;
}) {
  const set = (k: keyof TesseraEsternaInput, v: string) => onChange({ ...dati, [k]: v });
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <label className="block sm:col-span-2">
        <span className="mb-1 block text-xs font-medium text-gray-700">Federazione o ente di promozione sportiva</span>
        <input
          className={input}
          list="enti-affiliazione"
          value={dati.ente}
          onChange={(e) => set("ente", e.target.value)}
          placeholder="Scegli dall'elenco o scrivi il nome"
        />
        <datalist id="enti-affiliazione">
          {ENTI.map((e) => (
            <option key={e} value={e} />
          ))}
        </datalist>
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">ASD di appartenenza</span>
        <input className={input} value={dati.asd_nome} onChange={(e) => set("asd_nome", e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Codice affiliazione ASD (facoltativo)</span>
        <input className={input} value={dati.asd_codice ?? ""} onChange={(e) => set("asd_codice", e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Numero di tessera</span>
        <input className={input} value={dati.numero_tessera} onChange={(e) => set("numero_tessera", e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Disciplina</span>
        <input
          className={input}
          list="discipline-esterne"
          value={dati.disciplina}
          onChange={(e) => set("disciplina", e.target.value)}
        />
        <datalist id="discipline-esterne">
          {DISCIPLINE.map((d) => (
            <option key={d} value={d} />
          ))}
        </datalist>
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Scadenza della tessera</span>
        <input type="date" className={input} value={dati.data_scadenza} onChange={(e) => set("data_scadenza", e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Foto o scansione della tessera</span>
        <input
          type="file"
          accept=".pdf,image/*"
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-blue-700"
        />
      </label>
    </div>
  );
}
