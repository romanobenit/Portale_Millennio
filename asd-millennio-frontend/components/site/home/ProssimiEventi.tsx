"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Section, SectionHeading } from "@/components/site/Section";
import { ContatorePresenze } from "@/components/eventi/ContatorePresenze";
import { portalLinks } from "@/lib/site";
import {
  etichettaSport,
  fetchProssimiEventi,
  formattaDataEvento,
  formattaOra,
  formattaPrezzo,
  type EventoPubblico,
} from "@/lib/api/eventi";

/** Home: evento più vicino in evidenza + elenco degli altri eventi programmati. */
export function ProssimiEventi() {
  const [eventi, setEventi] = useState<EventoPubblico[] | null>(null);
  const [errore, setErrore] = useState(false);

  useEffect(() => {
    fetchProssimiEventi()
      .then(setEventi)
      .catch(() => setErrore(true));
  }, []);

  const [primo, ...altri] = eventi ?? [];

  return (
    <Section id="eventi" muted>
      <SectionHeading
        eyebrow="Palasirio"
        title="Prossimi eventi"
        subtitle="Vieni a giocare a pickleball e badminton: l'ingresso vale per tutto l'evento, arriva quando vuoi."
      />

      <div className="mt-10">
        {eventi === null && !errore && (
          <div className="mx-auto h-48 max-w-3xl animate-pulse rounded-2xl bg-slate-200" aria-label="Caricamento eventi" />
        )}

        {(errore || (eventi !== null && eventi.length === 0)) && (
          <p className="text-center text-slate-600">
            Nessun evento in programma al momento: i prossimi verranno pubblicati qui.
          </p>
        )}

        {primo && (
          <article className="mx-auto max-w-3xl overflow-hidden rounded-2xl bg-gradient-to-br from-accent-500 to-brand-600 text-white shadow-lg">
            <div className="flex flex-col gap-6 p-6 sm:flex-row sm:items-end sm:justify-between sm:p-8">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wider text-white/80">Il prossimo evento</p>
                <h3 className="mt-2 font-display text-2xl font-bold capitalize sm:text-3xl">
                  {formattaDataEvento(primo.data)}
                </h3>
                <p className="mt-1 text-lg">
                  {formattaOra(primo.ora_inizio)}–{formattaOra(primo.ora_fine)} · {etichettaSport(primo.sport)}
                </p>
                {primo.titolo && <p className="mt-1 text-white/90">{primo.titolo}</p>}
                <p className="mt-3 text-sm text-white/90">Ingresso {formattaPrezzo(primo.prezzo_eur)}</p>
              </div>
              <div className="flex flex-col gap-4 sm:items-end">
                <ContatorePresenze
                  partecipanti={primo.partecipanti}
                  postiMax={primo.posti_max}
                  inListaAttesa={primo.in_lista_attesa}
                  completo={primo.completo}
                  tono="scuro"
                />
                <Link
                  href={portalLinks.prenotaCampo}
                  className="rounded-lg bg-white px-5 py-2.5 text-center text-sm font-semibold text-brand-700 shadow-sm transition-colors hover:bg-brand-50"
                >
                  {primo.completo ? "Mettiti in lista d'attesa" : "Prenota"}
                </Link>
              </div>
            </div>
          </article>
        )}

        {altri.length > 0 && (
          <ul className="mx-auto mt-6 max-w-3xl divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {altri.map((ev) => (
              <li key={ev.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                <div className="min-w-0">
                  <p className="font-semibold capitalize text-slate-900">{formattaDataEvento(ev.data)}</p>
                  <p className="text-sm text-slate-600">
                    {formattaOra(ev.ora_inizio)}–{formattaOra(ev.ora_fine)} · {etichettaSport(ev.sport)} ·{" "}
                    {formattaPrezzo(ev.prezzo_eur)}
                  </p>
                  {ev.titolo && <p className="text-sm text-slate-500">{ev.titolo}</p>}
                </div>
                <div className="flex items-center gap-4 sm:shrink-0">
                  <ContatorePresenze
                    partecipanti={ev.partecipanti}
                    postiMax={ev.posti_max}
                    inListaAttesa={ev.in_lista_attesa}
                    completo={ev.completo}
                  />
                  <Link
                    href={portalLinks.prenotaCampo}
                    className="whitespace-nowrap rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-accent-600"
                  >
                    {ev.completo ? "Lista d'attesa" : "Prenota"}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Section>
  );
}
