"use client";

import { useState } from "react";
import { verificaAccesso } from "@/lib/api/nft";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function VerificaAccessoPage() {
  const [tokenId, setTokenId] = useState("");
  const [slotKey, setSlotKey] = useState("");
  const [risultato, setRisultato] = useState<{
    valid: boolean;
    socio: string | null;
    slot: Record<string, string> | null;
    checked_at: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);

  const handleVerifica = async () => {
    if (!tokenId || !slotKey) return;
    setLoading(true);
    setErrore(null);
    setRisultato(null);
    try {
      const data = await verificaAccesso(Number(tokenId), slotKey);
      setRisultato(data);
    } catch (e: unknown) {
      setErrore(e instanceof Error ? e.message : "Errore durante la verifica");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Verifica accesso Palasirion</h1>

      <Card title="Inserisci dati NFT">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Token ID</label>
            <input
              type="number"
              value={tokenId}
              onChange={(e) => setTokenId(e.target.value)}
              placeholder="es. 42"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Slot key (es. 2027-03-02_mattina)
            </label>
            <input
              type="text"
              value={slotKey}
              onChange={(e) => setSlotKey(e.target.value)}
              placeholder="YYYY-MM-DD_fascia"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
            />
          </div>
          <Button onClick={handleVerifica} loading={loading} disabled={!tokenId || !slotKey}>
            Verifica accesso
          </Button>
        </div>
      </Card>

      {errore && (
        <Card>
          <p className="text-red-600 font-medium">{errore}</p>
        </Card>
      )}

      {risultato && (
        <Card title="Esito verifica">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Badge variant={risultato.valid ? "green" : "red"}>
                {risultato.valid ? "ACCESSO VALIDO" : "ACCESSO NON VALIDO"}
              </Badge>
            </div>
            {risultato.slot && (
              <div className="text-sm">
                <span className="text-gray-500">Slot:</span>{" "}
                <strong>{risultato.slot.data} — {risultato.slot.fascia}</strong>
              </div>
            )}
            <div className="text-xs text-gray-400">
              Verificato il: {new Date(risultato.checked_at).toLocaleString("it-IT")}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
