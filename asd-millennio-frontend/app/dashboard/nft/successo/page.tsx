"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

function SuccessoContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  return (
    <Card title="Acquisto completato!">
      <div className="space-y-4">
        <p className="text-green-700 font-semibold text-lg">
          Pagamento ricevuto. Il tuo NFT è in fase di generazione.
        </p>
        <p className="text-gray-600 text-sm">
          Riceverai una email con il <strong>certificato di sostegno (PDF)</strong>, il file iCal,
          il Token ID assegnato on-chain e il link per verificare l&apos;NFT su Polygonscan.
          Il processo può richiedere fino a 60 secondi. Il certificato è anche scaricabile dalla
          pagina “Il mio sostegno”.
        </p>
        {sessionId && (
          <p className="text-xs text-gray-400 font-mono">Sessione: {sessionId}</p>
        )}
        <div className="flex gap-3">
          <Link href="/dashboard/miei-nft">
            <Button>Il mio sostegno</Button>
          </Link>
          <Link href="/dashboard/nft">
            <Button variant="secondary">Sostieni ancora</Button>
          </Link>
        </div>
        <p className="text-xs text-gray-500 border-t pt-3">
          Questo token NON è uno strumento finanziario ai sensi della Direttiva MiFID II.
          Rappresenta esclusivamente il diritto d&apos;uso del Palasirio per le fasce orarie specificate.
        </p>
      </div>
    </Card>
  );
}

export default function SuccessoPage() {
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Acquisto NFT</h1>
      <Suspense fallback={<p>Caricamento…</p>}>
        <SuccessoContent />
      </Suspense>
    </div>
  );
}
