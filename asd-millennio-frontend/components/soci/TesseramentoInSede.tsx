"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { cercaSoci, type SocioRicerca } from "@/lib/api/eventi";
import { fetchQuote, tesseramentoInSede, type Quota } from "@/lib/api/tesseramento";

const CATEGORIE = [
  { value: "pickleball", label: "Pickleball" },
  { value: "badminton", label: "Badminton" },
  { value: "volley", label: "Pallavolo" },
  { value: "kung_fu", label: "Kung Fu" },
  { value: "sostenitore", label: "Socio sostenitore" },
];

const input = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

const ANAGRAFICA_VUOTA = {
  nome: "",
  cognome: "",
  data_nascita: "",
  codice_fiscale: "",
  email: "",
  telefono: "",
  indirizzo: "",
};

/** Tesseramento fatto dalla dirigenza in sede: quota pagata sul posto, tessera subito attiva. */
export function TesseramentoInSede({ onFatto }: { onFatto: () => void }) {
  const [modo, setModo] = useState<"nuovo" | "esistente">("nuovo");
  const [anag, setAnag] = useState(ANAGRAFICA_VUOTA);
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState<SocioRicerca[]>([]);
  const [scelto, setScelto] = useState<SocioRicerca | null>(null);
  const [categoria, setCategoria] = useState("pickleball");
  const [consensi, setConsensi] = useState(false);
  const [quote, setQuote] = useState<Quota[]>([]);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    fetchQuote()
      .then(setQuote)
      .catch(() => setQuote([]));
  }, []);

  useEffect(() => {
    if (modo !== "esistente" || q.trim().length < 2) {
      setRisultati([]);
      return;
    }
    const t = setTimeout(() => {
      cercaSoci(q.trim())
        .then(setRisultati)
        .catch(() => setRisultati([]));
    }, 300);
    return () => clearTimeout(t);
  }, [q, modo]);

  const quota = quote.find((x) => x.categoria === categoria && !x.is_minore && x.attivo);

  const salva = async () => {
    if (modo === "esistente" && !scelto) {
      toast.error("Seleziona il socio da tesserare");
      return;
    }
    if (!consensi) {
      toast.error("Conferma i consensi firmati e il pagamento della quota");
      return;
    }
    setSalvando(true);
    try {
      const esito = await tesseramentoInSede({
        ...(modo === "esistente"
          ? { socio_id: scelto!.id }
          : {
              anagrafica: {
                ...anag,
                telefono: anag.telefono.trim() || null,
                indirizzo: anag.indirizzo.trim() || null,
              },
            }),
        categoria,
        consensi_firmati: true,
      });
      toast.success(`Tessera ${esito.numero_tessera} attiva per ${esito.nome} ${esito.cognome}`, { duration: 6000 });
      setAnag(ANAGRAFICA_VUOTA);
      setScelto(null);
      setQ("");
      setConsensi(false);
      onFatto();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Tesseramento non riuscito");
    } finally {
      setSalvando(false);
    }
  };

  const campo = (k: keyof typeof ANAGRAFICA_VUOTA, label: string, type = "text") => (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-gray-700">{label}</span>
      <input
        type={type}
        className={input}
        value={anag[k]}
        onChange={(e) => setAnag({ ...anag, [k]: k === "codice_fiscale" ? e.target.value.toUpperCase() : e.target.value })}
      />
    </label>
  );

  return (
    <div className="space-y-4 rounded-xl border border-blue-200 bg-blue-50/40 p-4 sm:p-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Tessera in sede</h2>
        <p className="text-sm text-gray-500">
          Per chi si tessera di persona: quota pagata sul posto e documento verificato ora, la tessera è subito attiva.
          Solo maggiorenni (i minori si tesserano dall&apos;area soci del tutore).
        </p>
      </div>

      <div className="inline-flex rounded-lg border border-gray-300 bg-white p-0.5 text-sm">
        {(["nuovo", "esistente"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setModo(m)}
            className={clsx("rounded-md px-3 py-1.5 font-medium", modo === m ? "bg-blue-700 text-white" : "text-gray-700")}
          >
            {m === "nuovo" ? "Nuova persona" : "Già registrata"}
          </button>
        ))}
      </div>

      {modo === "nuovo" ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {campo("nome", "Nome")}
          {campo("cognome", "Cognome")}
          {campo("data_nascita", "Data di nascita", "date")}
          {campo("codice_fiscale", "Codice fiscale")}
          {campo("email", "Email", "email")}
          {campo("telefono", "Telefono (facoltativo)", "tel")}
          <div className="sm:col-span-2">{campo("indirizzo", "Indirizzo (facoltativo)")}</div>
          <p className="text-xs text-gray-500 sm:col-span-2">
            Se poi la persona si registra al portale con questa email, ritrova in automatico profilo e tessera.
          </p>
        </div>
      ) : scelto ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2">
          <span className="text-sm">
            <span className="font-medium text-gray-900">
              {scelto.cognome} {scelto.nome}
            </span>
            <span className="ml-2 font-mono text-xs text-gray-500">{scelto.codice_fiscale}</span>
          </span>
          <button onClick={() => setScelto(null)} className="text-sm text-blue-700 hover:underline">
            Cambia
          </button>
        </div>
      ) : (
        <div>
          <input
            className={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Cerca per nome, cognome, codice fiscale o email"
          />
          {risultati.length > 0 && (
            <ul className="mt-2 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
              {risultati.map((s) => (
                <li key={s.id}>
                  <button onClick={() => setScelto(s)} className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50">
                    <span className="font-medium text-gray-900">
                      {s.cognome} {s.nome}
                    </span>
                    <span className="ml-2 font-mono text-xs text-gray-500">{s.codice_fiscale}</span>
                    {s.tessera_attiva && <span className="ml-2 text-xs text-green-700">ha già una tessera attiva</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-gray-700">Categoria</span>
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className={clsx(input, "w-auto")}>
            {CATEGORIE.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <p className="pb-2 text-sm text-gray-700">
          {quota ? (
            <>
              Quota da incassare: <strong>€{Number(quota.importo_eur).toFixed(2).replace(".", ",")}</strong>
            </>
          ) : (
            <span className="text-gray-500">Nessuna quota configurata per questa categoria</span>
          )}
        </p>
      </div>

      <label className="flex items-start gap-2 text-sm text-gray-700">
        <input type="checkbox" className="mt-0.5" checked={consensi} onChange={(e) => setConsensi(e.target.checked)} />
        <span>
          Ho verificato il documento d&apos;identità, la persona ha firmato i consensi privacy e trattamento dati sul
          modulo cartaceo e ha pagato la quota.
        </span>
      </label>

      <button
        onClick={salva}
        disabled={salvando}
        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {salvando ? "Tesseramento…" : "Emetti tessera"}
      </button>
    </div>
  );
}
