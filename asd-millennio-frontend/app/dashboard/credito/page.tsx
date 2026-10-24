"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { ListaMovimenti } from "@/components/credito/ListaMovimenti";
import { avviaRicaricaOnline, fetchMioCredito, formattaEuro, type MioCredito } from "@/lib/api/credito";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const TAGLI = [10, 20, 50, 100];

export default function CreditoPage() {
  const searchParams = useSearchParams();
  const esito = searchParams.get("status");
  const [credito, setCredito] = useState<MioCredito | null>(null);
  const [errore, setErrore] = useState<string | null>(null);
  const [importo, setImporto] = useState(20);
  const [invio, setInvio] = useState(false);

  const carica = useCallback(async () => {
    try {
      setCredito(await fetchMioCredito());
      setErrore(null);
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore di rete");
    }
  }, []);

  useEffect(() => {
    carica();
  }, [carica]);

  const ricarica = async () => {
    setInvio(true);
    try {
      window.location.href = await avviaRicaricaOnline(importo);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Ricarica non disponibile");
      setInvio(false);
    }
  };

  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!credito) return <p className="text-gray-500">Caricamento…</p>;

  const saldo = Number(credito.saldo_eur);
  const spazio = credito.saldo_max_eur - saldo;
  const importoValido =
    importo >= credito.ricarica_min_eur && importo <= credito.ricarica_max_eur && importo <= spazio;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Il mio credito</h1>
        <p className="mt-1 text-sm text-gray-500">
          Il credito si usa solo per i servizi della Millennio (per ora gli ingressi agli eventi) e non è trasferibile
          ad altri soci.
        </p>
      </div>

      {esito === "success" && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Pagamento completato: la ricarica compare tra qualche secondo (se non la vedi, aggiorna la pagina).
        </div>
      )}
      {esito === "cancel" && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
          Ricarica annullata: non ti è stato addebitato nulla.
        </div>
      )}

      <div className={card}>
        <p className="text-sm text-gray-500">Saldo disponibile</p>
        <p className="mt-1 text-4xl font-bold tabular-nums text-gray-900">{formattaEuro(saldo)}</p>
        {saldo > 0 && (
          <Link href="/dashboard/prenotazioni" className="mt-2 inline-block text-sm font-medium text-blue-700 hover:underline">
            Usalo per prenotare un evento →
          </Link>
        )}
      </div>

      <div className={card}>
        <h2 className="font-semibold text-gray-900">Ricarica</h2>
        {credito.ricarica_online_attiva ? (
          <>
            <div className="mt-3 flex flex-wrap gap-2">
              {TAGLI.filter((t) => t >= credito.ricarica_min_eur && t <= credito.ricarica_max_eur).map((t) => (
                <button key={t} type="button" onClick={() => setImporto(t)}
                  className={clsx("rounded-lg border px-4 py-2 text-sm font-semibold",
                    importo === t ? "border-blue-700 bg-blue-700 text-white" : "border-gray-300 text-gray-800")}>
                  € {t}
                </button>
              ))}
              <label className="flex items-center gap-2 text-sm text-gray-600">
                altro
                <input type="number" min={credito.ricarica_min_eur} max={credito.ricarica_max_eur} step={1}
                  value={importo} onChange={(e) => setImporto(Math.floor(Number(e.target.value) || 0))}
                  className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </label>
            </div>
            {!importoValido && (
              <p className="mt-2 text-xs text-red-600">
                {importo > spazio
                  ? `Il credito non può superare ${formattaEuro(credito.saldo_max_eur)}: puoi ricaricare al massimo ${formattaEuro(Math.max(0, Math.floor(spazio)))}.`
                  : `La ricarica va da ${credito.ricarica_min_eur} a ${credito.ricarica_max_eur} euro.`}
              </p>
            )}
            <button type="button" onClick={ricarica} disabled={!importoValido || invio} className={clsx(btnPrimario, "mt-4")}>
              {invio ? "Attendi…" : `Ricarica ${formattaEuro(importo)} con carta`}
            </button>
          </>
        ) : (
          <p className="mt-2 text-sm text-gray-600">
            Puoi ricaricare il credito in sede: la dirigenza registra il versamento e lo trovi subito qui.
          </p>
        )}
      </div>

      <div className={card}>
        <h2 className="font-semibold text-gray-900">Movimenti</h2>
        <div className="mt-1">
          <ListaMovimenti movimenti={credito.movimenti} />
        </div>
      </div>
    </div>
  );
}
