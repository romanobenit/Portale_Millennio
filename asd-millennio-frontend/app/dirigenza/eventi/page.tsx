"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { addDays, format, subDays } from "date-fns";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { ContatorePresenze } from "@/components/eventi/ContatorePresenze";
import { Locandina } from "@/components/eventi/Locandina";
import {
  aggiornaEvento,
  aggiungiPartecipante,
  annullaEvento,
  azzeraAssenze,
  caricaLocandina,
  cercaSoci,
  creaEvento,
  etichettaSport,
  fetchEventiDirigenza,
  fetchEventoDettaglio,
  formattaDataEvento,
  formattaOra,
  formattaPrezzo,
  impostaPresenzeManuali,
  motivoNonPrenotabile,
  rimuoviLocandina,
  segnaPrenotazione,
  type EventoDettaglio,
  type EventoDirigenza,
  type EventoInput,
  type Partecipante,
  type SocioRicerca,
} from "@/lib/api/eventi";

const SPORT = [
  { value: "pickleball", label: "Pickleball" },
  { value: "badminton", label: "Badminton" },
  { value: "volley", label: "Pallavolo" },
  { value: "kung_fu", label: "Kung Fu" },
];

const input = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm";
const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";

interface FormEvento {
  titolo: string;
  sport: string[];
  data: string;
  ora_inizio: string;
  ora_fine: string;
  prezzo_eur: string;
  posti_max: string;
  note: string;
}

const FORM_VUOTO: FormEvento = {
  titolo: "",
  sport: ["pickleball", "badminton"],
  data: format(addDays(new Date(), 1), "yyyy-MM-dd"),
  ora_inizio: "18:30",
  ora_fine: "20:30",
  prezzo_eur: "5",
  posti_max: "16",
  note: "",
};

function formDaEvento(ev: EventoDirigenza): FormEvento {
  return {
    titolo: ev.titolo ?? "",
    sport: ev.sport,
    data: ev.data,
    ora_inizio: formattaOra(ev.ora_inizio),
    ora_fine: formattaOra(ev.ora_fine),
    prezzo_eur: String(Number(ev.prezzo_eur)),
    posti_max: String(ev.posti_max),
    note: ev.note ?? "",
  };
}

