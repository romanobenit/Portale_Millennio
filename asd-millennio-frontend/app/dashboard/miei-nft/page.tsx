"use client";

import { useEffect, useState } from "react";
import { getKeycloak } from "@/lib/auth/keycloak";
import { fetchMieiNFT, scaricaCertificato, MioNFT } from "@/lib/api/nft";
import toast from "react-hot-toast";
import { clsx } from "clsx";

const STATO_BADGE: Record<string, { label: string; classes: string }> = {
  mintato: { label: "NFT emesso", classes: "bg-green-100 text-green-800" },
  pagato: { label: "In generazione", classes: "bg-yellow-100 text-yellow-800" },
};

export default function MieiNFTPage() {
  const [nft, setNft] = useState<MioNFT[]>([]);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);
  const [scaricando, setScaricando] = useState<string | null>(null);

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc.token) {
      kc.login();
      return;
    }
    fetchMieiNFT()
      .then(setNft)
      .catch(() => setErrore("Impossibile caricare i tuoi NFT. Riprova più tardi."))
      .finally(() => setLoading(false));
  }, []);

  const scarica = async (id: string) => {
    setScaricando(id);
    try {
      await scaricaCertificato(id);
    } catch {
      toast.error("Certificato non ancora disponibile. Riprova tra qualche istante.");
    } finally {
      setScaricando(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (errore) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
        {errore}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">I miei NFT</h1>
      <p className="text-gray-500 text-sm mb-6">
        Il certificato di sostegno è scaricabile qui e ti viene inviato via email alla conferma del conio.
      </p>

      {nft.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-gray-500 text-sm">Non hai ancora sostenuto il Palasirio.</p>
          <p className="text-gray-400 text-xs mt-2">
            Vai su “Sostieni e scegli ore” per ricevere il tuo titolo d’uso NFT.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {nft.map((n) => {
            const badge = STATO_BADGE[n.stato] ?? { label: n.stato, classes: "bg-gray-100 text-gray-700" };
            return (
              <div key={n.id} className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-semibold text-gray-900">
                        {n.token_id != null ? `NFT #${n.token_id}` : "NFT"}
                      </span>
                      <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full", badge.classes)}>
                        {badge.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">
                      {n.ore_totali} {n.ore_totali === 1 ? "ora" : "ore"} · € {n.importo_eur.toFixed(2)}
                      {n.data_primo_slot && (
                        <span className="text-gray-400"> — dal {n.data_primo_slot}</span>
                      )}
                    </p>
                    {n.mint_tx_hash && (
                      <p className="text-xs text-gray-400 font-mono mt-1 break-all">
                        conio: {n.mint_tx_hash.slice(0, 14)}…{n.mint_tx_hash.slice(-8)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    onClick={() => scarica(n.id)}
                    disabled={!n.certificato_disponibile || scaricando === n.id}
                    className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors"
                  >
                    {scaricando === n.id ? "Preparazione…" : "Scarica certificato PDF"}
                  </button>
                  {n.polygonscan_url && (
                    <a
                      href={n.polygonscan_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      Verifica su Polygonscan
                    </a>
                  )}
                </div>

                {!n.certificato_disponibile && (
                  <p className="text-xs text-amber-600 mt-3">
                    NFT in fase di generazione: il certificato sarà disponibile a breve.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
