"use client";

import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  fetchConsensiSocio,
  firmaConsenso,
  revocaConsenso,
  type Consenso,
} from "@/lib/api/soci";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";

const TIPO_LABEL: Record<Consenso["tipo"], string> = {
  privacy: "Informativa sulla privacy",
  trattamento_dati: "Trattamento dati per attività associativa",
  foto_video: "Riprese fotografiche e video",
  marketing: "Comunicazioni promozionali",
};

const TESTO_CONSENSO: Record<Consenso["tipo"], string> = {
  privacy:
    "Acconsento al trattamento dei miei dati personali ai sensi dell'art. 13 del GDPR (Reg. UE 2016/679) per le finalità indicate nell'informativa sulla privacy di ASD Millennio.",
  trattamento_dati:
    "Autorizzo ASD Millennio al trattamento dei miei dati per l'iscrizione e la gestione delle attività sportive associative.",
  foto_video:
    "Autorizzo ASD Millennio alla ripresa fotografica e video durante le attività sportive e alla loro diffusione sui canali istituzionali dell'associazione.",
  marketing:
    "Acconsento alla ricezione di comunicazioni promozionali e informative da parte di ASD Millennio.",
};

const VERSIONE_TESTO = "v1.0-2026";

const TIPI_OBBLIGATORI: Consenso["tipo"][] = ["privacy", "trattamento_dati"];

interface ConsensiSectionProps {
  socioId: string;
  isMinore?: boolean;
  tutoreId?: string | null;
}

export function ConsensiSection({ socioId, isMinore, tutoreId }: ConsensiSectionProps) {
  const [consensi, setConsensi] = useState<Consenso[]>([]);
  const [loading, setLoading] = useState(true);
  const [firmando, setFirmando] = useState<Consenso["tipo"] | null>(null);
  const [revocando, setRevocando] = useState<string | null>(null);

  const carica = useCallback(async () => {
    try {
      const lista = await fetchConsensiSocio(socioId);
      setConsensi(lista);
    } catch {
      toast.error("Impossibile caricare i consensi");
    } finally {
      setLoading(false);
    }
  }, [socioId]);

  useEffect(() => { carica(); }, [carica]);

  const consensiAttivi = consensi.filter((c) => !c.revocato_at);
  const tipiAttivi = new Set(consensiAttivi.map((c) => c.tipo));
  const tutoreLabel = isMinore ? " (firma del tutore richiesta)" : "";

  const handleFirma = async (tipo: Consenso["tipo"]) => {
    setFirmando(tipo);
    try {
      await firmaConsenso(socioId, {
        tipo,
        testo_versione: VERSIONE_TESTO,
        firmato_da: isMinore && tutoreId ? tutoreId : undefined,
      });
      toast.success("Consenso registrato");
      await carica();
    } catch {
      toast.error("Errore nella firma del consenso");
    } finally {
      setFirmando(null);
    }
  };

  const handleRevoca = async (consenso: Consenso) => {
    setRevocando(consenso.id);
    try {
      await revocaConsenso(socioId, consenso.id);
      toast.success("Consenso revocato");
      await carica();
    } catch {
      toast.error("Errore nella revoca del consenso");
    } finally {
      setRevocando(null);
    }
  };

  if (loading) {
    return (
      <Card title="Consensi GDPR">
        <p className="text-sm text-gray-500">Caricamento…</p>
      </Card>
    );
  }

  const tipiMancanti = (Object.keys(TIPO_LABEL) as Consenso["tipo"][]).filter(
    (t) => !tipiAttivi.has(t)
  );

  return (
    <Card title="Consensi GDPR">
      {isMinore && (
        <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
          Account minorenne — i consensi obbligatori devono essere firmati dal tutore legale.
        </div>
      )}

      {/* Consensi attivi */}
      {consensiAttivi.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
            Consensi attivi
          </p>
          <div className="space-y-2">
            {consensiAttivi.map((c) => (
              <div
                key={c.id}
                className="flex items-start justify-between gap-3 rounded-lg bg-green-50 border border-green-200 p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-green-900">
                    {TIPO_LABEL[c.tipo]}
                    {TIPI_OBBLIGATORI.includes(c.tipo) && (
                      <span className="ml-2 text-xs font-normal text-green-700">(obbligatorio)</span>
                    )}
                  </p>
                  <p className="text-xs text-green-700 mt-0.5">
                    Firmato il{" "}
                    {c.timestamp_firma
                      ? new Date(c.timestamp_firma).toLocaleDateString("it-IT")
                      : "—"}{" "}
                    · versione {c.testo_versione ?? "—"}
                  </p>
                </div>
                <button
                  onClick={() => handleRevoca(c)}
                  disabled={revocando === c.id}
                  className="shrink-0 text-xs text-red-600 hover:text-red-800 disabled:opacity-50"
                >
                  {revocando === c.id ? "Revoca…" : "Revoca"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consensi da firmare */}
      {tipiMancanti.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
            Da firmare{tutoreLabel}
          </p>
          <div className="space-y-3">
            {tipiMancanti.map((tipo) => (
              <div
                key={tipo}
                className={clsx(
                  "rounded-lg border p-3",
                  TIPI_OBBLIGATORI.includes(tipo)
                    ? "border-red-200 bg-red-50"
                    : "border-gray-200 bg-gray-50"
                )}
              >
                <p className="text-sm font-medium text-gray-900">
                  {TIPO_LABEL[tipo]}
                  {TIPI_OBBLIGATORI.includes(tipo) && (
                    <span className="ml-2 text-xs font-semibold text-red-700">OBBLIGATORIO</span>
                  )}
                </p>
                <p className="text-xs text-gray-600 mt-1 mb-3">{TESTO_CONSENSO[tipo]}</p>
                <Button
                  size="sm"
                  onClick={() => handleFirma(tipo)}
                  loading={firmando === tipo}
                  disabled={firmando !== null}
                >
                  Firma consenso
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {consensiAttivi.length > 0 && tipiMancanti.length === 0 && (
        <p className="text-sm text-green-700 font-medium mt-2">
          Tutti i consensi sono stati firmati.
        </p>
      )}

      {/* Storico revocati */}
      {consensi.filter((c) => c.revocato_at).length > 0 && (
        <details className="mt-4">
          <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
            Mostra consensi revocati ({consensi.filter((c) => c.revocato_at).length})
          </summary>
          <div className="mt-2 space-y-1">
            {consensi
              .filter((c) => c.revocato_at)
              .map((c) => (
                <div key={c.id} className="text-xs text-gray-400 pl-2 border-l border-gray-200">
                  {TIPO_LABEL[c.tipo]} — revocato il{" "}
                  {new Date(c.revocato_at!).toLocaleDateString("it-IT")}
                </div>
              ))}
          </div>
        </details>
      )}
    </Card>
  );
}
