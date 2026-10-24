"use client";

import { useEffect, useState } from "react";
import type { GiocatoreRicerca } from "@/lib/api/pickleball";

interface Props {
  etichetta: string;
  valore: GiocatoreRicerca | null;
  onChange: (g: GiocatoreRicerca | null) => void;
  cerca: (q: string) => Promise<GiocatoreRicerca[]>;
  esclusi?: string[];
}

/** Campo con ricerca per nome: digiti almeno 2 lettere e scegli dalla lista. */
export function SceltaGiocatore({ etichetta, valore, onChange, cerca, esclusi = [] }: Props) {
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState<GiocatoreRicerca[]>([]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setRisultati([]);
      return;
    }
    const t = setTimeout(() => {
      cerca(q.trim()).then(setRisultati).catch(() => setRisultati([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, cerca]);

  if (valore) {
    return (
      <div>
        <span className="block text-xs font-medium text-gray-600">{etichetta}</span>
        <div className="mt-1 flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm">
          <span className="font-medium text-blue-900">{valore.nome}</span>
          <button type="button" onClick={() => onChange(null)} className="text-xs text-blue-700 hover:underline">
            Cambia
          </button>
        </div>
      </div>
    );
  }

  const visibili = risultati.filter((r) => !esclusi.includes(r.socio_id));
  return (
    <div className="relative">
      <label className="block text-xs font-medium text-gray-600">
        {etichetta}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Cerca per nome…"
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </label>
      {visibili.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg">
          {visibili.map((r) => (
            <li key={r.socio_id}>
              <button
                type="button"
                onClick={() => {
                  onChange(r);
                  setQ("");
                  setRisultati([]);
                }}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50"
              >
                <span>{r.nome}</span>
                {(r.rating_singolo ?? r.rating_doppio) !== null && (
                  <span className="text-xs text-gray-500">
                    {r.rating_singolo !== null && `S ${Math.round(r.rating_singolo)}`}
                    {r.rating_singolo !== null && r.rating_doppio !== null && " · "}
                    {r.rating_doppio !== null && `D ${Math.round(r.rating_doppio)}`}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
