"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchDisponibilita,
  fetchCarrello,
  aggiungiAlCarrello,
  checkoutCarrello,
  fetchMiePrenotazioni,
  cancellaPrenotazione,
  GiornoDisponibile,
  PrenotazioneCampo,
} from "@/lib/api/campi";
import { format, addDays } from "date-fns";
import toast from "react-hot-toast";

export default function PrenotazioniPage() {
  const searchParams = useSearchParams();
  const paymentStatus = searchParams.get("status");

  const [disponibilita, setDisponibilita] = useState<GiornoDisponibile[]>([]);
  const [carrello, setCarrello] = useState<PrenotazioneCampo[]>([]);
  const [prenotazioni, setPrenotazioni] = useState<PrenotazioneCampo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pagamento, setPagamento] = useState(false);

  const oggi = format(new Date(), "yyyy-MM-dd");
  const fra60 = format(addDays(new Date(), 60), "yyyy-MM-dd");

  // Caricamento completo (mount + ritorno dal pagamento): è la fonte autorevole
  // iniziale del carrello.
  const caricaDati = async () => {
    try {
      const [disp, cart, mie] = await Promise.all([
        fetchDisponibilita(oggi, fra60),
        fetchCarrello().catch(() => [] as PrenotazioneCampo[]),
        fetchMiePrenotazioni().catch(() => [] as PrenotazioneCampo[]),
      ]);
      setDisponibilita(disp);
      setCarrello(cart);
      setPrenotazioni(mie);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Errore di rete");
    } finally {
      setLoading(false);
    }
  };

  // Riconciliazione in background dopo aggiungi/rimuovi: aggiorna SOLO la
  // disponibilità (conteggio campi liberi) e le prenotazioni confermate.
  // NON tocca il carrello: quello è gestito in modo ottimistico dalle azioni
  // utente, così due refetch in corsa non possono sovrascriverlo con una
  // fotografia stale del server (race che faceva "sparire" le prenotazioni).
  const ricaricaDisponibilita = async () => {
    try {
      const [disp, mie] = await Promise.all([
        fetchDisponibilita(oggi, fra60),
        fetchMiePrenotazioni().catch(() => [] as PrenotazioneCampo[]),
      ]);
      setDisponibilita(disp);
      setPrenotazioni(mie);
    } catch {
      /* i conteggi si aggiorneranno al prossimo caricamento completo */
    }
  };

  useEffect(() => {
    caricaDati();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const giorni = useMemo(() => {
    const m = new Map<string, GiornoDisponibile[]>();
    for (const s of disponibilita) {
      const arr = m.get(s.data) ?? [];
      arr.push(s);
      m.set(s.data, arr);
    }
    for (const arr of m.values()) arr.sort((a, b) => a.ora_inizio.localeCompare(b.ora_inizio));
    return Array.from(m.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [disponibilita]);

  // Quante ore ho nel carrello per ciascuno slot (data + ora), per mostrarlo nella griglia.
  const carrelloPerSlot = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of carrello) {
      const k = c.data + c.ora_inizio.slice(0, 5);
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [carrello]);

  const totaleCarrello = useMemo(
    () => carrello.reduce((s, c) => s + Number(c.importo_eur), 0),
    [carrello],
  );

  const aggiungi = async (s: GiornoDisponibile) => {
    setBusy(s.template_id + s.data + s.ora_inizio);
    try {
      const creata = await aggiungiAlCarrello(s.template_id, s.data, s.ora_inizio);
      // Feedback immediato: aggiorna subito il carrello (badge sullo slot + riga)
      // e mostra un toast, senza attendere il refetch completo della disponibilità
      // (loop server-side su 60 giorni → lento). I conteggi si riconciliano dopo.
      setCarrello((prev) => [...prev, creata]);
      toast.success(`Aggiunta al carrello · ${formattaOra(creata.ora_inizio)}`);
      ricaricaDisponibilita();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nell'aggiunta");
    } finally {
      setBusy(null);
    }
  };

  const rimuovi = async (id: string) => {
    const backup = carrello;
    // Rimozione ottimistica: la riga sparisce subito dal carrello.
    setCarrello((prev) => prev.filter((c) => c.id !== id));
    try {
      await cancellaPrenotazione(id);
      toast.success("Rimossa dal carrello");
      ricaricaDisponibilita();
    } catch (e: unknown) {
      setCarrello(backup); // ripristina in caso di errore
      toast.error(e instanceof Error ? e.message : "Errore nella rimozione");
    }
  };

  const paga = async () => {
    setPagamento(true);
    try {
      const res = await checkoutCarrello();
      window.location.href = res.stripe_checkout_url;
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Errore nel pagamento");
      setPagamento(false);
    }
  };

  const cancellaConfermata = async (id: string) => {
    if (!confirm("Sei sicuro di voler cancellare questa prenotazione confermata?")) return;
    try {
      await cancellaPrenotazione(id);
      await caricaDati();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Errore nella cancellazione");
    }
  };

  const formattaOra = (t: string) => t.slice(0, 5);
  const formattaData = (d: string) =>
    new Date(d + "T12:00:00").toLocaleDateString("it-IT", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Prenota un campo</h1>
        <p className="text-gray-500 text-sm mt-1">
          Aggiungi le ore che vuoi al carrello e paga tutto in un&apos;unica volta alla fine.
        </p>
      </div>

      {paymentStatus === "success" && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-green-800 text-sm">
          Pagamento completato. Le tue prenotazioni sono state confermate.
        </div>
      )}
      {paymentStatus === "cancel" && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4 text-yellow-800 text-sm">
          Pagamento annullato. Le ore restano nel carrello finché non scade il blocco.
        </div>
      )}

      {/* ── Carrello ─────────────────────────────────────────────────────── */}
      {carrello.length > 0 && (
        <section className="rounded-xl border-2 border-blue-200 bg-blue-50/40 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">
              Carrello · {carrello.length} {carrello.length === 1 ? "ora" : "ore"}
            </h2>
            <span className="text-xs text-orange-600">
              Bloccate per 30 min: se non paghi vengono rilasciate
            </span>
          </div>

          <div className="space-y-2">
            {carrello.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-blue-100 bg-white px-4 py-2.5"
              >
                <div className="text-sm">
                  <span className="font-medium text-gray-900 capitalize">{formattaData(c.data)}</span>
                  <span className="text-gray-600">
                    {" · "}{formattaOra(c.ora_inizio)}–{formattaOra(c.ora_fine)} · Campo {c.campo}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-gray-800">€{c.importo_eur}</span>
                  <button
                    onClick={() => rimuovi(c.id)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Rimuovi
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Totale: <span className="text-lg font-bold text-gray-900">€{totaleCarrello.toFixed(2)}</span>
            </div>
            <button
              onClick={paga}
              disabled={pagamento}
              className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors"
            >
              {pagamento ? "Reindirizzamento…" : `Paga tutto — €${totaleCarrello.toFixed(2)}`}
            </button>
          </div>
        </section>
      )}

      {/* ── Prenotazioni confermate ──────────────────────────────────────── */}
      {prenotazioni.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Le mie prenotazioni confermate</h2>
          <div className="space-y-2">
            {prenotazioni.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <div>
                  <p className="font-medium text-gray-900 text-sm capitalize">
                    {formattaData(p.data)} · {formattaOra(p.ora_inizio)}–{formattaOra(p.ora_fine)} · Campo {p.campo}
                  </p>
                  <p className="text-xs text-green-700 font-medium">Confermata · €{p.importo_eur}</p>
                </div>
                <button
                  onClick={() => cancellaConfermata(p.id)}
                  className="text-xs text-red-600 hover:text-red-800"
                >
                  Cancella
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Disponibilità per ora ────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">Disponibilità prossimi 60 giorni</h2>
          <div className="hidden sm:flex items-center gap-3 text-xs text-gray-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded bg-blue-100 border border-blue-300" /> libero
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded bg-emerald-500" /> nel carrello
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded bg-gray-100 border border-gray-200" /> esaurito
            </span>
          </div>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm py-8">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            Caricamento disponibilità…
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-800 text-sm">{error}</div>
        )}

        {!loading && !error && giorni.length === 0 && (
          <p className="text-gray-500 text-sm">Nessuna fascia prenotabile nei prossimi 60 giorni.</p>
        )}

        {!loading && !error && giorni.length > 0 && (
          <div className="grid gap-3 lg:grid-cols-2">
            {giorni.map(([data, slots]) => (
              <div key={data} className="rounded-xl border border-gray-200 bg-white p-4">
                <div className="flex items-baseline justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 text-sm capitalize">{formattaData(data)}</h3>
                  <span className="text-xs text-gray-500">
                    {slots[0].sport.join(" / ")} · €{slots[0].costo_ora}/ora
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {slots.map((s) => {
                    const nelCarrello = carrelloPerSlot.get(s.data + formattaOra(s.ora_inizio)) ?? 0;
                    const free = s.campi_disponibili > 0;
                    const adding = busy === s.template_id + s.data + s.ora_inizio;
                    return (
                      <button
                        key={s.ora_inizio}
                        disabled={!free || !!busy}
                        onClick={() => aggiungi(s)}
                        title={
                          free
                            ? `${s.campi_disponibili}/${s.campi_totali} campi liberi · €${s.importo_totale} — clicca per aggiungere`
                            : "Esaurito"
                        }
                        className={`relative flex flex-col items-center rounded-lg border px-3 py-1.5 min-w-[64px] transition
                          ${
                            nelCarrello > 0
                              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                              : free
                                ? "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-300"
                                : "border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed"
                          }
                          ${busy && !adding ? "opacity-50" : ""}`}
                      >
                        {nelCarrello > 0 && (
                          <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-white">
                            {nelCarrello}
                          </span>
                        )}
                        <span className="font-semibold text-sm tabular-nums">
                          {adding ? "…" : formattaOra(s.ora_inizio)}
                        </span>
                        <span className="text-[10px] leading-tight">
                          {free ? `${s.campi_disponibili} liberi` : "pieno"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
