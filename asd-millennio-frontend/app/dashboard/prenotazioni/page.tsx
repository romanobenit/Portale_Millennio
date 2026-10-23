"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import { clsx } from "clsx";
import { ContatorePresenze } from "@/components/eventi/ContatorePresenze";
import {
  annullaPrenotazioneEvento,
  esciListaAttesa,
  etichettaSport,
  fetchMieiEventi,
  fetchProssimiEventi,
  formattaDataEvento,
  formattaOra,
  formattaPrezzo,
  iscriviListaAttesa,
  prenotaEvento,
  type EventoPubblico,
  type MiaPrenotazione,
  type MieiEventi,
  type Modalita,
} from "@/lib/api/eventi";

const btnPrimario =
  "rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors";
const btnSecondario =
  "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-50 transition-colors";

function statoPrenotazione(p: MiaPrenotazione): { label: string; classes: string } {
  if (p.stato === "in_attesa_pagamento") return { label: "Pagamento da completare", classes: "bg-yellow-100 text-yellow-800" };
  if (p.modalita === "in_sede") {
    return p.pagato_in_sede
      ? { label: "Pagata in sede", classes: "bg-green-100 text-green-800" }
      : { label: "Da pagare in sede", classes: "bg-blue-100 text-blue-800" };
  }
  return { label: "Pagata online", classes: "bg-green-100 text-green-800" };
}

