"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { SceltaGiocatore } from "@/components/pickleball/SceltaGiocatore";
import { ClassificheClub } from "@/components/pickleball/ClassificheClub";
import { ConfigPanel } from "@/components/pickleball/dirigenza/ConfigPanel";
import { OspitiPanel } from "@/components/pickleball/dirigenza/OspitiPanel";
import { TorneiPanel } from "@/components/pickleball/dirigenza/TorneiPanel";
import {
  cercaGiocatoriDirigenza,
  fetchDashboardPickleball,
  fetchPartiteDirigenza,
  formattaData,
  formattaPunteggi,
  leggiPunteggi,
  nomiSquadra,
  registraPartitaDirigenza,
  risolviPartita,
  type DashboardPickleball,
  type Formato,
  type GiocatoreRicerca,
  type Partita,
  type StatoPartita,
} from "@/lib/api/pickleball";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

const ETICHETTA_STATO: Record<StatoPartita, { label: string; classes: string }> = {
  in_attesa_conferma: { label: "In attesa", classes: "bg-yellow-100 text-yellow-800" },
  confermata: { label: "Confermata", classes: "bg-green-100 text-green-800" },
  contestata: { label: "Contestata", classes: "bg-orange-100 text-orange-800" },
  annullata: { label: "Annullata", classes: "bg-gray-100 text-gray-600" },
};

const oggiIso = () => new Date().toLocaleDateString("sv-SE");

function Toggle<T extends string>({ valori, valore, onChange }: { valori: T[]; valore: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-gray-300 p-0.5">
      {valori.map((v) => (
        <button key={v} type="button" onClick={() => onChange(v)}
          className={clsx("rounded-md px-3 py-1 text-sm font-medium capitalize",
            valore === v ? "bg-blue-700 text-white" : "text-gray-700")}>
          {v}
        </button>
      ))}
    </div>
  );
}