export default function EventiDirigenzaPage() {
  const [eventi, setEventi] = useState<EventoDirigenza[]>([]);
  const [loading, setLoading] = useState(true);
  const [mostraPassati, setMostraPassati] = useState(false);
  const [form, setForm] = useState<FormEvento | null>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [aperto, setAperto] = useState<string | null>(null);

  const carica = useCallback(async () => {
    const oggi = new Date();
    const da = format(mostraPassati ? subDays(oggi, 60) : oggi, "yyyy-MM-dd");
    const a = format(addDays(oggi, 180), "yyyy-MM-dd");
    try {
      setEventi(await fetchEventiDirigenza(da, a));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Impossibile caricare gli eventi");
    } finally {
      setLoading(false);
    }
  }, [mostraPassati]);

  useEffect(() => {
    carica();
  }, [carica]);

  const salva = async () => {
    if (!form) return;
    if (form.sport.length === 0) {
      toast.error("Seleziona almeno uno sport");
      return;
    }
    const payload: EventoInput = {
      titolo: form.titolo.trim() || null,
      sport: form.sport,
      data: form.data,
      ora_inizio: form.ora_inizio,
      ora_fine: form.ora_fine,
      prezzo_eur: Number(form.prezzo_eur),
      posti_max: Number(form.posti_max),
      note: form.note.trim() || null,
    };
    setSalvando(true);
    try {
      if (editId) {
        await aggiornaEvento(editId, payload);
        toast.success("Evento aggiornato");
      } else {
        await creaEvento(payload);
        toast.success("Evento creato: è già visibile in home");
      }
      setForm(null);
      setEditId(null);
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Salvataggio non riuscito");
    } finally {
      setSalvando(false);
    }
  };

  const annulla = async (ev: EventoDirigenza) => {
    const msg =
      `Annullare l'evento di ${formattaDataEvento(ev.data)}?\n\n` +
      "I pagamenti online verranno rimborsati e i partecipanti avvisati via email. L'operazione non si può annullare.";
    if (!window.confirm(msg)) return;
    try {
      await annullaEvento(ev.id);
      toast.success("Evento annullato");
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Annullamento non riuscito");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Eventi campi</h1>
          <p className="mt-1 text-sm text-gray-500">
            Programma le finestre di gioco al Palasirio: chi partecipa paga l&apos;ingresso per tutta la durata.
          </p>
        </div>
        <button
          onClick={() => {
            setEditId(null);
            setForm(FORM_VUOTO);
          }}
          className={clsx(btnPrimario, "self-start whitespace-nowrap sm:self-auto")}
        >
          + Nuovo evento
        </button>
      </div>

      {form && (
        <div className="space-y-4 rounded-xl border border-blue-200 bg-blue-50/40 p-4 sm:p-5">
          <h2 className="text-lg font-semibold text-gray-900">{editId ? "Modifica evento" : "Nuovo evento"}</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-xs font-medium text-gray-700">Titolo (facoltativo)</span>
              <input
                className={input}
                value={form.titolo}
                maxLength={120}
                placeholder="es. Serata pickleball"
                onChange={(e) => setForm({ ...form, titolo: e.target.value })}
              />
            </label>
            <fieldset className="sm:col-span-2">
              <legend className="mb-1 text-xs font-medium text-gray-700">Sport</legend>
              <div className="flex flex-wrap gap-3">
                {SPORT.map((s) => (
                  <label key={s.value} className="inline-flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={form.sport.includes(s.value)}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          sport: e.target.checked
                            ? [...form.sport, s.value]
                            : form.sport.filter((x) => x !== s.value),
                        })
                      }
                    />
                    {s.label}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-700">Data</span>
              <input type="date" className={input} value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-gray-700">Inizio</span>
                <input type="time" className={input} value={form.ora_inizio} onChange={(e) => setForm({ ...form, ora_inizio: e.target.value })} />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-gray-700">Fine</span>
                <input type="time" className={input} value={form.ora_fine} onChange={(e) => setForm({ ...form, ora_fine: e.target.value })} />
              </label>
            </div>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-700">Prezzo ingresso (€)</span>
              <input
                type="number"
                min={0}
                step="0.50"
                className={input}
                value={form.prezzo_eur}
                onChange={(e) => setForm({ ...form, prezzo_eur: e.target.value })}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-700">Posti massimi</span>
              <input
                type="number"
                min={1}
                className={input}
                value={form.posti_max}
                onChange={(e) => setForm({ ...form, posti_max: e.target.value })}
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-xs font-medium text-gray-700">Note (visibili solo alla dirigenza)</span>
              <textarea className={input} rows={2} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={salva} disabled={salvando} className={btnPrimario}>
              {salvando ? "Salvataggio…" : editId ? "Salva modifiche" : "Crea evento"}
            </button>
            <button
              onClick={() => {
                setForm(null);
                setEditId(null);
              }}
              className={btnSecondario}
            >
              Chiudi
            </button>
          </div>
        </div>
      )}

      <label className="inline-flex items-center gap-2 text-sm text-gray-600">
        <input type="checkbox" checked={mostraPassati} onChange={(e) => setMostraPassati(e.target.checked)} />
        Mostra anche gli eventi degli ultimi 60 giorni
      </label>

      {loading ? (
        <p className="text-sm text-gray-500">Caricamento…</p>
      ) : eventi.length === 0 ? (
        <p className="text-sm text-gray-500">Nessun evento nel periodo. Crea il primo con «+ Nuovo evento».</p>
      ) : (
        <div className="space-y-3">
          {eventi.map((ev) => (
            <div
              key={ev.id}
              className={clsx("rounded-xl border bg-white", ev.stato === "annullato" ? "border-gray-200 opacity-60" : "border-gray-200")}
            >
              <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold capitalize text-gray-900">
                    {formattaDataEvento(ev.data)}
                    {ev.stato === "annullato" && (
                      <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium normal-case text-red-700">
                        Annullato
                      </span>
                    )}
                  </p>
                  <p className="text-sm text-gray-600">
                    {formattaOra(ev.ora_inizio)}–{formattaOra(ev.ora_fine)} · {etichettaSport(ev.sport)} · {formattaPrezzo(ev.prezzo_eur)}
                  </p>
                  {ev.titolo && <p className="text-sm text-gray-500">{ev.titolo}</p>}
                  <p className="mt-1 text-xs text-gray-500">
                    Online {ev.confermati_online} · In sede {ev.confermati_in_sede} · Manuali {ev.presenze_manuali}
                  </p>
                  {ev.stato === "programmato" ? (
                    <GestioneLocandina ev={ev} onCambio={carica} />
                  ) : (
                    ev.locandina_url && (
                      <Locandina url={ev.locandina_url} titolo={ev.titolo} className="mt-3 h-24 w-16 rounded-md" />
                    )
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <ContatorePresenze
                    partecipanti={ev.partecipanti}
                    postiMax={ev.posti_max}
                    inListaAttesa={ev.in_lista_attesa}
                    completo={ev.completo}
                  />
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => setAperto(aperto === ev.id ? null : ev.id)} className={btnSecondario}>
                      {aperto === ev.id ? "Chiudi" : "Partecipanti"}
                    </button>
                    {ev.stato === "programmato" && (
                      <>
                        <button
                          onClick={() => {
                            setEditId(ev.id);
                            setForm(formDaEvento(ev));
                            window.scrollTo({ top: 0, behavior: "smooth" });
                          }}
                          className={btnSecondario}
                        >
                          Modifica
                        </button>
                        <button onClick={() => annulla(ev)} className="px-2 text-sm font-medium text-red-600 hover:text-red-800">
                          Annulla evento
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
              {aperto === ev.id && <DettaglioEvento eventoId={ev.id} onCambio={carica} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Locandina mostrata in home e nella pagina prenotazioni dei soci. */
function GestioneLocandina({ ev, onCambio }: { ev: EventoDirigenza; onCambio: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const esegui = async (azione: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try {
      await azione();
      toast.success(ok);
      onCambio();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  return (
    <div className="mt-3 flex items-center gap-3">
      {ev.locandina_url && <Locandina url={ev.locandina_url} titolo={ev.titolo} className="h-24 w-16 rounded-md" />}
      <div className="flex flex-col items-start gap-1">
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) esegui(() => caricaLocandina(ev.id, file), "Locandina pubblicata");
          }}
        />
        <button type="button" disabled={busy} onClick={() => input.current?.click()} className={btnSecondario}>
          {busy ? "Caricamento…" : ev.locandina_url ? "Cambia locandina" : "Aggiungi locandina"}
        </button>
        {ev.locandina_url ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => window.confirm("Togliere la locandina?") && esegui(() => rimuoviLocandina(ev.id), "Locandina rimossa")}
            className="text-xs font-medium text-red-600 hover:text-red-800 disabled:opacity-50"
          >
            Togli
          </button>
        ) : (
          <span className="text-xs text-gray-500">JPG, PNG o WebP · compare in home e nelle prenotazioni</span>
        )}
      </div>
    </div>
  );
}

function DettaglioEvento({ eventoId, onCambio }: { eventoId: string; onCambio: () => void }) {
  const [dett, setDett] = useState<EventoDettaglio | null>(null);
  const [manuali, setManuali] = useState("0");
  const [busy, setBusy] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      const d = await fetchEventoDettaglio(eventoId);
      setDett(d);
      setManuali(String(d.evento.presenze_manuali));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Impossibile caricare i partecipanti");
    }
  }, [eventoId]);

  useEffect(() => {
    carica();
  }, [carica]);

  const esegui = async (chiave: string, azione: () => Promise<unknown>, ok?: string) => {
    setBusy(chiave);
    try {
      await azione();
      if (ok) toast.success(ok);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setBusy(null);
      await carica();
      onCambio();
    }
  };

  if (!dett) return <p className="border-t border-gray-100 p-4 text-sm text-gray-500">Caricamento partecipanti…</p>;
  const ev = dett.evento;
  const attivo = ev.stato === "programmato";

  return (
    <div className="space-y-5 border-t border-gray-100 bg-gray-50/60 p-4">
      {attivo && (
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-gray-700">Presenze aggiunte a mano</span>
            <input
              type="number"
              min={0}
              value={manuali}
              onChange={(e) => setManuali(e.target.value)}
              className="w-28 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            />
          </label>
          <button
            disabled={busy === "manuali" || Number(manuali) === ev.presenze_manuali}
            onClick={() => esegui("manuali", () => impostaPresenzeManuali(ev.id, Number(manuali)), "Contatore aggiornato")}
            className={btnSecondario}
          >
            Aggiorna contatore
          </button>
          <p className="w-full text-xs text-gray-500">
            Per chi entra senza aver prenotato. Le prenotazioni (online e in sede) sono già contate in automatico.
          </p>
        </div>
      )}

      {attivo && <AggiungiPartecipante eventoId={ev.id} dataEvento={ev.data} onAggiunto={() => esegui("add", async () => undefined)} />}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-gray-900">Partecipanti prenotati ({dett.partecipanti.length})</h3>
        {dett.partecipanti.length === 0 ? (
          <p className="text-sm text-gray-500">Nessuna prenotazione.</p>
        ) : (
          <ul className="space-y-2">
            {dett.partecipanti.map((p) => (
              <RigaPartecipante key={p.prenotazione_id} p={p} busy={busy} esegui={esegui} />
            ))}
          </ul>
        )}
      </div>

      {dett.lista_attesa.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-900">Lista d&apos;attesa ({dett.lista_attesa.length})</h3>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-700">
            {dett.lista_attesa.map((a) => (
              <li key={a.socio_id}>
                {a.cognome} {a.nome}
                {a.notificato_at && <span className="ml-2 text-xs text-gray-500">avvisato del posto libero</span>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function RigaPartecipante({
  p,
  busy,
  esegui,
}: {
  p: Partecipante;
  busy: string | null;
  esegui: (chiave: string, azione: () => Promise<unknown>, ok?: string) => Promise<void>;
}) {
  const occupato = busy === p.prenotazione_id;
  const inSede = p.modalita === "in_sede";
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="font-medium text-gray-900">
          {p.cognome} {p.nome}
        </p>
        <p className="text-xs text-gray-500">
          {p.stato === "in_attesa_pagamento"
            ? "Sta pagando online (posto trattenuto)"
            : inSede
              ? `Paga in sede · ${formattaPrezzo(p.importo_eur)}`
              : `Pagato online · ${formattaPrezzo(p.importo_eur)}`}
          {p.inserita_da_staff && " · inserito dalla segreteria"}
        </p>
        {p.assenze > 0 && (
          <p className={clsx("text-xs font-medium", p.solo_online ? "text-red-700" : "text-amber-700")}>
            {p.assenze} {p.assenze === 1 ? "assenza" : "assenze"} senza disdetta
            {p.solo_online && " · può prenotare solo online"}{" "}
            <button
              disabled={occupato}
              onClick={() => {
                if (window.confirm(`Azzerare le assenze di ${p.nome} ${p.cognome}?`)) {
                  esegui(p.prenotazione_id, () => azzeraAssenze(p.socio_id), "Assenze azzerate");
                }
              }}
              className="ml-1 underline hover:no-underline"
            >
              Azzera
            </button>
          </p>
        )}
      </div>
      {p.stato === "confermata" && (
        <div className="flex flex-wrap items-center gap-2">
          {inSede && (
            <label className="inline-flex items-center gap-1.5 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={p.pagato_in_sede}
                disabled={occupato}
                onChange={(e) =>
                  esegui(p.prenotazione_id, () =>
                    segnaPrenotazione(
                      p.prenotazione_id,
                      e.target.checked ? { pagato_in_sede: true, presenza: "presente" } : { pagato_in_sede: false },
                    ),
                  )
                }
              />
              Pagato
            </label>
          )}
          <button
            disabled={occupato}
            onClick={() =>
              esegui(p.prenotazione_id, () =>
                segnaPrenotazione(p.prenotazione_id, { presenza: p.presenza === "presente" ? null : "presente" }),
              )
            }
            className={clsx(
              "rounded-lg border px-2.5 py-1 text-xs font-semibold",
              p.presenza === "presente" ? "border-green-600 bg-green-600 text-white" : "border-gray-300 text-gray-700",
            )}
          >
            Presente
          </button>
          {inSede && (
            <button
              disabled={occupato || p.pagato_in_sede}
              onClick={() =>
                esegui(p.prenotazione_id, () =>
                  segnaPrenotazione(p.prenotazione_id, { presenza: p.presenza === "assente" ? null : "assente" }),
                )
              }
              className={clsx(
                "rounded-lg border px-2.5 py-1 text-xs font-semibold disabled:opacity-40",
                p.presenza === "assente" ? "border-red-600 bg-red-600 text-white" : "border-gray-300 text-gray-700",
              )}
            >
              Non presentato
            </button>
          )}
        </div>
      )}
    </li>
  );
}

function AggiungiPartecipante({
  eventoId,
  dataEvento,
  onAggiunto,
}: {
  eventoId: string;
  dataEvento: string;
  onAggiunto: () => void;
}) {
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState<SocioRicerca[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setRisultati([]);
      return;
    }
    const t = setTimeout(() => {
      cercaSoci(q.trim())
        .then(setRisultati)
        .catch(() => setRisultati([]));
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const aggiungi = async (s: SocioRicerca) => {
    setBusy(s.id);
    try {
      await aggiungiPartecipante(eventoId, s.id);
      toast.success(`${s.nome} ${s.cognome} aggiunto (paga in sede)`);
      setQ("");
      onAggiunto();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Impossibile aggiungere");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-gray-700">Prenota per un associato (paga in sede)</span>
        <input
          className={input}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Cerca per nome, cognome, codice fiscale o email"
        />
      </label>
      {risultati.length > 0 && (
        <ul className="mt-2 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {risultati.map((s) => {
            const motivo = motivoNonPrenotabile(s.abilitato_fino_al, dataEvento)
              ? s.abilitato_fino_al
                ? "Tessera non valida per questa data"
                : "Né tessera Millennio né iscrizione community"
              : s.solo_online
                ? `${s.assenze} assenze: solo online`
                : null;
            return (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <div className="min-w-0 text-sm">
                  <span className="font-medium text-gray-900">
                    {s.cognome} {s.nome}
                  </span>
                  <span className="ml-2 font-mono text-xs text-gray-500">{s.codice_fiscale}</span>
                  {motivo && <span className="ml-2 text-xs text-red-600">{motivo}</span>}
                </div>
                <button disabled={!!motivo || busy === s.id} onClick={() => aggiungi(s)} className={btnSecondario}>
                  {busy === s.id ? "Attendi…" : "Aggiungi"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
