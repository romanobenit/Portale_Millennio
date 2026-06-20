"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getKeycloak } from "@/lib/auth/keycloak";
import {
  fetchDisponibilita,
  fetchMiePrenotazioni,
  prenota,
  cancellaPrenotazione,
  GiornoDisponibile,
  PrenotazioneCampo,
} from "@/lib/api/campi";
import { format, addDays } from "date-fns";

export default function PrenotazioniPage() {
  const searchParams = useSearchParams();
  const paymentStatus = searchParams.get("status");

  const [disponibilita, setDisponibilita] = useState<GiornoDisponibile[]>([]);
  const [prenotazioni, setPrenotazioni] = useState<PrenotazioneCampo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPren, setLoadingPren] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prenotando, setPrenotando] = useState<string | null>(null);

  const oggi = format(new Date(), "yyyy-MM-dd");
  const fra60 = format(addDays(new Date(), 60), "yyyy-MM-dd");

  const token = () => getKeycloak().token ?? "";

  const caricaDati = async () => {
    try {
      const [disp, mie] = await Promise.all([
        fetchDisponibilita(oggi, fra60),
        fetchMiePrenotazioni(token()),
      ]);
      setDisponibilita(disp);
      setPrenotazioni(mie);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Errore di rete");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    caricaDati();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePrenota = async (slot: GiornoDisponibile) => {
    setPrenotando(slot.template_id + slot.data);
    try {
      const res = await prenota(token(), slot.template_id, slot.data);
      window.location.href = res.stripe_checkout_url;
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Errore nella prenotazione");
      setPrenotando(null);
    }
  };

  const handleCancella = async (id: string) => {
    if (!confirm("Sei sicuro di voler cancellare questa prenotazione?")) return;
    setLoadingPren(true);
    try {
      await cancellaPrenotazione(token(), id);
      await caricaDati();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Errore nella cancellazione");
    } finally {
      setLoadingPren(false);
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
          Badminton e pickleball · 4 campi disponibili · €30/ora
        </p>
      </div>

      {paymentStatus === "success" && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-green-800 text-sm">
          Pagamento completato. La tua prenotazione è stata confermata.
        </div>
      )}
      {paymentStatus === "cancel" && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4 text-yellow-800 text-sm">
          Pagamento annullato. La prenotazione è stata rilasciata.
        </div>
      )}

      {/* Le mie prenotazioni */}
      {prenotazioni.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Le mie prenotazioni</h2>
          <div className="space-y-2">
            {prenotazioni.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
              >
                <div>
                  <p className="font-medium text-gray-900 text-sm">
                    {formattaData(p.data)} · Campo {p.campo}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formattaOra(p.ora_inizio)}–{formattaOra(p.ora_fine)} ·{" "}
                    <span
                      className={
                        p.stato === "confermata"
                          ? "text-green-700 font-medium"
                          : "text-orange-600 font-medium"
                      }
                    >
                      {p.stato === "confermata" ? "Confermata" : "In attesa di pagamento"}
                    </span>
                    {" · "}€{p.importo_eur}
                  </p>
                </div>
                {p.stato === "confermata" && (
                  <button
                    onClick={() => handleCancella(p.id)}
                    disabled={loadingPren}
                    className="text-xs text-red-600 hover:text-red-800 disabled:opacity-50"
                  >
                    Cancella
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Disponibilità */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          Disponibilità prossimi 60 giorni
        </h2>

        {loading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm py-8">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            Caricamento disponibilità…
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-800 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && disponibilita.length === 0 && (
          <p className="text-gray-500 text-sm">Nessun campo disponibile nei prossimi 60 giorni.</p>
        )}

        {!loading && !error && disponibilita.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {disponibilita.map((slot) => {
              const key = slot.template_id + slot.data;
              const isLoading = prenotando === key;
              return (
                <div
                  key={key}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm flex flex-col gap-3"
                >
                  <div>
                    <p className="font-semibold text-gray-900 text-sm capitalize">
                      {formattaData(slot.data)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formattaOra(slot.ora_inizio)}–{formattaOra(slot.ora_fine)} ·{" "}
                      {slot.sport.join(" / ")}
                    </p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      {slot.campi_disponibili}/{slot.campi_totali} campi liberi
                    </span>
                    <span className="text-sm font-semibold text-blue-700">
                      €{slot.importo_totale}
                    </span>
                  </div>
                  <button
                    onClick={() => handlePrenota(slot)}
                    disabled={!!prenotando}
                    className="w-full rounded-lg bg-blue-700 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50 transition-colors"
                  >
                    {isLoading ? "Reindirizzamento…" : "Prenota"}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