export default function PrenotaEventiPage() {
  const searchParams = useSearchParams();
  const paymentStatus = searchParams.get("status");

  const [eventi, setEventi] = useState<EventoPubblico[]>([]);
  const [miei, setMiei] = useState<MieiEventi | null>(null);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      const [ev, mie] = await Promise.all([fetchProssimiEventi(), fetchMieiEventi()]);
      setEventi(ev);
      setMiei(mie);
      setErrore(null);
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore di rete");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carica();
  }, [carica]);

  const esegui = async (chiave: string, azione: () => Promise<void>) => {
    setBusy(chiave);
    try {
      await azione();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally {
      setBusy(null);
      await carica();
    }
  };

  const prenota = (ev: EventoPubblico, modalita: Modalita) =>
    esegui(`${ev.id}-${modalita}`, async () => {
      const res = await prenotaEvento(ev.id, modalita);
      if (res.stripe_checkout_url) {
        window.location.href = res.stripe_checkout_url;
        return;
      }
      toast.success(
        modalita === "in_sede"
          ? "Prenotato! Pagherai all'ingresso. Se non puoi venire, annulla entro il giorno prima."
          : "Prenotazione confermata.",
      );
    });

  const completaPagamento = (p: MiaPrenotazione) =>
    esegui(`pay-${p.id}`, async () => {
      const res = await prenotaEvento(p.evento_id, "online");
      if (res.stripe_checkout_url) window.location.href = res.stripe_checkout_url;
    });

  const annulla = (p: MiaPrenotazione) => {
    const msg =
      p.stato === "confermata" && p.modalita === "online" && Number(p.importo_eur) > 0
        ? "Annullare la prenotazione? Riceverai il rimborso dell'importo pagato."
        : "Annullare la prenotazione?";
    if (!window.confirm(msg)) return;
    esegui(`del-${p.id}`, async () => {
      await annullaPrenotazioneEvento(p.id);
      toast.success("Prenotazione annullata.");
    });
  };

  const listaAttesa = (ev: EventoPubblico, entra: boolean) =>
    esegui(`wait-${ev.id}`, async () => {
      if (entra) {
        await iscriviListaAttesa(ev.id);
        toast.success("Sei in lista d'attesa: ti avvisiamo via email se si libera un posto.");
      } else {
        await esciListaAttesa(ev.id);
      }
    });

  if (loading) return <p className="text-gray-500">Caricamento eventi…</p>;

  const prenotatoPer = new Map((miei?.prenotazioni ?? []).map((p) => [p.evento_id, p]));
  const inAttesa = new Set(miei?.lista_attesa ?? []);
  const puoInSede = !!miei?.tessera_attiva && !miei?.solo_online;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Prenota presenza</h1>
        <p className="mt-1 text-sm text-gray-500">
          L&apos;ingresso vale per tutta la durata dell&apos;evento: arriva quando vuoi e gioca quanto vuoi.
        </p>
      </div>

      {paymentStatus === "success" && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Pagamento completato: la prenotazione è confermata (se non la vedi ancora, aggiorna tra qualche secondo).
        </div>
      )}
      {paymentStatus === "cancel" && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
          Pagamento annullato: il posto resta riservato per qualche minuto, poi torna libero.
        </div>
      )}
      {errore && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{errore}</div>}

      {miei?.solo_online && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Hai {miei.assenze} assenze su prenotazioni da pagare in sede: per ora puoi prenotare solo pagando online.
          Per lo sblocco rivolgiti alla dirigenza.
        </div>
      )}

      {miei && miei.prenotazioni.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-gray-800">Le mie prenotazioni</h2>
          <div className="space-y-2">
            {miei.prenotazioni.map((p) => {
              const badge = statoPrenotazione(p);
              return (
                <div
                  key={p.id}
                  className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="font-medium capitalize text-gray-900">{formattaDataEvento(p.evento.data)}</p>
                    <p className="text-sm text-gray-600">
                      {formattaOra(p.evento.ora_inizio)}–{formattaOra(p.evento.ora_fine)} · {etichettaSport(p.evento.sport)} ·{" "}
                      {formattaPrezzo(p.importo_eur)}
                    </p>
                    <span className={clsx("mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium", badge.classes)}>
                      {badge.label}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {p.stato === "in_attesa_pagamento" && (
                      <button onClick={() => completaPagamento(p)} disabled={!!busy} className={btnPrimario}>
                        {busy === `pay-${p.id}` ? "Attendi…" : "Completa il pagamento"}
                      </button>
                    )}
                    {p.annullabile ? (
                      <button
                        onClick={() => annulla(p)}
                        disabled={!!busy}
                        className="text-sm font-medium text-red-600 hover:text-red-800 disabled:opacity-50"
                      >
                        {busy === `del-${p.id}` ? "Annullamento…" : "Annulla"}
                      </button>
                    ) : (
                      <span className="text-xs text-gray-400">Non più annullabile</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Si può annullare fino al giorno prima dell&apos;evento; chi ha pagato online riceve il rimborso.
          </p>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Eventi in programma</h2>
        {eventi.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun evento in programma al momento.</p>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {eventi.map((ev) => {
              const mia = prenotatoPer.get(ev.id);
              return (
                <div key={ev.id} className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold capitalize text-gray-900">{formattaDataEvento(ev.data)}</p>
                      <p className="text-sm text-gray-600">
                        {formattaOra(ev.ora_inizio)}–{formattaOra(ev.ora_fine)} · {etichettaSport(ev.sport)}
                      </p>
                      {ev.titolo && <p className="text-sm text-gray-500">{ev.titolo}</p>}
                      <p className="mt-1 text-sm font-semibold text-gray-800">Ingresso {formattaPrezzo(ev.prezzo_eur)}</p>
                    </div>
                    <ContatorePresenze
                      partecipanti={ev.partecipanti}
                      postiMax={ev.posti_max}
                      inListaAttesa={ev.in_lista_attesa}
                      completo={ev.completo}
                    />
                  </div>

                  {mia ? (
                    mia.stato === "confermata" ? (
                      <p className="text-sm font-medium text-green-700">Sei prenotato per questo evento.</p>
                    ) : (
                      <p className="text-sm font-medium text-yellow-700">
                        Pagamento da completare: trovi il pulsante in «Le mie prenotazioni».
                      </p>
                    )
                  ) : ev.completo ? (
                    inAttesa.has(ev.id) ? (
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm font-medium text-amber-700">Sei in lista d&apos;attesa</span>
                        <button onClick={() => listaAttesa(ev, false)} disabled={!!busy} className={btnSecondario}>
                          Esci dalla lista
                        </button>
                      </div>
                    ) : (
                      <button onClick={() => listaAttesa(ev, true)} disabled={!!busy} className={btnSecondario}>
                        {busy === `wait-${ev.id}` ? "Attendi…" : "Mettiti in lista d'attesa"}
                      </button>
                    )
                  ) : (
                    <div className="space-y-2">
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <button onClick={() => prenota(ev, "online")} disabled={!!busy} className={btnPrimario}>
                          {busy === `${ev.id}-online` ? "Attendi…" : `Paga online · ${formattaPrezzo(ev.prezzo_eur)}`}
                        </button>
                        <button
                          onClick={() => prenota(ev, "in_sede")}
                          disabled={!!busy || !puoInSede}
                          className={btnSecondario}
                        >
                          {busy === `${ev.id}-in_sede` ? "Attendi…" : "Pago in sede"}
                        </button>
                      </div>
                      {!puoInSede && (
                        <p className="text-xs text-gray-500">
                          {miei?.solo_online
                            ? "Pagamento in sede non disponibile per le assenze registrate."
                            : "Il pagamento in sede è riservato ai soci con tessera attiva."}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
