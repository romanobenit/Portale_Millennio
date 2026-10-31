"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  ETICHETTA_PIAZZAMENTO,
  fetchConfigPickleball,
  salvaConfigPickleball,
  type ConfigPickleball,
  type Livello,
} from "@/lib/api/pickleball";

const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

function Numero({ label, aiuto, valore, onChange, step = 1, min, max }: {
  label: string; aiuto?: string; valore: number; onChange: (v: number) => void; step?: number; min: number; max: number;
}) {
  return (
    <label className="block text-xs font-medium text-gray-600">
      {label}
      <input type="number" value={valore} step={step} min={min} max={max}
        onChange={(e) => onChange(Number(e.target.value))} className={input} />
      {aiuto && <span className="mt-1 block font-normal text-gray-400">{aiuto}</span>}
    </label>
  );
}

export function ConfigPanel() {
  const [cfg, setCfg] = useState<ConfigPickleball | null>(null);
  const [invio, setInvio] = useState(false);

  useEffect(() => {
    fetchConfigPickleball().then(setCfg).catch(() => toast.error("Impostazioni non disponibili"));
  }, []);

  if (!cfg) return <p className="text-gray-500">Caricamento…</p>;

  const salva = async () => {
    setInvio(true);
    try {
      setCfg(await salvaConfigPickleball(cfg));
      toast.success("Impostazioni salvate: classifica ricalcolata");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Salvataggio non riuscito");
    } finally {
      setInvio(false);
    }
  };

  const punti = Object.keys(cfg.punti) as (keyof ConfigPickleball["punti"])[];
  const livelli: [Livello, string][] = [["sociale", "Sociale"], ["open", "Open"], ["federale", "Federale"]];

  return (
    <div className="space-y-6">
      <div className={card}>
        <h2 className="font-semibold text-gray-900">Punteggio Elo</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <Numero label="Peso delle partite di torneo" aiuto="1 = come un'amichevole; 1,5 = conta il 50% in più"
            valore={cfg.peso_torneo} step={0.1} min={1} max={3}
            onChange={(v) => setCfg({ ...cfg, peso_torneo: v })} />
          <Numero label="Amichevoli contate a settimana" aiuto="Contro lo stesso avversario; le altre non contano"
            valore={cfg.amichevoli_max_settimana} min={1} max={20}
            onChange={(v) => setCfg({ ...cfg, amichevoli_max_settimana: v })} />
          <Numero label="Giorni senza partite per uscire dalla classifica" aiuto="Il punteggio resta; si rientra giocando"
            valore={cfg.giorni_inattivita} min={14} max={730}
            onChange={(v) => setCfg({ ...cfg, giorni_inattivita: v })} />
        </div>
      </div>

      <div className={card}>
        <h2 className="font-semibold text-gray-900">Circuito tornei</h2>
        <p className="mt-1 text-xs text-gray-500">Punti = punti del piazzamento × moltiplicatore del livello del torneo.</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-5">
          {punti.map((k) => (
            <Numero key={k} label={ETICHETTA_PIAZZAMENTO[k]} valore={cfg.punti[k]} min={0} max={1000}
              onChange={(v) => setCfg({ ...cfg, punti: { ...cfg.punti, [k]: v } })} />
          ))}
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-4">
          {livelli.map(([k, label]) => (
            <Numero key={k} label={`Moltiplicatore ${label.toLowerCase()}`} valore={cfg.livelli[k]} step={0.1} min={0.1} max={5}
              onChange={(v) => setCfg({ ...cfg, livelli: { ...cfg.livelli, [k]: v } })} />
          ))}
          <Numero label="Risultati che contano per stagione" valore={cfg.migliori_risultati} min={1} max={30}
            onChange={(v) => setCfg({ ...cfg, migliori_risultati: v })} />
        </div>
      </div>

      <button type="button" onClick={salva} disabled={invio}
        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">
        {invio ? "Salvataggio…" : "Salva e ricalcola"}
      </button>
      <p className="text-xs text-gray-500">Solo la dirigenza può modificare queste impostazioni.</p>
    </div>
  );
}
