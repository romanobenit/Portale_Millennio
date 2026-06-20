"use client";

import { useEffect, useState } from "react";
import { fetchMe, type Socio } from "@/lib/api/soci";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ConsensiSection } from "@/components/soci/ConsensiSection";

export default function ProfiloPage() {
  const [socio, setSocio] = useState<Socio | null>(null);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);

  useEffect(() => {
    // Il layout ha già autenticato — fetchMe usa il token nell'apiClient
    fetchMe()
      .then(setSocio)
      .catch((e: Error) => setErrore(e.message || "Errore di rete. Ricarica la pagina."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Caricamento profilo…</p>;
  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!socio) return null;

  const SPORT_LABEL: Record<string, string> = {
    volley: "Pallavolo", badminton: "Badminton", kung_fu: "Kung Fu", pickleball: "Pickleball",
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Il mio profilo</h1>

      <Card title="Dati personali">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div><dt className="text-gray-500">Nome</dt><dd className="font-medium">{socio.nome}</dd></div>
          <div><dt className="text-gray-500">Cognome</dt><dd className="font-medium">{socio.cognome}</dd></div>
          <div><dt className="text-gray-500">Email</dt><dd className="font-medium">{socio.email}</dd></div>
          <div><dt className="text-gray-500">Telefono</dt><dd className="font-medium">{socio.telefono ?? "—"}</dd></div>
          <div><dt className="text-gray-500">Data di nascita</dt><dd className="font-medium">{socio.data_nascita}</dd></div>
        </dl>
      </Card>

      <Card title="Sport">
        <div className="flex flex-wrap gap-2">
          {socio.sport.length === 0
            ? <p className="text-gray-500 text-sm">Nessuno sport associato</p>
            : socio.sport.map((s) => (
                <Badge key={s} variant="blue">{SPORT_LABEL[s] ?? s}</Badge>
              ))
          }
        </div>
      </Card>

      {socio.is_minor && (
        <Card>
          <p className="text-sm text-amber-700 font-medium">
            Account minorenne — le operazioni richiedono l&apos;autorizzazione del tutore legale.
          </p>
        </Card>
      )}

      <ConsensiSection
        socioId={socio.id}
        isMinore={socio.is_minor}
        tutoreId={socio.tutore_id}
      />
    </div>
  );
}
