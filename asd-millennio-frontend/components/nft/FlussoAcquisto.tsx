"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { avviaAcquistoNFT } from "@/lib/api/nft";
import type { RiepilogoSelezione } from "@/lib/api/calendario";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Socio } from "@/lib/api/soci";
import { MinoreSelector } from "@/components/soci/MinoreSelector";

interface FlussoAcquistoProps {
  riepilogo: RiepilogoSelezione;
  onAnnulla: () => void;
  minori?: Socio[];
}

export function FlussoAcquisto({ riepilogo, onAnnulla, minori = [] }: FlussoAcquistoProps) {
  const [loading, setLoading] = useState(false);
  const [accettaDisclaimer, setAccettaDisclaimer] = useState(false);
  const [acquistaPerMinore, setAcquistaPerMinore] = useState(false);
  const [minoreSelezionato, setMinoreSelezionato] = useState<string | null>(null);

  const nOre = riepilogo.ore_notte + riepilogo.ore_mattina + riepilogo.ore_pomeriggio;

  const handleProcedi = async () => {
    if (!accettaDisclaimer) {
      toast.error("Devi accettare la dichiarazione legale per procedere");
      return;
    }
    if (acquistaPerMinore && !minoreSelezionato) {
      toast.error("Seleziona il minorenne per cui stai acquistando");
      return;
    }
    setLoading(true);
    try {
      const resp = await avviaAcquistoNFT({
        selezione: riepilogo.selezione,
        acquisto_per_minore: acquistaPerMinore,
        minore_id: acquistaPerMinore ? (minoreSelezionato ?? undefined) : undefined,
      });
      window.location.href = resp.stripe_checkout_url;
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Errore durante l&apos;avvio del pagamento");
      setLoading(false);
    }
  };

  return (
    <Card title="Conferma acquisto NFT">
      <div className="space-y-4">
        <div className="rounded-lg bg-blue-50 p-4 text-sm text-blue-900">
          <p className="font-semibold mb-3">Riepilogo ordine — {nOre} ore totali</p>
          <div className="space-y-2">
            {riepilogo.dettaglio.map((d, i) => (
              <div key={i} className="flex justify-between text-xs">
                <span>
                  {d.data} — <span className="capitalize">{d.fascia}</span>{" "}
                  (ore {d.ore_selezionate.join(", ")}) × €{d.prezzo_ora.toFixed(2)}/h
                  {(d.moltiplicatore_data * d.moltiplicatore_scarsita) > 1.005 && (
                    <span className="text-orange-600 ml-1">×{(d.moltiplicatore_data * d.moltiplicatore_scarsita).toFixed(2)}</span>
                  )}
                </span>
                <span className="font-semibold">€{d.costo_slot.toFixed(2)}</span>
              </div>
            ))}
            <div className="border-t border-blue-200 pt-2 mt-2 flex justify-between font-bold text-base">
              <span>Totale</span>
              <span>€{riepilogo.costo_totale.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4 text-sm text-yellow-900">
          <p className="font-semibold mb-1">Dichiarazione legale obbligatoria</p>
          <p>
            Questo token <strong>NON è uno strumento finanziario</strong> ai sensi della Direttiva MiFID II.
            Rappresenta esclusivamente il diritto d&apos;uso del Palasirion per le ore specificate.
            Non garantisce rendimenti economici. Il token è personale e non trasferibile.
          </p>
        </div>

        <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 text-sm text-gray-700">
          <p className="font-semibold mb-1">Politica rimborsi</p>
          <p>
            Il token è <strong>non rimborsabile</strong> per scelta del socio.
            Rimborso previsto solo in caso di cancellazione da parte dell&apos;ASD.
          </p>
        </div>

        <MinoreSelector
          minori={minori}
          acquistaPerMinore={acquistaPerMinore}
          minoreSelezionato={minoreSelezionato}
          onToggle={setAcquistaPerMinore}
          onSeleziona={setMinoreSelezionato}
        />

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={accettaDisclaimer}
            onChange={(e) => setAccettaDisclaimer(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">
            Ho letto e accetto la dichiarazione legale. Comprendo che il token non è uno strumento
            finanziario e non garantisce rendimenti economici.
          </span>
        </label>

        <div className="flex gap-3 pt-2">
          <Button onClick={handleProcedi} loading={loading} disabled={!accettaDisclaimer}>
            Procedi al pagamento — €{riepilogo.costo_totale.toFixed(2)}
          </Button>
          <Button variant="secondary" onClick={onAnnulla} disabled={loading}>
            Annulla
          </Button>
        </div>
      </div>
    </Card>
  );
}
