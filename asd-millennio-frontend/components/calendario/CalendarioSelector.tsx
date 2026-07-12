"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { format, addDays, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import toast from "react-hot-toast";

import {
  fetchDisponibilita,
  lockSelezione,
  type RiepilogoSelezione,
  type SlotDisponibilita,
} from "@/lib/api/calendario";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface CalendarioSelectorProps {
  onProcedi: (riepilogo: RiepilogoSelezione) => void;
  tessera_attiva: boolean;
  autenticato: boolean;
}

// Chiave univoca per una singola ora selezionata: "slot_id::12"
type OraKey = string;

const CALENDARIO_INIZIO = process.env.NEXT_PUBLIC_CALENDARIO_INIZIO ?? "2027-01-01";
const CALENDARIO_FINE   = process.env.NEXT_PUBLIC_CALENDARIO_FINE   ?? "2040-12-31";

const GIORNI_IT = ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"];
const FASCIA_COLOR: Record<string, string> = {
  notte: "indigo",
  mattina: "blue",
  pomeriggio: "violet",
};

function oraKey(slotId: string, h: number): OraKey {
  return `${slotId}::${h}`;
}

export function CalendarioSelector({ onProcedi, tessera_attiva, autenticato }: CalendarioSelectorProps) {
  const [slots, setSlots] = useState<SlotDisponibilita[]>([]);
  const [selezionate, setSelezionate] = useState<Set<OraKey>>(new Set());
  const [loading, setLoading] = useState(true);
  const [lockLoading, setLockLoading] = useState(false);

  const [dataInizio, setDataInizio] = useState(() => {
    const oggi = format(new Date(), "yyyy-MM-dd");
    return oggi < CALENDARIO_INIZIO ? CALENDARIO_INIZIO : oggi;
  });
  const [filtroFascia, setFiltroFascia] = useState<string>("");
  const [filtroPeriodo, setFiltroPeriodo] = useState<"tutti" | "pari" | "dispari">("tutti");

  const carica = useCallback(async () => {
    setLoading(true);
    try {
      const raw_fine = format(addDays(parseISO(dataInizio), 90), "yyyy-MM-dd");
      const data_fine = raw_fine > CALENDARIO_FINE ? CALENDARIO_FINE : raw_fine;
      const items = await fetchDisponibilita({ data_inizio: dataInizio, data_fine });
      setSlots(items);
    } catch {
      toast.error("Impossibile caricare il calendario");
    } finally {
      setLoading(false);
    }
  }, [dataInizio]);

  useEffect(() => { carica(); }, [carica]);

  // Filtra slot
  const slotFiltrati = useMemo(() => {
    return slots.filter((s) => {
      if (filtroFascia && s.fascia !== filtroFascia) return false;
      const giorno = parseISO(s.data);
      const d = giorno.getDate();
      if (filtroPeriodo === "pari" && d % 2 !== 0) return false;
      if (filtroPeriodo === "dispari" && d % 2 === 0) return false;
      return true;
    });
  }, [slots, filtroFascia, filtroPeriodo]);

  // Raggruppa per data
  const perData = useMemo(() => {
    const acc: Record<string, SlotDisponibilita[]> = {};
    for (const s of slotFiltrati) {
      (acc[s.data] ??= []).push(s);
    }
    return acc;
  }, [slotFiltrati]);

  // Riepilogo selezione corrente (calcolato lato client per anteprima veloce)
  const riepilogoLocale = useMemo(() => {
    const ore: Record<string, number> = { notte: 0, mattina: 0, pomeriggio: 0 };
    let costo = 0;
    for (const s of slots) {
      for (const h of s.ore_libere) {
        if (selezionate.has(oraKey(s.slot_id, h))) {
          ore[s.fascia] += 1;
          costo += s.prezzo_ora;
        }
      }
    }
    return { ore, costo };
  }, [selezionate, slots]);

  const nOreSelezionate = Object.values(riepilogoLocale.ore).reduce((a, b) => a + b, 0);

  // Toggle singola ora
  const toggleOra = useCallback((slotId: string, h: number) => {
    const key = oraKey(slotId, h);
    setSelezionate((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Seleziona/deseleziona tutta una fascia per un giorno
  const toggleFasciaGiorno = useCallback((slot: SlotDisponibilita) => {
    setSelezionate((prev) => {
      const next = new Set(prev);
      const oreLibere = slot.ore_libere;
      const tutteSelezionate = oreLibere.every((h) => next.has(oraKey(slot.slot_id, h)));
      if (tutteSelezionate) {
        oreLibere.forEach((h) => next.delete(oraKey(slot.slot_id, h)));
      } else {
        oreLibere.forEach((h) => next.add(oraKey(slot.slot_id, h)));
      }
      return next;
    });
  }, []);

  const handleProcedi = async () => {
    if (!autenticato) { toast.error("Accedi per acquistare"); return; }
    if (!tessera_attiva) { toast.error("Tessera non attiva"); return; }
    if (nOreSelezionate === 0) { toast.error("Seleziona almeno un'ora"); return; }

    // Costruisci la struttura selezione per il backend
    const selMap: Record<string, number[]> = {};
    for (const key of selezionate) {
      const [slotId, hStr] = key.split("::");
      (selMap[slotId] ??= []).push(Number(hStr));
    }
    const selezione = Object.entries(selMap).map(([slot_id, ore]) => ({ slot_id, ore: ore.sort((a, b) => a - b) }));

    setLockLoading(true);
    try {
      const riepilogo = await lockSelezione(selezione);
      onProcedi(riepilogo);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        toast.error(axiosErr.response?.data?.detail ?? "Errore durante il lock delle ore");
      } else {
        toast.error("Errore durante la prenotazione");
      }
      // Ricarica per aggiornare disponibilità
      await carica();
      // Deseleziona ore che potrebbero essere diventate non disponibili
      setSelezionate(new Set());
    } finally {
      setLockLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* ── Filtri ─────────────────────────────────────────────── */}
      <Card title="Filtri calendario">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Da data</label>
            <input
              type="date"
              value={dataInizio}
              min={CALENDARIO_INIZIO}
              max={CALENDARIO_FINE}
              onChange={(e) => setDataInizio(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Fascia</label>
            <select
              value={filtroFascia}
              onChange={(e) => setFiltroFascia(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            >
              <option value="">Tutte</option>
              <option value="notte">Notte</option>
              <option value="mattina">Mattina</option>
              <option value="pomeriggio">Pomeriggio</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Periodo</label>
            <select
              value={filtroPeriodo}
              onChange={(e) => setFiltroPeriodo(e.target.value as typeof filtroPeriodo)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            >
              <option value="tutti">Tutto l&apos;anno</option>
              <option value="pari">Giorni pari</option>
              <option value="dispari">Giorni dispari</option>
            </select>
          </div>
          <Button size="sm" variant="secondary" onClick={() => setSelezionate(new Set())}>
            Deseleziona tutto
          </Button>
        </div>
        {/* Legenda */}
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-blue-400 inline-block" /> Libera — clicca per selezionare</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-blue-200 ring-2 ring-blue-500 inline-block" /> Selezionata</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-green-500 inline-block" /> Già venduta</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-orange-400 inline-block" /> In acquisto da altri</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-gray-300 inline-block" /> Non vendibile</span>
        </div>
      </Card>

      {/* ── Griglia calendario ─────────────────────────────────── */}
      {loading ? (
        <div className="py-16 text-center text-gray-400">Caricamento calendario…</div>
      ) : Object.keys(perData).length === 0 ? (
        <div className="py-16 text-center text-gray-400">
          <p className="text-lg font-medium">Nessuno slot disponibile in questo periodo</p>
          <p className="text-sm mt-1">
            {dataInizio < CALENDARIO_INIZIO
              ? `La vendita inizia il ${new Date(CALENDARIO_INIZIO).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })}`
              : "Prova a modificare il filtro data o la fascia oraria"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(perData)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([dataStr, daySlots]) => {
              const giorno = parseISO(dataStr);
              const ggStr = GIORNI_IT[giorno.getDay()];
              return (
                <Card key={dataStr}>
                  <h3 className="mb-3 text-sm font-bold text-gray-700 uppercase tracking-wide">
                    {ggStr} — {format(giorno, "d MMMM yyyy", { locale: it })}
                  </h3>
                  <div className="space-y-3">
                    {daySlots
                      .sort((a, b) => a.ora_inizio.localeCompare(b.ora_inizio))
                      .map((slot) => (
                        <FasciaRow
                          key={slot.slot_id}
                          slot={slot}
                          selezionate={selezionate}
                          onToggleOra={toggleOra}
                          onToggleFascia={toggleFasciaGiorno}
                        />
                      ))}
                  </div>
                </Card>
              );
            })}
        </div>
      )}

      {/* ── Riepilogo + CTA ────────────────────────────────────── */}
      <div className="sticky bottom-4">
        <Card title={`Riepilogo — ${nOreSelezionate} ore selezionate`}>
          {nOreSelezionate === 0 ? (
            <p className="text-sm text-gray-400">Seleziona le ore del Palasirio che vuoi acquistare come NFT</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-sm">
              {(["notte", "mattina", "pomeriggio"] as const).map((f) =>
                riepilogoLocale.ore[f] > 0 ? (
                  <div key={f} className="rounded-lg bg-gray-50 px-3 py-2">
                    <div className="text-xs text-gray-500 capitalize">{f}</div>
                    <div className="font-bold">{riepilogoLocale.ore[f]} ore</div>
                  </div>
                ) : null
              )}
              <div className="rounded-lg bg-blue-50 px-3 py-2">
                <div className="text-xs text-blue-600">Totale stimato*</div>
                <div className="font-bold text-blue-800 text-lg">€{riepilogoLocale.costo.toFixed(2)}</div>
              </div>
            </div>
          )}
          <p className="text-xs text-gray-400 mb-3">
            * Il prezzo definitivo viene confermato al momento del lock — può variare per aggiornamenti di disponibilità.
          </p>
          <div className="flex flex-col sm:flex-row items-start gap-3">
            <div title={
              !autenticato ? "Accedi per acquistare" :
              !tessera_attiva ? "Tessera non attiva" :
              nOreSelezionate === 0 ? "Seleziona almeno un'ora" : ""
            }>
              <Button
                onClick={handleProcedi}
                loading={lockLoading}
                disabled={!autenticato || !tessera_attiva || nOreSelezionate === 0}
                size="lg"
              >
                Ricevi il titolo di utilizzo — {nOreSelezionate} ore
              </Button>
            </div>
            {(!autenticato || !tessera_attiva) && (
              <p className="text-sm text-amber-600 self-center">
                {!autenticato ? "Accedi per acquistare" : "Tessera non attiva — rinnova la tessera per procedere"}
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Componente riga fascia ─────────────────────────────────────────────────────

interface FasciaRowProps {
  slot: SlotDisponibilita;
  selezionate: Set<OraKey>;
  onToggleOra: (slotId: string, h: number) => void;
  onToggleFascia: (slot: SlotDisponibilita) => void;
}

function FasciaRow({ slot, selezionate, onToggleOra, onToggleFascia }: FasciaRowProps) {
  const color = FASCIA_COLOR[slot.fascia] ?? "blue";
  const hInizio = parseInt(slot.ora_inizio.split(":")[0], 10);
  const tutteLeOre = Array.from({ length: slot.ore_totali }, (_, i) => hInizio + i);

  const oreLibere = new Set(slot.ore_libere);
  const oreVendute = new Set(slot.ore_vendute);
  const oreInLock = new Set(slot.ore_in_lock);

  const libereSelezionate = slot.ore_libere.filter((h) => selezionate.has(oraKey(slot.slot_id, h)));
  const tutteSelezionate = slot.ore_libere.length > 0 && libereSelezionate.length === slot.ore_libere.length;

  const moltiplicatoreLabel = (() => {
    const tot = slot.moltiplicatore_data * slot.moltiplicatore_scarsita;
    if (Math.abs(tot - 1) < 0.005) return null;
    return `×${tot.toFixed(2)}`;
  })();

  return (
    <div className="flex items-center gap-3">
      {/* Header fascia */}
      <div className="w-28 shrink-0">
        <button
          onClick={() => slot.ore_libere.length > 0 && onToggleFascia(slot)}
          disabled={slot.ore_libere.length === 0}
          className={`w-full text-left rounded-lg px-2 py-1.5 text-xs font-semibold transition
            ${slot.ore_libere.length === 0
              ? "text-gray-400 cursor-default"
              : tutteSelezionate
                ? `bg-${color}-100 text-${color}-800 ring-1 ring-${color}-400`
                : `text-${color}-700 hover:bg-${color}-50`
            }`}
        >
          <div className="capitalize">{slot.fascia}</div>
          <div className="font-normal text-gray-500">€{slot.prezzo_ora.toFixed(0)}/h</div>
          {moltiplicatoreLabel && (
            <div className="text-orange-500 font-bold">{moltiplicatoreLabel}</div>
          )}
          {slot.sconto_promo_pct > 0 && (
            <div className="text-green-600">-{slot.sconto_promo_pct.toFixed(0)}%</div>
          )}
        </button>
      </div>

      {/* Celle orarie */}
      <div className="flex flex-wrap gap-1">
        {tutteLeOre.map((h) => {
          const key = oraKey(slot.slot_id, h);
          const venduta = oreVendute.has(h);
          const inLock = oreInLock.has(h);
          const libera = oreLibere.has(h);
          const sel = selezionate.has(key);

          let cls = "w-9 h-9 text-xs rounded font-medium transition-all ";
          let title = `${h}:00`;
          if (venduta) {
            cls += "bg-green-500 text-white cursor-not-allowed";
            title += " — già venduta";
          } else if (inLock) {
            cls += "bg-orange-400 text-white cursor-not-allowed";
            title += " — in acquisto da altri";
          } else if (libera && sel) {
            cls += `bg-${color}-500 text-white ring-2 ring-offset-1 ring-${color}-600 cursor-pointer`;
            title += " — selezionata";
          } else if (libera) {
            cls += `bg-${color}-100 text-${color}-800 hover:bg-${color}-300 cursor-pointer`;
          } else {
            cls += "bg-gray-100 text-gray-400 cursor-not-allowed";
            title += " — non vendibile";
          }

          return (
            <button
              key={h}
              title={title}
              disabled={!libera}
              onClick={() => libera && onToggleOra(slot.slot_id, h)}
              className={cls}
            >
              {h}
            </button>
          );
        })}
      </div>

      {/* Badge ore selezionate in questa fascia */}
      {libereSelezionate.length > 0 && (
        <span className={`shrink-0 text-xs font-semibold text-${color}-700 bg-${color}-50 px-2 py-0.5 rounded-full`}>
          {libereSelezionate.length}h — €{(libereSelezionate.length * slot.prezzo_ora).toFixed(2)}
        </span>
      )}
    </div>
  );
}
