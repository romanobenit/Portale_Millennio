"use client";

import { useEffect, useState } from "react";
import { getKeycloak } from "@/lib/auth/keycloak";
import { fetchMe, fetchTessereSocio, Tessera } from "@/lib/api/soci";
import { clsx } from "clsx";

const SPORT_LABEL: Record<string, string> = {
  volley: "Volley",
  badminton: "Badminton",
  kung_fu: "Kung Fu",
  pickleball: "Pickleball",
  sostenitore: "Socio Sostenitore",
};

const STATO_BADGE: Record<string, { label: string; classes: string }> = {
  attiva: { label: "Attiva", classes: "bg-green-100 text-green-800" },
  bozza: { label: "Bozza", classes: "bg-gray-100 text-gray-700" },
  in_attesa_pagamento: { label: "In attesa pagamento", classes: "bg-yellow-100 text-yellow-800" },
  scaduta: { label: "Scaduta", classes: "bg-red-100 text-red-700" },
  sospesa: { label: "Sospesa", classes: "bg-orange-100 text-orange-800" },
};

export default function TesserePage() {
  const [tessere, setTessere] = useState<Tessera[]>([]);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);

  useEffect(() => {
    const kc = getKeycloak();
    // Usa kc.token invece di kc.authenticated — più affidabile dopo init
    if (!kc.token) {
      kc.login();
      return;
    }

    async function carica() {
      try {
        const socio = await fetchMe();
        const lista = await fetchTessereSocio(socio.id);
        setTessere(lista);
      } catch {
        setErrore("Impossibile caricare le tessere. Riprova più tardi.");
      } finally {
        setLoading(false);
      }
    }

    carica();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (errore) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
        {errore}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Le mie tessere</h1>

      {tessere.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-gray-500 text-sm">
            Nessuna tessera associata al tuo profilo.
          </p>
          <p className="text-gray-400 text-xs mt-2">
            Contatta lo staff per richiedere il tesseramento.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {tessere.map((t) => (
            <TesseraCard key={t.id} tessera={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function TesseraCard({ tessera }: { tessera: Tessera }) {
  const badge = STATO_BADGE[tessera.stato] ?? { label: tessera.stato, classes: "bg-gray-100 text-gray-700" };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <span className="font-mono text-sm font-semibold text-gray-800">
              {tessera.numero_tessera}
            </span>
            <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full", badge.classes)}>
              {badge.label}
            </span>
            {tessera.verifica_stato === "in_verifica" && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                In verifica
              </span>
            )}
            {tessera.verifica_stato === "confermata" && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-800">
                Confermata
              </span>
            )}
            {tessera.verifica_stato === "rifiutata" && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                Non confermata
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600">
            {SPORT_LABEL[tessera.sport] ?? tessera.sport}
            {tessera.anno_sportivo && (
              <span className="ml-2 text-gray-400">— Anno sportivo {tessera.anno_sportivo}</span>
            )}
          </p>
        </div>

        {tessera.pdf_url && tessera.stato === "attiva" && (
          <a
            href={tessera.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Scarica PDF
          </a>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-gray-500">
        {tessera.data_emissione && (
          <>
            <span>Emissione</span>
            <span className="text-gray-700">{tessera.data_emissione}</span>
          </>
        )}
        {tessera.data_scadenza && (
          <>
            <span>Scadenza</span>
            <span className={clsx(
              "font-medium",
              tessera.stato === "scaduta" ? "text-red-600" : "text-gray-700"
            )}>
              {tessera.data_scadenza}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
