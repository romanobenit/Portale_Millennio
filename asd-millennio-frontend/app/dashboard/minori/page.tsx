"use client";

import { useEffect, useState } from "react";
import { getKeycloak } from "@/lib/auth/keycloak";
import type { Socio } from "@/lib/api/soci";
import {
  fetchMieiMinori, aggiungiMinore, caricaDocumento,
  firmaConsensoSocio, avviaTesseramentoMinore, MinoreData,
} from "@/lib/api/tesseramento";
import toast from "react-hot-toast";

const CATEGORIE = [
  { value: "volley", label: "Pallavolo" },
  { value: "badminton", label: "Badminton" },
  { value: "kung_fu", label: "Kung Fu" },
  { value: "pickleball", label: "Pickleball" },
];

export default function MinoriPage() {
  const [minori, setMinori] = useState<Socio[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [nuovo, setNuovo] = useState<MinoreData>({ nome: "", cognome: "", data_nascita: "", codice_fiscale: "", indirizzo: "" });
  const [busy, setBusy] = useState(false);

  const carica = async () => {
    try { setMinori(await fetchMieiMinori()); } catch { /* profilo non ancora creato */ } finally { setLoading(false); }
  };

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc.token) { kc.login(); return; }
    carica();
  }, []);

  const salvaMinore = async () => {
    if (!nuovo.nome || !nuovo.cognome || !nuovo.data_nascita || nuovo.codice_fiscale.length !== 16) {
      toast.error("Compila i dati del minore (codice fiscale di 16 caratteri)."); return;
    }
    setBusy(true);
    try {
      await aggiungiMinore(nuovo);
      toast.success("Minore aggiunto.");
      setShowForm(false);
      setNuovo({ nome: "", cognome: "", data_nascita: "", codice_fiscale: "", indirizzo: "" });
      await carica();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore");
    } finally { setBusy(false); }
  };

  if (loading) return <div className="flex justify-center h-40 items-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-bold text-gray-900">I miei minori</h1>
        <button onClick={() => setShowForm((s) => !s)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
          {showForm ? "Annulla" : "Aggiungi minore"}
        </button>
      </div>
      <p className="text-gray-500 text-sm mb-6">Aggiungi un figlio minorenne e tesseralo. Il pagamento della quota è a tuo carico.</p>

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 mb-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <I label="Nome" v={nuovo.nome} on={(x) => setNuovo({ ...nuovo, nome: x })} />
            <I label="Cognome" v={nuovo.cognome} on={(x) => setNuovo({ ...nuovo, cognome: x })} />
          </div>
          <I label="Data di nascita" type="date" v={nuovo.data_nascita} on={(x) => setNuovo({ ...nuovo, data_nascita: x })} />
          <I label="Codice fiscale" v={nuovo.codice_fiscale} on={(x) => setNuovo({ ...nuovo, codice_fiscale: x.toUpperCase() })} />
          <button onClick={salvaMinore} disabled={busy} className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">Salva minore</button>
        </div>
      )}

      {minori.length === 0 ? (
        <p className="text-gray-500 text-sm">Nessun minore associato.</p>
      ) : (
        <div className="space-y-4">
          {minori.map((m) => <MinoreCard key={m.id} minore={m} />)}
        </div>
      )}
    </div>
  );
}

function MinoreCard({ minore }: { minore: Socio }) {
  const [open, setOpen] = useState(false);
  const [identita, setIdentita] = useState<File | null>(null);
  const [tutela, setTutela] = useState<File | null>(null);
  const [cons, setCons] = useState({ privacy: false, trattamento_dati: false, foto_video: false });
  const [categoria, setCategoria] = useState("volley");
  const [busy, setBusy] = useState(false);

  const tessera = async () => {
    if (!identita || !tutela) { toast.error("Carica documento d'identità e prova della tutela."); return; }
    if (!cons.privacy || !cons.trattamento_dati || !cons.foto_video) { toast.error("Firma tutti e tre i consensi."); return; }
    setBusy(true);
    try {
      await caricaDocumento("identita", identita, minore.id);
      await caricaDocumento("tutela", tutela, minore.id);
      await firmaConsensoSocio(minore.id, "privacy");
      await firmaConsensoSocio(minore.id, "trattamento_dati");
      await firmaConsensoSocio(minore.id, "foto_video");
      const res = await avviaTesseramentoMinore(minore.id, categoria);
      window.location.href = res.stripe_checkout_url;
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nel tesseramento del minore");
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-gray-900">{minore.nome} {minore.cognome}</p>
          <p className="text-xs text-gray-500">Nato il {minore.data_nascita} · CF {minore.codice_fiscale}</p>
        </div>
        <button onClick={() => setOpen((o) => !o)} className="text-sm text-blue-700 hover:underline">{open ? "Chiudi" : "Tessera il minore"}</button>
      </div>

      {open && (
        <div className="mt-4 border-t border-gray-100 pt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Documento d&apos;identità del minore</label>
            <input type="file" accept=".pdf,image/*" onChange={(e) => setIdentita(e.target.files?.[0] ?? null)} className="text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Documento che prova la tutela</label>
            <input type="file" accept=".pdf,image/*" onChange={(e) => setTutela(e.target.files?.[0] ?? null)} className="text-sm" />
          </div>
          <Chk v={cons.privacy} on={(x) => setCons({ ...cons, privacy: x })} label="Informativa privacy (firma del tutore)" />
          <Chk v={cons.trattamento_dati} on={(x) => setCons({ ...cons, trattamento_dati: x })} label="Trattamento dati del minore" />
          <Chk v={cons.foto_video} on={(x) => setCons({ ...cons, foto_video: x })} label="Autorizzazione foto/video per le attività" />
          <div className="flex items-center gap-2">
            <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {CATEGORIE.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <button onClick={tessera} disabled={busy} className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50">
              {busy ? "Attendi…" : "Paga la quota"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function I({ label, v, on, type = "text" }: { label: string; v: string; on: (x: string) => void; type?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input type={type} value={v} onChange={(e) => on(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
    </div>
  );
}

function Chk({ v, on, label }: { v: boolean; on: (x: boolean) => void; label: string }) {
  return (
    <label className="flex items-start gap-2 cursor-pointer">
      <input type="checkbox" checked={v} onChange={(e) => on(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-gray-300" />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
}
