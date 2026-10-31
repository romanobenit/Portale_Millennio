"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import {
  aggiornaTorneo,
  creaTorneo,
  eliminaTorneo,
  ETICHETTA_FASE,
  ETICHETTA_PIAZZAMENTO,
  fetchTornei,
  fetchTorneo,
  formattaData,
  formattaPunteggi,
  importaRisultati,
  impostaPiazzamento,
  nomiSquadra,
  ricalcolaPiazzamenti,
  risolviPartita,
  type ImportRisultati,
  type Livello,
  type Piazzamento,
  type Torneo,
  type TorneoDettaglio,
} from "@/lib/api/pickleball";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";
const card = "rounded-xl border border-gray-200 bg-white p-4 sm:p-5";
const input = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";

const LIVELLI: { valore: Livello; label: string }[] = [
  { valore: "sociale", label: "Sociale" },
  { valore: "open", label: "Open" },
  { valore: "federale", label: "Federale" },
];
const PIAZZAMENTI = Object.keys(ETICHETTA_PIAZZAMENTO) as Piazzamento[];

const MODELLO_CSV =
  "categoria;fase;squadra_a;squadra_b;punteggio;vincitore\n" +
  "SMO40;girone;Mario Rossi;Luca Bianchi;8-11;\n" +
  "SMO40;finale;Mario Rossi;Paolo Verdi;15-3;\n" +
  "DMO40;girone;Mario Rossi / Luca Bianchi;Paolo Verdi / Gino Neri;11-9, 7-11, 11-6;\n" +
  "DMO40;girone;Mario Rossi / Luca Bianchi;Anna Blu / Sara Viola;WO;A\n";

const oggiIso = () => new Date().toLocaleDateString("sv-SE");

function errore(e: unknown, fallback: string) {
  toast.error(e instanceof Error ? e.message : fallback);
}

function NuovoTorneo({ onCreato }: { onCreato: (t: Torneo) => void }) {
  const [nome, setNome] = useState("");
  const [data, setData] = useState(oggiIso());
  const [luogo, setLuogo] = useState("");
  const [livello, setLivello] = useState<Livello>("sociale");
  const [url, setUrl] = useState("");
  const [invio, setInvio] = useState(false);

  const crea = async () => {
    setInvio(true);
    try {
      const t = await creaTorneo({ nome: nome.trim(), data, luogo: luogo.trim() || null, livello, url_esterno: url.trim() || null });
      toast.success("Torneo creato: ora importa i risultati");
      setNome("");
      setLuogo("");
      setUrl("");
      onCreato(t);
    } catch (e) {
      errore(e, "Creazione non riuscita");
    } finally {
      setInvio(false);
    }
  };

  return (
    <div className={card}>
      <h2 className="font-semibold text-gray-900">Nuovo torneo</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block text-xs font-medium text-gray-600 sm:col-span-2">
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} maxLength={120} className={input}
            placeholder="es. Pickleball Cercola 18-10-2026" />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          Data
          <input type="date" value={data} onChange={(e) => setData(e.target.value)} className={input} />
        </label>
        <label className="block text-xs font-medium text-gray-600">
          Livello
          <select value={livello} onChange={(e) => setLivello(e.target.value as Livello)} className={input}>
            {LIVELLI.map((l) => <option key={l.valore} value={l.valore}>{l.label}</option>)}
          </select>
        </label>
        <label className="block text-xs font-medium text-gray-600 sm:col-span-2">
          Luogo (facoltativo)
          <input value={luogo} onChange={(e) => setLuogo(e.target.value)} maxLength={120} className={input} />
        </label>
        <label className="block text-xs font-medium text-gray-600 sm:col-span-2">
          Pagina dei risultati (facoltativa)
          <input value={url} onChange={(e) => setUrl(e.target.value)} maxLength={500} className={input}
            placeholder="https://www.tournamentsoftware.com/…" />
        </label>
      </div>
      <button type="button" onClick={crea} disabled={invio || nome.trim().length < 3} className={clsx(btnPrimario, "mt-4")}>
        {invio ? "Creazione…" : "Crea torneo"}
      </button>
    </div>
  );
}

