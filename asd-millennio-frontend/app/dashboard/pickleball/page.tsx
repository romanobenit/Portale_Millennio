"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { AndamentoRating } from "@/components/pickleball/AndamentoRating";
import { SceltaGiocatore } from "@/components/pickleball/SceltaGiocatore";
import { TabellaClassifica } from "@/components/pickleball/TabellaClassifica";
import { fetchMe } from "@/lib/api/soci";
import {
  aggiornaProfiloAtleta,
  cercaGiocatori,
  confermaPartita,
  contestaPartita,
  fetchClassifica,
  fetchMioPickleball,
  formattaData,
  formattaPunteggi,
  leggiPunteggi,
  registraPartita,
  ritiraPartita,
  type Formato,
  type GiocatoreRicerca,
  type MioPickleball,
  type Partita,
  type ProfiloAtleta,
  type RigaClassifica,
  type StatisticheFormato,
} from "@/lib/api/pickleball";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

const oggiIso = () => new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD nel fuso locale

function SchedaFormato({ titolo, s }: { titolo: string; s: StatisticheFormato }) {
  const verso = s.obiettivo && s.rating ? Math.min(100, Math.max(0, ((s.rating - 1200) / (s.obiettivo - 1200)) * 100)) : null;
  return (
    <div className={card}>
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold text-gray-900">{titolo}</h2>
        {s.posizione && <span className="text-sm text-gray-500">{s.posizione}° in classifica</span>}
      </div>
      {s.rating === null ? (
        <p className="mt-3 text-sm text-gray-500">
          Nessuna partita confermata. Si parte da <strong>1200</strong> punti.
        </p>
      ) : (
        <>
          <div className="mt-2 flex items-end gap-3">
            <span className="text-3xl font-bold tabular-nums text-gray-900">{Math.round(s.rating)}</span>
            {s.provvisorio && (
              <span className="mb-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                provvisorio ({s.partite}/10)
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {s.vittorie} vinte · {s.partite - s.vittorie} perse · massimo {Math.round(s.rating_max ?? 0)}
          </p>
        </>
      )}
      <div className="mt-3">
        <AndamentoRating punti={s.andamento} obiettivo={s.obiettivo} />
      </div>
      {verso !== null && (
        <div className="mt-2">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Verso l&apos;obiettivo {s.obiettivo}</span>
            <span>{Math.round(verso)}%</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-gray-100">
            <div className="h-1.5 rounded-full bg-blue-600" style={{ width: `${verso}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

function RigaPartita({ p, children }: { p: Partita; children?: React.ReactNode }) {
  const a = p.giocatori.filter((g) => g.squadra === "a");
  const b = p.giocatori.filter((g) => g.squadra === "b");
  const nomi = (lst: typeof a) => lst.map((g) => g.nome).join(" / ");
  return (
    <li className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm">
        <p>
          <span className={clsx(p.vincitore === "a" && "font-semibold")}>{nomi(a)}</span>
          <span className="mx-1.5 text-gray-400">vs</span>
          <span className={clsx(p.vincitore === "b" && "font-semibold")}>{nomi(b)}</span>
        </p>
        <p className="text-xs text-gray-500">
          {formattaData(p.data)} · {p.formato} · {formattaPunteggi(p)}
          {p.torneo && ` · ${p.torneo}`}
        </p>
        {p.note && <p className="text-xs text-orange-700">{p.note}</p>}
      </div>
      {children && <div className="flex shrink-0 gap-2">{children}</div>}
    </li>
  );
}

function VariazioneMia({ p, socioId }: { p: Partita; socioId: string }) {
  const g = p.giocatori.find((x) => x.socio_id === socioId);
  if (!g || g.rating_prima === null || g.rating_dopo === null) return null;
  const d = Math.round(g.rating_dopo - g.rating_prima);
  return (
    <span className={clsx("text-sm font-semibold tabular-nums", d >= 0 ? "text-green-700" : "text-red-700")}>
      {d >= 0 ? `+${d}` : d}
    </span>
  );
}

function FormPartita({ onFatto }: { onFatto: () => void }) {
  const [formato, setFormato] = useState<Formato>("doppio");
  const [data, setData] = useState(oggiIso());
  const [compagno, setCompagno] = useState<GiocatoreRicerca | null>(null);
  const [avv1, setAvv1] = useState<GiocatoreRicerca | null>(null);
  const [avv2, setAvv2] = useState<GiocatoreRicerca | null>(null);
  const [testo, setTesto] = useState("");
  const [invio, setInvio] = useState(false);

  const punteggi = leggiPunteggi(testo);
  const vinti = punteggi ? punteggi.filter(([a, b]) => a > b).length : 0;
  const persi = punteggi ? punteggi.length - vinti : 0;
  const scelti = [compagno, avv1, avv2].filter(Boolean).map((g) => g!.socio_id);
  const completo =
    punteggi && vinti !== persi && avv1 && (formato === "singolo" || (compagno && avv2));

  const invia = async () => {
    if (!completo) return;
    setInvio(true);
    try {
      await registraPartita({
        formato,
        data,
        compagno_id: formato === "doppio" ? compagno!.socio_id : null,
        avversari_ids: formato === "doppio" ? [avv1!.socio_id, avv2!.socio_id] : [avv1!.socio_id],
        punteggi: punteggi!,
      });
      toast.success("Partita registrata: conterà in classifica quando un avversario la conferma.");
      setCompagno(null);
      setAvv1(null);
      setAvv2(null);
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
      <h2 className="font-semibold text-gray-900">Registra una partita</h2>
      <p className="mt-1 text-xs text-gray-500">
        Conta in classifica solo dopo che un avversario l&apos;ha confermata.
      </p>
      <div className="mt-4 inline-flex rounded-lg border border-gray-300 p-0.5">
        {(["singolo", "doppio"] as Formato[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFormato(f)}
            className={clsx(
              "rounded-md px-4 py-1.5 text-sm font-medium capitalize",
              formato === f ? "bg-blue-700 text-white" : "text-gray-700",
            )}
          >
            {f}
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-xs font-medium text-gray-600">
          Data
          <input type="date" value={data} max={oggiIso()} onChange={(e) => setData(e.target.value)} className={input} />
        </label>
        {formato === "doppio" ? (
          <SceltaGiocatore etichetta="Il tuo compagno" valore={compagno} onChange={setCompagno}
            cerca={cercaGiocatori} esclusi={scelti} />
        ) : (
          <div className="hidden sm:block" />
        )}
        <SceltaGiocatore etichetta={formato === "doppio" ? "Avversario 1" : "Avversario"} valore={avv1}
          onChange={setAvv1} cerca={cercaGiocatori} esclusi={scelti} />
        {formato === "doppio" && (
          <SceltaGiocatore etichetta="Avversario 2" valore={avv2} onChange={setAvv2}
            cerca={cercaGiocatori} esclusi={scelti} />
        )}
      </div>
      <label className="mt-4 block text-xs font-medium text-gray-600">
        Punteggio dei game (prima il tuo)
        <input value={testo} onChange={(e) => setTesto(e.target.value)} placeholder="es. 11-7, 9-11, 11-8"
          className={input} />
      </label>
      {testo && (
        <p className={clsx("mt-1 text-xs", punteggi && vinti !== persi ? "text-gray-600" : "text-red-600")}>
          {!punteggi
            ? "Scrivi i game separati da virgola, es. 11-7, 9-11, 11-8"
            : vinti === persi
              ? "La partita non può finire in parità"
              : vinti > persi
                ? `Hai vinto ${vinti}-${persi}`
                : `Hai perso ${vinti}-${persi}`}
        </p>
      )}
      <button type="button" onClick={invia} disabled={!completo || invio} className={clsx(btnPrimario, "mt-4")}>
        {invio ? "Invio…" : "Registra partita"}
      </button>
    </div>
  );
}

function FormProfilo({ profilo, onSalvato }: { profilo: ProfiloAtleta; onSalvato: () => void }) {
  const [p, setP] = useState(profilo);
  const [salvo, setSalvo] = useState(false);
  useEffect(() => setP(profilo), [profilo]);

  const num = (v: string) => (v === "" ? null : Number(v));
  const salva = async () => {
    setSalvo(true);
    try {
      await aggiornaProfiloAtleta(p);
      toast.success("Profilo salvato");
      onSalvato();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Salvataggio non riuscito");
    } finally {
      setSalvo(false);
    }
  };

  return (
    <div className={card}>
      <h2 className="font-semibold text-gray-900">Obiettivi e profilo</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <label className="block text-xs font-medium text-gray-600">
          Obiettivo singolo (punti)
          <input type="number" min={800} max={2500} value={p.obiettivo_singolo ?? ""} className={input}
            onChange={(e) => setP({ ...p, obiettivo_singolo: num(e.target.value) })} placeholder="es. 1300" />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          Obiettivo doppio (punti)
          <input type="number" min={800} max={2500} value={p.obiettivo_doppio ?? ""} className={input}
            onChange={(e) => setP({ ...p, obiettivo_doppio: num(e.target.value) })} placeholder="es. 1300" />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          Partite al mese
          <input type="number" min={1} max={60} value={p.obiettivo_partite_mese ?? ""} className={input}
            onChange={(e) => setP({ ...p, obiettivo_partite_mese: num(e.target.value) })} placeholder="es. 8" />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          ID DUPR
          <input value={p.dupr_id ?? ""} maxLength={20} className={input}
            onChange={(e) => setP({ ...p, dupr_id: e.target.value || null })} />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          DUPR singolo
          <input type="number" step="0.001" min={1} max={8.5} value={p.dupr_singolo ?? ""} className={input}
            onChange={(e) => setP({ ...p, dupr_singolo: num(e.target.value) })} />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          DUPR doppio
          <input type="number" step="0.001" min={1} max={8.5} value={p.dupr_doppio ?? ""} className={input}
            onChange={(e) => setP({ ...p, dupr_doppio: num(e.target.value) })} />
        </label>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        Il DUPR è quello che leggi sulla tua app DUPR: qui lo mostriamo accanto al punteggio del club, non lo calcoliamo.
      </p>
      <label className="mt-4 flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" checked={p.visibile_in_classifica}
          onChange={(e) => setP({ ...p, visibile_in_classifica: e.target.checked })} />
        Mostra il mio nome nella classifica del club
      </label>
      <button type="button" onClick={salva} disabled={salvo} className={clsx(btnPrimario, "mt-4")}>
        {salvo ? "Salvataggio…" : "Salva"}
      </button>
    </div>
  );
}

export default function PickleballPage() {
  const [mio, setMio] = useState<MioPickleball | null>(null);
  const [socioId, setSocioId] = useState("");
  const [formatoClassifica, setFormatoClassifica] = useState<Formato>("doppio");
  const [classifica, setClassifica] = useState<RigaClassifica[]>([]);
  const [errore, setErrore] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      const [m, me] = await Promise.all([fetchMioPickleball(), fetchMe()]);
      setMio(m);
      setSocioId(me.id);
      setErrore(null);
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore di rete");
    }
  }, []);

  const caricaClassifica = useCallback(async () => {
    try {
      setClassifica(await fetchClassifica(formatoClassifica));
    } catch {
      setClassifica([]);
    }
  }, [formatoClassifica]);

  useEffect(() => {
    carica();
  }, [carica]);
  useEffect(() => {
    caricaClassifica();
  }, [caricaClassifica]);

  const esegui = async (chiave: string, azione: () => Promise<void>, ok: string) => {
    setBusy(chiave);
    try {
      await azione();
      toast.success(ok);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setBusy(null);
      await Promise.all([carica(), caricaClassifica()]);
    }
  };

  const contesta = (p: Partita) => {
    const motivo = window.prompt("Cosa non torna in questa partita?");
    if (!motivo || motivo.trim().length < 3) return;
    esegui(`c-${p.id}`, () => contestaPartita(p.id, motivo.trim()), "Segnalazione inviata alla dirigenza");
  };

  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!mio) return <p className="text-gray-500">Caricamento…</p>;

  const obiettivoMese = mio.profilo.obiettivo_partite_mese;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pickleball</h1>
        <p className="mt-1 text-sm text-gray-500">
          Il punteggio del club (Elo) parte da 1200 e cambia a ogni partita confermata: battere chi è più in alto
          vale di più. Singolo e doppio hanno classifiche separate.
        </p>
      </div>

      {mio.da_confermare.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 sm:p-5">
          <h2 className="font-semibold text-amber-900">Da confermare ({mio.da_confermare.length})</h2>
          <p className="text-xs text-amber-800">Un avversario ha registrato queste partite: confermale se sono corrette.</p>
          <ul className="mt-2 divide-y divide-amber-200">
            {mio.da_confermare.map((p) => (
              <RigaPartita key={p.id} p={p}>
                <button className={btnPrimario} disabled={busy !== null}
                  onClick={() => esegui(`ok-${p.id}`, () => confermaPartita(p.id), "Partita confermata")}>
                  Conferma
                </button>
                <button className={btnSecondario} disabled={busy !== null} onClick={() => contesta(p)}>
                  Non è corretta
                </button>
              </RigaPartita>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <SchedaFormato titolo="Singolo" s={mio.singolo} />
        <SchedaFormato titolo="Doppio" s={mio.doppio} />
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className={card}>
          <p className="text-xs text-gray-500">Partite questo mese</p>
          <p className="mt-1 text-xl font-bold tabular-nums">
            {mio.partite_questo_mese}
            {obiettivoMese && <span className="text-sm font-normal text-gray-500"> / {obiettivoMese}</span>}
          </p>
        </div>
        <div className={card}>
          <p className="text-xs text-gray-500">Vittorie di fila</p>
          <p className="mt-1 text-xl font-bold tabular-nums">{mio.serie_vittorie}</p>
        </div>
        <div className={card}>
          <p className="text-xs text-gray-500">Compagno più frequente</p>
          <p className="mt-1 truncate text-sm font-semibold">{mio.compagno_frequente ?? "—"}</p>
        </div>
        <div className={card}>
          <p className="text-xs text-gray-500">Avversario più frequente</p>
          <p className="mt-1 truncate text-sm font-semibold">{mio.avversario_frequente ?? "—"}</p>
        </div>
      </div>

      <FormPartita onFatto={carica} />

      {mio.in_attesa_altri.length > 0 && (
        <div className={card}>
          <h2 className="font-semibold text-gray-900">In attesa di conferma</h2>
          <ul className="mt-1 divide-y divide-gray-100">
            {mio.in_attesa_altri.map((p) => (
              <RigaPartita key={p.id} p={p}>
                {p.stato === "contestata" && (
                  <span className="self-center rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-800">
                    Contestata
                  </span>
                )}
                <button className={btnSecondario} disabled={busy !== null}
                  onClick={() => {
                    if (window.confirm("Ritirare questa partita?"))
                      esegui(`r-${p.id}`, () => ritiraPartita(p.id), "Partita ritirata");
                  }}>
                  Ritira
                </button>
              </RigaPartita>
            ))}
          </ul>
        </div>
      )}

      <div className={card}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-gray-900">Classifica del club</h2>
          <div className="inline-flex rounded-lg border border-gray-300 p-0.5">
            {(["doppio", "singolo"] as Formato[]).map((f) => (
              <button key={f} type="button" onClick={() => setFormatoClassifica(f)}
                className={clsx("rounded-md px-3 py-1 text-sm font-medium capitalize",
                  formatoClassifica === f ? "bg-blue-700 text-white" : "text-gray-700")}>
                {f}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-3">
          <TabellaClassifica righe={classifica} evidenzia={socioId} />
        </div>
      </div>

      {mio.recenti.length > 0 && (
        <div className={card}>
          <h2 className="font-semibold text-gray-900">Le mie ultime partite</h2>
          <ul className="mt-1 divide-y divide-gray-100">
            {mio.recenti.map((p) => (
              <RigaPartita key={p.id} p={p}>
                <VariazioneMia p={p} socioId={socioId} />
              </RigaPartita>
            ))}
          </ul>
        </div>
      )}

      <FormProfilo profilo={mio.profilo} onSalvato={() => Promise.all([carica(), caricaClassifica()])} />
    </div>
  );
}
