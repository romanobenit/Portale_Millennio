"use client";

import { useState, useEffect } from "react";
import { getKeycloak } from "@/lib/auth/keycloak";
import { fetchMe, fetchMinoriSocio, type Socio, type Tessera } from "@/lib/api/soci";
import { apiClient } from "@/lib/api/client";
import { CalendarioSelector } from "@/components/calendario/CalendarioSelector";
import { FlussoAcquisto } from "@/components/nft/FlussoAcquisto";
import type { RiepilogoSelezione } from "@/lib/api/calendario";

type Step = "calendario" | "conferma";

export default function AcquistoNFTPage() {
  const [step, setStep] = useState<Step>("calendario");
  const [riepilogo, setRiepilogo] = useState<RiepilogoSelezione | null>(null);
  const [autenticato, setAutenticato] = useState(false);
  const [tesseraAttiva, setTesseraAttiva] = useState(false);
  const [minori, setMinori] = useState<Socio[]>([]);

  useEffect(() => {
    const kc = getKeycloak();
    const auth = !!kc.token;
    setAutenticato(auth);
    if (!auth) return;

    fetchMe()
      .then(async (socio) => {
        const [tessereResp, minoriResp] = await Promise.all([
          apiClient.get<Tessera[]>(`/soci/${socio.id}/tessere`, { params: { stato: "attiva" } }),
          fetchMinoriSocio(socio.id).catch(() => [] as Socio[]),
        ]);
        setTesseraAttiva(tessereResp.data.length > 0);
        setMinori(minoriResp);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Sostieni il progetto Palasirio — Ricevi le tue ore di utilizzo</h1>
      <p className="text-gray-600 text-sm">
        Seleziona le ore del Palasirio (lun–ven, 00:00–14:59 fino al 2043) che vuoi associare al tuo contributo.
      </p>

      {step === "calendario" && (
        <CalendarioSelector
          onProcedi={(r) => { setRiepilogo(r); setStep("conferma"); }}
          tessera_attiva={tesseraAttiva}
          autenticato={autenticato}
        />
      )}

      {step === "conferma" && riepilogo && (
        <FlussoAcquisto
          riepilogo={riepilogo}
          onAnnulla={() => setStep("calendario")}
          minori={minori}
        />
      )}
    </div>
  );
}