function Importazione({ torneoId, onImportato }: { torneoId: string; onImportato: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [anteprima, setAnteprima] = useState<ImportRisultati | null>(null);
  const [invio, setInvio] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const scaricaModello = () => {
    const url = URL.createObjectURL(new Blob([MODELLO_CSV], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "modello-risultati-torneo.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const esegui = async (conferma: boolean) => {
    if (!file) return;
    setInvio(true);
    try {
      const r = await importaRisultati(torneoId, file, conferma);
      if (conferma) {
        toast.success(`Importate ${r.importate} partite`);
        setAnteprima(null);
        setFile(null);
        if (inputRef.current) inputRef.current.value = "";
        onImportato();
      } else {
        setAnteprima(r);
      }
    } catch (e) {
      errore(e, "Lettura del file non riuscita");
    } finally {
      setInvio(false);
    }
  };

  const coloreEsito = { ok: "text-green-700", errore: "text-red-700", saltata: "text-gray-400", gia_importata: "text-gray-400" };
  const tipoGiocatore = { socio: "", ospite: " (ospite)", nuovo_ospite: " (nuovo ospite)" };

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500">
        Un file CSV con una riga per partita: categoria, fase (girone, quarti, semifinale, finale), squadra A, squadra B
        (coppie separate da «/»), punteggio dal punto di vista della squadra A («11-8» o «11-8, 9-11, 11-6»), e il
        vincitore (A o B) solo per i walkover («WO»). Le partite annullate si possono lasciare: vengono saltate. Chi non
        è socio diventa un <strong>ospite</strong>.{" "}
        <button type="button" onClick={scaricaModello} className="font-medium text-blue-700 hover:underline">
          Scarica il modello
        </button>
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input ref={inputRef} type="file" accept=".csv,text/csv"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setAnteprima(null); }}
          className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:py-1.5 file:text-sm file:font-semibold" />
        <button type="button" onClick={() => esegui(false)} disabled={!file || invio} className={btnSecondario}>
          {invio && !anteprima ? "Lettura…" : "Anteprima"}
        </button>
      </div>
      {anteprima && (
        <div className="space-y-3">
          <p className="text-sm">
            <strong>{anteprima.da_importare}</strong> partite da importare
            {anteprima.saltate > 0 && ` · ${anteprima.saltate} non giocate`}
            {anteprima.gia_importate > 0 && ` · ${anteprima.gia_importate} già presenti`}
            {anteprima.errori > 0 && <span className="text-red-700"> · {anteprima.errori} con errori (saranno saltate)</span>}
          </p>
          {anteprima.nuovi_ospiti.length > 0 && (
            <p className="text-xs text-gray-600">
              Nuovi ospiti ({anteprima.nuovi_ospiti.length}): {anteprima.nuovi_ospiti.join(", ")}. Se qualcuno è già
              socio con un nome scritto diversamente, correggi il file o collegalo dopo dalla scheda Ospiti.
            </p>
          )}
          <div className="max-h-80 overflow-auto rounded-lg border border-gray-200">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50 text-left text-gray-500">
                <tr>
                  <th className="px-2 py-1.5">Riga</th>
                  <th className="px-2 py-1.5">Categoria</th>
                  <th className="px-2 py-1.5">Partita</th>
                  <th className="px-2 py-1.5">Punteggio</th>
                  <th className="px-2 py-1.5">Esito</th>
                </tr>
              </thead>
              <tbody>
                {anteprima.righe.map((r) => (
                  <tr key={r.riga} className="border-t border-gray-100">
                    <td className="px-2 py-1.5 text-gray-400">{r.riga}</td>
                    <td className="px-2 py-1.5">{r.categoria} {ETICHETTA_FASE[r.fase] ?? r.fase}</td>
                    <td className="px-2 py-1.5">
                      {r.squadra_a.map((g) => g.nome + tipoGiocatore[g.tipo]).join(" / ") || "—"}
                      <span className="text-gray-400"> vs </span>
                      {r.squadra_b.map((g) => g.nome + tipoGiocatore[g.tipo]).join(" / ") || "—"}
                    </td>
                    <td className="px-2 py-1.5 tabular-nums">{r.punteggio}{r.walkover && r.vincitore && ` (vince ${r.vincitore})`}</td>
                    <td className={clsx("px-2 py-1.5", coloreEsito[r.esito])}>{r.messaggio ?? "ok"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" onClick={() => esegui(true)} disabled={invio || anteprima.da_importare === 0} className={btnPrimario}>
            {invio ? "Importazione…" : `Importa ${anteprima.da_importare} partite`}
          </button>
        </div>
      )}
    </div>
  );
}

function DettaglioTorneo({ torneoId, onCambiato }: { torneoId: string; onCambiato: () => void }) {
  const [det, setDet] = useState<TorneoDettaglio | null>(null);
  const [busy, setBusy] = useState(false);

  const carica = useCallback(async () => {
    try {
      setDet(await fetchTorneo(torneoId));
    } catch (e) {
      errore(e, "Errore di rete");
    }
  }, [torneoId]);

  useEffect(() => {
    carica();
  }, [carica]);

  const azione = async (fn: () => Promise<unknown>, ok: string, ricarica = true) => {
    setBusy(true);
    try {
      await fn();
      toast.success(ok);
      if (ricarica) await carica();
      onCambiato();
    } catch (e) {
      errore(e, "Operazione non riuscita");
    } finally {
      setBusy(false);
    }
  };

  if (!det) return <p className="text-sm text-gray-500">Caricamento…</p>;
  const t = det.torneo;
  const categorie = Array.from(new Set([...t.categorie, ...det.piazzamenti.map((p) => p.categoria)])).sort();

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{t.nome}</h2>
          <p className="text-sm text-gray-500">
            {formattaData(t.data)}{t.luogo && ` · ${t.luogo}`} · stagione {t.anno_sportivo} · {t.partite} partite
            {t.url_esterno && (
              <> · <a href={t.url_esterno} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">risultati originali</a></>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={t.livello} disabled={busy} aria-label="Livello del torneo"
            onChange={(e) => azione(() => aggiornaTorneo(t.id, { livello: e.target.value as Livello }), "Livello aggiornato")}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm">
            {LIVELLI.map((l) => <option key={l.valore} value={l.valore}>{l.label}</option>)}
          </select>
          <button type="button" disabled={busy} className={t.concluso ? btnSecondario : btnPrimario}
            onClick={() => azione(() => aggiornaTorneo(t.id, { concluso: !t.concluso }),
              t.concluso ? "Torneo riaperto: esce dal circuito" : "Torneo concluso: i punti entrano nel circuito")}>
            {t.concluso ? "Riapri" : "Concludi torneo"}
          </button>
          <button type="button" disabled={busy} className="text-sm font-medium text-red-600 hover:text-red-800"
            onClick={() => {
              if (window.confirm(`Eliminare «${t.nome}» con tutte le sue partite? La classifica verrà ricalcolata.`))
                azione(() => eliminaTorneo(t.id), "Torneo eliminato", false);
            }}>
            Elimina
          </button>
        </div>
      </div>
      {!t.concluso && (
        <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
          Le partite contano già per l&apos;Elo; i punti del circuito arrivano quando segni il torneo come concluso.
        </p>
      )}

      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Importa risultati</h3>
        <Importazione torneoId={t.id} onImportato={() => { carica(); onCambiato(); }} />
      </section>

      {det.piazzamenti.length > 0 && (
        <section>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-700">Piazzamenti e punti del circuito</h3>
            <button type="button" disabled={busy} className={btnSecondario}
              onClick={() => azione(() => ricalcolaPiazzamenti(t.id), "Piazzamenti ricalcolati")}>
              Ricalcola dai risultati
            </button>
          </div>
          <p className="mb-2 text-xs text-gray-500">
            Ricavati dalle partite: chi ha solo dato forfait non prende punti. Se correggi un piazzamento, la correzione
            resta anche ai ricalcoli successivi.
          </p>
          <div className="grid gap-3 lg:grid-cols-2">
            {categorie.map((cat) => (
              <div key={cat} className="rounded-lg border border-gray-200 p-3">
                <p className="mb-2 text-sm font-semibold">{cat}</p>
                <ul className="space-y-1.5">
                  {det.piazzamenti.filter((p) => p.categoria === cat).map((p) => (
                    <li key={p.giocatore_id} className="flex items-center justify-between gap-2 text-sm">
                      <span className="min-w-0 truncate">{p.nome}</span>
                      <span className="flex shrink-0 items-center gap-2">
                        <select value={p.piazzamento} disabled={busy} aria-label={`Piazzamento di ${p.nome}`}
                          onChange={(e) => azione(() => impostaPiazzamento(t.id, {
                            categoria: cat, giocatore_id: p.giocatore_id, piazzamento: e.target.value as Piazzamento,
                          }), "Piazzamento corretto")}
                          className={clsx("rounded border px-1.5 py-1 text-xs", p.manuale ? "border-blue-300 bg-blue-50" : "border-gray-300")}>
                          {PIAZZAMENTI.map((x) => <option key={x} value={x}>{ETICHETTA_PIAZZAMENTO[x]}</option>)}
                        </select>
                        <span className="w-10 text-right text-xs tabular-nums text-gray-600">{p.punti}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {det.partite.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">Partite</h3>
          <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {det.partite.map((p) => (
              <li key={p.id} className={clsx("flex flex-col gap-1 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between",
                p.stato === "annullata" && "opacity-50")}>
                <div className="min-w-0">
                  <span className="mr-2 text-xs font-semibold text-gray-500">{p.categoria} {p.fase && ETICHETTA_FASE[p.fase]}</span>
                  <span className={clsx(p.vincitore === "a" && "font-semibold")}>{nomiSquadra(p, "a") || "—"}</span>
                  <span className="mx-1.5 text-gray-400">vs</span>
                  <span className={clsx(p.vincitore === "b" && "font-semibold")}>{nomiSquadra(p, "b") || "—"}</span>
                  <span className="ml-2 text-xs text-gray-500">{formattaPunteggi(p)}</span>
                </div>
                {p.stato !== "annullata" && (
                  <button type="button" disabled={busy} className="self-start text-xs font-medium text-red-600 hover:text-red-800 sm:self-auto"
                    onClick={() => {
                      if (window.confirm("Annullare questa partita? Classifica e piazzamenti verranno ricalcolati."))
                        azione(() => risolviPartita(p.id, "annulla"), "Partita annullata");
                    }}>
                    Annulla
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export function TorneiPanel() {
  const [tornei, setTornei] = useState<Torneo[] | null>(null);
  const [selezionato, setSelezionato] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      setTornei(await fetchTornei());
    } catch (e) {
      errore(e, "Errore di rete");
    }
  }, []);

  useEffect(() => {
    carica();
  }, [carica]);

  if (!tornei) return <p className="text-gray-500">Caricamento…</p>;
  const attivo = tornei.find((t) => t.id === selezionato);

  return (
    <div className="space-y-6">
      {tornei.length > 0 && (
        <div className={card}>
          <h2 className="font-semibold text-gray-900">Tornei</h2>
          <ul className="mt-2 divide-y divide-gray-100">
            {tornei.map((t) => (
              <li key={t.id}>
                <button type="button" onClick={() => setSelezionato(t.id === selezionato ? null : t.id)}
                  className={clsx("flex w-full flex-wrap items-center justify-between gap-2 py-2.5 text-left text-sm",
                    t.id === selezionato && "font-semibold text-blue-800")}>
                  <span>{formattaData(t.data)} · {t.nome}</span>
                  <span className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="capitalize">{t.livello}</span>
                    <span>{t.partite} partite</span>
                    <span className={clsx("rounded px-1.5 py-0.5", t.concluso ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800")}>
                      {t.concluso ? "Concluso" : "In corso"}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {attivo && (
        <div className={card}>
          <DettaglioTorneo key={attivo.id} torneoId={attivo.id} onCambiato={carica} />
        </div>
      )}

      <NuovoTorneo onCreato={(t) => { carica(); setSelezionato(t.id); }} />
    </div>
  );
}