function FormRisultato({ onFatto }: { onFatto: () => void }) {
  const [formato, setFormato] = useState<Formato>("doppio");
  const [data, setData] = useState(oggiIso());
  const [torneo, setTorneo] = useState("");
  const [g, setG] = useState<(GiocatoreRicerca | null)[]>([null, null, null, null]);
  const [testo, setTesto] = useState("");
  const [invio, setInvio] = useState(false);

  const n = formato === "doppio" ? 2 : 1;
  const a = g.slice(0, n);
  const b = g.slice(2, 2 + n);
  const punteggi = leggiPunteggi(testo);
  const vintiA = punteggi ? punteggi.filter(([x, y]) => x > y).length : 0;
  const vintiB = punteggi ? punteggi.length - vintiA : 0;
  const scelti = g.filter(Boolean).map((x) => x!.socio_id);
  const completo = punteggi && vintiA !== vintiB && [...a, ...b].every(Boolean);

  const imposta = (i: number) => (v: GiocatoreRicerca | null) => setG((old) => old.map((x, j) => (j === i ? v : x)));

  const invia = async () => {
    if (!completo) return;
    setInvio(true);
    try {
      await registraPartitaDirigenza({
        formato,
        data,
        squadra_a: a.map((x) => x!.socio_id),
        squadra_b: b.map((x) => x!.socio_id),
        punteggi: punteggi!,
        torneo: torneo.trim() || null,
      });
      toast.success("Risultato registrato e conteggiato in classifica");
      setG([null, null, null, null]);
      setTesto("");
      onFatto();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Registrazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  return (
    <div className={card}>
      <h2 className="font-semibold text-gray-900">Registra un risultato</h2>
      <p className="mt-1 text-xs text-gray-500">
        Per tornei e partite ufficiali: il risultato conta subito, senza conferma dei giocatori.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-4">
        <Toggle valori={["singolo", "doppio"] as Formato[]} valore={formato} onChange={setFormato} />
        <label className="block text-xs font-medium text-gray-600">
          Data
          <input type="date" value={data} max={oggiIso()} onChange={(e) => setData(e.target.value)} className={input} />
        </label>
        <label className="block min-w-[12rem] flex-1 text-xs font-medium text-gray-600">
          Torneo (facoltativo)
          <input value={torneo} maxLength={120} onChange={(e) => setTorneo(e.target.value)} className={input}
            placeholder="es. Torneo d'autunno" />
        </label>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-3 rounded-lg bg-gray-50 p-3">
          <p className="text-xs font-semibold uppercase text-gray-500">Squadra A</p>
          {Array.from({ length: n }, (_, i) => (
            <SceltaGiocatore key={`a${i}`} etichetta={`Giocatore ${i + 1}`} valore={g[i]} onChange={imposta(i)}
              cerca={cercaGiocatoriDirigenza} esclusi={scelti} />
          ))}
        </div>
        <div className="space-y-3 rounded-lg bg-gray-50 p-3">
          <p className="text-xs font-semibold uppercase text-gray-500">Squadra B</p>
          {Array.from({ length: n }, (_, i) => (
            <SceltaGiocatore key={`b${i}`} etichetta={`Giocatore ${i + 1}`} valore={g[2 + i]} onChange={imposta(2 + i)}
              cerca={cercaGiocatoriDirigenza} esclusi={scelti} />
          ))}
        </div>
      </div>
      <label className="mt-4 block text-xs font-medium text-gray-600">
        Punteggio dei game (prima la squadra A)
        <input value={testo} onChange={(e) => setTesto(e.target.value)} placeholder="es. 11-7, 9-11, 11-8"
          className={input} />
      </label>
      {testo && (
        <p className={clsx("mt-1 text-xs", punteggi && vintiA !== vintiB ? "text-gray-600" : "text-red-600")}>
          {!punteggi
            ? "Scrivi i game separati da virgola, es. 11-7, 9-11, 11-8"
            : vintiA === vintiB
              ? "La partita non può finire in parità"
              : `Vince la squadra ${vintiA > vintiB ? "A" : "B"} (${Math.max(vintiA, vintiB)}-${Math.min(vintiA, vintiB)})`}
        </p>
      )}
      <button type="button" onClick={invia} disabled={!completo || invio} className={clsx(btnPrimario, "mt-4")}>
        {invio ? "Invio…" : "Registra risultato"}
      </button>
    </div>
  );
}

function Panoramica() {
  const [dash, setDash] = useState<DashboardPickleball | null>(null);
  const [daRisolvere, setDaRisolvere] = useState<Partita[]>([]);
  const [versione, setVersione] = useState(0); // ricarica le classifiche dopo un'azione
  const [filtroStato, setFiltroStato] = useState<StatoPartita | "tutte">("confermata");
  const [storico, setStorico] = useState<Partita[]>([]);
  const [errore, setErrore] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      const [d, contestate, attesa] = await Promise.all([
        fetchDashboardPickleball(),
        fetchPartiteDirigenza("contestata"),
        fetchPartiteDirigenza("in_attesa_conferma"),
      ]);
      setDash(d);
      setDaRisolvere([...contestate, ...attesa]);
      setErrore(null);
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore di rete");
    }
  }, []);

  const caricaClassifica = useCallback(async () => setVersione((v) => v + 1), []);

  const caricaStorico = useCallback(async () => {
    setStorico(await fetchPartiteDirigenza(filtroStato === "tutte" ? undefined : filtroStato).catch(() => []));
  }, [filtroStato]);

  useEffect(() => {
    carica();
  }, [carica]);
  useEffect(() => {
    caricaStorico();
  }, [caricaStorico]);

  const ricarica = () => Promise.all([carica(), caricaClassifica(), caricaStorico()]);

  const risolvi = (p: Partita, esito: "conferma" | "annulla") => {
    if (esito === "annulla" && p.stato === "confermata" &&
      !window.confirm("Annullare una partita confermata? La classifica verrà ricalcolata.")) return;
    setBusy(p.id);
    risolviPartita(p.id, esito)
      .then(() => toast.success(esito === "conferma" ? "Partita confermata" : "Partita annullata"))
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Operazione non riuscita"))
      .finally(() => {
        setBusy(null);
        ricarica();
      });
  };

  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!dash) return <p className="text-gray-500">Caricamento…</p>;

  const maxSett = Math.max(1, ...dash.per_settimana.map((s) => s.partite));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["Giocatori attivi (30 gg)", dash.giocatori_attivi_30gg],
          ["Partite (30 gg)", dash.partite_30gg],
          ["Partite totali", dash.partite_totali],
          ["Da verificare", dash.da_risolvere + dash.in_attesa_conferma],
        ].map(([label, valore]) => (
          <div key={label as string} className={card}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{valore}</p>
          </div>
        ))}
      </div>

      <div className={card}>
        <h2 className="font-semibold text-gray-900">Partite confermate per settimana</h2>
        <div className="mt-4 flex h-32 items-end gap-2">
          {dash.per_settimana.map((s) => (
            <div key={s.settimana} className="flex flex-1 flex-col items-center gap-1">
              <span className="text-xs tabular-nums text-gray-600">{s.partite || ""}</span>
              <div className="w-full rounded-t bg-blue-600" style={{ height: `${(s.partite / maxSett) * 88}px` }} />
              <span className="text-[10px] text-gray-500">
                {new Date(`${s.settimana}T00:00:00`).toLocaleDateString("it-IT", { day: "numeric", month: "short" })}
              </span>
            </div>
          ))}
        </div>
      </div>

      {daRisolvere.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 sm:p-5">
          <h2 className="font-semibold text-amber-900">Da verificare ({daRisolvere.length})</h2>
          <p className="text-xs text-amber-800">
            Le contestate aspettano una tua decisione; quelle in attesa puoi confermarle se l&apos;avversario non lo fa.
          </p>
          <ul className="mt-2 divide-y divide-amber-200">
            {daRisolvere.map((p) => (
              <li key={p.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm">
                  <p>
                    <span className={clsx(p.vincitore === "a" && "font-semibold")}>{nomiSquadra(p, "a") || "—"}</span>
                    <span className="mx-1.5 text-gray-400">vs</span>
                    <span className={clsx(p.vincitore === "b" && "font-semibold")}>{nomiSquadra(p, "b") || "—"}</span>
                    <span className={clsx("ml-2 rounded px-1.5 py-0.5 text-xs", ETICHETTA_STATO[p.stato].classes)}>
                      {ETICHETTA_STATO[p.stato].label}
                    </span>
                  </p>
                  <p className="text-xs text-gray-600">
                    {formattaData(p.data)} · {p.formato} · {formattaPunteggi(p)}
                  </p>
                  {p.note && <p className="text-xs text-orange-800">{p.note}</p>}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button className={btnSecondario} disabled={busy !== null} onClick={() => risolvi(p, "conferma")}>
                    Conferma
                  </button>
                  <button className={btnSecondario} disabled={busy !== null} onClick={() => risolvi(p, "annulla")}>
                    Annulla
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <FormRisultato onFatto={ricarica} />

      <div className={card}>
        <h2 className="mb-3 font-semibold text-gray-900">Classifiche complete</h2>
        <ClassificheClub key={versione} completa />
      </div>

      <div className={card}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-gray-900">Storico partite</h2>
          <select value={filtroStato} onChange={(e) => setFiltroStato(e.target.value as StatoPartita | "tutte")}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
            <option value="confermata">Confermate</option>
            <option value="annullata">Annullate</option>
            <option value="tutte">Tutte</option>
          </select>
        </div>
        {storico.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-500">Nessuna partita.</p>
        ) : (
          <ul className="mt-2 divide-y divide-gray-100">
            {storico.map((p) => (
              <li key={p.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm">
                  <p>
                    <span className={clsx(p.vincitore === "a" && "font-semibold")}>{nomiSquadra(p, "a") || "—"}</span>
                    <span className="mx-1.5 text-gray-400">vs</span>
                    <span className={clsx(p.vincitore === "b" && "font-semibold")}>{nomiSquadra(p, "b") || "—"}</span>
                    <span className={clsx("ml-2 rounded px-1.5 py-0.5 text-xs", ETICHETTA_STATO[p.stato].classes)}>
                      {ETICHETTA_STATO[p.stato].label}
                    </span>
                  </p>
                  <p className="text-xs text-gray-500">
                    {formattaData(p.data)} · {p.formato} · {formattaPunteggi(p)}
                    {p.torneo && ` · ${p.torneo}`}
                    {p.inserita_da_dirigenza && " · inserita dalla dirigenza"}
                  </p>
                </div>
                {p.stato !== "annullata" && (
                  <button className={btnSecondario} disabled={busy !== null} onClick={() => risolvi(p, "annulla")}>
                    Annulla
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

type Scheda = "panoramica" | "tornei" | "ospiti" | "impostazioni";
const SCHEDE: [Scheda, string][] = [
  ["panoramica", "Panoramica"],
  ["tornei", "Tornei"],
  ["ospiti", "Ospiti"],
  ["impostazioni", "Impostazioni"],
];

export default function DirigenzaPickleballPage() {
  const [scheda, setScheda] = useState<Scheda>("panoramica");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pickleball</h1>
        <p className="mt-1 text-sm text-gray-500">
          Risultati, tornei, classifiche Elo e circuito. Qui i nomi sono completi e compaiono anche i minori, gli
          ospiti e chi ha scelto di non comparire nelle classifiche dei soci.
        </p>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-b border-gray-200" aria-label="Sezioni pickleball">
        {SCHEDE.map(([k, label]) => (
          <button key={k} type="button" onClick={() => setScheda(k)}
            className={clsx("whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium",
              scheda === k ? "border-blue-700 text-blue-800" : "border-transparent text-gray-500 hover:text-gray-800")}>
            {label}
          </button>
        ))}
      </nav>
      {scheda === "panoramica" && <Panoramica />}
      {scheda === "tornei" && <TorneiPanel />}
      {scheda === "ospiti" && <OspitiPanel />}
      {scheda === "impostazioni" && <ConfigPanel />}
    </div>
  );
}
