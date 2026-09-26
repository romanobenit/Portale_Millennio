"use client";

import { useEffect, useState } from "react";
import { fetchMe, fetchTessereSocio, type Socio, type Tessera } from "@/lib/api/soci";
import { fetchMieiDocumenti, caricaDocumento, type DocumentoResponse } from "@/lib/api/tesseramento";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ConsensiSection } from "@/components/soci/ConsensiSection";
import { CertificatoMedicoBox } from "@/components/soci/CertificatoMedicoBox";
import toast from "react-hot-toast";

const SPORT_LABEL: Record<string, string> = {
  volley: "Pallavolo", badminton: "Badminton", kung_fu: "Kung Fu", pickleball: "Pickleball",
  sostenitore: "Socio Sostenitore",
};

// Variante Badge + etichetta per stato tessera, coerenti con "Le mie tessere".
const STATO_TESSERA: Record<string, { label: string; variant: "green" | "orange" | "gray" | "red" }> = {
  attiva: { label: "Attiva", variant: "green" },
  in_attesa_pagamento: { label: "In attesa pagamento", variant: "orange" },
  bozza: { label: "Bozza", variant: "gray" },
  scaduta: { label: "Scaduta", variant: "red" },
  sospesa: { label: "Sospesa", variant: "orange" },
};

export default function ProfiloPage() {
  const [socio, setSocio] = useState<Socio | null>(null);
  const [tessere, setTessere] = useState<Tessera[]>([]);
  const [documenti, setDocumenti] = useState<DocumentoResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [errore, setErrore] = useState<string | null>(null);

  useEffect(() => {
    // Il layout ha già autenticato — fetchMe usa il token nell'apiClient
    fetchMe()
      .then(async (s) => {
        setSocio(s);
        try {
          setTessere(await fetchTessereSocio(s.id));
        } catch {
          // Non bloccante: il profilo resta visibile anche se le tessere non si caricano.
        }
        try {
          setDocumenti(await fetchMieiDocumenti());
        } catch {
          // Non bloccante: il profilo resta visibile anche se i documenti non si caricano.
        }
      })
      .catch((e: Error) => setErrore(e.message || "Errore di rete. Ricarica la pagina."))
      .finally(() => setLoading(false));
  }, []);

  const documentoIdentita = documenti.find((d) => d.tipo === "identita");

  if (loading) return <p className="text-gray-500">Caricamento profilo…</p>;
  if (errore) return <p className="text-red-600">{errore}</p>;
  if (!socio) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Il mio profilo</h1>

      <Card title="Dati personali">
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div><dt className="text-gray-500">Nome</dt><dd className="font-medium">{socio.nome}</dd></div>
          <div><dt className="text-gray-500">Cognome</dt><dd className="font-medium">{socio.cognome}</dd></div>
          <div><dt className="text-gray-500">Email</dt><dd className="font-medium break-all">{socio.email}</dd></div>
          <div><dt className="text-gray-500">Telefono</dt><dd className="font-medium">{socio.telefono ?? "—"}</dd></div>
          <div><dt className="text-gray-500">Data di nascita</dt><dd className="font-medium">{socio.data_nascita}</dd></div>
        </dl>
      </Card>

      <Card title="Sport">
        <div className="flex flex-wrap gap-2">
          {tessere.length === 0
            ? <p className="text-gray-500 text-sm">Nessuno sport associato</p>
            : tessere.map((t) => {
                const stato = STATO_TESSERA[t.stato] ?? { label: t.stato, variant: "gray" as const };
                return (
                  <Badge key={t.id} variant={stato.variant}>
                    {SPORT_LABEL[t.sport] ?? t.sport} — {stato.label}
                  </Badge>
                );
              })
          }
        </div>
      </Card>

      <Card title="Documenti">
        <div className="space-y-5">
          <div>
            <p className="text-sm font-medium text-gray-800 mb-1">Documento d&apos;identità</p>
            <DocumentoIdentitaBox
              documento={documentoIdentita ?? null}
              onCaricato={(d) => setDocumenti((prev) => [d, ...prev])}
            />
          </div>

          {tessere.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-800 mb-2">Certificato medico</p>
              <div className="space-y-3">
                {tessere.map((t) => (
                  <div key={t.id} className="rounded-lg border border-gray-100 p-3">
                    <p className="text-xs text-gray-500 mb-1">
                      {SPORT_LABEL[t.sport] ?? t.sport}
                      {t.anno_sportivo && <span className="text-gray-400"> — {t.anno_sportivo}</span>}
                    </p>
                    <CertificatoMedicoBox
                      tessera={t}
                      onAggiornato={(aggiornata) =>
                        setTessere((prev) => prev.map((p) => (p.id === aggiornata.id ? aggiornata : p)))
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
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

function DocumentoIdentitaBox({
  documento,
  onCaricato,
}: {
  documento: DocumentoResponse | null;
  onCaricato: (d: DocumentoResponse) => void;
}) {
  const [mostraForm, setMostraForm] = useState(!documento);
  const [file, setFile] = useState<File | null>(null);
  const [caricando, setCaricando] = useState(false);

  const salva = async () => {
    if (!file) {
      toast.error("Seleziona un file.");
      return;
    }
    setCaricando(true);
    try {
      const doc = await caricaDocumento("identita", file);
      toast.success("Documento caricato.");
      onCaricato(doc);
      setMostraForm(false);
      setFile(null);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nel caricamento del documento");
    } finally {
      setCaricando(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs text-gray-600">
          {documento ? (
            <span className="text-gray-800">
              Caricato il {new Date(documento.created_at).toLocaleDateString("it-IT")} ({documento.filename})
            </span>
          ) : (
            <span className="text-gray-400">nessuno caricato</span>
          )}
        </p>
        <button onClick={() => setMostraForm((s) => !s)} className="text-xs text-blue-700 hover:underline">
          {documento ? "Aggiorna documento" : "Carica documento"}
        </button>
      </div>

      {mostraForm && (
        <div className="mt-3 space-y-2 rounded-lg bg-gray-50 p-3">
          <p className="text-xs text-gray-500">Documento d&apos;identità valido (PDF o immagine).</p>
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-xs"
          />
          <button
            onClick={salva}
            disabled={caricando}
            className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors block"
          >
            {caricando ? "Caricamento…" : "Salva documento"}
          </button>
        </div>
      )}
    </div>
  );
}
