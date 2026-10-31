"use client";

import { Fragment, useEffect, useState } from "react";
import { clsx } from "clsx";
import { TabellaClassifica } from "@/components/pickleball/TabellaClassifica";
import {
  ETICHETTA_PIAZZAMENTO,
  fetchCircuito,
  fetchCircuitoCompleto,
  fetchClassifica,
  fetchClassificaCompleta,
  formattaData,
  type Circuito,
  type FiltriClassifica,
  type Formato,
  type RigaClassifica,
} from "@/lib/api/pickleball";

type Vista = Formato | "circuito";

const select = "rounded-lg border border-gray-300 px-2 py-1.5 text-sm";

function Schede({ vista, onChange }: { vista: Vista; onChange: (v: Vista) => void }) {
  const voci: [Vista, string][] = [["doppio", "Doppio"], ["singolo", "Singolo"], ["circuito", "Circuito tornei"]];
  return (
    <div className="inline-flex rounded-lg border border-gray-300 p-0.5">
      {voci.map(([v, label]) => (
        <button key={v} type="button" onClick={() => onChange(v)}
          className={clsx("rounded-md px-3 py-1 text-sm font-medium",
            vista === v ? "bg-blue-700 text-white" : "text-gray-700")}>
          {label}
        </button>
      ))}
    </div>
  );
}

function TabellaCircuito({ circuito, evidenzia }: { circuito: Circuito; evidenzia?: string }) {
  const [aperto, setAperto] = useState<string | null>(null);
  if (circuito.righe.length === 0) {
    return <p className="py-6 text-center text-sm text-gray-500">Nessun torneo concluso in questa categoria.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="py-2 pr-2">#</th>
            <th className="py-2 pr-2">Giocatore</th>
            <th className="py-2 pr-2 text-right">Punti</th>
            <th className="py-2 text-right">Tornei</th>
          </tr>
        </thead>
        <tbody>
          {circuito.righe.map((r) => (
            <Fragment key={r.giocatore_id}>
              <tr
                onClick={() => setAperto(aperto === r.giocatore_id ? null : r.giocatore_id)}
                className={clsx("cursor-pointer border-b border-gray-100 hover:bg-gray-50",
                  r.giocatore_id === evidenzia && "bg-blue-50 font-semibold")}
              >
                <td className="py-2 pr-2 text-gray-500">{r.posizione}</td>
                <td className="py-2 pr-2">{r.nome}</td>
                <td className="py-2 pr-2 text-right tabular-nums">{r.punti}</td>
                <td className="py-2 text-right tabular-nums text-gray-500">{r.tornei}</td>
              </tr>
              {aperto === r.giocatore_id && (
                <tr className="border-b border-gray-100 bg-gray-50">
                  <td />
                  <td colSpan={3} className="py-2 pr-2">
                    <ul className="space-y-1 text-xs text-gray-600">
                      {r.risultati.map((x) => (
                        <li key={x.torneo_id} className={clsx("flex justify-between gap-2", !x.conta && "text-gray-400 line-through")}>
                          <span>{formattaData(x.data)} · {x.torneo} · {ETICHETTA_PIAZZAMENTO[x.piazzamento]}</span>
                          <span className="tabular-nums">{x.punti}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">
        Contano i migliori {circuito.migliori_risultati} risultati della stagione. Tocca un giocatore per i dettagli.
      </p>
    </div>
  );
}

/** Classifiche del club: Elo (doppio/singolo, filtri per sesso ed età) e circuito tornei per categoria. */
export function ClassificheClub({ completa = false, evidenzia }: { completa?: boolean; evidenzia?: string }) {
  const [vista, setVista] = useState<Vista>("doppio");
  const [filtri, setFiltri] = useState<FiltriClassifica>({});
  const [righe, setRighe] = useState<RigaClassifica[]>([]);
  const [anno, setAnno] = useState<string | undefined>();
  const [categoria, setCategoria] = useState<string | undefined>();
  const [circuito, setCircuito] = useState<Circuito | null>(null);

  useEffect(() => {
    if (vista === "circuito") {
      (completa ? fetchCircuitoCompleto : fetchCircuito)(anno, categoria).then(setCircuito).catch(() => setCircuito(null));
    } else {
      (completa ? fetchClassificaCompleta : fetchClassifica)(vista, filtri).then(setRighe).catch(() => setRighe([]));
    }
  }, [vista, filtri, anno, categoria, completa]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <Schede vista={vista} onChange={setVista} />
        {vista !== "circuito" ? (
          <>
            <select className={select} value={filtri.sesso ?? ""} aria-label="Sesso"
              onChange={(e) => setFiltri({ ...filtri, sesso: (e.target.value || undefined) as FiltriClassifica["sesso"] })}>
              <option value="">Tutti</option>
              <option value="M">Uomini</option>
              <option value="F">Donne</option>
            </select>
            <select className={select} value={filtri.eta_min ?? ""} aria-label="Fascia d'età"
              onChange={(e) => setFiltri({ ...filtri, eta_min: e.target.value ? Number(e.target.value) : undefined })}>
              <option value="">Tutte le età</option>
              <option value="40">Over 40</option>
              <option value="50">Over 50</option>
              <option value="60">Over 60</option>
            </select>
          </>
        ) : circuito && (circuito.anni.length > 0) && (
          <>
            <select className={select} value={circuito.anno_sportivo ?? ""} aria-label="Stagione"
              onChange={(e) => { setAnno(e.target.value); setCategoria(undefined); }}>
              {circuito.anni.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <select className={select} value={circuito.categoria ?? ""} aria-label="Categoria"
              onChange={(e) => setCategoria(e.target.value)}>
              {circuito.categorie.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </>
        )}
      </div>
      <div className="mt-3">
        {vista === "circuito" ? (
          circuito ? <TabellaCircuito circuito={circuito} evidenzia={evidenzia} />
            : <p className="py-6 text-center text-sm text-gray-500">Caricamento…</p>
        ) : (
          <TabellaClassifica righe={righe} evidenzia={evidenzia} />
        )}
      </div>
    </div>
  );
}
